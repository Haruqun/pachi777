#!/usr/bin/env python3
"""
正確なグラフ抽出器 - 改良版色検出器を使用
補正なしの生データで高精度を実現
"""

import cv2
import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
from matplotlib import font_manager
import json
from datetime import datetime

class AccurateGraphExtractor:
    """改良版色検出を使用した正確なグラフ抽出器"""
    
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
        
        # 改良版色検出範囲
        self.color_ranges_hsv = {
            "pink": [
                [(160, 30, 100), (180, 255, 255)],
                [(0, 30, 100), (10, 255, 255)],
                [(150, 20, 120), (170, 150, 255)]
            ],
            "blue": [
                [(85, 30, 80), (115, 255, 255)],
                [(75, 20, 100), (125, 200, 255)],
                [(90, 15, 120), (110, 150, 255)],
                [(100, 25, 90), (120, 255, 255)]
            ],
            "purple": [
                [(120, 30, 70), (150, 255, 255)],
                [(130, 20, 80), (145, 200, 255)],
                [(140, 25, 60), (160, 255, 255)]
            ]
        }
        
        # 日本語フォント設定
        self.setup_japanese_font()
    
    def setup_japanese_font(self):
        """日本語フォント設定"""
        font_paths = [
            '/Library/Fonts/Osaka.ttf',
            '/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc'
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font_prop = font_manager.FontProperties(fname=font_path)
                    plt.rcParams['font.family'] = font_prop.get_name()
                    return
                except:
                    continue
    
    def detect_color_improved(self, img):
        """改良版色検出"""
        h, w = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 各色のスコアを計算
        color_scores = {}
        color_masks = {}
        
        for color_name, ranges in self.color_ranges_hsv.items():
            # HSVベースの検出
            combined_mask = np.zeros((h, w), dtype=np.uint8)
            for lower, upper in ranges:
                mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
                combined_mask = cv2.bitwise_or(combined_mask, mask)
            
            # ノイズ除去
            kernel = np.ones((3, 3), np.uint8)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
            
            # 青の場合は細線強調
            if color_name == "blue":
                kernel_line = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
                combined_mask = cv2.dilate(combined_mask, kernel_line, iterations=1)
            
            # グラフ領域（中央部）での検出を重視
            center_x = w // 2
            center_region = combined_mask[:, center_x-100:center_x+100]
            
            # スコア計算
            total_pixels = np.sum(combined_mask > 0)
            center_pixels = np.sum(center_region > 0)
            score = total_pixels + center_pixels * 2
            
            color_scores[color_name] = score
            color_masks[color_name] = combined_mask
        
        # 最高スコアの色を選択
        detected_color = max(color_scores, key=color_scores.get)
        detected_mask = color_masks[detected_color]
        
        return detected_mask, detected_color
    
    def extract_line_with_subpixel(self, img, x, mask):
        """サブピクセル精度でラインを抽出"""
        column_mask = mask[:, x]
        indices = np.where(column_mask > 0)[0]
        
        if len(indices) == 0:
            return None
        
        # RGB値から強度を計算
        column_bgr = img[:, x]
        intensities = []
        
        for idx in indices:
            b, g, r = column_bgr[idx].astype(float)
            # 色に応じた強度計算
            intensity = r - 0.5*g - 0.5*b  # デフォルトはピンク/紫向け
            intensities.append(intensity)
        
        intensities = np.array(intensities)
        
        # 最大強度の位置を見つける
        if len(intensities) > 0:
            max_idx = np.argmax(intensities)
            peak_y = indices[max_idx]
            
            # サブピクセル精度のためのパラボラフィッティング
            if 0 < max_idx < len(intensities) - 1:
                y1, y2, y3 = intensities[max_idx-1:max_idx+2]
                if y1 - 2*y2 + y3 != 0:
                    offset = (y1 - y3) / (2 * (y1 - 2*y2 + y3))
                    peak_y += offset
            
            return float(peak_y)
        
        return None
    
    def y_to_value_raw(self, y):
        """Y座標を値に変換（補正なし）"""
        zero_y = self.boundaries["zero_y"]
        top_y = self.boundaries["top_y"]
        bottom_y = self.boundaries["bottom_y"]
        
        if y < zero_y:
            value = (zero_y - y) / (zero_y - top_y) * 30000
        else:
            value = -(y - zero_y) / (bottom_y - zero_y) * 30000
        
        return np.clip(value, -30000, 30000)
    
    def adaptive_smoothing(self, values, window_size=5):
        """適応的スムージング"""
        smoothed = values.copy()
        n = len(values)
        
        for i in range(window_size//2, n - window_size//2):
            window = values[i-window_size//2:i+window_size//2+1]
            
            # 変化が大きい場合はスムージングを弱める
            if np.std(window) > 1000:
                smoothed[i] = np.median(window)
            else:
                smoothed[i] = np.mean(window)
        
        return smoothed
    
    def extract_graph_data(self, img_path):
        """グラフデータを抽出"""
        img = cv2.imread(img_path)
        if img is None:
            return None
        
        # 色検出
        mask, color_name = self.detect_color_improved(img)
        
        # データポイント抽出
        start_x = self.boundaries["start_x"]
        end_x = self.boundaries["end_x"]
        
        data_points = []
        for x in range(start_x, end_x + 1):
            y = self.extract_line_with_subpixel(img, x, mask)
            
            if y is not None:
                value = self.y_to_value_raw(y)
                data_points.append({
                    'x': x,
                    'y': y,
                    'value': value
                })
        
        if not data_points:
            return None
        
        # データフレーム作成
        df = pd.DataFrame(data_points)
        
        # スムージング
        values = df['value'].values
        smoothed_values = self.adaptive_smoothing(values)
        df['smoothed_value'] = smoothed_values
        
        return df, color_name
    
    def process_image(self, img_path, output_dir):
        """画像を処理"""
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        print(f"\n処理中: {base_name}")
        
        # データ抽出
        result = self.extract_graph_data(img_path)
        if result is None:
            print(f"  エラー: データ抽出失敗")
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
        
        print(f"  色: {color_name}")
        print(f"  最大値: {stats['max_value']:.0f}")
        print(f"  最終値: {stats['final_value']:.0f}")
        
        # CSVに保存
        csv_path = os.path.join(output_dir, f"{base_name}_accurate_data.csv")
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
        axes[1].plot(df['x'], df['value'], 'b-', alpha=0.3, label='生データ')
        axes[1].plot(df['x'], df['smoothed_value'], 'r-', linewidth=2, label='スムージング')
        axes[1].set_title('抽出データ（補正なし）')
        axes[1].set_xlabel('X座標')
        axes[1].set_ylabel('値')
        axes[1].grid(True, alpha=0.3)
        axes[1].axhline(y=0, color='green', linestyle='--', alpha=0.5)
        axes[1].legend()
        
        # 最大値と最終値を表示
        max_idx = df['smoothed_value'].idxmax()
        axes[1].scatter(df.loc[max_idx, 'x'], df.loc[max_idx, 'smoothed_value'], 
                       color='red', s=100, zorder=5)
        axes[1].annotate(f'最大: {stats["max_value"]:.0f}', 
                        (df.loc[max_idx, 'x'], df.loc[max_idx, 'smoothed_value']),
                        xytext=(10, 10), textcoords='offset points')
        
        axes[1].scatter(df.iloc[-1]['x'], df.iloc[-1]['smoothed_value'], 
                       color='blue', s=100, zorder=5)
        axes[1].annotate(f'最終: {stats["final_value"]:.0f}', 
                        (df.iloc[-1]['x'], df.iloc[-1]['smoothed_value']),
                        xytext=(10, -20), textcoords='offset points')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{base_name}_accurate_visualization.png"))
        plt.close()
    
    def process_all_images(self, input_dir, output_dir):
        """すべての画像を処理"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 画像ファイルを取得
        image_files = [f for f in os.listdir(input_dir) 
                      if f.endswith('.png') and 'optimal' in f 
                      and not any(x in f for x in ['analysis', 'zero_line', 'start_zero'])]
        
        all_stats = []
        
        for img_file in sorted(image_files):
            img_path = os.path.join(input_dir, img_file)
            stats = self.process_image(img_path, output_dir)
            if stats:
                all_stats.append(stats)
        
        # サマリーを保存
        summary_df = pd.DataFrame(all_stats)
        summary_df.to_csv(os.path.join(output_dir, 'extraction_summary.csv'), index=False)
        
        # レポート作成
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_images': len(all_stats),
            'color_distribution': summary_df['color'].value_counts().to_dict(),
            'average_data_points': summary_df['data_points'].mean()
        }
        
        with open(os.path.join(output_dir, 'extraction_report.json'), 'w') as f:
            json.dump(report, f, indent=2)
        
        return all_stats

def main():
    """メイン処理"""
    extractor = AccurateGraphExtractor()
    
    # すべての画像を処理
    input_dir = 'graphs/cropped'
    output_dir = 'graphs/accurate_extracted_data'
    
    print("正確なグラフ抽出を開始...")
    all_stats = extractor.process_all_images(input_dir, output_dir)
    
    print(f"\n✓ 抽出完了: {len(all_stats)}枚の画像を処理")
    print(f"  結果は {output_dir}/ に保存されました")

if __name__ == "__main__":
    main()