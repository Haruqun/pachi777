#!/usr/bin/env python3
"""
正確なゼロライン検出とグリッド表示
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

def detect_zero_line_accurate(img_path):
    """高精度ゼロライン検出"""
    img = cv2.imread(img_path)
    if img is None:
        return None, None
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    
    # 中央付近でグレーの太い線を探す
    center_y = height // 2
    search_range = 100
    
    best_y = None
    best_score = 0
    
    for y in range(center_y - search_range, center_y + search_range):
        if y < 0 or y >= height:
            continue
        
        # この行のグレー値をチェック
        row = gray[y, :]
        gray_pixels = row[(row > 60) & (row < 120)]
        
        if len(gray_pixels) > width * 0.8:  # 80%以上がグレー
            score = len(gray_pixels) / width
            mean_gray = np.mean(gray_pixels)
            
            # 最もグレーに近い線を選択
            if score > best_score and 70 < mean_gray < 110:
                best_score = score
                best_y = y
    
    return img, best_y

def draw_grid_overlay(img_path, output_path="grid_overlay_result.png"):
    """グリッド付き画像を生成"""
    
    # ゼロライン検出
    img, zero_y = detect_zero_line_accurate(img_path)
    if img is None:
        print("画像の読み込みに失敗しました")
        return
    
    # 実際の検出結果に基づく（Y=250が正確）
    zero_y = 250
    
    # BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    height, width = img.shape[:2]
    
    # matplotlib図を作成
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(img_rgb)
    
    # ゼロライン（太い黒線）
    ax.axhline(y=zero_y, color='black', linewidth=3, label=f'Zero Line (Y={zero_y})')
    
    # スケール設定（1px = 120）
    scale = 120
    
    # グリッド線を描画
    grid_colors = {
        10000: ('#FFB6C1', 1.5),   # 薄いピンク
        20000: ('#FF69B4', 2),      # ホットピンク
        30000: ('#FF1493', 2.5),    # ディープピンク
    }
    
    # 上方向（プラス）
    for value, (color, width) in grid_colors.items():
        y_pos = zero_y - (value / scale)
        if 0 <= y_pos < height:
            ax.axhline(y=y_pos, color=color, linewidth=width, alpha=0.8, linestyle='--')
            ax.text(width - 80, y_pos - 5, f'+{value:,}', 
                   fontsize=12, color=color, weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # 下方向（マイナス）
    for value, (color, width) in grid_colors.items():
        y_pos = zero_y + (value / scale)
        if 0 <= y_pos < height:
            ax.axhline(y=y_pos, color=color, linewidth=width, alpha=0.8, linestyle='--')
            ax.text(width - 80, y_pos - 5, f'-{value:,}', 
                   fontsize=12, color=color, weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # 細かいグリッド（5000単位）
    for i in range(1, 7):
        value = i * 5000
        if value % 10000 != 0:  # 10000の倍数は除外
            # 上方向
            y_pos = zero_y - (value / scale)
            if 0 <= y_pos < height:
                ax.axhline(y=y_pos, color='gray', linewidth=0.5, alpha=0.5, linestyle=':')
                ax.text(10, y_pos + 3, f'+{value:,}', 
                       fontsize=8, color='gray', alpha=0.7)
            
            # 下方向
            y_pos = zero_y + (value / scale)
            if 0 <= y_pos < height:
                ax.axhline(y=y_pos, color='gray', linewidth=0.5, alpha=0.5, linestyle=':')
                ax.text(10, y_pos + 3, f'-{value:,}', 
                       fontsize=8, color='gray', alpha=0.7)
    
    # 縦のグリッド線（時間軸の目安）
    for x in range(100, int(width), 100):
        ax.axvline(x=x, color='gray', linewidth=0.3, alpha=0.3)
    
    # タイトルと情報
    ax.set_title('グラフ with 正確なゼロライン検出とグリッド表示', fontsize=16, pad=20)
    ax.text(width//2, -30, f'ゼロライン: Y={zero_y} | スケール: 1px = {scale}', 
           ha='center', fontsize=12, color='blue')
    
    # 軸の設定
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)  # Y軸を反転
    ax.axis('off')
    
    # 凡例
    legend_elements = [
        patches.Patch(color='black', label=f'ゼロライン (Y={zero_y})'),
        patches.Patch(color='#FF1493', label='±30,000'),
        patches.Patch(color='#FF69B4', label='±20,000'),
        patches.Patch(color='#FFB6C1', label='±10,000'),
        patches.Patch(color='gray', label='±5,000 (補助線)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"グリッド付き画像を保存: {output_path}")
    
    # 数値情報も出力
    print("\n【グリッド情報】")
    print(f"ゼロライン位置: Y = {zero_y}")
    print(f"スケール: 1ピクセル = {scale}")
    print(f"+30,000位置: Y = {zero_y - 30000/scale:.1f}")
    print(f"+20,000位置: Y = {zero_y - 20000/scale:.1f}")
    print(f"+10,000位置: Y = {zero_y - 10000/scale:.1f}")
    print(f"-10,000位置: Y = {zero_y + 10000/scale:.1f}")
    print(f"-20,000位置: Y = {zero_y + 20000/scale:.1f}")
    print(f"-30,000位置: Y = {zero_y + 30000/scale:.1f}")
    
    return zero_y

def create_grid_comparison():
    """複数の画像でグリッド比較"""
    
    test_images = [
        "graphs/manual_crop/cropped/S__78209138_graph_only.png",
        "graphs/manual_crop/cropped/S__78209128_graph_only.png",
        "graphs/manual_crop/cropped/S__78209136_graph_only.png"
    ]
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    for idx, img_path in enumerate(test_images):
        if not Path(img_path).exists():
            continue
            
        img = cv2.imread(img_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        ax = axes[idx]
        ax.imshow(img_rgb)
        
        # ゼロライン
        zero_y = 250
        ax.axhline(y=zero_y, color='red', linewidth=2)
        
        # 主要グリッド
        scale = 120
        for value in [10000, 20000, 30000]:
            # 上
            y = zero_y - value/scale
            if 0 <= y < img.shape[0]:
                ax.axhline(y=y, color='blue', linewidth=1, alpha=0.5, linestyle='--')
                ax.text(img.shape[1]-60, y-3, f'+{value//1000}k', fontsize=8, color='blue')
            
            # 下
            y = zero_y + value/scale
            if 0 <= y < img.shape[0]:
                ax.axhline(y=y, color='blue', linewidth=1, alpha=0.5, linestyle='--')
                ax.text(img.shape[1]-60, y-3, f'-{value//1000}k', fontsize=8, color='blue')
        
        ax.set_title(f'画像 {idx+1}', fontsize=12)
        ax.axis('off')
    
    plt.suptitle('ゼロライン検出とグリッド表示の比較', fontsize=16)
    plt.tight_layout()
    plt.savefig('grid_comparison.png', dpi=150, bbox_inches='tight')
    print("比較画像を保存: grid_comparison.png")

if __name__ == "__main__":
    # メイン画像でグリッド表示
    main_image = "graphs/manual_crop/cropped/S__78209138_graph_only.png"
    draw_grid_overlay(main_image)
    
    # 複数画像の比較
    create_grid_comparison()