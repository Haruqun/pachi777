#!/usr/bin/env python3
"""
3枚での集中精度テスト - 開始点と終点の精度向上
"""

import sys
import os
import random
sys.path.append('/Users/haruqun/Work/pachi777')

from perfect_data_extractor import PerfectDataExtractor
import pandas as pd
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

def analyze_endpoint_precision(image_path, expected_final=None):
    """開始点と終点の精度分析"""
    print(f"\n" + "="*60)
    print(f"🎯 開始・終点精度分析: {os.path.basename(image_path)}")
    print("="*60)
    
    # データ抽出器を初期化
    extractor = PerfectDataExtractor(debug_mode=False)
    
    # CSVパス設定
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    csv_path = f"graphs/extracted_data/{base_name}_focused.csv"
    
    try:
        # データ抽出を実行
        result = extractor.extract_perfect_data(image_path, csv_path)
        
        if result is None or len(result) == 0:
            print("❌ データ抽出失敗")
            return None
        
        print(f"✅ データ抽出成功: {len(result)}点")
        
        # 開始点分析
        print(f"\n📈 開始点分析:")
        start_points = result['y_value'].iloc[:10]  # 最初の10点
        start_original = result['y_value'].iloc[0]
        start_avg = start_points.mean()
        start_median = start_points.median()
        
        print(f"   元の開始値: {start_original:7.0f}円")
        print(f"   平均10点:   {start_avg:7.0f}円")
        print(f"   中央値:     {start_median:7.0f}円")
        print(f"   0ライン差:  {abs(start_original):7.0f}円 ({'✅' if abs(start_original) < 1000 else '⚠️'})")
        
        # 終点分析
        print(f"\n📉 終点分析:")
        end_points = result['y_value'].iloc[-10:]  # 最後の10点
        end_original = result['y_value'].iloc[-1]
        end_avg = end_points.mean()
        end_median = end_points.median()
        end_std = end_points.std()
        
        # 外れ値除去
        q1 = end_points.quantile(0.25)
        q3 = end_points.quantile(0.75)
        iqr = q3 - q1
        filtered_end = end_points[(end_points >= q1 - 1.5 * iqr) & 
                                 (end_points <= q3 + 1.5 * iqr)]
        end_filtered = filtered_end.mean() if len(filtered_end) > 0 else end_avg
        
        # 最後の安定した5点を検出
        if len(result) >= 15:
            last_15 = result['y_value'].iloc[-15:]
            min_std = float('inf')
            best_stable = end_points.iloc[-5:]
            
            for i in range(len(last_15) - 4):
                segment = last_15.iloc[i:i+5]
                std = segment.std()
                if std < min_std:
                    min_std = std
                    best_stable = segment
            
            end_stable = best_stable.mean()
            stable_std = best_stable.std()
        else:
            end_stable = end_avg
            stable_std = end_std
        
        print(f"   元の終点値: {end_original:7.0f}円")
        print(f"   平均10点:   {end_avg:7.0f}円")
        print(f"   中央値:     {end_median:7.0f}円")
        print(f"   外れ値除去: {end_filtered:7.0f}円")
        print(f"   安定区間:   {end_stable:7.0f}円 (std: {stable_std:.1f})")
        print(f"   変動性:     {end_std:7.1f} ({'✅' if end_std < 200 else '⚠️' if end_std < 500 else '❌'})")
        
        # 期待値との比較
        if expected_final is not None:
            print(f"\n🎯 期待値: {expected_final}円")
            methods = {
                '元の値': end_original,
                '平均10点': end_avg,
                '中央値': end_median,
                '外れ値除去': end_filtered,
                '安定区間': end_stable
            }
            
            best_method = None
            best_error = float('inf')
            
            for name, value in methods.items():
                error = abs(value - expected_final)
                error_pct = (error / abs(expected_final)) * 100 if expected_final != 0 else 0
                print(f"   {name:12s}: 誤差 {error:4.0f}円 ({error_pct:4.1f}%)")
                
                if error < best_error:
                    best_error = error
                    best_method = name
            
            print(f"\n🏆 最良手法: {best_method} (誤差: {best_error:.0f}円)")
        
        # グラフの境界問題を検出
        print(f"\n🔍 境界問題検出:")
        
        # 開始点が0ラインから大きく外れている
        if abs(start_original) > 2000:
            print(f"   ⚠️ 開始点が0ラインから {abs(start_original):.0f}円離れています")
        
        # 終点の変動が大きい
        if end_std > 500:
            print(f"   ⚠️ 終点の変動が大きいです (std: {end_std:.1f})")
        
        # 極値に張り付いている
        if abs(end_original) >= 29000:
            print(f"   ⚠️ 終点が極値に張り付いています ({end_original:.0f}円)")
        
        return {
            'start_original': start_original,
            'start_improved': start_avg,
            'end_original': end_original,
            'end_improved': end_stable,
            'end_stability': stable_std,
            'data_points': len(result)
        }
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None

def main():
    """3枚での集中テスト"""
    print("🎯 開始・終点精度向上 - 3枚集中テスト")
    
    # テスト対象画像を3枚に絞る
    test_cases = [
        {
            'path': "graphs/cropped_auto/S__78209088_cropped.png",
            'expected': 3125,  # 実測値
            'description': "基準画像（実測値あり）"
        },
        {
            'path': "graphs/cropped_auto/S__78209160_cropped.png", 
            'expected': None,  # 表示値約7060
            'description': "ブルーライン・変動パターン"
        },
        {
            'path': "graphs/cropped_auto/S__78209132_cropped.png",
            'expected': None,  # 上限30000
            'description': "極値到達パターン"
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n[{i}/3] {case['description']}")
        
        if os.path.exists(case['path']):
            result = analyze_endpoint_precision(case['path'], case['expected'])
            if result:
                results.append((os.path.basename(case['path']), case['description'], result))
        else:
            print(f"⚠️ {case['path']} が見つかりません")
    
    # 総合評価
    print(f"\n" + "="*80)
    print(f"📊 3枚集中テスト総合評価")
    print("="*80)
    
    total_improvement = 0
    stable_images = 0
    
    for image_name, description, result in results:
        stability = "✅" if result['end_stability'] < 200 else "⚠️" if result['end_stability'] < 500 else "❌"
        start_accuracy = "✅" if abs(result['start_original']) < 1000 else "⚠️"
        
        print(f"{image_name:30s}")
        print(f"  説明: {description}")
        print(f"  開始精度: {start_accuracy} ({result['start_original']:+.0f}円)")
        print(f"  終点安定性: {stability} (std: {result['end_stability']:.1f})")
        print(f"  データ点数: {result['data_points']}点")
        print(f"  改善効果: {result['end_original']:.0f} → {result['end_improved']:.0f}円")
        
        if result['end_stability'] < 200:
            stable_images += 1
        
        print()
    
    print(f"🏆 安定画像: {stable_images}/{len(results)}枚")
    
    # 改善提案
    print(f"\n💡 精度向上の提案:")
    print(f"  1. 開始点: 0ライン検出後の数点平均を使用")
    print(f"  2. 終点: 安定区間検出アルゴリズムの活用")
    print(f"  3. 外れ値: IQRベースのフィルタリング")

if __name__ == "__main__":
    main()