#!/usr/bin/env python3
"""
全画像で2ピクセル補正ありなしを比較
"""

import pandas as pd
import numpy as np
import csv
import os

# results.txtを読み込み
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

# 境界設定
boundaries = {
    "start_x": 36,
    "end_x": 620,
    "top_y": 26,
    "bottom_y": 523,
    "zero_y": 274
}

def y_to_value_no_correction(y):
    """Y座標を値に変換（補正なし）"""
    zero_y = boundaries["zero_y"]
    top_y = boundaries["top_y"]
    bottom_y = boundaries["bottom_y"]
    
    if y < zero_y:
        value = (zero_y - y) / (zero_y - top_y) * 30000
    else:
        value = -(y - zero_y) / (bottom_y - zero_y) * 30000
    
    return np.clip(value, -30000, 30000)

print("全画像での2ピクセル補正比較")
print("="*120)
print(f"{'画像':20} {'色':6} {'実際の最大':>8} {'補正あり':>8} {'補正なし':>8} {'改善':>6} | {'実際の最終':>8} {'補正あり':>8} {'補正なし':>8} {'改善':>6}")
print("-"*120)

total_improved_max = 0
total_improved_final = 0
total_count = 0

pink_improved = 0
blue_improved = 0
purple_improved = 0

for base_name, actual in results.items():
    csv_path = f'graphs/stable_extracted_data/{base_name}_optimal_stable_data.csv'
    
    if not os.path.exists(csv_path):
        continue
    
    df = pd.read_csv(csv_path)
    
    # 色を取得（extraction_summary.csvから）
    color = 'unknown'
    summary_df = pd.read_csv('graphs/stable_extracted_data/extraction_summary.csv')
    color_row = summary_df[summary_df['file_name'] == f'{base_name}_optimal']
    if not color_row.empty:
        color = color_row.iloc[0]['color']
    
    # 補正なしで値を再計算
    no_correction_values = []
    for _, row in df.iterrows():
        value = y_to_value_no_correction(row['y'])
        no_correction_values.append(value)
    
    # 比較
    max_with = df['smoothed_value'].max()
    max_no = max(no_correction_values)
    final_with = df['smoothed_value'].iloc[-1]
    final_no = no_correction_values[-1]
    
    # 誤差
    max_error_with = abs(max_with - actual['actual_max'])
    max_error_no = abs(max_no - actual['actual_max'])
    final_error_with = abs(final_with - actual['actual_final'])
    final_error_no = abs(final_no - actual['actual_final'])
    
    # 改善判定
    max_improved = '◎' if max_error_no < max_error_with else '×'
    final_improved = '◎' if final_error_no < final_error_with else '×'
    
    if max_error_no < max_error_with:
        total_improved_max += 1
        if color == 'pink': pink_improved += 1
        elif color == 'blue': blue_improved += 1
        elif color == 'purple': purple_improved += 1
    
    if final_error_no < final_error_with:
        total_improved_final += 1
    
    total_count += 1
    
    print(f"{base_name:20} {color:6} {actual['actual_max']:>8.0f} {max_with:>8.0f} {max_no:>8.0f} {max_improved:>6} | {actual['actual_final']:>8.0f} {final_with:>8.0f} {final_no:>8.0f} {final_improved:>6}")

print("-"*120)
print(f"\n補正なしの方が改善した画像数:")
print(f"  最大値: {total_improved_max}/{total_count} ({total_improved_max/total_count*100:.1f}%)")
print(f"  最終値: {total_improved_final}/{total_count} ({total_improved_final/total_count*100:.1f}%)")

print(f"\n色別の最大値改善数:")
print(f"  ピンク: {pink_improved}枚")
print(f"  青: {blue_improved}枚")
print(f"  紫: {purple_improved}枚")