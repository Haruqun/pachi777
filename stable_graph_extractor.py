#!/usr/bin/env python3
"""
安定版のグラフ抽出手法を再現
2ピクセル補正とサブピクセル精度を実装
"""

import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
from scipy import signal, interpolate
from scipy.ndimage import gaussian_filter1d
from datetime import datetime

class StableGraphExtractor:
    """安定版のグラフ抽出手法"""
    
    def __init__(self):
        # グラフ境界設定（実測値）
        self.boundaries = {
            "start_x": 36,
            "end_x": 620,
            "top_y": 26,
            "bottom_y": 523,
            "zero_y": 274
        }
        
        # 値の範囲
        self.value_range = (-30000, 30000)
        
        # 2ピクセル補正値（重要）
        self.peak_correction = 2.0
        
    def detect_graph_color_advanced(self, img):
        """高度な色検出（HSVとLAB色空間を併用）- 改良版ブルー検出"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 色範囲の定義 - ブルー/シアンの検出範囲を拡張
        color_ranges = {
            "pink": [(150, 40, 80), (170, 255, 255)],
            "purple": [(120, 40, 80), (150, 255, 255)],
            # ブルーとシアンを統合し、範囲を拡張
            "blue": [(75, 20, 70), (125, 255, 255)],
        }
        
        # 追加の薄いブルー検出範囲
        light_blue_range = [(90, 20, 100), (110, 150, 255)]
        
        # 各色のマスクを作成
        masks = {}
        for color_name, (lower, upper) in color_ranges.items():
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            
            # ブルーの場合、薄いブルーも含める
            if color_name == "blue":
                light_mask = cv2.inRange(hsv, np.array(light_blue_range[0]), np.array(light_blue_range[1]))
                mask = cv2.bitwise_or(mask, light_mask)
            
            masks[color_name] = mask
        
        # 最も多いピクセル数の色を選択
        max_pixels = 0
        detected_color = "pink"
        detected_mask = None
        
        for color_name, mask in masks.items():
            pixel_count = np.sum(mask > 0)
            if pixel_count > max_pixels:
                max_pixels = pixel_count
                detected_color = color_name
                detected_mask = mask
        
        # ノイズ除去
        kernel = np.ones((3, 3), np.uint8)
        mask_cleaned = cv2.morphologyEx(detected_mask, cv2.MORPH_CLOSE, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_OPEN, kernel)
        
        # ブルーの場合、細い線を保護するための追加処理
        if detected_color == "blue":
            kernel_small = np.ones((2, 2), np.uint8)
            mask_cleaned = cv2.dilate(mask_cleaned, kernel_small, iterations=1)
            mask_cleaned = cv2.erode(mask_cleaned, kernel_small, iterations=1)
        
        return mask_cleaned, detected_color
    
    def extract_line_advanced(self, img, x, mask):
        """サブピクセル精度でラインを抽出"""
        column_mask = mask[:, x]
        indices = np.where(column_mask > 0)[0]
        
        if len(indices) == 0:
            return None
        
        # RGB値からピンク/青の強度を計算
        column_bgr = img[:, x]
        
        # 強度計算（色に応じて調整可能）
        intensities = []
        for idx in indices:
            b, g, r = column_bgr[idx].astype(float)
            # ピンク系の場合: R成分重視
            # 青系の場合: B成分重視（必要に応じて切り替え）
            intensity = r - 0.5*g - 0.5*b
            intensities.append(intensity)
        
        intensities = np.array(intensities)
        
        # 最大強度の位置を見つける
        if len(intensities) > 0:
            max_idx = np.argmax(intensities)
            peak_y = indices[max_idx]
            
            # サブピクセル精度のためのパラボラフィッティング
            if 0 < max_idx < len(intensities) - 1:
                # 3点でパラボラフィッティング
                y1, y2, y3 = intensities[max_idx-1:max_idx+2]
                offset = (y1 - y3) / (2 * (y1 - 2*y2 + y3))
                peak_y += offset
            
            return float(peak_y)
        
        return None
    
    def y_to_value(self, y, is_peak=False, is_bottom=False):
        """Y座標を実際の値に変換（2ピクセル補正付き）"""
        zero_y = self.boundaries["zero_y"]
        top_y = self.boundaries["top_y"]
        bottom_y = self.boundaries["bottom_y"]
        
        # 2ピクセル補正
        adjusted_y = y
        if is_peak:
            # 最大値の場合
            value_at_y = (zero_y - y) / (zero_y - top_y) * 30000
            if value_at_y > 0:  # プラス領域の最大値
                adjusted_y = y - self.peak_correction  # 2px上に補正
            else:  # マイナス領域の最小値
                adjusted_y = y + self.peak_correction  # 2px下に補正
        
        # 値の計算
        if adjusted_y < zero_y:
            # ゼロラインより上（正の値）
            value = (zero_y - adjusted_y) / (zero_y - top_y) * 30000
        else:
            # ゼロラインより下（負の値）
            value = -(adjusted_y - zero_y) / (bottom_y - zero_y) * 30000
        
        return np.clip(value, -30000, 30000)
    
    def adaptive_smoothing(self, values):
        """適応的スムージング（ピーク保護付き）"""
        if len(values) < 10:
            return values
        
        # ピークとボトムを検出
        peaks, _ = signal.find_peaks(values, prominence=500)
        bottoms, _ = signal.find_peaks(-np.array(values), prominence=500)
        
        # 重要な点を保護しながらスムージング
        smoothed = values.copy()
        window_size = 5
        
        for i in range(len(values)):
            # ピークやボトムは保護
            if i in peaks or i in bottoms:
                continue
            
            # 移動平均
            start = max(0, i - window_size // 2)
            end = min(len(values), i + window_size // 2 + 1)
            smoothed[i] = np.mean(values[start:end])
        
        return smoothed
    
    def extract_graph_data(self, img_path):
        """グラフデータを抽出"""
        # 画像読み込み
        img = cv2.imread(img_path)
        if img is None:
            print(f"Error: Cannot load image {img_path}")
            return None
        
        # 色検出
        mask, color_name = self.detect_graph_color_advanced(img)
        print(f"Detected color: {color_name}")
        
        # グラフ境界内でデータ抽出
        start_x = self.boundaries["start_x"]
        end_x = self.boundaries["end_x"]
        
        data_points = []
        
        for x in range(start_x, end_x + 1):
            y = self.extract_line_advanced(img, x, mask)
            if y is not None:
                value = self.y_to_value(y)
                data_points.append({
                    'x': x,
                    'y': y,
                    'value': value
                })
        
        if not data_points:
            print("Warning: No data points found")
            return None
        
        # データフレーム作成
        df = pd.DataFrame(data_points)
        
        # 値のスムージング
        values = df['value'].values
        smoothed_values = self.adaptive_smoothing(values)
        df['smoothed_value'] = smoothed_values
        
        # 最大値と最終値を特定（2ピクセル補正適用）
        max_idx = np.argmax(smoothed_values)
        min_idx = np.argmin(smoothed_values)
        
        # 最大値の再計算（2ピクセル補正）
        if max_idx < len(df):
            y_at_max = df.iloc[max_idx]['y']
            df.loc[max_idx, 'value'] = self.y_to_value(y_at_max, is_peak=True)
            df.loc[max_idx, 'smoothed_value'] = df.loc[max_idx, 'value']
        
        # 最小値の再計算（2ピクセル補正）
        if min_idx < len(df):
            y_at_min = df.iloc[min_idx]['y']
            df.loc[min_idx, 'value'] = self.y_to_value(y_at_min, is_peak=True)
            df.loc[min_idx, 'smoothed_value'] = df.loc[min_idx, 'value']
        
        return df, color_name
    
    def process_image(self, img_path, output_dir):
        """単一画像を処理"""
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        print(f"\nProcessing: {base_name}")
        
        # データ抽出
        result = self.extract_graph_data(img_path)
        if result is None:
            return None
        
        df, color_name = result
        
        # 統計情報
        stats = {
            'file_name': base_name,
            'color': color_name,
            'max_value': df['smoothed_value'].max(),
            'min_value': df['smoothed_value'].min(),
            'final_value': df['smoothed_value'].iloc[-1],
            'data_points': len(df)
        }
        
        # CSVに保存
        csv_path = os.path.join(output_dir, f"{base_name}_stable_data.csv")
        df.to_csv(csv_path, index=False)
        
        # 可視化
        self.visualize_results(img_path, df, stats, output_dir)
        
        return stats
    
    def visualize_results(self, img_path, df, stats, output_dir):
        """結果を可視化"""
        img = cv2.imread(img_path)
        base_name = stats['file_name']
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # 1. 元画像とデータポイント
        axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        axes[0].scatter(df['x'], df['y'], c='red', s=1, alpha=0.5)
        axes[0].set_title(f'データポイント ({stats["color"]}色)')
        axes[0].set_xlim(0, img.shape[1])
        axes[0].set_ylim(img.shape[0], 0)
        
        # ゼロラインを表示
        axes[0].axhline(y=self.boundaries["zero_y"], color='green', linestyle='--', alpha=0.5)
        
        # 2. 抽出データ
        axes[1].plot(df['x'], df['value'], 'b-', alpha=0.3, label='Raw')
        axes[1].plot(df['x'], df['smoothed_value'], 'r-', linewidth=2, label='Smoothed')
        axes[1].set_title('抽出データ（2ピクセル補正済み）')
        axes[1].set_xlabel('X座標')
        axes[1].set_ylabel('値')
        axes[1].grid(True, alpha=0.3)
        axes[1].axhline(y=0, color='green', linestyle='--', alpha=0.5)
        axes[1].legend()
        
        # 最大値と最終値を表示
        max_idx = df['smoothed_value'].idxmax()
        axes[1].scatter(df.loc[max_idx, 'x'], df.loc[max_idx, 'smoothed_value'], 
                       color='red', s=100, zorder=5, label=f'最大: {stats["max_value"]:.0f}')
        axes[1].scatter(df.iloc[-1]['x'], df.iloc[-1]['smoothed_value'], 
                       color='blue', s=100, zorder=5, label=f'最終: {stats["final_value"]:.0f}')
        
        plt.suptitle(f'安定版手法による抽出: {base_name}')
        plt.tight_layout()
        
        viz_path = os.path.join(output_dir, f"{base_name}_stable_viz.png")
        plt.savefig(viz_path, dpi=150, bbox_inches='tight')
        plt.close()

def main():
    """メイン処理"""
    # 出力ディレクトリ
    output_dir = "graphs/stable_extracted_data"
    os.makedirs(output_dir, exist_ok=True)
    
    # 抽出器を初期化
    extractor = StableGraphExtractor()
    
    # cropped画像を処理
    import glob
    image_files = glob.glob("graphs/cropped/*_optimal.png")
    
    print(f"安定版手法によるグラフデータ抽出")
    print(f"処理対象: {len(image_files)}枚")
    print(f"出力先: {output_dir}")
    
    results = []
    for img_path in sorted(image_files):
        stats = extractor.process_image(img_path, output_dir)
        if stats:
            results.append(stats)
    
    # サマリー表示
    print(f"\n{'='*60}")
    print("処理完了サマリー")
    print(f"{'='*60}")
    
    for result in results:
        print(f"\n{result['file_name']}:")
        print(f"  色: {result['color']}")
        print(f"  最大値: {result['max_value']:.0f}")
        print(f"  最終値: {result['final_value']:.0f}")
        print(f"  データポイント: {result['data_points']}")
    
    # CSVサマリーを保存
    df_summary = pd.DataFrame(results)
    df_summary.to_csv(os.path.join(output_dir, "extraction_summary.csv"), index=False)
    
    print(f"\nサマリー保存: {output_dir}/extraction_summary.csv")

if __name__ == "__main__":
    main()