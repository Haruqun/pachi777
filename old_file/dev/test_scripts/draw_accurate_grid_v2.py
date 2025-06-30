#!/usr/bin/env python3
"""
正確なゼロライン検出とグリッド表示（修正版）
実際のグラフ範囲に合わせて調整
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

def analyze_graph_bounds(img_path):
    """グラフの実際の表示範囲を分析"""
    img = cv2.imread(img_path)
    if img is None:
        return None
    
    # 画像サイズ
    height, width = img.shape[:2]
    print(f"画像サイズ: {width}x{height}")
    
    # ゼロライン位置（検証済み）
    zero_y = 250
    
    # スケール（1px = 120）
    scale = 120
    
    # 上端と下端の実際の値を計算
    top_value = (zero_y - 0) * scale  # Y=0での値
    bottom_value = (zero_y - (height-1)) * scale  # Y=499での値
    
    print(f"ゼロライン: Y={zero_y}")
    print(f"上端（Y=0）の値: +{top_value}")
    print(f"下端（Y={height-1}）の値: {bottom_value}")
    
    return {
        'zero_y': zero_y,
        'scale': scale,
        'top_value': top_value,
        'bottom_value': bottom_value,
        'height': height,
        'width': width
    }

def draw_grid_overlay_corrected(img_path, output_path="grid_overlay_corrected.png"):
    """修正版グリッド付き画像を生成"""
    
    # 画像読み込み
    img = cv2.imread(img_path)
    if img is None:
        print("画像の読み込みに失敗しました")
        return
    
    # 画像情報を分析
    info = analyze_graph_bounds(img_path)
    
    # BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    height, width = img.shape[:2]
    
    # matplotlib図を作成
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(img_rgb)
    
    # ゼロライン（太い黒線）
    zero_y = info['zero_y']
    scale = info['scale']
    ax.axhline(y=zero_y, color='black', linewidth=3, label=f'Zero Line (Y={zero_y})')
    
    # グリッド線を描画（実際に表示される範囲のみ）
    grid_values = [30000, 25000, 20000, 15000, 10000, 5000, 0, -5000, -10000, -15000, -20000, -25000, -30000]
    
    for value in grid_values:
        y_pos = zero_y - (value / scale)
        
        # 画像範囲内かチェック
        if 0 <= y_pos <= height:
            if value == 0:
                continue  # ゼロラインは既に描画済み
            
            # 色と線の太さを設定
            if abs(value) == 30000:
                color = '#FF1493'
                width = 2.5
                style = '-'
            elif abs(value) == 20000:
                color = '#FF69B4'
                width = 2
                style = '--'
            elif abs(value) == 10000:
                color = '#FFB6C1'
                width = 1.5
                style = '--'
            elif abs(value) % 5000 == 0:
                color = 'gray'
                width = 0.5
                style = ':'
            else:
                continue
            
            ax.axhline(y=y_pos, color=color, linewidth=width, alpha=0.8, linestyle=style)
            
            # ラベル（主要な線のみ）
            if abs(value) % 10000 == 0:
                label_text = f'{value:+,}' if value != 0 else '0'
                ax.text(width - 80, y_pos - 5, label_text, 
                       fontsize=12, color=color if abs(value) >= 10000 else 'black', 
                       weight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # 実際のグラフ範囲を表示
    ax.text(10, 20, f'上端: 約+{int(info["top_value"]):,}', 
           fontsize=10, color='red', weight='bold',
           bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8))
    ax.text(10, height-10, f'下端: 約{int(info["bottom_value"]):,}', 
           fontsize=10, color='blue', weight='bold',
           bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8))
    
    # 縦のグリッド線（時間軸の目安）
    for x in range(100, int(width), 100):
        ax.axvline(x=x, color='gray', linewidth=0.3, alpha=0.3)
    
    # タイトルと情報
    ax.set_title('グラフ with 正確なゼロライン検出とグリッド表示（修正版）', fontsize=16, pad=20)
    ax.text(width//2, -30, f'ゼロライン: Y={zero_y} | スケール: 1px = {scale} | 表示範囲: +{int(info["top_value"]):,} 〜 {int(info["bottom_value"]):,}', 
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
    print(f"修正版グリッド付き画像を保存: {output_path}")
    
    return info

def check_scale_accuracy(img_path):
    """スケールの精度を確認"""
    info = analyze_graph_bounds(img_path)
    
    print("\n【スケール精度の確認】")
    print(f"画像の高さ: {info['height']}px")
    print(f"ゼロラインの位置: Y={info['zero_y']}")
    print(f"")
    print(f"仮定するスケール: 1px = {info['scale']}")
    print(f"")
    print(f"このスケールでの計算値:")
    print(f"  上端（Y=0）: +{info['top_value']:,}")
    print(f"  下端（Y=499）: {info['bottom_value']:,}")
    print(f"")
    print(f"実際のグラフを見ると:")
    print(f"  - 上端は約+30,000付近")
    print(f"  - 下端は約-30,000付近")
    print(f"")
    
    # より正確なスケールを逆算
    expected_range = 60000  # +30000 から -30000
    actual_height = info['height']
    calculated_scale = expected_range / actual_height
    
    print(f"逆算したスケール: 1px = {calculated_scale:.2f}")

if __name__ == "__main__":
    # メイン画像でグリッド表示
    main_image = "graphs/manual_crop/cropped/S__78209138_graph_only.png"
    
    # スケール精度の確認
    check_scale_accuracy(main_image)
    
    # 修正版グリッド描画
    draw_grid_overlay_corrected(main_image)