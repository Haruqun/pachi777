#!/usr/bin/env python3
"""
安定版手法の精度を確認
"""

import pandas as pd
import csv

# results.txtを読み込み
results = {}
with open('results.txt', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        base_name = row['画像名'].replace('.jpg', '')
        # 空の値をスキップ
        if row['実際の最大値'] and row['実際の最終差玉']:
            results[base_name] = {
                '実際の最大値': float(row['実際の最大値'].replace(',', '')),
                '実際の最終値': float(row['実際の最終差玉'].replace(',', ''))
            }

# 抽出結果を読み込み
df = pd.read_csv('graphs/stable_extracted_data/extraction_summary.csv')

print("安定版手法の精度確認")
print("="*80)
print(f"{'画像名':<20} {'実際の最大値':>10} {'抽出最大値':>10} {'誤差':>10} {'実際の最終値':>10} {'抽出最終値':>10} {'誤差':>10}")
print("-"*80)

total_max_error = 0
total_final_error = 0
count = 0

for _, row in df.iterrows():
    file_name = row['file_name'].replace('_optimal', '')
    if file_name in results:
        actual = results[file_name]
        max_error = row['max_value'] - actual['実際の最大値']
        final_error = row['final_value'] - actual['実際の最終値']
        
        total_max_error += abs(max_error)
        total_final_error += abs(final_error)
        count += 1
        
        print(f"{file_name:<20} {actual['実際の最大値']:>10.0f} {row['max_value']:>10.0f} {max_error:>+10.0f} {actual['実際の最終値']:>10.0f} {row['final_value']:>10.0f} {final_error:>+10.0f}")

print("-"*80)
print(f"平均絶対誤差: 最大値 {total_max_error/count:.0f}, 最終値 {total_final_error/count:.0f}")
print(f"平均精度: 最大値 {100 - total_max_error/count/300:.1f}%, 最終値 {100 - total_final_error/count/300:.1f}%")