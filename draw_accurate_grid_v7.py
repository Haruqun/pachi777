#!/usr/bin/env python3
"""
正確なゼロライン検出とグリッド表示（30,000を上部に配置版）
±20,000の表示を削除
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import platform

# 日本語フォント設定
if platform.system() == 'Darwin':  # macOS
    plt.rcParams['font.family'] = 'Hiragino Sans'

def draw_grid_with_30k_at_top(img_path, output_path=None):
    """0ラインのみを表示したグリッド付き画像を生成"""
    
    # 画像読み込み
    img = cv2.imread(img_path)
    if img is None:
        print("画像の読み込みに失敗しました")
        return
    
    # 出力ファイル名を自動生成
    if output_path is None:
        base_name = Path(img_path).stem
        output_path = f"zero_plus_30k_{base_name}.png"
    
    # BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    height, width = img.shape[:2]
    
    # スケール計算
    # 30,000を画像上部（Y=5）に配置したい
    zero_y = 250
    target_y_for_30k = 5  # 画像上部
    distance = zero_y - target_y_for_30k  # 245px
    scale = 30000 / distance  # 30000 / 245 = 122.4
    
    print(f"スケール計算:")
    print(f"  +30,000をY={target_y_for_30k}に配置")
    print(f"  ゼロライン(Y={zero_y})からの距離: {distance}px")
    print(f"  計算されたスケール: 1px = {scale:.1f}")
    
    # matplotlib図を作成
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(img_rgb)
    
    # ゼロライン（太い黒線）
    ax.axhline(y=zero_y, color='black', linewidth=3, label=f'Zero Line (Y={zero_y})')
    
    # グリッド線を描画（0ラインと+30000ライン）
    grid_config = {
        30000: {'color': '#FF1493', 'width': 2.5, 'style': '-', 'alpha': 0.9}
    }
    
    # 描画する値（+30000のみ）
    values_to_draw = [30000]
    
    for value in values_to_draw:
        y_pos = zero_y - (value / scale)
        
        # 画像範囲内かチェック
        if -10 <= y_pos <= height + 10:
            if value == 0:
                continue
            
            # 設定を取得
            abs_value = abs(value)
            if abs_value in grid_config:
                config = grid_config[abs_value]
            else:
                continue
            
            # 画像範囲内のみ描画
            if 0 <= y_pos <= height:
                ax.axhline(y=y_pos, color=config['color'], linewidth=config['width'], 
                          alpha=config['alpha'], linestyle=config['style'])
            
            # ラベル（主要な線のみ）
            if abs_value % 10000 == 0 and 15 <= y_pos <= height - 15:
                label_text = f'{value:+,}'
                # 位置を調整
                if value > 0:
                    label_x = 10  # プラス値は左側
                else:
                    label_x = width - 90  # マイナス値は右側
                    
                ax.text(label_x, y_pos - 5, label_text, 
                       fontsize=12, color=config['color'], 
                       weight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # 実際の表示範囲
    top_value = (zero_y - 0) * scale
    bottom_value = (zero_y - (height-1)) * scale
    
    ax.text(width//2, 20, f'表示範囲: 約+{int(top_value):,} 〜 約{int(bottom_value):,}', 
           ha='center', fontsize=11, color='darkblue', weight='bold',
           bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow', alpha=0.9))
    
    # 縦のグリッド線（時間軸の目安）
    for x in range(100, int(width), 100):
        ax.axvline(x=x, color='gray', linewidth=0.3, alpha=0.3)
    
    # タイトルと情報
    ax.set_title('パチンコグラフ - ゼロライン+30000ライン表示', fontsize=16, pad=20)
    ax.text(width//2, -30, f'ゼロライン: Y={zero_y} | スケール: 1px = {scale:.1f}', 
           ha='center', fontsize=12, color='blue')
    
    # 軸の設定
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)  # Y軸を反転
    ax.axis('off')
    
    # 凡例（0ラインと+30000ライン）
    legend_elements = [
        patches.Patch(color='black', label=f'ゼロライン (Y={zero_y})'),
        patches.Patch(color='#FF1493', label='+30,000ライン')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"ゼロライン+30000ライン画像を保存: {output_path}")
    
    # グリッド位置の詳細情報
    print("\n【グリッド位置情報】")
    print(f"{'値':>8} | {'Y座標':>8} | {'状態':>10}")
    print("-" * 35)
    for value in [30000, 25000, 15000, 10000, 0, -10000, -15000, -25000, -30000]:
        y_pos = zero_y - (value / scale)
        if 0 <= y_pos <= height:
            status = "表示"
        else:
            status = "画像外"
        print(f"{value:+8,} | {y_pos:8.1f} | {status:>10}")
    
    return scale

if __name__ == "__main__":
    # 複数の画像を処理
    image_files = [
        "graphs/manual_crop/cropped/S__78209138_graph_only.png",
        "graphs/manual_crop/cropped/S__78209156_graph_only.png", 
        "graphs/manual_crop/cropped/S__78209158_graph_only.png",
        "graphs/manual_crop/cropped/S__78209162_graph_only.png",
        "graphs/manual_crop/cropped/S__78209166_graph_only.png"
    ]
    
    for img_file in image_files:
        print(f"\n=== 処理中: {img_file} ===")
        draw_grid_with_30k_at_top(img_file)