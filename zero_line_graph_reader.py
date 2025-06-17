#!/usr/bin/env python3
"""
ゼロライン検出付きグラフ読み込みツール
ゼロラインを基準にY軸を正確にキャリブレーション
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os

class ZeroLineGraphReader:
    """ゼロライン検出付きグラフ読み込みクラス"""
    
    def __init__(self):
        # グラフの基本パラメータ
        self.y_min = -30000
        self.y_max = 30000
        self.y_range = self.y_max - self.y_min
        
    def detect_zero_line(self, img):
        """ゼロラインを検出"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # エッジ検出
        edges = cv2.Canny(gray, 50, 150)
        
        # 水平線検出（ハフ変換）
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, 
                                minLineLength=width*0.5, maxLineGap=10)
        
        if lines is None:
            return None
            
        # 最も長い水平線を探す（ゼロラインの候補）
        horizontal_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # 水平に近い線（角度が小さい）
            if abs(y2 - y1) < 5:
                length = abs(x2 - x1)
                horizontal_lines.append((y1, length))
        
        if not horizontal_lines:
            return None
            
        # 最も長い水平線をゼロラインとする
        horizontal_lines.sort(key=lambda x: x[1], reverse=True)
        zero_y = horizontal_lines[0][0]
        
        # グラフの中央付近にあるかチェック
        if height * 0.3 < zero_y < height * 0.7:
            return zero_y
        
        return None
    
    def find_graph_bounds(self, mask):
        """グラフデータの境界を検出"""
        height, width = mask.shape
        
        # 各列でピンクピクセルがある範囲を検出
        left_bound = width
        right_bound = 0
        
        for x in range(width):
            if np.any(mask[:, x] > 0):
                left_bound = min(left_bound, x)
                right_bound = max(right_bound, x)
        
        # マージンを追加
        margin = 10
        left_bound = max(0, left_bound - margin)
        right_bound = min(width - 1, right_bound + margin)
        
        return left_bound, right_bound
    
    def read_graph(self, image_path):
        """グラフ画像を読み込んで解析"""
        print(f"\n{'='*60}")
        print(f"画像を読み込み中: {os.path.basename(image_path)}")
        print(f"{'='*60}")
        
        # 画像を読み込み
        img = cv2.imread(image_path)
        if img is None:
            print(f"エラー: 画像を読み込めません: {image_path}")
            return None
            
        height, width = img.shape[:2]
        print(f"画像サイズ: {width}x{height}")
        
        # ゼロラインを検出
        zero_y = self.detect_zero_line(img)
        if zero_y is None:
            print("警告: ゼロラインを検出できませんでした。画像中央を使用します。")
            zero_y = height // 2
        else:
            print(f"ゼロライン検出: Y={zero_y}")
        
        # HSV色空間に変換
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # ピンク色の範囲を定義
        pink_ranges = [
            ((150, 50, 50), (180, 255, 255)),
            ((150, 30, 100), (180, 255, 255)),
            ((140, 50, 50), (170, 255, 255)),
        ]
        
        # マスクを作成
        combined_mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in pink_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            combined_mask = cv2.bitwise_or(combined_mask, mask)
        
        # ノイズ除去
        kernel = np.ones((3, 3), np.uint8)
        mask_cleaned = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_OPEN, kernel)
        
        # グラフの境界を検出
        left_bound, right_bound = self.find_graph_bounds(mask_cleaned)
        print(f"グラフ境界: X={left_bound} to {right_bound}")
        
        # グラフデータを抽出
        data_points = []
        for x in range(left_bound, right_bound + 1):
            column = mask_cleaned[:, x]
            pink_pixels = np.where(column > 0)[0]
            
            if len(pink_pixels) > 0:
                # 最も下のピンクピクセル
                y_pixel = pink_pixels[-1]
                
                # ゼロラインからの距離を基準に値を計算
                pixels_from_zero = zero_y - y_pixel
                
                # Y軸の上下の範囲を推定（ゼロラインが中央にあると仮定）
                pixels_per_unit = zero_y / 30000  # ゼロから上端までが30000
                y_value = pixels_from_zero / pixels_per_unit
                
                data_points.append({
                    'x': x,
                    'y_pixel': y_pixel,
                    'y_value': y_value,
                    'pixels_from_zero': pixels_from_zero
                })
        
        print(f"検出されたデータポイント数: {len(data_points)}")
        
        if len(data_points) > 0:
            # 基本統計
            y_values = [p['y_value'] for p in data_points]
            print(f"\n基本統計:")
            print(f"  最小値: {min(y_values):.0f}")
            print(f"  最大値: {max(y_values):.0f}")
            print(f"  最終値: {y_values[-1]:.0f}")
            print(f"  平均値: {np.mean(y_values):.0f}")
            
            # 可視化
            self.visualize_results(img, mask_cleaned, data_points, zero_y, image_path)
            
            return {
                'data_points': data_points,
                'min_value': min(y_values),
                'max_value': max(y_values),
                'final_value': y_values[-1],
                'mean_value': np.mean(y_values),
                'zero_line_y': zero_y
            }
        else:
            print("警告: データポイントが検出されませんでした")
            return None
    
    def visualize_results(self, img, mask, data_points, zero_y, image_path):
        """結果を可視化"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. 元画像とゼロライン
        img_with_zero = img.copy()
        cv2.line(img_with_zero, (0, zero_y), (img.shape[1], zero_y), (0, 255, 0), 2)
        axes[0, 0].imshow(cv2.cvtColor(img_with_zero, cv2.COLOR_BGR2RGB))
        axes[0, 0].set_title('元画像（緑線：ゼロライン）')
        axes[0, 0].axis('off')
        
        # 2. マスク画像
        axes[0, 1].imshow(mask, cmap='gray')
        axes[0, 1].set_title('ピンク色検出マスク')
        axes[0, 1].axis('off')
        
        # 3. 検出されたポイント
        img_with_points = img.copy()
        cv2.line(img_with_points, (0, zero_y), (img.shape[1], zero_y), (0, 255, 0), 2)
        for point in data_points[::10]:  # 10ポイントごとに表示
            cv2.circle(img_with_points, (point['x'], point['y_pixel']), 2, (255, 0, 0), -1)
        axes[1, 0].imshow(cv2.cvtColor(img_with_points, cv2.COLOR_BGR2RGB))
        axes[1, 0].set_title('検出されたデータポイント（青点）')
        axes[1, 0].axis('off')
        
        # 4. 抽出されたグラフ
        x_values = [p['x'] for p in data_points]
        y_values = [p['y_value'] for p in data_points]
        axes[1, 1].plot(x_values, y_values, 'b-', linewidth=2)
        axes[1, 1].set_title('抽出されたデータ')
        axes[1, 1].set_xlabel('X座標')
        axes[1, 1].set_ylabel('値')
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].axhline(y=0, color='r', linestyle='--', alpha=0.5)
        axes[1, 1].set_ylim(-35000, 35000)
        
        plt.suptitle(f'ゼロライン基準グラフ読み込み結果: {os.path.basename(image_path)}')
        plt.tight_layout()
        
        # 保存
        output_path = image_path.replace('.png', '_zero_line_analysis.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n可視化結果を保存: {output_path}")
        plt.close()

def main():
    """メイン処理"""
    reader = ZeroLineGraphReader()
    
    # テスト画像のパス
    test_images = [
        "graphs/cropped/S__78209130_optimal.png",
        "graphs/cropped/S__78209132_optimal.png",
        "graphs/cropped/S__78209088_optimal.png"
    ]
    
    results = {}
    for image_path in test_images:
        if os.path.exists(image_path):
            result = reader.read_graph(image_path)
            if result:
                results[os.path.basename(image_path)] = result
        else:
            print(f"警告: ファイルが見つかりません: {image_path}")
    
    # 結果のサマリー
    print(f"\n{'='*60}")
    print("全体サマリー")
    print(f"{'='*60}")
    
    # results.txtとの比較
    actual_values = {
        'S__78209130_optimal.png': {'max': 9060, 'final': -5997},
        'S__78209132_optimal.png': {'max': 36350, 'final': 28935},
        'S__78209088_optimal.png': {'max': 3340, 'final': 3125}
    }
    
    for image_name, result in results.items():
        print(f"\n{image_name}:")
        print(f"  抽出最大値: {result['max_value']:.0f}")
        print(f"  抽出最終値: {result['final_value']:.0f}")
        print(f"  ゼロラインY: {result['zero_line_y']}")
        
        if image_name in actual_values:
            actual = actual_values[image_name]
            max_error = result['max_value'] - actual['max']
            final_error = result['final_value'] - actual['final']
            print(f"  実際の最大値: {actual['max']}")
            print(f"  実際の最終値: {actual['final']}")
            print(f"  最大値誤差: {max_error:.0f} ({abs(max_error/actual['max']*100):.1f}%)")
            print(f"  最終値誤差: {final_error:.0f}")

if __name__ == "__main__":
    main()