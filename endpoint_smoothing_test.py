#!/usr/bin/env python3
"""
終点スムージングテスト
"""

import pandas as pd
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

def test_endpoint_smoothing():
    """S__78209088のデータで終点スムージングをテスト"""
    
    # 抽出されたCSVデータを読み込み（存在する場合）
    csv_path = "graphs/extracted_data/S__78209088_cropped.csv"
    
    try:
        df = pd.read_csv(csv_path)
        print(f"📊 データ読み込み成功: {len(df)}点")
    except FileNotFoundError:
        print("❌ CSVファイルが見つかりません。仮想データで実行します")
        # 仮想データ作成（最終部分にスパイクを含む）
        x = np.linspace(0, 1, 100)
        y = np.sin(x * 2 * np.pi) * 1000 + np.random.normal(0, 50, 100)
        y[-5:] += [100, 200, 400, 380, 406]  # 最終部分にスパイク
        df = pd.DataFrame({'x_normalized': x, 'y_value': y})
    
    original_final = df['y_value'].iloc[-1]
    print(f"🎯 元の最終値: {original_final:.0f}")
    
    # 方法1: 複数点平均
    end_points = min(10, len(df))
    final_section = df['y_value'].iloc[-end_points:]
    method1_result = final_section.mean()
    print(f"📏 方法1(平均{end_points}点): {method1_result:.0f}")
    
    # 方法2: 中央値フィルタ
    method2_result = final_section.median()
    print(f"📏 方法2(中央値): {method2_result:.0f}")
    
    # 方法3: 外れ値除去後平均
    q1 = final_section.quantile(0.25)
    q3 = final_section.quantile(0.75)
    iqr = q3 - q1
    filtered_values = final_section[(final_section >= q1 - 1.5 * iqr) & 
                                   (final_section <= q3 + 1.5 * iqr)]
    method3_result = filtered_values.mean() if len(filtered_values) > 0 else method1_result
    print(f"📏 方法3(外れ値除去): {method3_result:.0f}")
    
    # 方法4: 移動平均スムージング
    if len(df) >= 20:
        smoothed = signal.savgol_filter(df['y_value'], window_length=min(21, len(df)//2*2+1), polyorder=3)
        method4_result = smoothed[-1]
        print(f"📏 方法4(Savitzky-Golay): {method4_result:.0f}")
    else:
        method4_result = method1_result
        print(f"📏 方法4(データ不足): {method4_result:.0f}")
    
    # 方法5: 最後の安定した部分を検出
    # 最後の20点で標準偏差が最小となる5点の連続区間を探す
    if len(df) >= 20:
        last_20 = df['y_value'].iloc[-20:]
        min_std = float('inf')
        best_segment = last_20.iloc[-5:]
        
        for i in range(len(last_20) - 4):
            segment = last_20.iloc[i:i+5]
            std = segment.std()
            if std < min_std:
                min_std = std
                best_segment = segment
        
        method5_result = best_segment.mean()
        print(f"📏 方法5(安定区間): {method5_result:.0f} (std: {min_std:.1f})")
    else:
        method5_result = method1_result
        print(f"📏 方法5(データ不足): {method5_result:.0f}")
    
    # 実測値との比較
    actual_value = 3125
    print(f"\n🎯 実測値: {actual_value}")
    
    methods = [
        ("元の値", original_final),
        ("平均10点", method1_result),
        ("中央値", method2_result), 
        ("外れ値除去", method3_result),
        ("Savgol", method4_result),
        ("安定区間", method5_result)
    ]
    
    print(f"\n📊 各手法の精度比較:")
    best_method = None
    best_error = float('inf')
    
    for name, value in methods:
        error = abs(value - actual_value)
        error_pct = (error / actual_value) * 100
        print(f"   {name:12s}: {value:6.0f} (誤差: {error:4.0f} = {error_pct:4.1f}%)")
        
        if error < best_error:
            best_error = error
            best_method = name
    
    print(f"\n🏆 最良手法: {best_method} (誤差: {best_error:.0f})")
    
    return best_method, methods

if __name__ == "__main__":
    test_endpoint_smoothing()