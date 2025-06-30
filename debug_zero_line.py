#!/usr/bin/env python3
"""
ゼロライン検出デバッグツール
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

def debug_zero_line(image_path):
    """ゼロライン検出をデバッグ"""
    img = cv2.imread(image_path)
    if img is None:
        print(f"画像読み込みエラー: {image_path}")
        return
    
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    print(f"\n画像: {os.path.basename(image_path)}")
    print(f"サイズ: {width}x{height}")
    
    mid_y = height // 2
    print(f"中央Y: {mid_y}")
    
    # 検索範囲の行を分析
    print("\n検索範囲の分析:")
    candidates = []
    
    for y in range(mid_y - 50, mid_y + 50):
        if y < 0 or y >= height:
            continue
        
        row = gray[y, :]
        mean_val = np.mean(row)
        std_val = np.std(row)
        
        # 暗い線の候補
        if mean_val < 150:  # 閾値を緩和
            candidates.append({
                'y': y,
                'mean': mean_val,
                'std': std_val,
                'score': (150 - mean_val) * (1 - std_val/128)
            })
    
    # 候補をスコアでソート
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    print("\nゼロライン候補（上位10）:")
    for i, cand in enumerate(candidates[:10]):
        print(f"  {i+1}. Y={cand['y']}, 平均={cand['mean']:.1f}, 標準偏差={cand['std']:.1f}, スコア={cand['score']:.1f}")
    
    # 実際のゼロライン（固定値として正しい位置を仮定）
    # 画像が597x500で、中央が250なら、実際のゼロラインは...
    actual_zero_y = 250  # 現在の検出値
    adjusted_zero_y = 240  # 提案される調整値（10px上）
    
    # 可視化
    plt.figure(figsize=(15, 10))
    
    # 1. 元画像
    plt.subplot(2, 2, 1)
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.axhline(y=actual_zero_y, color='red', linestyle='--', label='現在の検出')
    plt.axhline(y=adjusted_zero_y, color='green', linestyle='-', label='調整後')
    plt.title('元画像とゼロライン')
    plt.legend()
    
    # 2. グレースケール
    plt.subplot(2, 2, 2)
    plt.imshow(gray, cmap='gray')
    plt.axhline(y=actual_zero_y, color='red', linestyle='--')
    plt.axhline(y=adjusted_zero_y, color='green', linestyle='-')
    plt.title('グレースケール')
    
    # 3. 輝度プロファイル
    plt.subplot(2, 2, 3)
    y_range = range(mid_y - 50, mid_y + 50)
    mean_values = [np.mean(gray[y, :]) if 0 <= y < height else 255 for y in y_range]
    plt.plot(y_range, mean_values)
    plt.axvline(x=actual_zero_y, color='red', linestyle='--', label='現在')
    plt.axvline(x=adjusted_zero_y, color='green', linestyle='-', label='調整後')
    plt.xlabel('Y座標')
    plt.ylabel('平均輝度')
    plt.title('Y方向の輝度プロファイル')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 4. エッジ検出
    plt.subplot(2, 2, 4)
    edges = cv2.Canny(gray, 50, 150)
    plt.imshow(edges, cmap='gray')
    plt.axhline(y=actual_zero_y, color='red', linestyle='--')
    plt.axhline(y=adjusted_zero_y, color='green', linestyle='-')
    plt.title('エッジ検出')
    
    plt.tight_layout()
    output_path = f"graphs/extracted_data/debug_zero_{os.path.basename(image_path)}"
    plt.savefig(output_path, dpi=150)
    plt.close()
    
    print(f"\nデバッグ画像保存: {output_path}")
    
    return adjusted_zero_y

# テスト実行
if __name__ == "__main__":
    import glob
    
    # すべてのクロップ画像をチェック
    image_files = glob.glob("graphs/manual_crop/cropped/*.png")
    image_files.sort()
    
    print("ゼロライン検出デバッグ")
    print("=" * 60)
    
    for img_path in image_files[:5]:
        debug_zero_line(img_path)