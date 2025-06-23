#!/usr/bin/env python3
"""
グラフエリアのみを正確に切り出すツール
不要な部分（オレンジバー、ボタン、余白）を除去
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os
import json
from datetime import datetime
import pandas as pd

class GraphOnlyCropper:
    """グラフエリアのみを切り出すクラス"""
    
    def __init__(self, original_dir="graphs/original", output_dir="graphs/graph_only"):
        self.original_dir = original_dir
        self.output_dir = output_dir
        self.cropped_dir = os.path.join(output_dir, "cropped")
        self.data_dir = os.path.join(output_dir, "extracted_data")
        self.report_dir = os.path.join(output_dir, "reports")
        
        # 出力ディレクトリを作成
        for dir_path in [self.output_dir, self.cropped_dir, self.data_dir, self.report_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def detect_graph_boundaries(self, img):
        """グラフエリアの正確な境界を検出"""
        height, width = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. オレンジバーを検出（上端の基準）
        orange_ranges = [
            ((10, 100, 100), (30, 255, 255)),
            ((5, 120, 120), (35, 255, 255)),
        ]
        
        orange_mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in orange_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            orange_mask = cv2.bitwise_or(orange_mask, mask)
        
        # オレンジバーの下端を見つける
        horizontal_projection = np.sum(orange_mask, axis=1)
        orange_bottom = 0
        for y in range(height):
            if horizontal_projection[y] > width * 0.3:
                orange_bottom = max(orange_bottom, y)
        
        # 2. ボタンエリアを検出（下端の基準）
        # グレースケールで明るい矩形領域（ボタン）を検出
        buttons_detected = False
        button_top = height
        
        # 下半分でボタンを探す
        bottom_half = gray[height//2:]
        
        # ボタンの特徴：明るい矩形領域
        _, thresh = cv2.threshold(bottom_half, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # ボタンサイズの条件
            if w > 80 and h > 30 and w < 200 and h < 80:
                button_y = y + height//2  # 元の座標系に戻す
                button_top = min(button_top, button_y)
                buttons_detected = True
        
        # ボタンが検出されない場合、「最大値」テキストを探す
        if not buttons_detected:
            # 「最大值」テキストのY座標を推定
            button_top = int(height * 0.85)  # 画像の85%位置
        
        # 3. 左右の境界を検出
        # Y軸ラベル「30,000」の左端を探す
        left_boundary = 0
        right_boundary = width
        
        # グラフエリアの中央部分（オレンジバー下からボタン上まで）で分析
        graph_area = gray[orange_bottom+20:button_top-20, :]
        if graph_area.shape[0] > 0:
            # 各列の分散を計算（グラフラインがある部分は分散が大きい）
            col_variance = np.var(graph_area, axis=0)
            
            # 左端：分散が一定以上になる最初の点
            threshold = np.mean(col_variance) * 0.5
            for x in range(width):
                if x < len(col_variance) and col_variance[x] > threshold:
                    left_boundary = max(0, x - 10)  # 少し余裕を持たせる
                    break
            
            # 右端：分散が一定以上になる最後の点
            for x in range(width-1, -1, -1):
                if x < len(col_variance) and col_variance[x] > threshold:
                    right_boundary = min(width, x + 10)  # 少し余裕を持たせる
                    break
        
        # 4. 最終的な境界を決定
        graph_top = orange_bottom + 10  # オレンジバーの少し下
        graph_bottom = button_top - 10   # ボタンの少し上
        graph_left = max(0, left_boundary)
        graph_right = min(width, right_boundary)
        
        return {
            'top': graph_top,
            'bottom': graph_bottom,
            'left': graph_left,
            'right': graph_right,
            'width': graph_right - graph_left,
            'height': graph_bottom - graph_top
        }
    
    def crop_graph_only(self, image_path):
        """グラフエリアのみを切り出し"""
        print(f"\nグラフのみ切り抜き: {os.path.basename(image_path)}")
        
        img = cv2.imread(image_path)
        if img is None:
            print(f"エラー: 画像を読み込めません: {image_path}")
            return None, None
        
        # グラフ境界を検出
        boundaries = self.detect_graph_boundaries(img)
        
        print(f"検出境界: top={boundaries['top']}, bottom={boundaries['bottom']}, "
              f"left={boundaries['left']}, right={boundaries['right']}")
        print(f"グラフサイズ: {boundaries['width']}x{boundaries['height']}")
        
        # 切り抜き実行
        cropped = img[boundaries['top']:boundaries['bottom'], 
                     boundaries['left']:boundaries['right']]
        
        if cropped.size == 0:
            print("エラー: 切り抜き結果が空です")
            return None, None
        
        return cropped, boundaries
    
    def extract_graph_data(self, cropped_img):
        """切り抜いたグラフからデータを抽出"""
        if cropped_img is None:
            return None, None
            
        height, width = cropped_img.shape[:2]
        
        # ゼロライン位置を推定（グラフの中央付近）
        zero_y = int(height * 0.6)  # 経験的に60%位置
        
        # HSV変換
        hsv = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2HSV)
        
        # ピンク色と青色/オレンジ色の検出
        pink_ranges = [
            ((150, 50, 50), (180, 255, 255)),
            ((140, 30, 100), (170, 255, 255)),
        ]
        
        other_ranges = [
            # 青色
            ((100, 50, 50), (130, 255, 255)),
            ((90, 30, 100), (120, 255, 255)),
            # オレンジ/赤色
            ((0, 50, 50), (20, 255, 255)),
            ((160, 50, 50), (180, 255, 255)),
        ]
        
        # 各色のマスクを作成
        pink_mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in pink_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            pink_mask = cv2.bitwise_or(pink_mask, mask)
        
        other_mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in other_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            other_mask = cv2.bitwise_or(other_mask, mask)
        
        # 優勢な色を選択
        pink_pixels = np.sum(pink_mask)
        other_pixels = np.sum(other_mask)
        
        if pink_pixels > other_pixels:
            primary_mask = pink_mask
            graph_color = "pink"
        else:
            primary_mask = other_mask
            graph_color = "blue_orange"
        
        # ノイズ除去
        kernel = np.ones((3, 3), np.uint8)
        mask_cleaned = cv2.morphologyEx(primary_mask, cv2.MORPH_CLOSE, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_OPEN, kernel)
        
        # データポイント抽出
        data_points = []
        for x in range(width):
            column = mask_cleaned[:, x]
            graph_pixels = np.where(column > 0)[0]
            
            if len(graph_pixels) > 0:
                y_pixel = graph_pixels[-1]  # 最下端のピクセル
                
                # Y座標を実際の値に変換
                pixels_from_zero = zero_y - y_pixel
                
                # スケーリング（ゼロライン基準で±30000）
                if y_pixel < zero_y:
                    # ゼロラインより上（正の値）
                    y_value = pixels_from_zero * (30000 / zero_y)
                else:
                    # ゼロラインより下（負の値）  
                    y_value = pixels_from_zero * (30000 / (height - zero_y))
                
                data_points.append({
                    'x': x,
                    'y_pixel': y_pixel,
                    'y_value': y_value
                })
        
        return data_points, graph_color
    
    def process_image(self, image_path):
        """単一画像を処理"""
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # 1. グラフのみ切り抜き
        cropped, boundaries = self.crop_graph_only(image_path)
        
        if cropped is None:
            return None
        
        # 切り抜き画像を保存
        cropped_path = os.path.join(self.cropped_dir, f"{base_name}_graph_only.png")
        cv2.imwrite(cropped_path, cropped)
        
        # 2. データ抽出
        data_points, graph_color = self.extract_graph_data(cropped)
        
        if not data_points:
            print("警告: データポイントが検出されませんでした")
            return None
        
        # データをCSVに保存
        df = pd.DataFrame(data_points)
        csv_path = os.path.join(self.data_dir, f"{base_name}_data.csv")
        df.to_csv(csv_path, index=False)
        
        # 統計情報
        y_values = [p['y_value'] for p in data_points]
        stats = {
            'file_name': base_name,
            'boundaries': boundaries,
            'graph_color': graph_color,
            'min_value': min(y_values),
            'max_value': max(y_values),
            'final_value': y_values[-1],
            'mean_value': np.mean(y_values),
            'data_points': len(data_points)
        }
        
        # 可視化
        self.visualize_results(cropped, data_points, stats, base_name)
        
        return stats
    
    def visualize_results(self, img, data_points, stats, base_name):
        """結果を可視化"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # 1. 切り抜き画像
        axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        axes[0].set_title(f'Graph Only ({stats["boundaries"]["width"]}x{stats["boundaries"]["height"]})')
        axes[0].axis('off')
        
        # 2. 抽出データ
        x_values = [p['x'] for p in data_points]
        y_values = [p['y_value'] for p in data_points]
        
        color = 'hotpink' if stats['graph_color'] == 'pink' else 'blue'
        axes[1].plot(x_values, y_values, color=color, linewidth=2)
        axes[1].set_title(f'Extracted Data ({stats["graph_color"]})')
        axes[1].set_xlabel('X Position')
        axes[1].set_ylabel('Value')
        axes[1].grid(True, alpha=0.3)
        axes[1].axhline(y=0, color='red', linestyle='--', alpha=0.5)
        axes[1].set_ylim(-35000, 35000)
        
        # 統計情報
        stats_text = f"Max: {stats['max_value']:.0f}\nFinal: {stats['final_value']:.0f}"
        axes[1].text(0.02, 0.98, stats_text, transform=axes[1].transAxes,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.suptitle(f'Graph Only Cropper: {base_name}')
        plt.tight_layout()
        
        viz_path = os.path.join(self.report_dir, f"{base_name}_visualization.png")
        plt.savefig(viz_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def process_all(self):
        """全画像を処理"""
        print(f"\n{'='*80}")
        print("グラフのみ切り抜きパイプライン開始")
        print(f"{'='*80}")
        
        # 画像ファイルを取得
        import glob
        image_files = glob.glob(os.path.join(self.original_dir, "*.jpg"))
        image_files.sort()
        
        print(f"処理対象: {len(image_files)}枚")
        
        results = []
        
        for image_path in image_files:
            result = self.process_image(image_path)
            if result:
                results.append(result)
        
        # サマリーレポート
        self.generate_summary(results)
        
        return results
    
    def generate_summary(self, results):
        """サマリーレポートを生成"""
        print(f"\n{'='*80}")
        print("グラフのみ切り抜き完了サマリー")
        print(f"{'='*80}")
        
        if results:
            # サイズの統計
            widths = [r['boundaries']['width'] for r in results]
            heights = [r['boundaries']['height'] for r in results]
            
            print(f"\n切り抜きサイズ:")
            print(f"  幅: 平均 {np.mean(widths):.0f}px, 範囲 {min(widths)}-{max(widths)}px")
            print(f"  高さ: 平均 {np.mean(heights):.0f}px, 範囲 {min(heights)}-{max(heights)}px")
            
            # 色別統計
            pink_count = sum(1 for r in results if r['graph_color'] == 'pink')
            other_count = len(results) - pink_count
            print(f"\nグラフ色分布:")
            print(f"  ピンク: {pink_count}枚")
            print(f"  その他: {other_count}枚")
            
            print(f"\n処理成功: {len(results)}枚")
        
        # レポート保存
        report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_processed': len(results),
            'results': results
        }
        
        report_path = os.path.join(self.report_dir, f"graph_only_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        # float32をfloatに変換
        def convert_types(obj):
            if isinstance(obj, np.float32):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(item) for item in obj]
            return obj
        
        report = convert_types(report)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\nレポート保存: {report_path}")

def main():
    """メイン処理"""
    cropper = GraphOnlyCropper(
        original_dir="/Users/haruqun/Work/pachi777/graphs/original"
    )
    
    results = cropper.process_all()

if __name__ == "__main__":
    main()