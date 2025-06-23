#!/usr/bin/env python3
"""
2ピクセル補正なしでテスト
"""

import cv2
import numpy as np
import pandas as pd
import os

class NoCorrectionExtractor:
    """2ピクセル補正なしの抽出器"""
    
    def __init__(self):
        # グラフ境界設定（実測値）
        self.boundaries = {
            "start_x": 36,
            "end_x": 620,
            "top_y": 26,
            "bottom_y": 523,
            "zero_y": 274
        }
        
    def y_to_value(self, y):
        """Y座標を値に変換（補正なし）"""
        zero_y = self.boundaries["zero_y"]
        top_y = self.boundaries["top_y"]
        bottom_y = self.boundaries["bottom_y"]
        
        # 補正なしでそのまま計算
        if y < zero_y:
            # ゼロラインより上（正の値）
            value = (zero_y - y) / (zero_y - top_y) * 30000
        else:
            # ゼロラインより下（負の値）
            value = -(y - zero_y) / (bottom_y - zero_y) * 30000
        
        return np.clip(value, -30000, 30000)
    
    def test_image(self, image_name, actual_max, actual_final):
        """画像をテスト"""
        # stable_graph_extractor.pyの結果を読み込み
        csv_path = f'graphs/stable_extracted_data/{image_name}_optimal_stable_data.csv'
        
        if not os.path.exists(csv_path):
            return None
            
        df = pd.read_csv(csv_path)
        
        # 補正なしで値を再計算
        no_correction_values = []
        for _, row in df.iterrows():
            value = self.y_to_value(row['y'])
            no_correction_values.append(value)
        
        # 最大値と最終値
        max_no_corr = max(no_correction_values)
        final_no_corr = no_correction_values[-1]
        
        # 補正ありの値（元の値）
        max_with_corr = df['smoothed_value'].max()
        final_with_corr = df['smoothed_value'].iloc[-1]
        
        return {
            'image': image_name,
            'actual_max': actual_max,
            'actual_final': actual_final,
            'max_with_corr': max_with_corr,
            'max_no_corr': max_no_corr,
            'final_with_corr': final_with_corr,
            'final_no_corr': final_no_corr,
            'max_error_with': max_with_corr - actual_max,
            'max_error_no': max_no_corr - actual_max,
            'final_error_with': final_with_corr - actual_final,
            'final_error_no': final_no_corr - actual_final,
        }

def main():
    """メイン処理"""
    # テストケース（results.txtから）
    test_cases = [
        ('S__78209088', 3340, 3125),
        ('S__78209128', 11430, 6771),
        ('S__78209130', 9060, -5997),
        ('S__78209136', 3620, -10925),
        ('S__78209160', 7080, 3010),  # 青
        ('S__78209162', 12700, 1700),  # 青
        ('S__78209164', 21020, 15450), # 青
    ]
    
    extractor = NoCorrectionExtractor()
    
    print("2ピクセル補正ありvs補正なしの比較")
    print("="*100)
    print(f"{'画像':15} {'実際の最大':>8} {'補正あり':>8} {'補正なし':>8} {'差(あり)':>8} {'差(なし)':>8} | {'実際の最終':>8} {'補正あり':>8} {'補正なし':>8} {'差(あり)':>8} {'差(なし)':>8}")
    print("-"*100)
    
    total_max_error_with = 0
    total_max_error_no = 0
    total_final_error_with = 0
    total_final_error_no = 0
    count = 0
    
    for image_name, actual_max, actual_final in test_cases:
        result = extractor.test_image(image_name, actual_max, actual_final)
        
        if result:
            print(f"{result['image']:15} {result['actual_max']:>8.0f} {result['max_with_corr']:>8.0f} {result['max_no_corr']:>8.0f} {result['max_error_with']:>+8.0f} {result['max_error_no']:>+8.0f} | {result['actual_final']:>8.0f} {result['final_with_corr']:>8.0f} {result['final_no_corr']:>8.0f} {result['final_error_with']:>+8.0f} {result['final_error_no']:>+8.0f}")
            
            total_max_error_with += abs(result['max_error_with'])
            total_max_error_no += abs(result['max_error_no'])
            total_final_error_with += abs(result['final_error_with'])
            total_final_error_no += abs(result['final_error_no'])
            count += 1
    
    print("-"*100)
    print(f"平均絶対誤差:")
    print(f"  最大値 - 補正あり: {total_max_error_with/count:.0f}, 補正なし: {total_max_error_no/count:.0f}")
    print(f"  最終値 - 補正あり: {total_final_error_with/count:.0f}, 補正なし: {total_final_error_no/count:.0f}")
    
    print(f"\n精度（300で割る方式）:")
    print(f"  最大値 - 補正あり: {100 - total_max_error_with/count/300:.1f}%, 補正なし: {100 - total_max_error_no/count/300:.1f}%")
    print(f"  最終値 - 補正あり: {100 - total_final_error_with/count/300:.1f}%, 補正なし: {100 - total_final_error_no/count/300:.1f}%")

if __name__ == "__main__":
    main()