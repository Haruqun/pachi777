#!/usr/bin/env python3
"""
改良版抽出器の精度チェック
"""

import pandas as pd
import numpy as np
import csv
import os

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

print("改良版グラフ抽出器の精度チェック")
print("=" * 120)
print(f"{'画像':20} {'色':6} {'実際の最大':>10} {'抽出':>10} {'誤差':>8} {'精度%':>8} | {'実際の最終':>10} {'抽出':>10} {'誤差':>8} {'精度%':>8}")
print("-" * 120)

total_max_error = 0
total_final_error = 0
count = 0

# 色別統計
color_stats = {'pink': [], 'blue': [], 'purple': []}

# サマリー読み込み
summary_df = pd.read_csv('graphs/accurate_extracted_data/extraction_summary.csv')

for _, summary_row in summary_df.iterrows():
    base_name = summary_row['file_name'].replace('_optimal', '')
    
    if base_name not in results:
        continue
    
    actual = results[base_name]
    color = summary_row['color']
    
    # CSVデータ読み込み
    csv_path = f'graphs/accurate_extracted_data/{summary_row["file_name"]}_accurate_data.csv'
    if not os.path.exists(csv_path):
        continue
    
    df = pd.read_csv(csv_path)
    
    # 抽出値
    extracted_max = df['smoothed_value'].max()
    extracted_final = df['smoothed_value'].iloc[-1]
    
    # 誤差計算
    max_error = extracted_max - actual['actual_max']
    final_error = extracted_final - actual['actual_final']
    
    # 精度計算（300で割る方式）
    max_accuracy = 100 - abs(max_error) / 300
    final_accuracy = 100 - abs(final_error) / 300
    
    # 統計に追加
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
    print(f"{base_name:20} {color:6} {actual['actual_max']:>10.0f} {extracted_max:>10.0f} "
          f"{max_error:>+8.0f} {max_accuracy:>7.1f}% | "
          f"{actual['actual_final']:>10.0f} {extracted_final:>10.0f} "
          f"{final_error:>+8.0f} {final_accuracy:>7.1f}%")

print("-" * 120)

# 全体統計
avg_max_error = total_max_error / count
avg_final_error = total_final_error / count
avg_max_accuracy = 100 - avg_max_error / 300
avg_final_accuracy = 100 - avg_final_error / 300

print(f"\n全体統計:")
print(f"  平均最大値誤差: {avg_max_error:.0f} ({avg_max_accuracy:.1f}%)")
print(f"  平均最終値誤差: {avg_final_error:.0f} ({avg_final_accuracy:.1f}%)")

# 色別統計
print(f"\n色別精度:")
for color, stats in color_stats.items():
    if stats:
        avg_max_acc = np.mean([s['max_accuracy'] for s in stats])
        avg_final_acc = np.mean([s['final_accuracy'] for s in stats])
        print(f"  {color}: 最大値 {avg_max_acc:.1f}%, 最終値 {avg_final_acc:.1f}% (n={len(stats)})")

# 精度分布
print(f"\n精度分布:")
accuracy_ranges = [(98, 100), (95, 98), (90, 95), (0, 90)]
for min_acc, max_acc in accuracy_ranges:
    count_in_range = sum(1 for _, summary_row in summary_df.iterrows()
                        if summary_row['file_name'].replace('_optimal', '') in results
                        for csv_path in [f'graphs/accurate_extracted_data/{summary_row["file_name"]}_accurate_data.csv']
                        if os.path.exists(csv_path)
                        for df in [pd.read_csv(csv_path)]
                        for final_val in [df['smoothed_value'].iloc[-1]]
                        for actual_final in [results[summary_row['file_name'].replace('_optimal', '')]['actual_final']]
                        for accuracy in [100 - abs(final_val - actual_final) / 300]
                        if min_acc <= accuracy < max_acc)
    
    if max_acc == 100:
        print(f"  {min_acc}%以上: {count_in_range}枚")
    else:
        print(f"  {min_acc}-{max_acc}%: {count_in_range}枚")