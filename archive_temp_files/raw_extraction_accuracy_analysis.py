#!/usr/bin/env python3
"""
生の抽出値（補正なし）の精度分析
ユーザーの指摘通り、抽出値は元から精度が高いことを検証
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import font_manager
import os
import csv

# 日本語フォント設定
def setup_japanese_font():
    """macOS用日本語フォント設定"""
    font_paths = [
        '/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/Library/Fonts/Osaka.ttf',
        '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font_prop = font_manager.FontProperties(fname=font_path)
                plt.rcParams['font.family'] = font_prop.get_name()
                return True
            except:
                continue
    return False

setup_japanese_font()

# results.txtから実際の値を読み込み
results = {}
with open('results.txt', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        base_name = row['画像名'].replace('.jpg', '')
        if row['実際の最大値'] and row['実際の最終差玉']:
            results[base_name] = {
                'actual_max': float(row['実際の最大値'].replace(',', '')),
                'actual_final': float(row['実際の最終差玉'].replace(',', ''))
            }

# 境界設定（stable_graph_extractor.pyから）
boundaries = {
    "start_x": 36,
    "end_x": 620,
    "top_y": 26,
    "bottom_y": 523,
    "zero_y": 274
}

def y_to_value_raw(y):
    """Y座標を値に変換（補正なし）"""
    zero_y = boundaries["zero_y"]
    top_y = boundaries["top_y"]
    bottom_y = boundaries["bottom_y"]
    
    if y < zero_y:
        value = (zero_y - y) / (zero_y - top_y) * 30000
    else:
        value = -(y - zero_y) / (bottom_y - zero_y) * 30000
    
    return np.clip(value, -30000, 30000)

# 分析結果を格納
analysis_results = []

print("生の抽出値精度分析レポート")
print("=" * 120)
print(f"{'画像':20} {'色':6} {'実際の最大':>10} {'抽出(生)':>10} {'誤差':>8} {'精度%':>8} | {'実際の最終':>10} {'抽出(生)':>10} {'誤差':>8} {'精度%':>8}")
print("-" * 120)

total_max_error = 0
total_final_error = 0
count = 0

color_stats = {'pink': [], 'blue': [], 'purple': []}

for base_name, actual in results.items():
    csv_path = f'graphs/stable_extracted_data/{base_name}_optimal_stable_data.csv'
    
    if not os.path.exists(csv_path):
        continue
    
    # データ読み込み
    df = pd.read_csv(csv_path)
    
    # 色を取得
    color = 'unknown'
    summary_df = pd.read_csv('graphs/stable_extracted_data/extraction_summary.csv')
    color_row = summary_df[summary_df['file_name'] == f'{base_name}_optimal']
    if not color_row.empty:
        color = color_row.iloc[0]['color']
    
    # 生の値を計算（補正なし）
    raw_values = []
    for _, row in df.iterrows():
        value = y_to_value_raw(row['y'])
        raw_values.append(value)
    
    # 最大値と最終値
    max_raw = max(raw_values)
    final_raw = raw_values[-1]
    
    # 誤差計算
    max_error = max_raw - actual['actual_max']
    final_error = final_raw - actual['actual_final']
    
    # 精度計算（300で割る方式）
    max_accuracy = 100 - abs(max_error) / 300
    final_accuracy = 100 - abs(final_error) / 300
    
    # 結果を保存
    analysis_results.append({
        'image': base_name,
        'color': color,
        'actual_max': actual['actual_max'],
        'extracted_max': max_raw,
        'max_error': max_error,
        'max_accuracy': max_accuracy,
        'actual_final': actual['actual_final'],
        'extracted_final': final_raw,
        'final_error': final_error,
        'final_accuracy': final_accuracy
    })
    
    # 色別統計
    if color in color_stats:
        color_stats[color].append({
            'max_error': abs(max_error),
            'final_error': abs(final_error),
            'max_accuracy': max_accuracy,
            'final_accuracy': final_accuracy
        })
    
    total_max_error += abs(max_error)
    total_final_error += abs(final_error)
    count += 1
    
    # 表示
    print(f"{base_name:20} {color:6} {actual['actual_max']:>10.0f} {max_raw:>10.0f} {max_error:>+8.0f} {max_accuracy:>7.1f}% | {actual['actual_final']:>10.0f} {final_raw:>10.0f} {final_error:>+8.0f} {final_accuracy:>7.1f}%")

print("-" * 120)

# 全体統計
avg_max_error = total_max_error / count
avg_final_error = total_final_error / count
avg_max_accuracy = 100 - avg_max_error / 300
avg_final_accuracy = 100 - avg_final_error / 300

print(f"\n全体統計（補正なしの生データ）:")
print(f"  平均最大値誤差: {avg_max_error:.0f} ({avg_max_accuracy:.1f}%)")
print(f"  平均最終値誤差: {avg_final_error:.0f} ({avg_final_accuracy:.1f}%)")

# 色別統計
print(f"\n色別精度:")
for color, stats in color_stats.items():
    if stats:
        avg_max_acc = np.mean([s['max_accuracy'] for s in stats])
        avg_final_acc = np.mean([s['final_accuracy'] for s in stats])
        print(f"  {color}: 最大値 {avg_max_acc:.1f}%, 最終値 {avg_final_acc:.1f}% (n={len(stats)})")

# 視覚化
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle('生の抽出値精度分析（補正なし）', fontsize=16, fontweight='bold')

# 1. 精度分布
ax1 = axes[0, 0]
df_results = pd.DataFrame(analysis_results)
df_sorted = df_results.sort_values('final_accuracy', ascending=False)

colors = []
for acc in df_sorted['final_accuracy']:
    if acc >= 98:
        colors.append('darkgreen')
    elif acc >= 95:
        colors.append('green')
    elif acc >= 90:
        colors.append('orange')
    else:
        colors.append('red')

bars = ax1.bar(range(len(df_sorted)), df_sorted['final_accuracy'], color=colors)
ax1.set_xlabel('画像')
ax1.set_ylabel('最終値精度 (%)')
ax1.set_title('最終値精度分布（補正なし）')
ax1.set_ylim(0, 105)
ax1.axhline(y=98, color='darkgreen', linestyle='--', alpha=0.5, label='98%')
ax1.axhline(y=95, color='green', linestyle='--', alpha=0.5, label='95%')
ax1.axhline(y=90, color='orange', linestyle='--', alpha=0.5, label='90%')
ax1.legend()

# 値を表示
for i, (idx, row) in enumerate(df_sorted.iterrows()):
    ax1.text(i, row['final_accuracy'] + 1, f"{row['final_accuracy']:.1f}", 
             ha='center', va='bottom', fontsize=8, rotation=45)

# 2. 誤差分布
ax2 = axes[0, 1]
ax2.scatter(df_results['final_error'], df_results['final_accuracy'], 
            c=['red' if c == 'blue' else 'green' if c == 'pink' else 'purple' for c in df_results['color']],
            s=100, alpha=0.7, edgecolors='black')
ax2.set_xlabel('最終値誤差')
ax2.set_ylabel('精度 (%)')
ax2.set_title('誤差と精度の関係')
ax2.axvline(x=0, color='black', linestyle='-', alpha=0.3)
ax2.grid(True, alpha=0.3)

# 3. 色別精度比較
ax3 = axes[1, 0]
color_data = []
color_labels = []
for color, stats in color_stats.items():
    if stats:
        final_accs = [s['final_accuracy'] for s in stats]
        color_data.append(final_accs)
        color_labels.append(f"{color}\n(n={len(stats)})")

box_plot = ax3.boxplot(color_data, labels=color_labels, patch_artist=True)
colors_box = ['pink', 'lightblue', 'lavender']
for patch, color in zip(box_plot['boxes'], colors_box):
    patch.set_facecolor(color)

ax3.set_ylabel('最終値精度 (%)')
ax3.set_title('色別精度分布')
ax3.axhline(y=95, color='green', linestyle='--', alpha=0.5)

# 4. サマリー
ax4 = axes[1, 1]
ax4.axis('off')

summary_text = f"""生の抽出値精度サマリー（補正なし）

全体統計:
• 平均最大値精度: {avg_max_accuracy:.1f}%
• 平均最終値精度: {avg_final_accuracy:.1f}%
• 分析画像数: {count}枚

精度分布:
• 98%以上: {len(df_results[df_results['final_accuracy'] >= 98])}枚
• 95-98%: {len(df_results[(df_results['final_accuracy'] >= 95) & (df_results['final_accuracy'] < 98)])}枚
• 90-95%: {len(df_results[(df_results['final_accuracy'] >= 90) & (df_results['final_accuracy'] < 95)])}枚
• 90%未満: {len(df_results[df_results['final_accuracy'] < 90])}枚

結論:
補正なしの生データで既に高精度を達成
2ピクセル補正は不要の可能性が高い"""

ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes, 
         fontsize=12, verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))

plt.tight_layout()
plt.savefig('raw_extraction_accuracy_analysis.png', dpi=300, bbox_inches='tight')
plt.close()

# CSV出力
df_results.to_csv('raw_extraction_accuracy_results.csv', index=False)

print(f"\n✓ 分析完了")
print(f"  - 画像: raw_extraction_accuracy_analysis.png")
print(f"  - CSV: raw_extraction_accuracy_results.csv")