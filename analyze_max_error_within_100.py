#!/usr/bin/env python3
"""
最大値の誤差が±100以内の画像を分析
"""

import pandas as pd
import numpy as np

# CSVファイルを読み込み
df = pd.read_csv('stable_extraction_comparison_report.csv')

# Max Diff列を数値に変換
df['Max Diff Numeric'] = df['Max Diff'].str.replace(',', '').str.replace('+', '').astype(float)

# 誤差が±100以内の画像を抽出
within_100 = df[abs(df['Max Diff Numeric']) <= 100]

print("最大値の誤差が±100以内の画像:")
print("="*60)

for idx, row in within_100.iterrows():
    print(f"{row['Image']}: 誤差 {row['Max Diff']} ({row['Max Acc %']})")

print(f"\n合計: {len(within_100)}/{len(df)}枚 ({len(within_100)/len(df)*100:.1f}%)")

print("\n詳細:")
print("-"*60)
print(within_100[['Image', 'Machine', 'Reported Max', 'Extracted Max', 'Max Diff', 'Max Acc %']])

# 誤差の分布を表示
print("\n最大値誤差の分布:")
print("-"*60)
ranges = [
    (-float('inf'), -1000, '< -1000'),
    (-1000, -500, '-1000 ~ -500'),
    (-500, -100, '-500 ~ -100'),
    (-100, -50, '-100 ~ -50'),
    (-50, 0, '-50 ~ 0'),
    (0, 50, '0 ~ 50'),
    (50, 100, '50 ~ 100'),
    (100, 500, '100 ~ 500'),
    (500, 1000, '500 ~ 1000'),
    (1000, float('inf'), '> 1000')
]

for min_val, max_val, label in ranges:
    count = len(df[(df['Max Diff Numeric'] > min_val) & (df['Max Diff Numeric'] <= max_val)])
    if count > 0:
        print(f"{label:>15}: {'#' * count} ({count})")

# 最も精度の高い画像
print("\n最も精度の高い画像 TOP 5:")
print("-"*60)
top5 = df.nlargest(5, 'Max Acc %')[['Image', 'Machine', 'Max Diff', 'Max Acc %']]
print(top5)