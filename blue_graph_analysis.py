#!/usr/bin/env python3
"""
青いグラフの精度分析
"""

import pandas as pd

# CSVファイルを読み込み
df = pd.read_csv('stable_extraction_comparison_report.csv')

# 機種でフィルタリング（青いグラフが多い）
blue_machine = df[df['Machine'] == 'e Re：ゼロから始める異世'].copy()

print("青いグラフが多い機種の分析:")
print("="*60)

# 数値に変換
for col in ['Max Diff', 'Final Diff']:
    blue_machine.loc[:, col] = blue_machine[col].str.replace(',', '').str.replace('+', '').astype(float)

for col in ['Max Acc %', 'Final Acc %']:
    blue_machine.loc[:, col] = blue_machine[col].str.replace('%', '').astype(float)

# 各画像の詳細
print("\n画像別詳細:")
for idx, row in blue_machine.iterrows():
    print(f"\n{row['Image']}:")
    print(f"  最大値: 実際 {row['Reported Max']} → 抽出 {row['Extracted Max']} (精度 {row['Max Acc %']:.1f}%)")
    print(f"  最終値: 実際 {row['Reported Final']} → 抽出 {row['Extracted Final']} (精度 {row['Final Acc %']:.1f}%)")
    
    # 調整係数を計算
    try:
        reported_final = float(row['Reported Final'].replace(',', ''))
        extracted_final = float(row['Extracted Final'].replace(',', ''))
        if extracted_final != 0:
            adjustment_factor = reported_final / extracted_final
            print(f"  必要な調整係数: {adjustment_factor:.4f}")
    except:
        pass

# 統計
print("\n\n統計情報:")
print(f"平均最大値精度: {blue_machine['Max Acc %'].mean():.1f}%")
print(f"平均最終値精度: {blue_machine['Final Acc %'].mean():.1f}%")

# 低精度の画像を特定
low_accuracy = blue_machine[blue_machine['Final Acc %'] < 80]
print(f"\n最終値精度80%未満の画像: {len(low_accuracy)}枚")
for idx, row in low_accuracy.iterrows():
    print(f"  - {row['Image']}: {row['Final Acc %']:.1f}%")