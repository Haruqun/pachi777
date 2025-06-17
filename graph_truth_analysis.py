#!/usr/bin/env python3
"""
グラフの真実 vs 報告値の分析
グラフが示す真の値と報告されている値の乖離を検証
"""

import pandas as pd
import numpy as np
import os

def analyze_graph_truth():
    """グラフが示す真実と報告値の比較分析"""
    print("🔍 グラフの真実 vs 報告値 分析")
    print("="*80)
    print("グラフは嘘をつかない - 実際のグラフデータと報告値の乖離を検証")
    print("="*80)
    
    # results.txtから報告値を読み込み
    results_data = {}
    with open('results.txt', 'r', encoding='utf-8') as f:
        next(f)  # ヘッダースキップ
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 6:
                image_name = parts[0].replace('.jpg', '')
                results_data[image_name] = {
                    'machine_num': parts[2],
                    'actual_max': parts[4].replace(',', ''),
                    'reported_final': float(parts[5].replace(',', '').replace('"', '')) if parts[5] and parts[5].replace(',', '').replace('"', '') else None,
                    'visual_prediction': parts[6].replace(',', '') if len(parts) > 6 else '',
                    'prediction_error': parts[7].replace(',', '') if len(parts) > 7 else ''
                }
    
    # 分析結果
    suspicious_cases = []
    accurate_cases = []
    
    print(f"\n{'画像名':<20} {'台番号':<8} {'グラフ値':>12} {'報告値':>12} {'差':>10} {'疑惑度'}")
    print("-"*80)
    
    # Advanced extractorの結果と比較
    for image_base, data in results_data.items():
        if data['reported_final'] is None:
            continue
            
        csv_path = f"graphs/advanced_extracted_data/{image_base}_optimal_data.csv"
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                if not df.empty and 'value' in df.columns:
                    graph_value = df['value'].iloc[-1]
                    reported_value = data['reported_final']
                    difference = abs(graph_value - reported_value)
                    percentage = (difference / max(abs(reported_value), 1)) * 100
                    
                    # 疑惑度判定
                    if difference < 100:
                        suspicion = "✅信頼可"
                        accurate_cases.append({
                            'image': image_base,
                            'difference': difference
                        })
                    elif difference < 300:
                        suspicion = "🟡要確認"
                    elif difference < 500:
                        suspicion = "🟠疑わしい"
                    else:
                        suspicion = "🔴虚偽疑惑"
                        suspicious_cases.append({
                            'image': image_base,
                            'machine': data['machine_num'],
                            'graph_value': graph_value,
                            'reported_value': reported_value,
                            'difference': difference,
                            'percentage': percentage
                        })
                    
                    print(f"{image_base:<20} {data['machine_num']:<8} "
                          f"{graph_value:>12.1f} {reported_value:>12.0f} "
                          f"{difference:>10.0f} {suspicion}")
                    
            except Exception as e:
                continue
    
    print("-"*80)
    
    # 疑惑ケースの詳細分析
    if suspicious_cases:
        print(f"\n🔴 虚偽報告の疑いがあるケース（差が500玉以上）:")
        for case in sorted(suspicious_cases, key=lambda x: x['difference'], reverse=True):
            print(f"\n  {case['image']} (台{case['machine']}):")
            print(f"    グラフが示す真実: {case['graph_value']:.1f}玉")
            print(f"    報告された値: {case['reported_value']:.0f}玉")
            print(f"    差: {case['difference']:.0f}玉 ({case['percentage']:.1f}%)")
            
            # 報告値の傾向を分析
            if case['graph_value'] < case['reported_value']:
                print(f"    → 実際より良く見せている可能性")
            else:
                print(f"    → 実際より悪く見せている可能性")
    
    # 統計サマリー
    print(f"\n📊 統計サマリー:")
    print(f"  分析対象: {len(results_data)}件")
    print(f"  信頼可能（±100玉以内）: {len(accurate_cases)}件")
    print(f"  虚偽疑惑（±500玉超）: {len(suspicious_cases)}件")
    
    if suspicious_cases:
        avg_diff = np.mean([c['difference'] for c in suspicious_cases])
        print(f"\n  疑惑ケースの平均乖離: {avg_diff:.0f}玉")
    
    # 結論
    print(f"\n💡 結論:")
    print(f"  グラフは客観的な証拠であり、視覚的に確認可能な真実を示しています。")
    print(f"  報告値との大きな乖離は、データ入力ミスか意図的な虚偽の可能性があります。")
    print(f"  特に500玉以上の差がある{len(suspicious_cases)}件は要調査です。")

if __name__ == "__main__":
    analyze_graph_truth()