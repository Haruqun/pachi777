#!/usr/bin/env python3
"""
グラフデータ読み取りツール
グレースケール変換して複数色のグラフラインを検出・読み取り
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os
import json
from datetime import datetime
import pandas as pd

class GraphDataReader:
    """グラフデータ読み取りクラス"""
    
    def __init__(self, input_dir="graphs/manual_crop/cropped", output_dir="graphs/extracted_data"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # 出力ディレクトリ作成
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "grayscale"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "detected_lines"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "csv"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "plots"), exist_ok=True)
        
        # 日本語フォント設定
        try:
            japanese_fonts = [f for f in font_manager.fontManager.ttflist if 'Hiragino' in f.name]
            if japanese_fonts:
                plt.rcParams['font.family'] = japanese_fonts[0].name
        except:
            pass
    
    def analyze_graph_colors(self, img):
        """グラフの色を分析"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        height, width = img.shape[:2]
        
        # ゼロラインは固定位置（画像の太いグレーの線）
        # 500px高さの画像で、ゼロラインは中央から少し下
        zero_line_y = 260  # 固定値（258から2px下）
        
        print(f"  ゼロライン検出: Y={zero_line_y}")
        
        # 色の範囲定義（HSV）
        color_ranges = {
            'pink': {
                'lower': np.array([140, 30, 100]),
                'upper': np.array([170, 255, 255]),
                'bgr': (255, 100, 200)
            },
            'orange': {
                'lower': np.array([5, 100, 100]),
                'upper': np.array([25, 255, 255]),
                'bgr': (0, 165, 255)
            },
            'red': {
                'lower': np.array([0, 100, 100]),
                'upper': np.array([10, 255, 255]),
                'bgr': (0, 0, 255)
            },
            'blue': {
                'lower': np.array([90, 100, 100]),
                'upper': np.array([120, 255, 255]),
                'bgr': (255, 0, 0)
            },
            'green': {
                'lower': np.array([40, 100, 100]),
                'upper': np.array([80, 255, 255]),
                'bgr': (0, 255, 0)
            }
        }
        
        # 各色のピクセル数をカウント
        color_counts = {}
        for color_name, ranges in color_ranges.items():
            mask = cv2.inRange(hsv, ranges['lower'], ranges['upper'])
            count = np.sum(mask > 0)
            if count > width * 10:  # 最低でも10行分のピクセルがある
                color_counts[color_name] = count
                print(f"  {color_name}: {count} pixels")
        
        return color_ranges, color_counts, zero_line_y
    
    def extract_graph_line(self, img, color_mask, zero_line_y):
        """マスクからグラフラインを抽出"""
        height, width = img.shape[:2]
        data_points = []
        
        for x in range(width):
            column = color_mask[:, x]
            
            # その列で色がある全てのy座標を取得
            y_positions = np.where(column > 0)[0]
            
            if len(y_positions) > 0:
                # 最も多くのピクセルが集中している位置を採用
                # または平均位置を使用
                y = int(np.median(y_positions))
                
                # ゼロラインからの相対位置（上がプラス）
                relative_y = zero_line_y - y
                
                # -250から+250の範囲に正規化（実際の値への変換は後で）
                data_points.append({
                    'x': x,
                    'y': y,
                    'relative_y': relative_y,
                    'value': relative_y * 120  # 1ピクセル = 120の値（仮定）
                })
        
        return data_points
    
    def convert_to_grayscale_enhanced(self, img):
        """グレースケール変換（グラフライン強調版）"""
        # 通常のグレースケール
        gray_standard = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # HSVで彩度の高い部分を抽出
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        
        # 彩度が高い部分（グラフライン）を強調
        enhanced = np.where(saturation > 50, 255 - gray_standard, gray_standard)
        
        return gray_standard, enhanced.astype(np.uint8)
    
    def process_image(self, img_path):
        """画像を処理してグラフデータを抽出"""
        print(f"\n処理中: {os.path.basename(img_path)}")
        
        img = cv2.imread(img_path)
        if img is None:
            print(f"エラー: 画像を読み込めません: {img_path}")
            return None
        
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        height, width = img.shape[:2]
        
        # 1. 色分析
        color_ranges, color_counts, zero_line_y = self.analyze_graph_colors(img)
        
        # 2. グレースケール変換
        gray_standard, gray_enhanced = self.convert_to_grayscale_enhanced(img)
        
        # グレースケール画像を保存
        gray_path = os.path.join(self.output_dir, "grayscale", f"{base_name}_gray.png")
        cv2.imwrite(gray_path, gray_standard)
        
        gray_enhanced_path = os.path.join(self.output_dir, "grayscale", f"{base_name}_gray_enhanced.png")
        cv2.imwrite(gray_enhanced_path, gray_enhanced)
        
        # 3. 各色のグラフラインを抽出
        all_data = {}
        detection_img = img.copy()
        
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        for color_name in color_counts.keys():
            print(f"  {color_name}のライン抽出中...")
            
            # 色マスクを作成
            ranges = color_ranges[color_name]
            mask = cv2.inRange(hsv, ranges['lower'], ranges['upper'])
            
            # ノイズ除去
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # グラフライン抽出
            data_points = self.extract_graph_line(img, mask, zero_line_y)
            
            if len(data_points) > 10:  # 有効なデータがある場合
                all_data[color_name] = data_points
                
                # 検出結果を描画
                for point in data_points[::5]:  # 5点ごとに描画（見やすさのため）
                    cv2.circle(detection_img, (point['x'], point['y']), 
                             2, ranges['bgr'], -1)
        
        # 4. ゼロラインを描画
        cv2.line(detection_img, (0, zero_line_y), (width, zero_line_y), 
                (0, 0, 0), 2)
        cv2.putText(detection_img, "0", (10, zero_line_y + 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # 検出結果を保存
        detection_path = os.path.join(self.output_dir, "detected_lines", 
                                    f"{base_name}_detected.png")
        cv2.imwrite(detection_path, detection_img)
        
        # 5. CSVに保存
        for color_name, data_points in all_data.items():
            df = pd.DataFrame(data_points)
            csv_path = os.path.join(self.output_dir, "csv", 
                                  f"{base_name}_{color_name}.csv")
            df.to_csv(csv_path, index=False)
            print(f"  {color_name}: {len(data_points)}点のデータを保存")
        
        # 6. グラフをプロット
        self.plot_extracted_data(all_data, base_name, zero_line_y, height)
        
        return {
            'image': base_name,
            'size': (width, height),
            'zero_line': zero_line_y,
            'colors_detected': list(all_data.keys()),
            'data_points': {color: len(points) for color, points in all_data.items()}
        }
    
    def plot_extracted_data(self, all_data, base_name, zero_line_y, img_height):
        """抽出したデータをプロット"""
        if not all_data:
            return
        
        plt.figure(figsize=(12, 8))
        
        # 各色のデータをプロット
        for color_name, data_points in all_data.items():
            if not data_points:
                continue
            
            x_values = [p['x'] for p in data_points]
            y_values = [p['value'] for p in data_points]
            
            plt.plot(x_values, y_values, label=f'{color_name}', linewidth=2)
        
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        plt.grid(True, alpha=0.3)
        plt.xlabel('X座標（ピクセル）')
        plt.ylabel('値（推定）')
        plt.title(f'抽出グラフデータ: {base_name}')
        plt.legend()
        
        # Y軸の範囲を設定（±15000程度）
        plt.ylim(-15000, 15000)
        
        plot_path = os.path.join(self.output_dir, "plots", f"{base_name}_plot.png")
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  プロット保存: {plot_path}")
    
    def process_all(self):
        """すべての画像を処理"""
        import glob
        image_files = glob.glob(os.path.join(self.input_dir, "*.png"))
        image_files.sort()
        
        print(f"グラフデータ読み取り開始")
        print(f"対象: {len(image_files)}枚")
        
        results = []
        
        for img_path in image_files[:5]:  # まず5枚でテスト
            result = self.process_image(img_path)
            if result:
                results.append(result)
        
        # サマリーレポート
        self.generate_report(results)
        
        return results
    
    def generate_report(self, results):
        """レポート生成"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_images': len(results),
            'results': results
        }
        
        report_path = os.path.join(self.output_dir, 
                                 f"extraction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n処理完了サマリー:")
        print(f"処理画像数: {len(results)}")
        
        # 検出色の統計
        all_colors = []
        for r in results:
            all_colors.extend(r['colors_detected'])
        
        from collections import Counter
        color_stats = Counter(all_colors)
        
        print(f"\n検出された色:")
        for color, count in color_stats.items():
            print(f"  {color}: {count}枚")
        
        print(f"\nレポート保存: {report_path}")

def main():
    """メイン処理"""
    reader = GraphDataReader()
    results = reader.process_all()

if __name__ == "__main__":
    main()