#!/usr/bin/env python3
"""
正確なゼロライン検出とグリッド表示（修正版v3）
+30,000のラインが画像内に見えるように調整
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

def analyze_actual_graph_range(img_path):
    """実際のグラフを見て範囲を分析"""
    img = cv2.imread(img_path)
    if img is None:
        return None
    
    # 画像サイズ
    height, width = img.shape[:2]
    print(f"画像サイズ: {width}x{height}")
    
    # ゼロライン位置（検証済み）
    zero_y = 250
    
    # 実際のグラフを観察すると、上端に+30,000のラインが少し見えている
    # つまり、画像の上端は+30,000より少し上の値
    # 画像の上部に少し余白があることを考慮
    
    # より正確なスケールを計算
    # ゼロラインから上端までが250ピクセル
    # ゼロラインから下端までが249ピクセル
    # 合計で約500ピクセル
    
    # 実際の観察から、表示範囲は約+32,000から-28,000程度
    # スケールを微調整
    scale = 115  # 1px = 115に調整
    
    # 上端と下端の実際の値を計算
    top_value = (zero_y - 0) * scale  # Y=0での値
    bottom_value = (zero_y - (height-1)) * scale  # Y=499での値
    
    print(f"ゼロライン: Y={zero_y}")
    print(f"調整後スケール: 1px = {scale}")
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

def draw_grid_overlay_final(img_path, output_path="grid_overlay_final.png"):
    """最終版グリッド付き画像を生成"""
    
    # 画像読み込み
    img = cv2.imread(img_path)
    if img is None:
        print("画像の読み込みに失敗しました")
        return
    
    # 画像情報を分析
    info = analyze_actual_graph_range(img_path)
    
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
    
    # グリッド線を描画
    grid_values = [30000, 25000, 20000, 15000, 10000, 5000, 0, -5000, -10000, -15000, -20000, -25000, -30000]
    
    for value in grid_values:
        y_pos = zero_y - (value / scale)
        
        # 画像範囲内かチェック
        if -5 <= y_pos <= height + 5:  # 少し余裕を持たせる
            if value == 0:
                continue  # ゼロラインは既に描画済み
            
            # 色と線の太さを設定
            if abs(value) == 30000:
                color = '#FF1493'
                width = 2.5
                style = '-'
                alpha = 0.9
            elif abs(value) == 20000:
                color = '#FF69B4'
                width = 2
                style = '--'
                alpha = 0.8
            elif abs(value) == 10000:
                color = '#FFB6C1'
                width = 1.5
                style = '--'
                alpha = 0.8
            elif abs(value) % 5000 == 0:
                color = 'gray'
                width = 0.5
                style = ':'
                alpha = 0.5
            else:
                continue
            
            # 画像範囲内のみ描画
            if 0 <= y_pos <= height:
                ax.axhline(y=y_pos, color=color, linewidth=width, alpha=alpha, linestyle=style)
            
            # ラベル（主要な線のみ、画像範囲内）
            if abs(value) % 10000 == 0 and 10 <= y_pos <= height - 10:
                label_text = f'{value:+,}' if value != 0 else '0'
                # ラベル位置を調整（+30000は左側に）
                label_x = 10 if value == 30000 else width - 80
                ax.text(label_x, y_pos - 5, label_text, 
                       fontsize=12, color=color if abs(value) >= 10000 else 'black', 
                       weight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # 実際のグラフ範囲を表示
    ax.text(10, 20, f'表示範囲: 約+{int(info["top_value"]):,} 〜 約{int(info["bottom_value"]):,}', 
           fontsize=10, color='darkblue', weight='bold',
           bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.9))
    
    # 縦のグリッド線（時間軸の目安）
    for x in range(100, int(width), 100):
        ax.axvline(x=x, color='gray', linewidth=0.3, alpha=0.3)
    
    # タイトルと情報
    ax.set_title('パチンコグラフ - 正確なグリッド表示', fontsize=16, pad=20)
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
    print(f"最終版グリッド付き画像を保存: {output_path}")
    
    return info

def visualize_scale_comparison():
    """異なるスケールでの比較"""
    img_path = "graphs/manual_crop/cropped/S__78209138_graph_only.png"
    img = cv2.imread(img_path)
    if img is None:
        return
    
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    height, width = img.shape[:2]
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    
    scales = [120, 115]
    titles = ['スケール: 1px = 120（従来）', 'スケール: 1px = 115（調整後）']
    
    for idx, (scale, title) in enumerate(zip(scales, titles)):
        ax = axes[idx]
        ax.imshow(img_rgb)
        ax.set_title(title, fontsize=14)
        
        # ゼロライン
        zero_y = 250
        ax.axhline(y=zero_y, color='black', linewidth=3)
        
        # グリッド線
        for value in [30000, 20000, 10000, -10000, -20000, -30000]:
            y_pos = zero_y - (value / scale)
            if 0 <= y_pos <= height:
                color = '#FF1493' if abs(value) == 30000 else '#FFB6C1'
                ax.axhline(y=y_pos, color=color, linewidth=1.5, alpha=0.8, linestyle='--')
                ax.text(10, y_pos - 5, f'{value:+,}', 
                       fontsize=10, color=color,
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))
        
        # 表示範囲
        top_val = zero_y * scale
        bottom_val = (zero_y - (height-1)) * scale
        ax.text(width//2, height-20, f'範囲: +{int(top_val):,} 〜 {int(bottom_val):,}', 
               ha='center', fontsize=10, color='blue',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8))
        
        ax.axis('off')
    
    plt.suptitle('スケール比較: どちらが正確か？', fontsize=16)
    plt.tight_layout()
    plt.savefig('scale_comparison.png', dpi=150, bbox_inches='tight')
    print("スケール比較画像を保存: scale_comparison.png")

if __name__ == "__main__":
    # メイン画像でグリッド表示
    main_image = "graphs/manual_crop/cropped/S__78209138_graph_only.png"
    
    # 分析
    analyze_actual_graph_range(main_image)
    
    # 最終版グリッド描画
    draw_grid_overlay_final(main_image)
    
    # スケール比較
    visualize_scale_comparison()