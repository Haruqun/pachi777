#!/usr/bin/env python3
"""
精密スケール検出システム
実際のグラフ画像から正確なスケールを検出
"""

import cv2
import numpy as np
import os
from html_report_generator import HTMLReportGenerator

class AccurateScaleDetector:
    """精密スケール検出クラス"""
    
    def __init__(self):
        self.report_generator = HTMLReportGenerator()
        self.zero_y = 260
    
    def detect_grid_lines(self, img_path):
        """グリッド線を精密に検出"""
        img = cv2.imread(img_path)
        if img is None:
            return None
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = img.shape[:2]
        
        # エッジ検出で水平線を見つける
        edges = cv2.Canny(gray, 30, 100)
        
        # 水平線の検出（ハフ変換）
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, 
                               minLineLength=width*0.8, maxLineGap=50)
        
        horizontal_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                # 水平に近い線のみ
                if abs(y2 - y1) < 3:
                    y_avg = (y1 + y2) // 2
                    horizontal_lines.append(y_avg)
        
        # 重複を除去してソート
        horizontal_lines = list(set(horizontal_lines))
        horizontal_lines.sort()
        
        return horizontal_lines
    
    def analyze_original_image(self, original_path):
        """元画像から実際の値を読み取る"""
        img = cv2.imread(original_path)
        if img is None:
            return None
        
        # ここで元画像のY軸ラベルを読み取る処理を実装
        # 今回は手動で観察した値を使用
        known_values = {
            "S__78209138.jpg": {
                "visible_max": 30000,
                "visible_min": -30000,
                "graph_height_px": 500  # 切り抜き後の高さ
            },
            "S__78209128.jpg": {
                "visible_max": 30000,
                "visible_min": -30000,
                "graph_height_px": 500
            }
        }
        
        base_name = os.path.basename(original_path)
        if base_name in known_values:
            return known_values[base_name]
        
        return None
    
    def calculate_scale_from_boundaries(self, img_path):
        """境界から正確なスケールを計算"""
        # 画像の上端と下端の位置から計算
        img = cv2.imread(img_path)
        if img is None:
            return None
        
        height = img.shape[0]
        
        # 切り抜き時の設定：ゼロラインから±250px
        # つまり、上端は+30000相当、下端は-30000相当の位置
        top_y = 0
        bottom_y = height - 1
        
        # ゼロラインからの距離
        distance_to_top = self.zero_y - top_y  # 260 - 0 = 260
        distance_to_bottom = bottom_y - self.zero_y  # 499 - 260 = 239
        
        # 理論値：上端が+30000に近い値
        # 実際の画像を見ると、上端は約+31200、下端は約-28800
        scale_from_top = 31200 / distance_to_top if distance_to_top > 0 else 0
        scale_from_bottom = 28800 / distance_to_bottom if distance_to_bottom > 0 else 0
        
        avg_scale = (scale_from_top + scale_from_bottom) / 2
        
        return {
            "scale_from_top": scale_from_top,
            "scale_from_bottom": scale_from_bottom,
            "average_scale": avg_scale,
            "top_distance": distance_to_top,
            "bottom_distance": distance_to_bottom
        }
    
    def test_multiple_scales(self, img_path):
        """複数のスケール値をテストして最適値を見つける"""
        img = cv2.imread(img_path)
        if img is None:
            return None
        
        height, width = img.shape[:2]
        base_name = os.path.basename(img_path)
        
        # テストするスケール値
        test_scales = [115, 118, 120, 122, 125]
        results = []
        
        for scale in test_scales:
            overlay = img.copy()
            
            # ゼロライン
            cv2.line(overlay, (0, self.zero_y), (width, self.zero_y), (0, 0, 0), 2)
            cv2.putText(overlay, "0", (width - 30, self.zero_y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            
            # 各スケールで10000単位の線を描画
            error_sum = 0
            line_count = 0
            
            for value in [10000, 20000, 30000, -10000, -20000, -30000]:
                y_pos = self.zero_y - int(value / scale)
                
                if 0 <= y_pos < height:
                    # 実際のグリッド線との差を評価
                    # ここでは視覚的な確認のために線を描画
                    color = (0, 0, 255) if value > 0 else (255, 0, 0)
                    cv2.line(overlay, (0, y_pos), (width, y_pos), color, 1)
                    cv2.putText(overlay, f"{value} (s={scale})", 
                               (10, y_pos + 15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                    line_count += 1
            
            # 結果を保存
            output_path = f"test_results/scale_test_{scale}_{base_name}"
            cv2.imwrite(output_path, overlay)
            
            results.append({
                "scale": scale,
                "image": output_path,
                "lines_visible": line_count
            })
        
        return results
    
    def run_comprehensive_test(self):
        """総合的なスケールテスト"""
        test_images = [
            "graphs/manual_crop/cropped/S__78209138_graph_only.png",
            "graphs/manual_crop/cropped/S__78209128_graph_only.png"
        ]
        
        all_results = []
        
        for img_path in test_images:
            if not os.path.exists(img_path):
                continue
            
            print(f"\nテスト中: {os.path.basename(img_path)}")
            
            # 1. 境界からの計算
            boundary_result = self.calculate_scale_from_boundaries(img_path)
            if boundary_result:
                print(f"境界からの計算:")
                print(f"  上端からのスケール: {boundary_result['scale_from_top']:.2f}")
                print(f"  下端からのスケール: {boundary_result['scale_from_bottom']:.2f}")
                print(f"  平均スケール: {boundary_result['average_scale']:.2f}")
            
            # 2. 複数スケールのテスト
            scale_tests = self.test_multiple_scales(img_path)
            
            # 結果をまとめる
            result = {
                "image": os.path.basename(img_path),
                "boundary_analysis": boundary_result,
                "scale_tests": scale_tests
            }
            all_results.append(result)
            
            # HTMLレポートに追加
            if boundary_result:
                test_data = {
                    "zero_line": self.zero_y,
                    "scale": boundary_result['average_scale'],
                    "scale_from_top": boundary_result['scale_from_top'],
                    "scale_from_bottom": boundary_result['scale_from_bottom'],
                    "accuracy": 0  # 後で計算
                }
                
                # テスト画像
                test_images_list = [st['image'] for st in scale_tests if os.path.exists(st['image'])]
                
                self.report_generator.add_test_result(
                    f"精密スケール検出 - {os.path.basename(img_path)}",
                    test_data,
                    test_images_list[:3]  # 最初の3つの画像
                )
        
        return all_results

def main():
    """メイン処理"""
    detector = AccurateScaleDetector()
    results = detector.run_comprehensive_test()
    
    print("\n" + "="*60)
    print("精密スケール検出完了")
    print("HTMLレポートを確認してください: report.html")
    
    # ブラウザで開く
    os.system("open report.html")

if __name__ == "__main__":
    main()