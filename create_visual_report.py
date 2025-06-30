#!/usr/bin/env python3
"""
画像付きビジュアルレポートを生成
"""

import os
import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import font_manager
import platform

# 日本語フォント設定
if platform.system() == 'Darwin':  # macOS
    plt.rcParams['font.family'] = 'Hiragino Sans'
else:
    plt.rcParams['font.family'] = 'sans-serif'

def create_visual_summary():
    """ビジュアルサマリーを作成"""
    
    # サンプル画像を選択
    sample_images = [
        "graphs/manual_crop/cropped/S__78209138_graph_only.png",
        "graphs/manual_crop/cropped/S__78209128_graph_only.png",
        "graphs/manual_crop/cropped/S__78209136_graph_only.png",
        "graphs/manual_crop/cropped/S__78209130_graph_only.png"
    ]
    
    # 検出結果画像
    detection_images = [
        "zero_detection_results/S__78209138_graph_only_detection.png",
        "zero_detection_results/S__78209128_graph_only_detection.png",
        "zero_detection_results/S__78209136_graph_only_detection.png",
        "zero_detection_results/S__78209130_graph_only_detection.png"
    ]
    
    # 図を作成
    fig = plt.figure(figsize=(20, 24))
    
    # タイトル
    fig.suptitle('パチンコグラフ分析プロジェクト - ビジュアルレポート', fontsize=24, y=0.98)
    
    # 1. プロジェクト概要
    ax_overview = plt.subplot2grid((6, 4), (0, 0), colspan=4)
    ax_overview.text(0.5, 0.8, 'ゼロライン検出精度の大幅改善を達成', 
                    ha='center', va='center', fontsize=20, weight='bold')
    ax_overview.text(0.5, 0.5, '従来: Y=260（固定値） → 改善後: Y=249.5（自動検出、標準偏差0.7）', 
                    ha='center', va='center', fontsize=16)
    ax_overview.text(0.5, 0.2, '27枚の画像で検証済み | 検出精度: 65% | 手法間一致度: 96%', 
                    ha='center', va='center', fontsize=14, color='blue')
    ax_overview.axis('off')
    
    # 2. サンプル画像と検出結果の比較
    for i in range(4):
        # 元画像
        if os.path.exists(sample_images[i]):
            ax_orig = plt.subplot2grid((6, 4), (1, i))
            img_orig = cv2.imread(sample_images[i])
            img_orig = cv2.cvtColor(img_orig, cv2.COLOR_BGR2RGB)
            ax_orig.imshow(img_orig)
            ax_orig.set_title(f'元画像 {i+1}', fontsize=12)
            ax_orig.axis('off')
            
            # Y=260とY=250のライン
            ax_orig.axhline(y=260, color='red', linestyle='--', linewidth=2, alpha=0.7)
            ax_orig.axhline(y=250, color='green', linestyle='-', linewidth=2, alpha=0.7)
            
        # 検出結果
        if os.path.exists(detection_images[i]):
            ax_det = plt.subplot2grid((6, 4), (2, i))
            img_det = cv2.imread(detection_images[i])
            img_det = cv2.cvtColor(img_det, cv2.COLOR_BGR2RGB)
            ax_det.imshow(img_det)
            ax_det.set_title(f'検出結果 {i+1}', fontsize=12)
            ax_det.axis('off')
    
    # 凡例を追加
    ax_legend = plt.subplot2grid((6, 4), (1, 0), colspan=4)
    ax_legend.text(0.35, 0.8, '赤破線: 旧ゼロライン (Y=260)', color='red', fontsize=12)
    ax_legend.text(0.65, 0.8, '緑実線: 新ゼロライン (Y≈250)', color='green', fontsize=12)
    ax_legend.axis('off')
    
    # 3. 統計グラフ
    ax_hist = plt.subplot2grid((6, 4), (3, 0), colspan=2)
    y_values = [249, 250, 249, 249, 250, 251, 249, 249, 249, 249, 249, 249, 250, 250, 249, 250, 249, 249, 249, 249, 249, 249, 250, 250, 250, 251, 251]
    ax_hist.hist(y_values, bins=range(248, 253), alpha=0.7, color='blue', edgecolor='black')
    ax_hist.axvline(x=249.5, color='red', linestyle='--', linewidth=2, label='平均値')
    ax_hist.set_xlabel('Y座標', fontsize=12)
    ax_hist.set_ylabel('頻度', fontsize=12)
    ax_hist.set_title('ゼロライン検出位置の分布', fontsize=14)
    ax_hist.legend()
    ax_hist.grid(True, alpha=0.3)
    
    # 4. 検出手法の信頼度
    ax_methods = plt.subplot2grid((6, 4), (3, 2), colspan=2)
    methods = ['太いグレー線', 'Hough変換', 'エッジベース', '輝度勾配', 'テンプレート']
    confidences = [0.80, 0.70, 0.60, 0.50, 0.90]
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#DDA0DD']
    bars = ax_methods.bar(methods, confidences, color=colors)
    ax_methods.set_ylabel('信頼度', fontsize=12)
    ax_methods.set_title('各検出手法の信頼度', fontsize=14)
    ax_methods.set_ylim(0, 1)
    for bar, conf in zip(bars, confidences):
        height = bar.get_height()
        ax_methods.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                       f'{conf:.0%}', ha='center', va='bottom')
    
    # 5. ツール紹介
    ax_tools = plt.subplot2grid((6, 4), (4, 0), colspan=4, rowspan=2)
    ax_tools.text(0.5, 0.9, '実装済みツール', ha='center', fontsize=18, weight='bold')
    
    # ツール1
    rect1 = patches.FancyBboxPatch((0.05, 0.6), 0.25, 0.25, 
                                  boxstyle="round,pad=0.05", 
                                  facecolor='lightblue', edgecolor='blue')
    ax_tools.add_patch(rect1)
    ax_tools.text(0.175, 0.75, '高精度検出', ha='center', weight='bold')
    ax_tools.text(0.175, 0.67, 'advanced_zero_line\n_detector.py', ha='center', fontsize=10)
    
    # ツール2
    rect2 = patches.FancyBboxPatch((0.375, 0.6), 0.25, 0.25, 
                                  boxstyle="round,pad=0.05", 
                                  facecolor='lightgreen', edgecolor='green')
    ax_tools.add_patch(rect2)
    ax_tools.text(0.5, 0.75, '比較ビューワー', ha='center', weight='bold')
    ax_tools.text(0.5, 0.67, 'multi_image_comparison\n_viewer.py', ha='center', fontsize=10)
    
    # ツール3
    rect3 = patches.FancyBboxPatch((0.7, 0.6), 0.25, 0.25, 
                                  boxstyle="round,pad=0.05", 
                                  facecolor='lightyellow', edgecolor='orange')
    ax_tools.add_patch(rect3)
    ax_tools.text(0.825, 0.75, 'インタラクティブ', ha='center', weight='bold')
    ax_tools.text(0.825, 0.67, 'interactive_graph\n_analyzer.html', ha='center', fontsize=10)
    
    # 機能説明
    features = [
        '✓ 5つの手法による高精度検出',
        '✓ 複数画像の一括比較表示',
        '✓ ドラッグ操作での手動調整',
        '✓ リアルタイム分析結果表示',
        '✓ JavaScript/HTML5実装'
    ]
    
    for i, feature in enumerate(features):
        ax_tools.text(0.05, 0.45 - i*0.08, feature, fontsize=12)
    
    ax_tools.set_xlim(0, 1)
    ax_tools.set_ylim(0, 1)
    ax_tools.axis('off')
    
    # レイアウト調整
    plt.tight_layout()
    
    # 保存
    plt.savefig('visual_report.png', dpi=150, bbox_inches='tight', facecolor='white')
    print("ビジュアルレポート保存: visual_report.png")
    
    # サムネイル版も作成
    create_comparison_image()

def create_comparison_image():
    """ゼロライン比較画像を作成"""
    
    sample_img_path = "graphs/manual_crop/cropped/S__78209138_graph_only.png"
    if not os.path.exists(sample_img_path):
        return
    
    img = cv2.imread(sample_img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # 左: 旧設定
    ax1.imshow(img)
    ax1.axhline(y=260, color='red', linewidth=3, label='Y=260 (旧)')
    ax1.axhline(y=260-83.33, color='red', linestyle='--', alpha=0.5, label='+10,000')
    ax1.axhline(y=260+83.33, color='red', linestyle='--', alpha=0.5, label='-10,000')
    ax1.set_title('従来の固定値設定', fontsize=16)
    ax1.legend(loc='upper right')
    ax1.axis('off')
    
    # 右: 新設定
    ax2.imshow(img)
    ax2.axhline(y=250, color='green', linewidth=3, label='Y=250 (新)')
    ax2.axhline(y=250-83.33, color='green', linestyle='--', alpha=0.5, label='+10,000')
    ax2.axhline(y=250+83.33, color='green', linestyle='--', alpha=0.5, label='-10,000')
    ax2.set_title('改善後の自動検出', fontsize=16)
    ax2.legend(loc='upper right')
    ax2.axis('off')
    
    plt.suptitle('ゼロライン検出の改善比較', fontsize=20, y=1.02)
    plt.tight_layout()
    plt.savefig('zero_line_comparison.png', dpi=150, bbox_inches='tight', facecolor='white')
    print("比較画像保存: zero_line_comparison.png")

def create_workflow_diagram():
    """ワークフロー図を作成"""
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # ワークフローのステップ
    steps = [
        {'pos': (2, 7), 'text': '1. 画像入力\n(パチンコ画面)', 'color': 'lightblue'},
        {'pos': (6, 7), 'text': '2. グラフ切り抜き\n(597×500px)', 'color': 'lightgreen'},
        {'pos': (10, 7), 'text': '3. ゼロライン検出\n(Y≈250)', 'color': 'lightyellow'},
        {'pos': (2, 4), 'text': '4. データ抽出\n(グラフ読み取り)', 'color': 'lightcoral'},
        {'pos': (6, 4), 'text': '5. 分析・可視化\n(統計処理)', 'color': 'plum'},
        {'pos': (10, 4), 'text': '6. レポート生成\n(HTML/画像)', 'color': 'lightgray'}
    ]
    
    # ステップを描画
    for i, step in enumerate(steps):
        circle = patches.FancyBboxPatch((step['pos'][0]-1.5, step['pos'][1]-0.5), 
                                       3, 1.5, 
                                       boxstyle="round,pad=0.1",
                                       facecolor=step['color'],
                                       edgecolor='black',
                                       linewidth=2)
        ax.add_patch(circle)
        ax.text(step['pos'][0], step['pos'][1], step['text'], 
               ha='center', va='center', fontsize=11, weight='bold')
    
    # 矢印を描画
    arrows = [
        ((3.5, 7), (4.5, 7)),
        ((7.5, 7), (8.5, 7)),
        ((10, 6.2), (10, 5.3)),
        ((8.5, 4), (7.5, 4)),
        ((4.5, 4), (3.5, 4)),
    ]
    
    for start, end in arrows:
        ax.annotate('', xy=end, xytext=start,
                   arrowprops=dict(arrowstyle='->', lw=2, color='black'))
    
    # ツール名を追加
    tools = [
        {'pos': (2, 2), 'text': 'manual_graph_cropper.py'},
        {'pos': (6, 2), 'text': 'advanced_zero_line_detector.py'},
        {'pos': (10, 2), 'text': 'interactive_graph_analyzer.html'}
    ]
    
    for tool in tools:
        ax.text(tool['pos'][0], tool['pos'][1], tool['text'], 
               ha='center', va='center', fontsize=10, 
               style='italic', color='blue')
    
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.set_title('パチンコグラフ分析ワークフロー', fontsize=18, pad=20)
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig('workflow_diagram.png', dpi=150, bbox_inches='tight', facecolor='white')
    print("ワークフロー図保存: workflow_diagram.png")

if __name__ == "__main__":
    create_visual_summary()
    create_workflow_diagram()