#!/usr/bin/env python3
"""
統合グラフ処理パイプライン
original画像フォルダから開始して、切り抜き、データ抽出、精度検証まで実行
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os
import json
from datetime import datetime
import pandas as pd

class IntegratedGraphPipeline:
    """統合グラフ処理パイプラインクラス"""
    
    def __init__(self, original_dir="graphs/original", output_dir="graphs/pipeline_output"):
        self.original_dir = original_dir
        self.output_dir = output_dir
        self.cropped_dir = os.path.join(output_dir, "cropped")
        self.data_dir = os.path.join(output_dir, "extracted_data")
        self.report_dir = os.path.join(output_dir, "reports")
        
        # 出力ディレクトリを作成
        for dir_path in [self.output_dir, self.cropped_dir, self.data_dir, self.report_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # グラフパラメータ
        self.standard_width = 911
        self.standard_height = 797
        self.y_min = -30000
        self.y_max = 30000
        
    def detect_orange_bar(self, img):
        """オレンジバーを検出してグラフエリアの上端を特定"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # オレンジ色の範囲
        orange_lower = np.array([5, 100, 100])
        orange_upper = np.array([25, 255, 255])
        
        mask = cv2.inRange(hsv, orange_lower, orange_upper)
        
        # 水平方向に投影
        horizontal_projection = np.sum(mask, axis=1)
        
        # しきい値を超える最初の行を探す
        threshold = img.shape[1] * 0.5
        for y in range(len(horizontal_projection)):
            if horizontal_projection[y] > threshold:
                return y
        
        return None
    
    def detect_zero_line(self, img, graph_area):
        """グラフエリア内のゼロラインを検出"""
        gray = cv2.cvtColor(graph_area, cv2.COLOR_BGR2GRAY)
        
        # エッジ検出
        edges = cv2.Canny(gray, 50, 150)
        
        # 水平線検出
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100,
                                minLineLength=graph_area.shape[1]*0.5, maxLineGap=10)
        
        if lines is None:
            return graph_area.shape[0] // 2
        
        # 最も長い水平線を探す
        horizontal_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) < 3:
                length = abs(x2 - x1)
                horizontal_lines.append((y1, length))
        
        if horizontal_lines:
            horizontal_lines.sort(key=lambda x: x[1], reverse=True)
            return horizontal_lines[0][0]
        
        return graph_area.shape[0] // 2
    
    def crop_graph(self, image_path):
        """画像からグラフエリアを切り抜き"""
        print(f"\n切り抜き処理: {os.path.basename(image_path)}")
        
        img = cv2.imread(image_path)
        if img is None:
            print(f"エラー: 画像を読み込めません: {image_path}")
            return None
        
        height, width = img.shape[:2]
        
        # オレンジバーを検出
        orange_y = self.detect_orange_bar(img)
        
        if orange_y is None:
            print("警告: オレンジバーが検出できません。標準レイアウトを使用します。")
            # 標準的な位置を仮定
            graph_top = int(height * 0.35)
        else:
            # オレンジバーの下がグラフエリア
            # グラフの上端（30000の線）から下端（-30000の線）まで含める
            graph_top = orange_y + 50
            print(f"オレンジバー検出: Y={orange_y}")
        
        # グラフエリアを検出して適切なサイズで切り抜く
        # 画像内でグラフを探す（通常、グラフは画像の中央付近にある）
        # 上下30000の範囲全体を含むために、十分な高さを確保
        
        # グラフの探索範囲を設定
        search_start = graph_top
        search_end = min(height - 50, graph_top + 1000)
        
        # グレースケール変換してエッジ検出
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 水平線を検出（グラフの上下の境界線）
        horizontal_projection = np.sum(edges[search_start:search_end, :], axis=1)
        
        # グラフの境界を見つける（エッジが多い領域）
        threshold = width * 0.3
        graph_regions = []
        in_graph = False
        start_y = 0
        
        for i, value in enumerate(horizontal_projection):
            y = i + search_start
            if value > threshold and not in_graph:
                start_y = y
                in_graph = True
            elif value < threshold * 0.5 and in_graph:
                if y - start_y > 100:  # 最小高さ
                    graph_regions.append((start_y, y))
                in_graph = False
        
        # 最も大きな領域を選択
        if graph_regions:
            graph_regions.sort(key=lambda x: x[1] - x[0], reverse=True)
            graph_top = graph_regions[0][0] - 20  # 上部マージン
            graph_bottom = graph_regions[0][1] + 20  # 下部マージン
        else:
            # デフォルトサイズ
            graph_bottom = graph_top + self.standard_height
        
        # 左右の位置
        graph_left = (width - self.standard_width) // 2
        graph_right = graph_left + self.standard_width
        
        # 境界チェック
        graph_top = max(0, graph_top)
        graph_bottom = min(graph_bottom, height)
        graph_left = max(0, graph_left)
        graph_right = min(graph_right, width)
        
        # 切り抜き
        cropped = img[graph_top:graph_bottom, graph_left:graph_right]
        
        print(f"切り抜き領域: Y={graph_top}〜{graph_bottom}, X={graph_left}〜{graph_right}")
        print(f"切り抜きサイズ: {cropped.shape[1]}x{cropped.shape[0]}")
        
        return cropped
    
    def extract_graph_data(self, cropped_img):
        """切り抜いた画像からグラフデータを抽出"""
        height, width = cropped_img.shape[:2]
        
        # ゼロラインを検出
        zero_y = self.detect_zero_line(cropped_img, cropped_img)
        print(f"ゼロライン検出: Y={zero_y}")
        
        # HSV変換
        hsv = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2HSV)
        
        # ピンク色の検出
        pink_ranges = [
            ((150, 50, 50), (180, 255, 255)),
            ((150, 30, 100), (180, 255, 255)),
            ((140, 50, 50), (170, 255, 255)),
        ]
        
        # 青色の検出
        blue_ranges = [
            ((100, 50, 50), (130, 255, 255)),  # 標準的な青
            ((90, 30, 100), (120, 255, 255)),  # 明るい青
            ((95, 100, 100), (115, 255, 255)), # 濃い青
        ]
        
        # ピンク色マスク
        pink_mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in pink_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            pink_mask = cv2.bitwise_or(pink_mask, mask)
        
        # 青色マスク
        blue_mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in blue_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            blue_mask = cv2.bitwise_or(blue_mask, mask)
        
        # 両方のマスクを結合
        combined_mask = cv2.bitwise_or(pink_mask, blue_mask)
        
        # どちらの色が優勢か判定
        pink_pixels = np.sum(pink_mask)
        blue_pixels = np.sum(blue_mask)
        
        if pink_pixels > blue_pixels:
            print(f"ピンク色のグラフを検出 (ピクセル数: {pink_pixels})")
            primary_mask = pink_mask
        else:
            print(f"青色のグラフを検出 (ピクセル数: {blue_pixels})")
            primary_mask = blue_mask
        
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
                # グラフの最も下のピクセル（最も大きいY座標）
                y_pixel = graph_pixels[-1]
                
                # ゼロラインからの距離を基準に値を計算
                # ゼロラインより上は正の値、下は負の値
                pixels_from_zero = zero_y - y_pixel
                
                # グラフの高さ全体が-30000から30000の範囲に対応
                # ゼロラインから上端までと下端までの距離を考慮
                if zero_y > 0:
                    pixels_per_unit = zero_y / 30000  # ゼロから上端までが30000
                else:
                    pixels_per_unit = height / 60000  # 全体の高さが60000に対応
                
                y_value = pixels_from_zero / pixels_per_unit
                
                data_points.append({
                    'x': x,
                    'y_pixel': y_pixel,
                    'y_value': y_value
                })
        
        print(f"検出されたデータポイント数: {len(data_points)}")
        
        return data_points, zero_y
    
    def process_single_image(self, image_path):
        """単一画像の完全処理"""
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # 1. 切り抜き
        cropped = self.crop_graph(image_path)
        if cropped is None:
            return None
        
        # 切り抜き画像を保存
        cropped_path = os.path.join(self.cropped_dir, f"{base_name}_cropped.png")
        cv2.imwrite(cropped_path, cropped)
        print(f"切り抜き画像保存: {cropped_path}")
        
        # 2. データ抽出
        data_points, zero_y = self.extract_graph_data(cropped)
        
        if not data_points:
            print("警告: データポイントが検出されませんでした")
            return None
        
        # データをCSVに保存
        df = pd.DataFrame(data_points)
        csv_path = os.path.join(self.data_dir, f"{base_name}_data.csv")
        df.to_csv(csv_path, index=False)
        print(f"データ保存: {csv_path}")
        
        # 3. 統計情報を計算
        y_values = [p['y_value'] for p in data_points]
        stats = {
            'file_name': base_name,
            'min_value': float(min(y_values)),
            'max_value': float(max(y_values)),
            'final_value': float(y_values[-1]),
            'mean_value': float(np.mean(y_values)),
            'start_value': float(y_values[0]),
            'data_points': len(data_points),
            'zero_line_y': int(zero_y)
        }
        
        # 4. 可視化
        self.visualize_results(cropped, data_points, zero_y, base_name)
        
        return stats
    
    def visualize_results(self, img, data_points, zero_y, base_name):
        """処理結果を可視化"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # 1. 切り抜き画像とゼロライン
        img_with_zero = img.copy()
        cv2.line(img_with_zero, (0, zero_y), (img.shape[1], zero_y), (0, 255, 0), 2)
        axes[0].imshow(cv2.cvtColor(img_with_zero, cv2.COLOR_BGR2RGB))
        axes[0].set_title('切り抜き画像（緑：ゼロライン）')
        axes[0].axis('off')
        
        # 2. 抽出されたグラフ
        x_values = [p['x'] for p in data_points]
        y_values = [p['y_value'] for p in data_points]
        axes[1].plot(x_values, y_values, 'b-', linewidth=2)
        axes[1].set_title('抽出されたデータ')
        axes[1].set_xlabel('X座標')
        axes[1].set_ylabel('値')
        axes[1].grid(True, alpha=0.3)
        axes[1].axhline(y=0, color='r', linestyle='--', alpha=0.5)
        
        # 統計情報を追加
        stats_text = f"最大: {max(y_values):.0f}\n最終: {y_values[-1]:.0f}"
        axes[1].text(0.02, 0.98, stats_text, transform=axes[1].transAxes,
                     verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.suptitle(f'パイプライン処理結果: {base_name}')
        plt.tight_layout()
        
        # 保存
        viz_path = os.path.join(self.report_dir, f"{base_name}_visualization.png")
        plt.savefig(viz_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"可視化保存: {viz_path}")
    
    def process_all_images(self):
        """全画像を処理"""
        print(f"\n{'='*60}")
        print("統合グラフ処理パイプライン開始")
        print(f"入力ディレクトリ: {self.original_dir}")
        print(f"出力ディレクトリ: {self.output_dir}")
        print(f"{'='*60}")
        
        # 画像ファイルを取得
        image_files = []
        for ext in ['*.jpg', '*.png', '*.jpeg']:
            pattern = os.path.join(self.original_dir, ext)
            import glob
            image_files.extend(glob.glob(pattern))
        
        image_files.sort()
        print(f"\n処理対象画像数: {len(image_files)}")
        
        # 全画像を処理
        results = []
        for image_path in image_files:
            result = self.process_single_image(image_path)
            if result:
                results.append(result)
        
        # サマリーレポートを生成
        self.generate_summary_report(results)
        
        return results
    
    def generate_summary_report(self, results):
        """処理結果のサマリーレポートを生成"""
        if not results:
            print("\n処理結果がありません")
            return
        
        # レポートデータを作成
        report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_processed': len(results),
            'pipeline_settings': {
                'standard_width': self.standard_width,
                'standard_height': self.standard_height,
                'y_range': f"{self.y_min} to {self.y_max}"
            },
            'results': results
        }
        
        # JSONレポートを保存
        report_path = os.path.join(self.report_dir, f"pipeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # CSVサマリーを保存
        df = pd.DataFrame(results)
        csv_path = os.path.join(self.report_dir, "pipeline_summary.csv")
        df.to_csv(csv_path, index=False)
        
        # コンソールにサマリーを表示
        print(f"\n{'='*60}")
        print("処理完了サマリー")
        print(f"{'='*60}")
        print(f"処理画像数: {len(results)}")
        print(f"レポート保存: {report_path}")
        print(f"CSVサマリー: {csv_path}")
        
        print("\n各画像の結果:")
        for result in results:
            print(f"\n{result['file_name']}:")
            print(f"  最大値: {result['max_value']:.0f}")
            print(f"  最終値: {result['final_value']:.0f}")
            print(f"  データポイント数: {result['data_points']}")

def main():
    """メイン処理"""
    # パイプラインを初期化
    pipeline = IntegratedGraphPipeline(
        original_dir="/Users/haruqun/Work/pachi777/graphs/original",
        output_dir="/Users/haruqun/Work/pachi777/graphs/pipeline_output"
    )
    
    # 全画像を処理
    results = pipeline.process_all_images()
    
    print(f"\n{'='*60}")
    print("パイプライン処理完了")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()