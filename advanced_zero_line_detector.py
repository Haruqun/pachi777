#!/usr/bin/env python3
"""
高精度ゼロライン検出システム
複数の手法を組み合わせてゼロラインを精密に検出
"""

import cv2
import numpy as np
import os
from pathlib import Path

class AdvancedZeroLineDetector:
    """高度なゼロライン検出クラス"""
    
    def __init__(self):
        self.methods = {
            'thick_gray_line': self.detect_thick_gray_line,
            'horizontal_lines': self.detect_horizontal_lines,
            'edge_based': self.detect_edge_based,
            'intensity_gradient': self.detect_intensity_gradient,
            'template_matching': self.detect_template_matching
        }
    
    def detect_thick_gray_line(self, img):
        """太いグレーの線を検出（現在の手法）"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # 中央付近でグレーの太い線を探す
        center_region = gray[height//2-100:height//2+100, :]
        
        # 水平方向の平均を計算
        horizontal_means = []
        for y in range(center_region.shape[0]):
            row = center_region[y, :]
            # グレー値の範囲（60-120）
            gray_pixels = row[(row > 60) & (row < 120)]
            if len(gray_pixels) > width * 0.8:  # 80%以上がグレー
                horizontal_means.append((y + height//2 - 100, np.mean(gray_pixels)))
        
        if horizontal_means:
            # 最も濃いグレーの線を選択
            best_line = min(horizontal_means, key=lambda x: abs(x[1] - 90))
            return best_line[0], 0.8
        
        return None, 0
    
    def detect_horizontal_lines(self, img):
        """Hough変換による水平線検出"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
        
        if lines is not None:
            horizontal_lines = []
            for line in lines:
                rho, theta = line[0]
                # 水平線のみ（theta ≈ 90度）
                if 85 < np.degrees(theta) < 95:
                    a = np.cos(theta)
                    b = np.sin(theta)
                    y0 = b * rho
                    horizontal_lines.append(int(y0))
            
            if horizontal_lines:
                # 中央に最も近い線を選択
                center = img.shape[0] // 2
                best_line = min(horizontal_lines, key=lambda y: abs(y - center))
                confidence = 0.7
                return best_line, confidence
        
        return None, 0
    
    def detect_edge_based(self, img):
        """エッジベースの検出"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Sobelフィルタで水平エッジを検出
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        abs_sobel_y = np.absolute(sobel_y)
        
        # 水平方向の平均
        horizontal_profile = np.mean(abs_sobel_y, axis=1)
        
        # ピークを検出
        center = len(horizontal_profile) // 2
        search_range = 100
        center_region = horizontal_profile[center-search_range:center+search_range]
        
        if len(center_region) > 0:
            peak_idx = np.argmax(center_region)
            zero_line = center - search_range + peak_idx
            confidence = min(center_region[peak_idx] / np.max(horizontal_profile), 1.0)
            return zero_line, confidence * 0.6
        
        return None, 0
    
    def detect_intensity_gradient(self, img):
        """輝度勾配による検出"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # 垂直方向の輝度変化を計算
        vertical_profile = np.mean(gray, axis=1)
        gradient = np.gradient(vertical_profile)
        
        # 中央付近で最大の勾配変化を探す
        center = height // 2
        search_range = 100
        center_region = gradient[center-search_range:center+search_range]
        
        # 勾配の絶対値の最大値
        max_grad_idx = np.argmax(np.abs(center_region))
        zero_line = center - search_range + max_grad_idx
        
        confidence = min(np.abs(center_region[max_grad_idx]) / np.max(np.abs(gradient)), 1.0)
        return zero_line, confidence * 0.5
    
    def detect_template_matching(self, img):
        """テンプレートマッチングによる検出"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # ゼロライン付近のテンプレートを作成（太いグレーの線）
        template_height = 10
        template = np.ones((template_height, width), dtype=np.uint8) * 90
        
        # テンプレートマッチング
        result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val > 0.5:
            zero_line = max_loc[1] + template_height // 2
            return zero_line, max_val * 0.9
        
        return None, 0
    
    def detect_zero_line(self, img_path):
        """複数の手法を組み合わせてゼロラインを検出"""
        img = cv2.imread(img_path)
        if img is None:
            return None
        
        results = {}
        
        # 各手法で検出
        for method_name, method_func in self.methods.items():
            try:
                line_y, confidence = method_func(img)
                if line_y is not None:
                    results[method_name] = {
                        'y': line_y,
                        'confidence': confidence
                    }
            except Exception as e:
                print(f"Method {method_name} failed: {e}")
        
        # 結果を統合
        if results:
            # 信頼度で重み付け平均
            weighted_sum = sum(r['y'] * r['confidence'] for r in results.values())
            total_confidence = sum(r['confidence'] for r in results.values())
            
            if total_confidence > 0:
                final_y = int(weighted_sum / total_confidence)
                avg_confidence = total_confidence / len(results)
                
                return {
                    'final_y': final_y,
                    'confidence': avg_confidence,
                    'method_results': results,
                    'agreement': self.calculate_agreement(results)
                }
        
        return None
    
    def calculate_agreement(self, results):
        """各手法の結果の一致度を計算"""
        if len(results) < 2:
            return 1.0
        
        y_values = [r['y'] for r in results.values()]
        std_dev = np.std(y_values)
        
        # 標準偏差が小さいほど一致度が高い
        agreement = max(0, 1 - (std_dev / 10))  # 10ピクセルの差で0になる
        return agreement
    
    def visualize_detection(self, img_path, detection_result):
        """検出結果を可視化"""
        img = cv2.imread(img_path)
        if img is None or detection_result is None:
            return None
        
        overlay = img.copy()
        height, width = img.shape[:2]
        
        # 各手法の結果を描画
        colors = {
            'thick_gray_line': (255, 0, 0),      # 青
            'horizontal_lines': (0, 255, 0),      # 緑
            'edge_based': (0, 0, 255),           # 赤
            'intensity_gradient': (255, 255, 0),  # シアン
            'template_matching': (255, 0, 255)    # マゼンタ
        }
        
        # 各手法の線を細く描画
        for method, result in detection_result['method_results'].items():
            color = colors.get(method, (128, 128, 128))
            y = result['y']
            cv2.line(overlay, (0, y), (width, y), color, 1)
            cv2.putText(overlay, f"{method[:8]} ({result['confidence']:.2f})", 
                       (10, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
        
        # 最終結果を太く描画
        final_y = detection_result['final_y']
        cv2.line(overlay, (0, final_y), (width, final_y), (0, 0, 0), 3)
        cv2.line(overlay, (0, final_y), (width, final_y), (255, 255, 255), 2)
        
        # 統計情報
        info_text = [
            f"Final Y: {final_y}",
            f"Confidence: {detection_result['confidence']:.2f}",
            f"Agreement: {detection_result['agreement']:.2f}"
        ]
        
        y_offset = 30
        for text in info_text:
            cv2.putText(overlay, text, (width - 200, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            cv2.putText(overlay, text, (width - 200, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 20
        
        return overlay

def test_all_images():
    """全画像でテスト"""
    detector = AdvancedZeroLineDetector()
    
    # テストディレクトリ作成
    os.makedirs("zero_detection_results", exist_ok=True)
    
    # テスト画像
    test_images = list(Path("graphs/manual_crop/cropped").glob("*.png"))
    
    results = []
    
    for img_path in test_images:
        print(f"\nProcessing: {img_path.name}")
        
        # ゼロライン検出
        detection_result = detector.detect_zero_line(str(img_path))
        
        if detection_result:
            print(f"  Final Y: {detection_result['final_y']}")
            print(f"  Confidence: {detection_result['confidence']:.2f}")
            print(f"  Agreement: {detection_result['agreement']:.2f}")
            
            # 可視化
            vis_img = detector.visualize_detection(str(img_path), detection_result)
            if vis_img is not None:
                output_path = f"zero_detection_results/{img_path.stem}_detection.png"
                cv2.imwrite(output_path, vis_img)
            
            results.append({
                'image': img_path.name,
                'final_y': detection_result['final_y'],
                'confidence': detection_result['confidence'],
                'agreement': detection_result['agreement'],
                'methods': detection_result['method_results']
            })
    
    # 結果をまとめて表示
    print("\n" + "="*60)
    print("Summary of Zero Line Detection Results:")
    print("="*60)
    
    for result in results:
        print(f"\n{result['image']}:")
        print(f"  Final Y: {result['final_y']} (Conf: {result['confidence']:.2f}, Agree: {result['agreement']:.2f})")
        print("  Method details:")
        for method, detail in result['methods'].items():
            print(f"    {method}: Y={detail['y']} (Conf: {detail['confidence']:.2f})")
    
    # 統計
    y_values = [r['final_y'] for r in results]
    print(f"\nOverall Statistics:")
    print(f"  Mean Y: {np.mean(y_values):.1f}")
    print(f"  Std Dev: {np.std(y_values):.1f}")
    print(f"  Range: {min(y_values)} - {max(y_values)}")

if __name__ == "__main__":
    test_all_images()