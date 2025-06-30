#!/usr/bin/env python3
"""
有効範囲内のデータのみで精度分析
30000を超える値は除外
"""

import pandas as pd
import numpy as np
import os

def analyze_valid_range_accuracy():
    """有効範囲（-30000～30000）内のデータのみで精度分析"""
    
    # データ読み込み
    df = pd.read_csv('comprehensive_accuracy_report.csv')
    
    print("📊 有効範囲内データの精度分析")
    print("="*60)
    print("※ 実際の最大値が30,000を超えるデータは除外")
    print("="*60)
    
    # 有効範囲内のデータのみフィルタリング
    valid_df = df[
        (df['実際の最終差玉'].notna()) & 
        (df['実際の最大値'].notna()) &
        (df['実際の最大値'].abs() <= 30000)  # 30000以内
    ]
    
    excluded_df = df[
        (df['実際の最大値'].notna()) &
        (df['実際の最大値'].abs() > 30000)
    ]
    
    print(f"\n総データ数: {len(df[df['実際の最終差玉'].notna()])}件")
    print(f"有効データ数: {len(valid_df)}件")
    print(f"除外データ数: {len(excluded_df)}件")
    
    if len(excluded_df) > 0:
        print("\n除外されたデータ:")
        for _, row in excluded_df.iterrows():
            print(f"  - 画像{row['画像番号']}: 最大値 {row['実際の最大値']:.0f}玉")
    
    # 各手法の精度を計算
    print("\n" + "="*100)
    print(f"{'画像番号':<10} {'台番号':<8} {'実際の値':>10} {'従来手法':>10} {'従来誤差':>10} {'保守的SP':>12} {'SP誤差':>10} {'改善':>8}")
    print("-"*100)
    
    # 統計情報
    conventional_errors = []
    subpixel_errors = []
    improvements = []
    
    for _, row in valid_df.iterrows():
        image_num = row['画像番号']
        machine_num = row['台番号']
        actual = row['実際の最終差玉']
        conventional = row['抽出した最終差玉']
        conv_error = row['最終差玉誤差']
        
        # 保守的サブピクセル結果
        csv_path = f"graphs/conservative_subpixel_data/S__{image_num}_optimal_data.csv"
        if os.path.exists(csv_path):
            df_sp = pd.read_csv(csv_path)
            if not df_sp.empty:
                subpixel = df_sp['value'].iloc[-1]
                sp_error = subpixel - actual
                improvement = abs(conv_error) - abs(sp_error)
                
                conventional_errors.append(abs(conv_error))
                subpixel_errors.append(abs(sp_error))
                improvements.append(improvement)
                
                mark = "✅" if improvement > 0 else "❌" if improvement < -50 else "➖"
                
                print(f"{image_num:<10} {machine_num:<8} {actual:>10.0f} {conventional:>10.0f} {conv_error:>+10.0f} "
                      f"{subpixel:>12.1f} {sp_error:>+10.1f} {improvement:>7.0f} {mark}")
    
    print("-"*100)
    
    # 統計サマリー
    if conventional_errors:
        print("\n📈 有効範囲内データの統計:")
        
        conv_mean = np.mean(conventional_errors)
        sp_mean = np.mean(subpixel_errors)
        
        print(f"\n  従来手法:")
        print(f"    平均誤差: {conv_mean:.1f}玉")
        print(f"    中央値: {np.median(conventional_errors):.1f}玉")
        print(f"    標準偏差: {np.std(conventional_errors):.1f}玉")
        print(f"    最小/最大: {np.min(conventional_errors):.1f} / {np.max(conventional_errors):.1f}玉")
        
        print(f"\n  保守的サブピクセル:")
        print(f"    平均誤差: {sp_mean:.1f}玉")
        print(f"    中央値: {np.median(subpixel_errors):.1f}玉")
        print(f"    標準偏差: {np.std(subpixel_errors):.1f}玉")
        print(f"    最小/最大: {np.min(subpixel_errors):.1f} / {np.max(subpixel_errors):.1f}玉")
        
        improvement_rate = (conv_mean - sp_mean) / conv_mean * 100
        print(f"\n  全体改善率: {improvement_rate:+.1f}%")
        print(f"  改善した画像: {sum(1 for i in improvements if i > 0)}/{len(improvements)}件")
        
        # 誤差範囲別の集計
        print(f"\n🎯 誤差範囲別達成率:")
        thresholds = [50, 100, 150, 200, 300]
        
        print(f"\n{'閾値':>8} {'従来手法':>20} {'保守的サブピクセル':>25}")
        print("-"*55)
        
        for t in thresholds:
            conv_count = sum(1 for e in conventional_errors if e <= t)
            sp_count = sum(1 for e in subpixel_errors if e <= t)
            conv_rate = conv_count / len(conventional_errors) * 100
            sp_rate = sp_count / len(subpixel_errors) * 100
            
            print(f"±{t:3d}玉 {conv_count:3d}/{len(conventional_errors)}件 ({conv_rate:5.1f}%) "
                  f"{sp_count:3d}/{len(subpixel_errors)}件 ({sp_rate:5.1f}%)")
        
        # ±50玉、±100玉達成の詳細
        print(f"\n💡 高精度達成ケース:")
        
        print(f"\n  ±50玉以内:")
        for _, row in valid_df.iterrows():
            if abs(row['最終差玉誤差']) <= 50:
                print(f"    従来: 画像{row['画像番号']} (誤差 {row['最終差玉誤差']:+.0f}玉)")
        
        sp_50_count = 0
        for _, row in valid_df.iterrows():
            csv_path = f"graphs/conservative_subpixel_data/S__{row['画像番号']}_optimal_data.csv"
            if os.path.exists(csv_path):
                df_sp = pd.read_csv(csv_path)
                if not df_sp.empty:
                    sp_error = df_sp['value'].iloc[-1] - row['実際の最終差玉']
                    if abs(sp_error) <= 50:
                        print(f"    SP: 画像{row['画像番号']} (誤差 {sp_error:+.1f}玉)")
                        sp_50_count += 1
        
        print(f"\n  ±100玉以内の新規達成:")
        for _, row in valid_df.iterrows():
            if abs(row['最終差玉誤差']) > 100:  # 従来は100玉超
                csv_path = f"graphs/conservative_subpixel_data/S__{row['画像番号']}_optimal_data.csv"
                if os.path.exists(csv_path):
                    df_sp = pd.read_csv(csv_path)
                    if not df_sp.empty:
                        sp_error = abs(df_sp['value'].iloc[-1] - row['実際の最終差玉'])
                        if sp_error <= 100:
                            print(f"    画像{row['画像番号']}: {abs(row['最終差玉誤差']):.0f}玉 → {sp_error:.1f}玉")

if __name__ == "__main__":
    analyze_valid_range_accuracy()