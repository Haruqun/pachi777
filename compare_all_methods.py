#!/usr/bin/env python3
"""
全手法の精度比較
- 従来手法
- 保守的サブピクセル
"""

import pandas as pd
import os
import numpy as np

def compare_all_methods():
    """全手法の精度比較"""
    
    # 実際の値
    actual_data = pd.read_csv('comprehensive_accuracy_report.csv')
    
    print("📊 全手法の精度比較")
    print("="*100)
    print(f"{'画像番号':<10} {'実際の値':>10} {'従来手法':>10} {'従来誤差':>10} {'保守的SP':>12} {'SP誤差':>10} {'改善':>8}")
    print("-"*100)
    
    # 統計情報
    conventional_errors = []
    subpixel_errors = []
    improvements = []
    
    # 各画像について比較
    for _, row in actual_data.iterrows():
        if pd.isna(row['実際の最終差玉']):
            continue
            
        image_num = row['画像番号']
        actual = row['実際の最終差玉']
        conventional = row['抽出した最終差玉']
        conv_error = row['最終差玉誤差']
        
        # 保守的サブピクセル結果を読み込み
        csv_path = f"graphs/conservative_subpixel_data/S__{image_num}_optimal_data.csv"
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if not df.empty:
                subpixel = df['value'].iloc[-1]
                sp_error = subpixel - actual
                improvement = abs(conv_error) - abs(sp_error)
                
                conventional_errors.append(abs(conv_error))
                subpixel_errors.append(abs(sp_error))
                improvements.append(improvement)
                
                # 改善マーク
                mark = "✅" if improvement > 0 else "❌" if improvement < -50 else "➖"
                
                print(f"{image_num:<10} {actual:>10.0f} {conventional:>10.0f} {conv_error:>+10.0f} "
                      f"{subpixel:>12.1f} {sp_error:>+10.1f} {improvement:>7.0f} {mark}")
    
    print("-"*100)
    
    # 統計サマリー
    conv_mean = np.mean(conventional_errors)
    sp_mean = np.mean(subpixel_errors)
    total_improvement = (conv_mean - sp_mean) / conv_mean * 100
    
    print(f"\n📈 統計サマリー:")
    print(f"  従来手法:")
    print(f"    平均誤差: {conv_mean:.1f}玉")
    print(f"    中央値: {np.median(conventional_errors):.1f}玉")
    print(f"    最小誤差: {np.min(conventional_errors):.1f}玉")
    print(f"    最大誤差: {np.max(conventional_errors):.1f}玉")
    
    print(f"\n  保守的サブピクセル:")
    print(f"    平均誤差: {sp_mean:.1f}玉")
    print(f"    中央値: {np.median(subpixel_errors):.1f}玉")
    print(f"    最小誤差: {np.min(subpixel_errors):.1f}玉")
    print(f"    最大誤差: {np.max(subpixel_errors):.1f}玉")
    
    print(f"\n  改善率: {total_improvement:.1f}%")
    print(f"  改善した画像数: {sum(1 for i in improvements if i > 0)}/{len(improvements)}件")
    
    # 誤差範囲別の集計
    print(f"\n🎯 誤差範囲別集計:")
    thresholds = [50, 100, 150, 200, 300]
    
    print(f"\n  従来手法:")
    for t in thresholds:
        count = sum(1 for e in conventional_errors if e <= t)
        print(f"    ±{t:3d}玉以内: {count:2d}/{len(conventional_errors)}件 ({count/len(conventional_errors)*100:5.1f}%)")
    
    print(f"\n  保守的サブピクセル:")
    for t in thresholds:
        count = sum(1 for e in subpixel_errors if e <= t)
        print(f"    ±{t:3d}玉以内: {count:2d}/{len(subpixel_errors)}件 ({count/len(subpixel_errors)*100:5.1f}%)")
    
    # 最も改善した/悪化したケース
    if improvements:
        best_idx = np.argmax(improvements)
        worst_idx = np.argmin(improvements)
        
        print(f"\n💡 特筆すべきケース:")
        print(f"  最大改善: 画像{actual_data.iloc[best_idx]['画像番号']} ({improvements[best_idx]:.0f}玉改善)")
        print(f"  最大悪化: 画像{actual_data.iloc[worst_idx]['画像番号']} ({-improvements[worst_idx]:.0f}玉悪化)")

if __name__ == "__main__":
    compare_all_methods()