#!/usr/bin/env python3
"""
ゼロライン自動検出テストツール
複数の手法でゼロラインを検出し、精度を比較
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
from datetime import datetime

class ZeroLineAutoDetector:
    """ゼロライン自動検出クラス"""
    
    def __init__(self, manual_zero_y=268):
        self.manual_zero_y = manual_zero_y
        self.results = []
        
    def detect_method1_darkness(self, img):
        """方法1: 暗い水平線を探す"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = img.shape[:2]
        
        best_y = 0
        best_score = -1
        
        # 画像の中央付近を探索
        for y in range(height//2 - 50, height//2 + 50):
            if y < 0 or y >= height:
                continue
            
            row = gray[y, :]
            # 暗さと均一性を評価
            darkness = 1.0 - (np.mean(row) / 255.0)
            uniformity = 1.0 - (np.std(row) / 128.0)
            score = darkness * 0.7 + uniformity * 0.3
            
            if score > best_score:
                best_score = score
                best_y = y
        
        return best_y, best_score
    
    def detect_method2_edge(self, img):
        """方法2: エッジ検出後、最も強い水平線"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # エッジ検出
        edges = cv2.Canny(gray, 50, 150)
        
        # 水平方向の投影
        height, width = img.shape[:2]
        horizontal_sum = np.sum(edges, axis=1)
        
        # 中央付近で最大値を探す
        center = height // 2
        search_range = slice(center - 50, center + 50)
        
        max_idx = np.argmax(horizontal_sum[search_range])
        best_y = center - 50 + max_idx
        
        return best_y, horizontal_sum[best_y]
    
    def detect_method3_hough(self, img):
        """方法3: ハフ変換で水平線検出"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # ハフ変換で直線検出
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, 
                               minLineLength=200, maxLineGap=10)
        
        if lines is None:
            return 0, 0
        
        # 水平に近い線を抽出
        horizontal_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            if angle < 5 or angle > 175:  # ほぼ水平
                horizontal_lines.append((y1 + y2) // 2)
        
        if not horizontal_lines:
            return 0, 0
        
        # 中央に最も近い線
        center = img.shape[0] // 2
        horizontal_lines.sort(key=lambda y: abs(y - center))
        
        return horizontal_lines[0], len(horizontal_lines)
    
    def detect_method4_template(self, img):
        """方法4: グレーの太い線のテンプレートマッチング"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = img.shape[:2]
        
        # グレーの太い線の特徴を探す
        best_y = 0
        best_score = -1
        
        for y in range(height//2 - 50, height//2 + 50):
            if y < 2 or y >= height - 2:
                continue
            
            # 3ピクセル幅で評価
            region = gray[y-1:y+2, :]
            
            # グレー値の範囲（90-150）
            gray_pixels = np.logical_and(region > 90, region < 150)
            gray_ratio = np.sum(gray_pixels) / gray_pixels.size
            
            # 連続性
            mean_val = np.mean(region)
            std_val = np.std(region)
            
            score = gray_ratio * 0.5 + (1 - std_val/50) * 0.5
            
            if score > best_score:
                best_score = score
                best_y = y
        
        return best_y, best_score
    
    def detect_method5_color(self, img):
        """方法5: 色情報を使った検出"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        height, width = img.shape[:2]
        
        # グレーの範囲（彩度が低い）
        lower_gray = np.array([0, 0, 90])
        upper_gray = np.array([180, 30, 150])
        gray_mask = cv2.inRange(hsv, lower_gray, upper_gray)
        
        # 水平方向の投影
        horizontal_sum = np.sum(gray_mask, axis=1)
        
        # 中央付近で最大値を探す
        center = height // 2
        search_range = slice(center - 50, center + 50)
        
        max_idx = np.argmax(horizontal_sum[search_range])
        best_y = center - 50 + max_idx
        
        return best_y, horizontal_sum[best_y]
    
    def process_image(self, img_path):
        """画像を処理して各手法でゼロラインを検出"""
        img = cv2.imread(img_path)
        if img is None:
            return None
        
        base_name = os.path.basename(img_path)
        print(f"\n処理中: {base_name}")
        
        # 各手法で検出
        methods = {
            '暗さベース': self.detect_method1_darkness,
            'エッジ検出': self.detect_method2_edge,
            'ハフ変換': self.detect_method3_hough,
            'テンプレート': self.detect_method4_template,
            '色情報': self.detect_method5_color
        }
        
        results = {
            'image': base_name,
            'manual': self.manual_zero_y,
            'detections': {}
        }
        
        for method_name, method_func in methods.items():
            y, score = method_func(img)
            error = abs(y - self.manual_zero_y)
            results['detections'][method_name] = {
                'y': y,
                'score': score,
                'error': error
            }
            print(f"  {method_name}: Y={y}, 誤差={error}px")
        
        # 可視化
        self.visualize_results(img, results)
        
        return results
    
    def visualize_results(self, img, results):
        """検出結果を可視化"""
        overlay = img.copy()
        height, width = img.shape[:2]
        
        # 手動設定値（太い黒線）
        cv2.line(overlay, (0, self.manual_zero_y), (width, self.manual_zero_y), 
                (0, 0, 0), 3)
        cv2.putText(overlay, f"Manual: Y={self.manual_zero_y}", 
                   (10, self.manual_zero_y - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        # 各手法の結果
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), 
                 (255, 255, 0), (255, 0, 255)]
        
        y_offset = 30
        for i, (method_name, detection) in enumerate(results['detections'].items()):
            color = colors[i % len(colors)]
            y = detection['y']
            
            # 検出線
            cv2.line(overlay, (0, y), (width, y), color, 1)
            
            # ラベル（左端）
            label = f"{method_name}: Y={y} (err={detection['error']})"
            cv2.putText(overlay, label, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            y_offset += 20
        
        # 保存
        output_dir = "graphs/zero_line_test"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{results['image']}_zero_test.png")
        cv2.imwrite(output_path, overlay)
        
        return output_path
    
    def test_all_images(self):
        """すべてのクロップ画像でテスト"""
        image_files = glob.glob("graphs/manual_crop/cropped/*.png")
        image_files.sort()
        
        print("ゼロライン自動検出テスト")
        print(f"手動設定値: Y={self.manual_zero_y}")
        print("=" * 60)
        
        all_results = []
        
        # 最初の5枚でテスト
        for img_path in image_files[:5]:
            result = self.process_image(img_path)
            if result:
                all_results.append(result)
                self.results.append(result)
        
        # 統計を計算
        self.calculate_statistics()
        
        return all_results
    
    def calculate_statistics(self):
        """検出精度の統計を計算"""
        if not self.results:
            return
        
        print("\n" + "=" * 60)
        print("検出精度統計")
        print("=" * 60)
        
        # 各手法の誤差を集計
        method_errors = {}
        
        for result in self.results:
            for method_name, detection in result['detections'].items():
                if method_name not in method_errors:
                    method_errors[method_name] = []
                method_errors[method_name].append(detection['error'])
        
        # 統計を表示
        for method_name, errors in method_errors.items():
            avg_error = np.mean(errors)
            max_error = np.max(errors)
            min_error = np.min(errors)
            std_error = np.std(errors)
            
            print(f"\n{method_name}:")
            print(f"  平均誤差: {avg_error:.1f}px")
            print(f"  最大誤差: {max_error}px")
            print(f"  最小誤差: {min_error}px")
            print(f"  標準偏差: {std_error:.1f}px")
        
        # 最良の手法を特定
        best_method = min(method_errors.items(), key=lambda x: np.mean(x[1]))
        print(f"\n最良の手法: {best_method[0]} (平均誤差: {np.mean(best_method[1]):.1f}px)")

def main():
    """メイン処理"""
    detector = ZeroLineAutoDetector(manual_zero_y=268)
    detector.test_all_images()

if __name__ == "__main__":
    main()