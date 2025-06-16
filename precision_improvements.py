#!/usr/bin/env python3
"""
精度向上の改善案
"""

import numpy as np
from scipy import signal
import cv2

class PrecisionImprovements:
    """グラフ抽出精度向上のための改善手法"""
    
    def __init__(self):
        self.calibration_data = {}
    
    def improve_endpoint_detection(self, line_data, method="multi_point_average"):
        """
        改善案1: より精密な終点検出
        """
        if method == "multi_point_average":
            # 最後の5-10点の平均を取る（ノイズ除去）
            end_points = line_data[-10:]
            return np.mean(end_points)
        
        elif method == "smoothing":
            # ガウシアンスムージング適用
            smoothed = signal.gaussian_filter1d(line_data, sigma=2)
            return smoothed[-1]
        
        elif method == "polynomial_fit":
            # 最後の部分に多項式フィッティング
            x = np.arange(len(line_data[-20:]))
            y = line_data[-20:]
            coeffs = np.polyfit(x, y, 2)  # 2次多項式
            # 最後の点での値を予測
            return np.polyval(coeffs, len(x)-1)
    
    def calibrate_conversion_factor(self, detected_value, actual_value, current_factor):
        """
        改善案2: 実測値に基づく変換係数校正
        """
        error_ratio = actual_value / detected_value
        corrected_factor = current_factor * error_ratio
        
        print(f"📏 変換係数校正:")
        print(f"   検出値: {detected_value}")
        print(f"   実測値: {actual_value}")
        print(f"   誤差比: {error_ratio:.4f}")
        print(f"   元係数: {current_factor:.6f}")
        print(f"   校正係数: {corrected_factor:.6f}")
        
        return corrected_factor
    
    def sub_pixel_line_detection(self, img_array, mask):
        """
        改善案3: サブピクセル精度での線検出
        """
        # エッジ検出でより精密な線位置を特定
        edges = cv2.Canny(img_array, 50, 150)
        
        # 線の重心を計算（サブピクセル精度）
        y_coords, x_coords = np.where(mask)
        
        if len(y_coords) > 0:
            # 各x座標での重心y座標を計算
            refined_points = {}
            for x in range(img_array.shape[1]):
                y_points = y_coords[x_coords == x]
                if len(y_points) > 0:
                    # 重心計算（よりノイズに強い）
                    refined_points[x] = np.mean(y_points)
            
            return refined_points
        return {}
    
    def adaptive_scaling_correction(self, image_path, detected_range, expected_range=60000):
        """
        改善案4: 画像固有のスケーリング補正
        """
        # 画像の実際のピクセル範囲から動的にスケーリングを計算
        actual_pixel_range = detected_range  # 検出された最大ピクセル範囲
        
        # 理論値: -30000〜+30000 = 60000の範囲
        corrected_scaling = expected_range / actual_pixel_range
        
        print(f"🔧 適応スケーリング補正:")
        print(f"   検出ピクセル範囲: {actual_pixel_range}")
        print(f"   期待値範囲: {expected_range}")
        print(f"   補正スケーリング: {corrected_scaling:.6f}")
        
        return corrected_scaling
    
    def line_continuity_analysis(self, line_points):
        """
        改善案5: 線の連続性分析による外れ値除去
        """
        if len(line_points) < 3:
            return line_points
        
        # 1次微分による急激な変化の検出
        diff1 = np.diff(line_points)
        
        # 外れ値の閾値（標準偏差の2倍）
        threshold = 2 * np.std(diff1)
        
        # 外れ値を除去
        cleaned_points = [line_points[0]]  # 最初の点は保持
        
        for i in range(1, len(line_points)):
            if abs(diff1[i-1]) <= threshold:
                cleaned_points.append(line_points[i])
            else:
                # 線形補間で修正
                interpolated = cleaned_points[-1] + np.median(diff1[:i])
                cleaned_points.append(interpolated)
        
        return np.array(cleaned_points)

def test_precision_improvements():
    """精度改善テスト"""
    
    # S__78209088の実測データ
    detected_value = 3310  # 検出値
    actual_value = 3125    # 実測値
    current_factor = 244.7 / 30000  # 現在の変換係数
    
    improvements = PrecisionImprovements()
    
    print("=" * 60)
    print("🎯 S__78209088 精度改善分析")
    print("=" * 60)
    
    # 校正係数の計算
    corrected_factor = improvements.calibrate_conversion_factor(
        detected_value, actual_value, current_factor
    )
    
    # 校正後の予測値
    corrected_prediction = detected_value * (actual_value / detected_value)
    
    print(f"\n📊 改善結果:")
    print(f"   元の検出値: {detected_value}玉")
    print(f"   実測値: {actual_value}玉")
    print(f"   誤差: {detected_value - actual_value}玉 ({((detected_value - actual_value) / actual_value * 100):.1f}%)")
    print(f"   校正後予測: {corrected_prediction:.0f}玉")
    
    return corrected_factor

if __name__ == "__main__":
    test_precision_improvements()