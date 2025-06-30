#!/usr/bin/env python3
"""
スタート地点0を基準としたグラフ読み込みツール
グラフの最初のデータポイントが必ず0であることを利用して正確なスケーリング
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os
from scipy import stats

class StartZeroGraphReader:
    """スタート地点0を基準としたグラフ読み込みクラス"""
    
    def __init__(self):
        # グラフの基本パラメータ
        self.y_min = -30000
        self.y_max = 30000
        
    def detect_zero_line(self, img):
        """ゼロラインを検出"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # エッジ検出
        edges = cv2.Canny(gray, 50, 150)
        
        # 水平線検出
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, 
                                minLineLength=width*0.5, maxLineGap=10)
        
        if lines is None:
            return height // 2
            
        # 最も長い水平線を探す
        horizontal_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) < 5:  # 水平に近い線
                length = abs(x2 - x1)
                horizontal_lines.append((y1, length))
        
        if not horizontal_lines:
            return height // 2
            
        # 最も長い水平線をゼロラインとする
        horizontal_lines.sort(key=lambda x: x[1], reverse=True)
        return horizontal_lines[0][0]
    
    def extract_graph_data(self, img, mask):
        """グラフデータを抽出"""
        height, width = mask.shape
        data_points = []
        
        # 各X座標でピンクピクセルを探す
        for x in range(width):
            column = mask[:, x]
            pink_pixels = np.where(column > 0)[0]
            
            if len(pink_pixels) > 0:
                # 最も下のピンクピクセル（グラフライン）
                y_pixel = pink_pixels[-1]
                data_points.append({
                    'x': x,
                    'y_pixel': y_pixel
                })
        
        return data_points
    
    def calibrate_y_axis(self, data_points, zero_y):
        """最初のデータポイントが0であることを利用してY軸をキャリブレーション"""
        if len(data_points) < 10:
            return None
            
        # 最初の数ポイントの平均Y座標を取得（ノイズ対策）
        first_points_y = [p['y_pixel'] for p in data_points[:5]]
        start_y = np.mean(first_points_y)
        
        # スタート地点は必ず0なので、これをゼロラインとの関係から計算
        # start_y（ピクセル座標）が値0に対応する
        
        # ピクセル単位から実際の値への変換係数を計算
        # ゼロラインがわかっている場合
        pixels_from_zero_to_start = zero_y - start_y
        
        # グラフの範囲から推定される1ピクセルあたりの値
        # グラフの高さの半分が30000に相当すると仮定
        pixels_per_unit = zero_y / 30000
        
        # 各データポイントの値を計算
        calibrated_points = []
        for point in data_points:
            y_pixel = point['y_pixel']
            
            # スタート地点からの相対位置で計算
            pixels_from_start = start_y - y_pixel
            
            # 実際の値に変換
            y_value = pixels_from_start / pixels_per_unit
            
            calibrated_points.append({
                'x': point['x'],
                'y_pixel': y_pixel,
                'y_value': y_value
            })
        
        return calibrated_points, pixels_per_unit
    
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
        print(f"ゼロライン検出: Y={zero_y}")
        
        # HSV色空間に変換
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # ピンク色の検出
        pink_ranges = [
            ((150, 50, 50), (180, 255, 255)),
            ((150, 30, 100), (180, 255, 255)),
            ((140, 50, 50), (170, 255, 255)),
        ]
        
        combined_mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in pink_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            combined_mask = cv2.bitwise_or(combined_mask, mask)
        
        # ノイズ除去
        kernel = np.ones((3, 3), np.uint8)
        mask_cleaned = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_OPEN, kernel)
        
        # グラフデータを抽出
        data_points = self.extract_graph_data(img, mask_cleaned)
        print(f"検出されたデータポイント数: {len(data_points)}")
        
        if len(data_points) < 10:
            print("警告: 十分なデータポイントが検出されませんでした")
            return None
        
        # Y軸のキャリブレーション（スタート地点=0を利用）
        calibrated_points, pixels_per_unit = self.calibrate_y_axis(data_points, zero_y)
        
        if calibrated_points:
            y_values = [p['y_value'] for p in calibrated_points]
            
            print(f"\n基本統計:")
            print(f"  最小値: {min(y_values):.0f}")
            print(f"  最大値: {max(y_values):.0f}")
            print(f"  最終値: {y_values[-1]:.0f}")
            print(f"  平均値: {np.mean(y_values):.0f}")
            print(f"  開始値: {y_values[0]:.0f} (理論値: 0)")
            print(f"  スケーリング: 1ピクセル = {1/pixels_per_unit:.0f}玉")
            
            # 可視化
            self.visualize_results(img, mask_cleaned, calibrated_points, zero_y, image_path)
            
            return {
                'data_points': calibrated_points,
                'min_value': min(y_values),
                'max_value': max(y_values),
                'final_value': y_values[-1],
                'mean_value': np.mean(y_values),
                'start_value': y_values[0],
                'pixels_per_unit': pixels_per_unit
            }
        
        return None
    
    def visualize_results(self, img, mask, data_points, zero_y, image_path):
        """結果を可視化"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. 元画像とゼロライン、スタート地点
        img_annotated = img.copy()
        cv2.line(img_annotated, (0, zero_y), (img.shape[1], zero_y), (0, 255, 0), 2)
        if data_points:
            start_y = data_points[0]['y_pixel']
            cv2.line(img_annotated, (0, start_y), (100, start_y), (255, 0, 0), 2)
            cv2.putText(img_annotated, "Start=0", (5, start_y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        
        axes[0, 0].imshow(cv2.cvtColor(img_annotated, cv2.COLOR_BGR2RGB))
        axes[0, 0].set_title('元画像（緑：ゼロライン、青：スタート地点）')
        axes[0, 0].axis('off')
        
        # 2. マスク画像
        axes[0, 1].imshow(mask, cmap='gray')
        axes[0, 1].set_title('ピンク色検出マスク')
        axes[0, 1].axis('off')
        
        # 3. 検出されたポイント
        img_with_points = img.copy()
        cv2.line(img_with_points, (0, zero_y), (img.shape[1], zero_y), (0, 255, 0), 2)
        for i, point in enumerate(data_points[::10]):  # 10ポイントごと
            color = (255, 0, 0) if i == 0 else (0, 0, 255)
            cv2.circle(img_with_points, (point['x'], point['y_pixel']), 2, color, -1)
        axes[1, 0].imshow(cv2.cvtColor(img_with_points, cv2.COLOR_BGR2RGB))
        axes[1, 0].set_title('検出されたデータポイント')
        axes[1, 0].axis('off')
        
        # 4. 抽出されたグラフ
        x_values = [p['x'] for p in data_points]
        y_values = [p['y_value'] for p in data_points]
        axes[1, 1].plot(x_values, y_values, 'b-', linewidth=2)
        axes[1, 1].scatter(x_values[0], y_values[0], color='red', s=100, 
                          label=f'スタート: {y_values[0]:.0f}')
        axes[1, 1].set_title('抽出されたデータ（スタート地点=0基準）')
        axes[1, 1].set_xlabel('X座標')
        axes[1, 1].set_ylabel('値')
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].axhline(y=0, color='r', linestyle='--', alpha=0.5)
        axes[1, 1].legend()
        axes[1, 1].set_ylim(-35000, 35000)
        
        plt.suptitle(f'スタート地点0基準グラフ読み込み: {os.path.basename(image_path)}')
        plt.tight_layout()
        
        # 保存
        output_path = image_path.replace('.png', '_start_zero_analysis.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n可視化結果を保存: {output_path}")
        plt.close()

def main():
    """メイン処理"""
    reader = StartZeroGraphReader()
    
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
    print("全体サマリー（スタート地点=0基準）")
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
        print(f"  開始値: {result['start_value']:.0f} (理論値: 0)")
        
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