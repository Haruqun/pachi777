#!/usr/bin/env python3
"""
サブピクセル精度の改善効果を比較
"""

import pandas as pd
import os

def compare_accuracy():
    """精度比較"""
    
    # 実際の値（results.txtから）
    actual_values = {
        "S__78209160": {"最終差玉": 3010, "画像番号": "160"},
        "S__78209132": {"最終差玉": 28935, "画像番号": "132"},
        "S__78209128": {"最終差玉": 6771, "画像番号": "128"},
        "S__78209174": {"最終差玉": 8000, "画像番号": "174"},
        "S__78209088": {"最終差玉": 3125, "画像番号": "088"},
    }
    
    # 従来の抽出結果
    conventional = {
        "S__78209160": 2994,
        "S__78209132": 29022,
        "S__78209128": 6660,
        "S__78209174": 7882,
        "S__78209088": 2994,
    }
    
    print("📊 サブピクセル精度の改善効果")
    print("="*80)
    print(f"{'画像番号':<15} {'実際の値':>10} {'従来手法':>10} {'従来誤差':>10} {'サブピクセル':>12} {'改善誤差':>10} {'改善率':>8}")
    print("-"*80)
    
    total_conventional_error = 0
    total_subpixel_error = 0
    improvements = []
    
    for image_name, actual_data in actual_values.items():
        actual = actual_data["最終差玉"]
        conv = conventional[image_name]
        conv_error = conv - actual
        
        # サブピクセル結果を読み込み
        csv_path = f"graphs/subpixel_extracted_data/{image_name}_optimal_subpixel_data.csv"
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if not df.empty:
                subpixel = df['value'].iloc[-1]
                subpixel_error = subpixel - actual
                
                improvement = abs(conv_error) - abs(subpixel_error)
                improvement_rate = (improvement / abs(conv_error) * 100) if conv_error != 0 else 0
                
                total_conventional_error += abs(conv_error)
                total_subpixel_error += abs(subpixel_error)
                improvements.append(improvement_rate)
                
                print(f"{actual_data['画像番号']:<15} {actual:>10,} {conv:>10,} {conv_error:>+10} {subpixel:>12.1f} {subpixel_error:>+10.1f} {improvement_rate:>7.1f}%")
    
    print("-"*80)
    
    # 平均改善率
    avg_improvement = sum(improvements) / len(improvements) if improvements else 0
    total_improvement = (total_conventional_error - total_subpixel_error) / total_conventional_error * 100
    
    print(f"\n📈 改善サマリー:")
    print(f"  従来手法の平均誤差: {total_conventional_error / len(actual_values):.0f}玉")
    print(f"  サブピクセルの平均誤差: {total_subpixel_error / len(actual_values):.1f}玉")
    print(f"  平均改善率: {avg_improvement:.1f}%")
    print(f"  総合改善率: {total_improvement:.1f}%")
    
    # ±50玉、±100玉の達成状況
    within_50 = sum(1 for image_name in actual_values 
                   if os.path.exists(f"graphs/subpixel_extracted_data/{image_name}_optimal_subpixel_data.csv"))
    
    subpixel_errors = []
    for image_name, actual_data in actual_values.items():
        csv_path = f"graphs/subpixel_extracted_data/{image_name}_optimal_subpixel_data.csv"
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if not df.empty:
                actual = actual_data["最終差玉"]
                subpixel = df['value'].iloc[-1]
                error = abs(subpixel - actual)
                subpixel_errors.append(error)
    
    if subpixel_errors:
        within_50 = sum(1 for e in subpixel_errors if e <= 50)
        within_100 = sum(1 for e in subpixel_errors if e <= 100)
        
        print(f"\n🎯 精度達成状況:")
        print(f"  ±50玉以内: {within_50}/{len(subpixel_errors)}件 ({within_50/len(subpixel_errors)*100:.0f}%)")
        print(f"  ±100玉以内: {within_100}/{len(subpixel_errors)}件 ({within_100/len(subpixel_errors)*100:.0f}%)")

if __name__ == "__main__":
    compare_accuracy()