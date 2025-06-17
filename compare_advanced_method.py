#!/usr/bin/env python3
"""
高度な手法の精度比較
"""

import pandas as pd
import os
import numpy as np

def compare_advanced_method():
    """高度な手法と他の手法を比較"""
    
    # 実際の値
    actual_data = pd.read_csv('comprehensive_accuracy_report.csv')
    
    # 有効範囲内のデータのみフィルタリング
    valid_df = actual_data[
        (actual_data['実際の最終差玉'].notna()) & 
        (actual_data['実際の最大値'].notna()) &
        (actual_data['実際の最大値'].abs() <= 30000)
    ]
    
    print("🚀 高度な手法の精度比較（有効範囲データのみ）")
    print("="*120)
    print(f"{'画像番号':<10} {'実際の値':>10} {'従来手法':>10} {'従来誤差':>10} {'保守的SP':>12} {'SP誤差':>10} {'高度な手法':>12} {'高度誤差':>10} {'改善':>8}")
    print("-"*120)
    
    # 統計情報
    conventional_errors = []
    subpixel_errors = []
    advanced_errors = []
    improvements = []
    
    for _, row in valid_df.iterrows():
        image_num = row['画像番号']
        actual = row['実際の最終差玉']
        conventional = row['抽出した最終差玉']
        conv_error = row['最終差玉誤差']
        
        # 保守的サブピクセル結果
        sp_value = None
        sp_error = None
        csv_path = f"graphs/conservative_subpixel_data/S__{image_num}_optimal_data.csv"
        if os.path.exists(csv_path):
            df_sp = pd.read_csv(csv_path)
            if not df_sp.empty:
                sp_value = df_sp['value'].iloc[-1]
                sp_error = sp_value - actual
        
        # 高度な手法の結果
        adv_value = None
        adv_error = None
        csv_path = f"graphs/advanced_extracted_data/S__{image_num}_optimal_data.csv"
        if os.path.exists(csv_path):
            df_adv = pd.read_csv(csv_path)
            if not df_adv.empty:
                adv_value = df_adv['value'].iloc[-1]
                adv_error = adv_value - actual
                
                if sp_error is not None:
                    improvement = abs(sp_error) - abs(adv_error)
                else:
                    improvement = abs(conv_error) - abs(adv_error)
                
                conventional_errors.append(abs(conv_error))
                if sp_error is not None:
                    subpixel_errors.append(abs(sp_error))
                if adv_error is not None:
                    advanced_errors.append(abs(adv_error))
                    improvements.append(improvement)
                
                mark = "✅" if improvement > 0 else "❌" if improvement < -50 else "➖"
                
                sp_str = f"{sp_value:>12.1f}" if sp_value is not None else "     -      "
                sp_err_str = f"{sp_error:>+10.1f}" if sp_error is not None else "     -    "
                
                print(f"{image_num:<10} {actual:>10.0f} {conventional:>10.0f} {conv_error:>+10.0f} "
                      f"{sp_str} {sp_err_str} {adv_value:>12.1f} {adv_error:>+10.1f} {improvement:>7.0f} {mark}")
    
    print("-"*120)
    
    # 統計サマリー
    if advanced_errors:
        print("\n📈 統計サマリー:")
        
        print(f"\n  従来手法:")
        print(f"    平均誤差: {np.mean(conventional_errors):.1f}玉")
        print(f"    中央値: {np.median(conventional_errors):.1f}玉")
        print(f"    標準偏差: {np.std(conventional_errors):.1f}玉")
        
        if subpixel_errors:
            print(f"\n  保守的サブピクセル:")
            print(f"    平均誤差: {np.mean(subpixel_errors):.1f}玉")
            print(f"    中央値: {np.median(subpixel_errors):.1f}玉")
            print(f"    標準偏差: {np.std(subpixel_errors):.1f}玉")
        
        print(f"\n  高度な手法:")
        print(f"    平均誤差: {np.mean(advanced_errors):.1f}玉")
        print(f"    中央値: {np.median(advanced_errors):.1f}玉")
        print(f"    標準偏差: {np.std(advanced_errors):.1f}玉")
        print(f"    最小/最大: {np.min(advanced_errors):.1f} / {np.max(advanced_errors):.1f}玉")
        
        # 誤差範囲別の集計
        print(f"\n🎯 誤差範囲別達成率:")
        thresholds = [50, 100, 150, 200, 300]
        
        print(f"\n{'閾値':>8} {'従来手法':>20} {'保守的SP':>20} {'高度な手法':>25}")
        print("-"*75)
        
        for t in thresholds:
            conv_count = sum(1 for e in conventional_errors if e <= t)
            sp_count = sum(1 for e in subpixel_errors if e <= t) if subpixel_errors else 0
            adv_count = sum(1 for e in advanced_errors if e <= t)
            
            conv_rate = conv_count / len(conventional_errors) * 100
            sp_rate = sp_count / len(subpixel_errors) * 100 if subpixel_errors else 0
            adv_rate = adv_count / len(advanced_errors) * 100
            
            sp_str = f"{sp_count:3d}/{len(subpixel_errors)}件 ({sp_rate:5.1f}%)" if subpixel_errors else "     -     "
            
            print(f"±{t:3d}玉 {conv_count:3d}/{len(conventional_errors)}件 ({conv_rate:5.1f}%) "
                  f"{sp_str} "
                  f"{adv_count:3d}/{len(advanced_errors)}件 ({adv_rate:5.1f}%)")
        
        # 高精度達成ケース
        print(f"\n💡 ±50玉以内を達成したケース（高度な手法）:")
        count_50 = 0
        for _, row in valid_df.iterrows():
            csv_path = f"graphs/advanced_extracted_data/S__{row['画像番号']}_optimal_data.csv"
            if os.path.exists(csv_path):
                df_adv = pd.read_csv(csv_path)
                if not df_adv.empty:
                    adv_error = df_adv['value'].iloc[-1] - row['実際の最終差玉']
                    if abs(adv_error) <= 50:
                        print(f"  画像{row['画像番号']}: 誤差 {adv_error:+.1f}玉")
                        count_50 += 1
        
        if count_50 == 0:
            print("  （該当なし）")
        
        # 改善率
        if subpixel_errors:
            sp_improvement = (np.mean(subpixel_errors) - np.mean(advanced_errors)) / np.mean(subpixel_errors) * 100
            print(f"\n📊 保守的サブピクセルからの改善率: {sp_improvement:+.1f}%")
        
        conv_improvement = (np.mean(conventional_errors) - np.mean(advanced_errors)) / np.mean(conventional_errors) * 100
        print(f"📊 従来手法からの改善率: {conv_improvement:+.1f}%")

if __name__ == "__main__":
    compare_advanced_method()