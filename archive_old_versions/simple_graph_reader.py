#!/usr/bin/env python3
"""
シンプルなグラフ読み込みツール
グラフ画像から基本的な方法で数値を抽出
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os

class SimpleGraphReader:
    """シンプルなグラフ読み込みクラス"""
    
    def __init__(self):
        # グラフの基本パラメータ
        self.graph_width = 911
        self.graph_height = 797
        self.y_min = -30000
        self.y_max = 30000
        self.y_range = self.y_max - self.y_min
        
        # グラフエリアの境界（おおよその値）
        self.graph_left = 80
        self.graph_right = 890
        self.graph_top = 50
        self.graph_bottom = 720
        
    def read_graph(self, image_path):
        """グラフ画像を読み込んで基本的な解析を行う"""
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
        
        # 画像サイズに基づいてグラフ境界を調整
        self.graph_left = int(width * 0.08)
        self.graph_right = min(int(width * 0.95), width - 1)
        self.graph_top = int(height * 0.06)
        self.graph_bottom = int(height * 0.90)
        
        # HSV色空間に変換
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # ピンク色の範囲を定義（複数の範囲を試す）
        pink_ranges = [
            # 標準的なピンク
            ((150, 50, 50), (180, 255, 255)),
            # 明るいピンク
            ((150, 30, 100), (180, 255, 255)),
            # 紫がかったピンク
            ((140, 50, 50), (170, 255, 255)),
            # 赤みがかったピンク
            ((170, 50, 50), (180, 255, 255)),
            ((0, 50, 50), (10, 255, 255))
        ]
        
        # 各色範囲でマスクを作成
        combined_mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in pink_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            combined_mask = cv2.bitwise_or(combined_mask, mask)
        
        # ノイズ除去
        kernel = np.ones((3, 3), np.uint8)
        mask_cleaned = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_OPEN, kernel)
        
        # グラフデータを抽出（各X座標で最も下のピンクピクセルを探す）
        data_points = []
        for x in range(self.graph_left, self.graph_right):
            column = mask_cleaned[:, x]
            pink_pixels = np.where(column > 0)[0]
            
            if len(pink_pixels) > 0:
                # 最も下のピンクピクセル（Y座標が大きい）
                y_pixel = pink_pixels[-1]
                
                # ピクセル座標を実際の値に変換
                y_normalized = (self.graph_bottom - y_pixel) / (self.graph_bottom - self.graph_top)
                y_value = self.y_min + y_normalized * self.y_range
                
                data_points.append({
                    'x': x,
                    'y_pixel': y_pixel,
                    'y_value': y_value
                })
        
        print(f"\n検出されたデータポイント数: {len(data_points)}")
        
        if len(data_points) > 0:
            # 基本統計
            y_values = [p['y_value'] for p in data_points]
            print(f"\n基本統計:")
            print(f"  最小値: {min(y_values):.0f}")
            print(f"  最大値: {max(y_values):.0f}")
            print(f"  最終値: {y_values[-1]:.0f}")
            print(f"  平均値: {np.mean(y_values):.0f}")
            
            # 可視化
            self.visualize_results(img, mask_cleaned, data_points, image_path)
            
            return {
                'data_points': data_points,
                'min_value': min(y_values),
                'max_value': max(y_values),
                'final_value': y_values[-1],
                'mean_value': np.mean(y_values)
            }
        else:
            print("警告: データポイントが検出されませんでした")
            return None
    
    def visualize_results(self, img, mask, data_points, image_path):
        """結果を可視化"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. 元画像
        axes[0, 0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        axes[0, 0].set_title('元画像')
        axes[0, 0].axis('off')
        
        # 2. マスク画像
        axes[0, 1].imshow(mask, cmap='gray')
        axes[0, 1].set_title('ピンク色検出マスク')
        axes[0, 1].axis('off')
        
        # 3. 検出されたポイント
        img_with_points = img.copy()
        for point in data_points[::10]:  # 10ポイントごとに表示
            cv2.circle(img_with_points, (point['x'], point['y_pixel']), 2, (0, 255, 0), -1)
        axes[1, 0].imshow(cv2.cvtColor(img_with_points, cv2.COLOR_BGR2RGB))
        axes[1, 0].set_title('検出されたデータポイント')
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
        
        plt.suptitle(f'シンプルグラフ読み込み結果: {os.path.basename(image_path)}')
        plt.tight_layout()
        
        # 保存
        output_path = image_path.replace('.png', '_simple_analysis.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n可視化結果を保存: {output_path}")
        plt.close()

def main():
    """メイン処理"""
    reader = SimpleGraphReader()
    
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
    for image_name, result in results.items():
        print(f"\n{image_name}:")
        print(f"  最大値: {result['max_value']:.0f}")
        print(f"  最終値: {result['final_value']:.0f}")
        print(f"  データポイント数: {len(result['data_points'])}")

if __name__ == "__main__":
    main()