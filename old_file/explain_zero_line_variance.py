#!/usr/bin/env python3
"""
ゼロラインのばらつきを詳しく分析・可視化
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import platform

# 日本語フォント設定
if platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'Hiragino Sans'

def analyze_zero_line_variance():
    """各画像のゼロライン位置を詳しく分析"""
    
    # 検出結果データ（advanced_zero_line_detector.pyの結果より）
    detection_results = {
        'S__78209168': 249,
        'S__78209160': 250,
        'S__78848020': 249,
        'S__78209166': 249,
        'S__78209174': 250,
        'S__78209088': 251,
        'S__78716957': 249,
        'S__78209164': 249,
        'S__78209170': 249,
        'S__78209162': 249,
        'S__78716960': 249,
        'S__78209156': 249,
        'S__78209128': 250,
        'S__78716972': 250,
        'S__78848016': 249,
        'S__78209158': 250,
        'S__78848010': 249,
        'S__78848018': 249,
        'S__78716974': 249,
        'S__78848012': 249,
        'S__78209136': 249,
        'S__78848008': 249,
        'S__78716970': 250,
        'S__78848014': 250,
        'S__78209138': 250,
        'S__78716962': 251,
        'S__78209130': 251
    }
    
    # 統計計算
    y_values = list(detection_results.values())
    mean_y = np.mean(y_values)
    std_y = np.std(y_values)
    
    # 図を作成
    fig = plt.figure(figsize=(16, 12))
    
    # 1. タイトルと説明
    fig.suptitle('ゼロラインの位置ばらつき分析', fontsize=20, y=0.98)
    
    # 2. ばらつきの説明
    ax_explain = plt.subplot2grid((4, 3), (0, 0), colspan=3)
    explanation = """ゼロライン平均Y=249.5の意味：
    
    • 27枚の画像でゼロラインの位置を自動検出した結果、Y座標が249〜251の範囲でばらついています
    • これは画像の撮影条件やグラフの表示位置の微妙な違いによるものです
    • 標準偏差0.7ピクセルは非常に小さく、ほぼ安定した位置にあることを示しています
    • 従来のY=260は約10ピクセルずれていたことが判明しました"""
    
    ax_explain.text(0.05, 0.5, explanation, fontsize=14, va='center')
    ax_explain.axis('off')
    
    # 3. サンプル画像での比較
    sample_images = [
        ('S__78209138', 250, 'graphs/manual_crop/cropped/S__78209138_graph_only.png'),
        ('S__78209128', 250, 'graphs/manual_crop/cropped/S__78209128_graph_only.png'),
        ('S__78209088', 251, 'graphs/manual_crop/cropped/S__78209088_graph_only.png'),
        ('S__78716957', 249, 'graphs/manual_crop/cropped/S__78716957_graph_only.png')
    ]
    
    for i, (name, y_pos, path) in enumerate(sample_images):
        if Path(path).exists():
            ax = plt.subplot2grid((4, 3), (1, i % 3))
            img = cv2.imread(path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # 画像表示
            ax.imshow(img)
            
            # 検出されたゼロライン
            ax.axhline(y=y_pos, color='green', linewidth=3, label=f'検出: Y={y_pos}')
            
            # 平均位置
            ax.axhline(y=249.5, color='blue', linewidth=2, linestyle='--', alpha=0.7, label='平均: Y=249.5')
            
            # 旧固定値
            ax.axhline(y=260, color='red', linewidth=2, linestyle=':', alpha=0.7, label='旧: Y=260')
            
            # 拡大表示エリア
            ax.add_patch(plt.Rectangle((400, 240), 150, 30, fill=False, edgecolor='yellow', linewidth=2))
            
            ax.set_title(f'{name}\n検出位置: Y={y_pos}', fontsize=12)
            ax.legend(loc='upper left', fontsize=8)
            ax.axis('off')
    
    # 4. ヒストグラム
    ax_hist = plt.subplot2grid((4, 3), (2, 0), colspan=2)
    counts = [y_values.count(249), y_values.count(250), y_values.count(251)]
    positions = [249, 250, 251]
    colors = ['#4ECDC4', '#45B7D1', '#96CEB4']
    
    bars = ax_hist.bar(positions, counts, color=colors, edgecolor='black', linewidth=2)
    
    # 各バーに枚数を表示
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax_hist.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{count}枚', ha='center', va='bottom', fontsize=12)
    
    ax_hist.axvline(x=mean_y, color='red', linestyle='--', linewidth=2, label=f'平均: {mean_y:.1f}')
    ax_hist.set_xlabel('Y座標', fontsize=14)
    ax_hist.set_ylabel('画像数', fontsize=14)
    ax_hist.set_title('ゼロライン位置の分布', fontsize=16)
    ax_hist.set_xticks(positions)
    ax_hist.legend()
    ax_hist.grid(True, alpha=0.3)
    
    # 5. 統計情報
    ax_stats = plt.subplot2grid((4, 3), (2, 2))
    stats_text = f"""統計情報:
    
    サンプル数: 27枚
    平均値: Y = {mean_y:.1f}
    標準偏差: {std_y:.1f} px
    最小値: Y = {min(y_values)}
    最大値: Y = {max(y_values)}
    範囲: {max(y_values) - min(y_values)} px
    
    ばらつきの原因:
    • 撮影角度の違い
    • 画面の微妙な位置ずれ
    • グラフ表示の個体差"""
    
    ax_stats.text(0.1, 0.5, stats_text, fontsize=12, va='center')
    ax_stats.axis('off')
    
    # 6. 拡大比較図
    ax_zoom = plt.subplot2grid((4, 3), (3, 0), colspan=3)
    
    # 3つの代表的な位置を示す
    x = np.arange(0, 600, 50)
    y_249 = np.ones_like(x) * 249
    y_250 = np.ones_like(x) * 250
    y_251 = np.ones_like(x) * 251
    y_260 = np.ones_like(x) * 260
    
    ax_zoom.plot(x, y_249, 'o-', color='#4ECDC4', linewidth=3, markersize=8, label='Y=249 (15枚)')
    ax_zoom.plot(x, y_250, 's-', color='#45B7D1', linewidth=3, markersize=8, label='Y=250 (9枚)')
    ax_zoom.plot(x, y_251, '^-', color='#96CEB4', linewidth=3, markersize=8, label='Y=251 (3枚)')
    ax_zoom.plot(x, y_260, 'x-', color='red', linewidth=2, markersize=10, alpha=0.5, label='Y=260 (旧固定値)')
    
    ax_zoom.fill_between([0, 600], 248, 252, alpha=0.2, color='green', label='検出範囲')
    ax_zoom.set_xlim(0, 600)
    ax_zoom.set_ylim(245, 265)
    ax_zoom.set_xlabel('X座標', fontsize=12)
    ax_zoom.set_ylabel('Y座標', fontsize=12)
    ax_zoom.set_title('ゼロライン位置の比較（拡大図）', fontsize=14)
    ax_zoom.legend(loc='upper right')
    ax_zoom.grid(True, alpha=0.3)
    
    # 差を矢印で示す
    ax_zoom.annotate('', xy=(300, 250), xytext=(300, 260),
                    arrowprops=dict(arrowstyle='<->', color='red', lw=2))
    ax_zoom.text(310, 255, '10px差', fontsize=12, color='red', weight='bold')
    
    plt.tight_layout()
    plt.savefig('zero_line_variance_analysis.png', dpi=150, bbox_inches='tight', facecolor='white')
    print("ゼロラインばらつき分析画像保存: zero_line_variance_analysis.png")

if __name__ == "__main__":
    analyze_zero_line_variance()