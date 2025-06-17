#!/usr/bin/env python3
"""
誤差が大きい画像の分析
"""

import pandas as pd
import numpy as np

# CSVファイルを読み込み
df = pd.read_csv('stable_extraction_comparison_report.csv')

# Max Diff列を数値に変換
df['Max Diff Numeric'] = df['Max Diff'].str.replace(',', '').str.replace('+', '').astype(float)
df['Max Error Abs'] = abs(df['Max Diff Numeric'])

# 誤差の大きい順にソート
df_sorted = df.sort_values('Max Error Abs', ascending=False)

print("最大値の誤差が大きい画像（絶対値順）:")
print("="*80)

# 誤差カテゴリ別に分類
categories = [
    (1000, float('inf'), '誤差 > 1000'),
    (500, 1000, '誤差 500-1000'),
    (200, 500, '誤差 200-500'),
    (100, 200, '誤差 100-200'),
    (0, 100, '誤差 < 100')
]

for min_err, max_err, label in categories:
    category_df = df_sorted[(df_sorted['Max Error Abs'] >= min_err) & (df_sorted['Max Error Abs'] < max_err)]
    if len(category_df) > 0:
        print(f"\n{label}:")
        print("-"*80)
        for idx, row in category_df.iterrows():
            print(f"{row['Image']:15} {row['Machine']:20} 実際:{row['Reported Max']:>8} → 抽出:{row['Extracted Max']:>8} (誤差:{row['Max Diff']:>8}, 精度:{row['Max Acc %']:>6})")

# 統計情報
print("\n\n誤差統計:")
print("="*80)
print(f"平均絶対誤差: {df['Max Error Abs'].mean():.0f}")
print(f"中央値絶対誤差: {df['Max Error Abs'].median():.0f}")
print(f"標準偏差: {df['Max Error Abs'].std():.0f}")

# 誤差が大きい原因を分析
print("\n\n誤差が特に大きい画像の詳細:")
print("="*80)
large_error_df = df_sorted[df_sorted['Max Error Abs'] > 500]
for idx, row in large_error_df.iterrows():
    print(f"\n{row['Image']}:")
    print(f"  機種: {row['Machine']}")
    print(f"  実際の最大値: {row['Reported Max']}")
    print(f"  抽出最大値: {row['Extracted Max']}")
    print(f"  誤差: {row['Max Diff']} ({row['Max Error Abs']:.0f})")
    print(f"  精度: {row['Max Acc %']}")
    
    # 誤差の割合を計算
    reported_val = float(row['Reported Max'].replace(',', ''))
    error_ratio = row['Max Error Abs'] / reported_val * 100
    print(f"  誤差率: {error_ratio:.1f}%")

# 機種別の誤差分析
print("\n\n機種別の最大値誤差分析:")
print("="*80)
machine_stats = df.groupby('Machine')['Max Error Abs'].agg(['mean', 'median', 'std', 'count'])
print(machine_stats)