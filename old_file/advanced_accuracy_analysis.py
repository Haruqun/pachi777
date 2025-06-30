#!/usr/bin/env python3
"""
改良されたAdvanced Graph Extractorの精度分析
results.txtの実際の最終差玉と比較
"""

import pandas as pd
import numpy as np
import os
import csv

def parse_results_txt():
    """results.txtを解析して実際の値を取得（異常値を除外）"""
    actual_values = {}
    excluded_cases = []
    
    with open('results.txt', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # ヘッダーをスキップ
        
        for row in reader:
            if len(row) >= 6:
                image_name = row[0]  # S__78209088.jpg
                image_num = row[1]
                machine_num = row[2]
                actual_max = row[4]   # 実際の最大値
                actual_final = row[5]  # 実際の最終差玉
                
                # 画像名からベース名を抽出 (S__78209088.jpg -> S__78209088_optimal)
                if image_name.endswith('.jpg'):
                    base_name = image_name.replace('.jpg', '_optimal')
                else:
                    base_name = f"S__{image_num}_optimal"
                
                # カンマを除去して数値に変換
                try:
                    actual_max_value = float(actual_max.replace(',', ''))
                    actual_final_value = float(actual_final.replace(',', ''))
                    
                    # ±30000を超える最大値は異常値として除外
                    if abs(actual_max_value) > 30000:
                        excluded_cases.append({
                            'image_num': image_num,
                            'machine_num': machine_num,
                            'actual_max': actual_max_value,
                            'reason': f'最大値{actual_max_value:,.0f}玉が±30000を超過'
                        })
                        continue
                    
                    actual_values[base_name] = {
                        'image_num': image_num,
                        'machine_num': machine_num,
                        'actual_max': actual_max_value,
                        'actual_final': actual_final_value
                    }
                except ValueError:
                    continue
    
    return actual_values, excluded_cases

def analyze_advanced_accuracy():
    """Advanced Graph Extractorの精度を分析"""
    print("📊 Advanced Graph Extractor 精度分析")
    print("="*60)
    print("※ 最大値が±30000を超えるデータは異常値として除外")
    print("="*60)
    
    # 実際の値を取得（異常値除外）
    actual_values, excluded_cases = parse_results_txt()
    
    # 除外されたケースを表示
    if excluded_cases:
        print("\n🚫 除外された異常値ケース:")
        for case in excluded_cases:
            print(f"  画像{case['image_num']} (台{case['machine_num']}): {case['reason']}")
        print()
    
    # Advanced extractorの結果フォルダ
    results_folder = "graphs/advanced_extracted_data"
    
    comparison_data = []
    
    print(f"{'画像番号':<8} {'台番号':<8} {'最大値':>10} {'実際の値':>12} {'抽出値':>12} {'誤差':>12} {'精度':<8}")
    print("-" * 80)
    
    total_error = 0
    valid_count = 0
    errors = []
    
    for base_name, actual_data in actual_values.items():
        csv_path = os.path.join(results_folder, f"{base_name}_data.csv")
        
        if os.path.exists(csv_path):
            try:
                # 抽出されたデータを読み込み
                df = pd.read_csv(csv_path)
                
                if not df.empty and 'value' in df.columns:
                    extracted_final = df['value'].iloc[-1]  # 最終値
                    actual_final = actual_data['actual_final']
                    actual_max = actual_data['actual_max']
                    
                    error = extracted_final - actual_final
                    abs_error = abs(error)
                    
                    # 精度評価
                    if abs_error <= 100:
                        accuracy = "✅優秀"
                    elif abs_error <= 300:
                        accuracy = "🟡良好"
                    elif abs_error <= 500:
                        accuracy = "🟠普通"
                    else:
                        accuracy = "❌要改善"
                    
                    print(f"{actual_data['image_num']:<8} {actual_data['machine_num']:<8} "
                          f"{actual_max:>10,.0f} {actual_final:>12,.0f} {extracted_final:>12,.1f} "
                          f"{error:>+12,.0f} {accuracy:<8}")
                    
                    comparison_data.append({
                        'image_num': actual_data['image_num'],
                        'machine_num': actual_data['machine_num'],
                        'actual_max': actual_max,
                        'actual_final': actual_final,
                        'extracted_final': extracted_final,
                        'error': error,
                        'abs_error': abs_error
                    })
                    
                    errors.append(abs_error)
                    total_error += abs_error
                    valid_count += 1
                
            except Exception as e:
                print(f"エラー {base_name}: {e}")
        else:
            print(f"ファイルが見つかりません: {csv_path}")
    
    print("-" * 80)
    
    # 統計情報
    if valid_count > 0:
        mean_error = np.mean(errors)
        median_error = np.median(errors)
        std_error = np.std(errors)
        min_error = np.min(errors)
        max_error = np.max(errors)
        
        print(f"\n📈 統計サマリー (対象: {valid_count}件)")
        print(f"  平均誤差: {mean_error:.1f}玉")
        print(f"  中央値誤差: {median_error:.1f}玉")
        print(f"  標準偏差: {std_error:.1f}玉")
        print(f"  最小誤差: {min_error:.1f}玉")
        print(f"  最大誤差: {max_error:.1f}玉")
        
        # 精度達成率
        print(f"\n🎯 精度達成率:")
        thresholds = [100, 200, 300, 500, 1000]
        
        for threshold in thresholds:
            count = sum(1 for e in errors if e <= threshold)
            rate = count / valid_count * 100
            print(f"  ±{threshold:4d}玉以内: {count:2d}/{valid_count}件 ({rate:5.1f}%)")
        
        # 最高精度のケース
        print(f"\n💎 高精度達成ケース (±100玉以内):")
        for data in comparison_data:
            if data['abs_error'] <= 100:
                print(f"  画像{data['image_num']}: 実際{data['actual_final']:.0f}玉 → "
                      f"抽出{data['extracted_final']:.1f}玉 (誤差{data['error']:+.0f}玉)")
        
        # 改善が必要なケース
        print(f"\n⚠️  改善が必要なケース (±500玉超):")
        for data in comparison_data:
            if data['abs_error'] > 500:
                print(f"  画像{data['image_num']}: 実際{data['actual_final']:.0f}玉 → "
                      f"抽出{data['extracted_final']:.1f}玉 (誤差{data['error']:+.0f}玉)")
    
    # 結果をCSVに保存
    if comparison_data:
        df_results = pd.DataFrame(comparison_data)
        df_results.to_csv('advanced_extractor_accuracy_results.csv', index=False)
        print(f"\n💾 結果を保存: advanced_extractor_accuracy_results.csv")
    
    return comparison_data

if __name__ == "__main__":
    analyze_advanced_accuracy()