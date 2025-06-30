#!/usr/bin/env python3
"""
正確なゼロライン検出とグリッド表示（修正版v4）
+30,000のラインが画像内に見えるように、スケールを大きく調整
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

def find_optimal_scale(img_path):
    """最適なスケールを見つける"""
    img = cv2.imread(img_path)
    if img is None:
        return None
    
    height, width = img.shape[:2]
    zero_y = 250
    
    # 画像の上端付近に+30,000のラインが来るようにスケールを調整
    # 上端から少し下（例：Y=20）に+30,000が来るとする
    target_y_for_30k = 20
    
    # ゼロラインから+30,000の位置までの距離
    distance_to_30k = zero_y - target_y_for_30k  # 250 - 20 = 230ピクセル
    
    # スケール計算: 30,000 / 230 ≈ 130
    optimal_scale = 30000 / distance_to_30k
    
    print(f"最適スケール計算:")
    print(f"  +30,000をY={target_y_for_30k}に配置")
    print(f"  ゼロライン(Y={zero_y})からの距離: {distance_to_30k}px")
    print(f"  計算されたスケール: 1px = {optimal_scale:.1f}")
    
    return optimal_scale

def draw_grid_overlay_optimal(img_path, output_path="grid_overlay_optimal.png", custom_scale=None):
    """最適化されたグリッド付き画像を生成"""
    
    # 画像読み込み
    img = cv2.imread(img_path)
    if img is None:
        print("画像の読み込みに失敗しました")
        return
    
    # BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    height, width = img.shape[:2]
    
    # スケール設定
    if custom_scale is None:
        scale = find_optimal_scale(img_path)
    else:
        scale = custom_scale
    
    zero_y = 250
    
    # matplotlib図を作成
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(img_rgb)
    
    # ゼロライン（太い黒線）
    ax.axhline(y=zero_y, color='black', linewidth=3, label=f'Zero Line (Y={zero_y})')
    
    # グリッド線を描画
    grid_config = {
        30000: {'color': '#FF1493', 'width': 2.5, 'style': '-', 'alpha': 0.9},
        25000: {'color': '#FF1493', 'width': 1.2, 'style': '--', 'alpha': 0.6},
        20000: {'color': '#FF69B4', 'width': 2, 'style': '--', 'alpha': 0.8},
        15000: {'color': '#FF69B4', 'width': 1.2, 'style': ':', 'alpha': 0.6},
        10000: {'color': '#FFB6C1', 'width': 1.5, 'style': '--', 'alpha': 0.8},
        5000: {'color': 'gray', 'width': 0.5, 'style': ':', 'alpha': 0.5}
    }
    
    # プラス側とマイナス側の両方を描画
    for value in [30000, 25000, 20000, 15000, 10000, 5000, -5000, -10000, -15000, -20000, -25000, -30000]:
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
    ax.set_title('パチンコグラフ - 最適化グリッド表示', fontsize=16, pad=20)
    ax.text(width//2, -30, f'ゼロライン: Y={zero_y} | スケール: 1px = {scale:.1f}', 
           ha='center', fontsize=12, color='blue')
    
    # 軸の設定
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)  # Y軸を反転
    ax.axis('off')
    
    # 凡例
    legend_elements = [
        patches.Patch(color='black', label=f'ゼロライン (Y={zero_y})'),
        patches.Patch(color='#FF1493', label='±30,000 / ±25,000'),
        patches.Patch(color='#FF69B4', label='±20,000 / ±15,000'),
        patches.Patch(color='#FFB6C1', label='±10,000'),
        patches.Patch(color='gray', label='±5,000 (補助線)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"最適化グリッド付き画像を保存: {output_path}")
    
    return scale

def test_multiple_scales(img_path):
    """複数のスケールをテスト"""
    scales = [115, 120, 125, 130, 135]
    
    for scale in scales:
        output_name = f"grid_test_scale_{scale}.png"
        draw_grid_overlay_optimal(img_path, output_name, custom_scale=scale)
        print(f"スケール {scale} でテスト画像作成: {output_name}")

if __name__ == "__main__":
    # メイン画像
    main_image = "graphs/manual_crop/cropped/S__78209138_graph_only.png"
    
    # 最適スケールを見つけて描画
    optimal_scale = find_optimal_scale(main_image)
    draw_grid_overlay_optimal(main_image)
    
    # 複数のスケールでテスト（確認用）
    # test_multiple_scales(main_image)