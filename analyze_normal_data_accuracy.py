#!/usr/bin/env python3
"""
正常データのみで±50玉精度の達成可能性を分析
異常値（極端に小さい値、ゼロ付近）を除外
"""

import pandas as pd
import numpy as np

def analyze_normal_data_accuracy():
    """正常データのみで精度分析"""
    
    # データ読み込み
    df = pd.read_csv('comprehensive_accuracy_report.csv')
    
    # 異常値の定義と除外
    # 1. 最終差玉の絶対値が1000玉未満（ゼロ付近）
    # 2. 誤差が極端に大きい（500玉以上）
    
    print("📊 全データの分析")
    print("="*60)
    
    valid_df = df[df['最終差玉誤差'].notna()]
    print(f"総データ数: {len(valid_df)}件")
    print(f"平均誤差: {valid_df['最終差玉誤差'].abs().mean():.0f}玉")
    
    # 異常値を除外
    normal_df = valid_df[
        (valid_df['実際の最終差玉'].abs() >= 1000) &  # 1000玉以上の変動があるもの
        (valid_df['最終差玉誤差'].abs() < 500)        # 誤差500玉未満
    ]
    
    print(f"\n異常値除外後: {len(normal_df)}件")
    
    # 正常データの詳細分析
    print("\n📊 正常データの分析")
    print("="*60)
    
    errors = normal_df['最終差玉誤差'].abs()
    
    # 誤差分布
    ranges = [50, 100, 150, 200, 250, 300]
    
    print("\n誤差分布:")
    for i, threshold in enumerate(ranges):
        count = len(errors[errors <= threshold])
        percentage = count / len(normal_df) * 100
        print(f"±{threshold:3d}玉以内: {count:2d}件 ({percentage:5.1f}%)")
    
    # 統計情報
    print(f"\n統計情報:")
    print(f"平均誤差: {errors.mean():.1f}玉")
    print(f"中央値: {errors.median():.1f}玉")
    print(f"標準偏差: {errors.std():.1f}玉")
    print(f"最小誤差: {errors.min():.1f}玉")
    print(f"最大誤差: {errors.max():.1f}玉")
    
    # 個別データ表示
    print("\n📋 正常データの詳細:")
    print("="*60)
    
    # 誤差の小さい順にソート
    sorted_df = normal_df.sort_values('最終差玉誤差', key=abs)
    
    for _, row in sorted_df.iterrows():
        print(f"\n画像{row['画像番号']} ({row['機種']}):")
        print(f"  実際: {row['実際の最終差玉']:6.0f}玉")
        print(f"  抽出: {row['抽出した最終差玉']:6.0f}玉")
        print(f"  誤差: {row['最終差玉誤差']:+6.0f}玉 (精度: {row['最終差玉精度(%)']:.1f}%)")
    
    # ±50玉達成の可能性評価
    print("\n" + "="*60)
    print("🎯 ±50玉精度達成の可能性評価")
    print("="*60)
    
    # 現在の達成率
    within_50 = len(errors[errors <= 50])
    current_rate = within_50 / len(normal_df) * 100
    
    print(f"\n現在の達成率: {within_50}/{len(normal_df)}件 ({current_rate:.1f}%)")
    
    # 必要な改善率を計算
    target_rate = 80  # 目標: 80%以上
    if current_rate < target_rate:
        required_improvement = (errors.mean() - 50) / errors.mean() * 100
        print(f"目標達成率: {target_rate}%")
        print(f"必要な改善率: {required_improvement:.1f}%")
    
    # 改善可能性の評価
    print("\n📈 改善可能性の評価:")
    
    # ピクセル精度の計算（1ピクセル = 約122玉）
    pixel_to_value = 60000 / 491  # Y軸範囲 / 高さ
    print(f"1ピクセルの誤差: 約{pixel_to_value:.0f}玉")
    
    # 現在の平均誤差をピクセル単位で表示
    avg_pixel_error = errors.mean() / pixel_to_value
    print(f"現在の平均誤差: 約{avg_pixel_error:.1f}ピクセル")
    
    # ±50玉はピクセル単位で
    target_pixel_error = 50 / pixel_to_value
    print(f"目標誤差(±50玉): 約{target_pixel_error:.1f}ピクセル")
    
    # 結論
    print("\n💡 結論:")
    if avg_pixel_error < 1.0:
        print("すでにサブピクセル精度が必要なレベルです。")
        print("±50玉の達成は物理的に困難です。")
    elif avg_pixel_error < 2.0:
        print("現在1-2ピクセルの精度です。")
        print("サブピクセル補間などの高度な技術で改善の余地があります。")
    else:
        print("まだ改善の余地があります。")
        print("アルゴリズムの最適化で±50玉に近づける可能性があります。")

if __name__ == "__main__":
    analyze_normal_data_accuracy()