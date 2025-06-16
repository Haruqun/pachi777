#!/usr/bin/env python3
"""
複数画像での精度検証
"""

import sys
import os
import random
sys.path.append('/Users/haruqun/Work/pachi777')

from perfect_data_extractor import PerfectDataExtractor
import pandas as pd
import numpy as np
from scipy import signal

def test_image_precision(image_path, expected_value=None):
    """単一画像の精度テスト"""
    print(f"\n" + "="*60)
    print(f"🎯 画像精度テスト: {os.path.basename(image_path)}")
    print("="*60)
    
    # データ抽出器を初期化
    extractor = PerfectDataExtractor(debug_mode=False)
    
    # CSVパス設定
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    csv_path = f"graphs/extracted_data/{base_name}.csv"
    
    try:
        # データ抽出を実行
        result = extractor.extract_perfect_data(image_path, csv_path)
        
        if result is None or len(result) == 0:
            print("❌ データ抽出失敗")
            return None
        
        print(f"✅ データ抽出成功: {len(result)}点")
        
        # 各種終点検出方法をテスト
        methods = {}
        
        # 元の最終値
        original_final = result['y_value'].iloc[-1]
        methods['元の値'] = original_final
        
        # 最後の10点平均
        end_points = min(10, len(result))
        final_section = result['y_value'].iloc[-end_points:]
        methods['平均10点'] = final_section.mean()
        
        # 中央値
        methods['中央値'] = final_section.median()
        
        # 外れ値除去後平均
        q1 = final_section.quantile(0.25)
        q3 = final_section.quantile(0.75)
        iqr = q3 - q1
        filtered_values = final_section[(final_section >= q1 - 1.5 * iqr) & 
                                       (final_section <= q3 + 1.5 * iqr)]
        methods['外れ値除去'] = filtered_values.mean() if len(filtered_values) > 0 else methods['平均10点']
        
        # Savitzky-Golayスムージング
        if len(result) >= 20:
            try:
                smoothed = signal.savgol_filter(result['y_value'], 
                                              window_length=min(21, len(result)//2*2+1), 
                                              polyorder=3)
                methods['Savgol'] = smoothed[-1]
            except:
                methods['Savgol'] = methods['元の値']
        else:
            methods['Savgol'] = methods['元の値']
        
        # 安定区間検出
        if len(result) >= 20:
            last_20 = result['y_value'].iloc[-20:]
            min_std = float('inf')
            best_segment = last_20.iloc[-5:]
            
            for i in range(len(last_20) - 4):
                segment = last_20.iloc[i:i+5]
                std = segment.std()
                if std < min_std:
                    min_std = std
                    best_segment = segment
            
            methods['安定区間'] = best_segment.mean()
            print(f"📊 安定区間標準偏差: {min_std:.1f}")
        else:
            methods['安定区間'] = methods['元の値']
        
        # 結果表示
        print(f"\n📊 各手法の結果:")
        for name, value in methods.items():
            print(f"   {name:12s}: {value:7.0f}円")
        
        # 期待値がある場合の精度評価
        if expected_value is not None:
            print(f"\n🎯 期待値: {expected_value}円")
            print(f"📊 精度比較:")
            
            best_method = None
            best_error = float('inf')
            
            for name, value in methods.items():
                error = abs(value - expected_value)
                error_pct = (error / abs(expected_value)) * 100 if expected_value != 0 else 0
                print(f"   {name:12s}: 誤差 {error:4.0f} ({error_pct:4.1f}%)")
                
                if error < best_error:
                    best_error = error
                    best_method = name
            
            print(f"\n🏆 最良手法: {best_method} (誤差: {best_error:.0f}円)")
            return methods, best_method, best_error
        
        return methods, '元の値', 0
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None

def main():
    """複数画像テスト実行"""
    print("🎯 複数画像での精度向上検証")
    
    # テスト対象画像を選択（S_画像とIMG画像の両方）
    test_images = [
        # S_画像（校正済み変換係数適用）
        "graphs/cropped_auto/S__78209136_cropped.png",  # ランダム選択
        "graphs/cropped_auto/S__78209160_cropped.png",  # ランダム選択
        "graphs/cropped_auto/S__78209132_cropped.png",  # ランダム選択
        
        # IMG画像（従来変換係数）  
        "graphs/cropped_auto/IMG_4403_cropped.png",
        "graphs/cropped_auto/IMG_8949_cropped.png",
    ]
    
    results = []
    
    for image_path in test_images:
        if os.path.exists(image_path):
            result = test_image_precision(image_path)
            if result:
                results.append((os.path.basename(image_path), result))
        else:
            print(f"⚠️ {image_path} が見つかりません")
    
    # 全体総括
    print(f"\n" + "="*80)
    print(f"📊 全体総括")
    print("="*80)
    
    for image_name, (methods, best_method, best_error) in results:
        image_type = "S_画像(校正済み)" if "S__" in image_name else "IMG画像"
        final_value = methods['元の値']
        print(f"{image_name:30s} | {image_type:15s} | 最終値: {final_value:6.0f}円")
    
    # S_画像での校正効果の確認
    s_images = [r for r in results if "S__" in r[0]]
    img_images = [r for r in results if "IMG" in r[0]]
    
    if s_images:
        print(f"\n📈 S_画像（校正済み係数 0.007701）:")
        for image_name, (methods, _, _) in s_images:
            print(f"   {image_name}: {methods['元の値']:.0f}円")
    
    if img_images:
        print(f"\n📈 IMG画像（従来係数 0.0111）:")
        for image_name, (methods, _, _) in img_images:
            print(f"   {image_name}: {methods['元の値']:.0f}円")

if __name__ == "__main__":
    main()