#!/usr/bin/env python3
"""
ゼロ開始補正付きオーバーレイ生成器
グラフの開始点を0に補正し、様々な要素を可視化
"""

import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os
import csv

class ZeroStartOverlayGenerator:
    """ゼロ開始補正とリッチなオーバーレイを生成"""
    
    def __init__(self):
        # グラフ境界設定
        self.boundaries = {
            "start_x": 36,
            "end_x": 620,
            "top_y": 26,
            "bottom_y": 523,
            "zero_y": 274
        }
        
        # 日本語フォント設定
        self.setup_japanese_font()
        
        # 実際の値を読み込み
        self.actual_values = self.load_actual_values()
    
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
                    plt.rcParams['font.size'] = 10
                    return
                except:
                    continue
    
    def load_actual_values(self):
        """results.txtから実際の値を読み込み"""
        results = {}
        with open('results.txt', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                base_name = row['画像名'].replace('.jpg', '')
                if row['実際の最大値'] and row['実際の最終差玉']:
                    results[base_name] = {
                        'actual_max': float(row['実際の最大値'].replace(',', '')),
                        'actual_final': float(row['実際の最終差玉'].replace(',', ''))
                    }
        return results
    
    def value_to_y(self, value):
        """値をY座標に変換"""
        zero_y = self.boundaries["zero_y"]
        top_y = self.boundaries["top_y"]
        bottom_y = self.boundaries["bottom_y"]
        
        if value > 0:
            y = zero_y - (value / 30000) * (zero_y - top_y)
        else:
            y = zero_y - (value / 30000) * (bottom_y - zero_y)
        
        return np.clip(y, top_y, bottom_y)
    
    def create_rich_overlay(self, image_path, csv_path, output_dir):
        """リッチなオーバーレイを作成"""
        base_name = os.path.basename(image_path).replace('_optimal.png', '')
        
        # 画像とデータを読み込み
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        df = pd.read_csv(csv_path)
        
        # 実際の値を取得
        actual = self.actual_values.get(base_name, None)
        if not actual:
            return None
        
        # ゼロ開始補正
        initial_value = df['smoothed_value'].iloc[0]
        df['corrected_value'] = df['smoothed_value'] - initial_value
        
        # 図を作成
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]})
        
        # メイン画像
        ax1.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        # グラフ境界を描画
        rect = plt.Rectangle((self.boundaries["start_x"], self.boundaries["top_y"]),
                           self.boundaries["end_x"] - self.boundaries["start_x"],
                           self.boundaries["bottom_y"] - self.boundaries["top_y"],
                           fill=False, edgecolor='blue', linewidth=2, linestyle='--')
        ax1.add_patch(rect)
        
        # ゼロラインを描画
        ax1.axhline(y=self.boundaries["zero_y"], color='green', linewidth=2, 
                   linestyle='--', alpha=0.8, label='ゼロライン')
        
        # 抽出データをオーバーレイ（赤）
        ax1.plot(df['x'], df['y'], 'r-', linewidth=2, alpha=0.8, label='抽出データ')
        
        # 補正後の理想的な位置を計算してオーバーレイ（青）
        corrected_y = []
        for value in df['corrected_value']:
            y = self.value_to_y(value)
            corrected_y.append(y)
        
        ax1.plot(df['x'], corrected_y, 'b-', linewidth=2, alpha=0.8, label='ゼロ開始補正')
        
        # 重要なポイントをマーク
        max_idx = df['corrected_value'].idxmax()
        min_idx = df['corrected_value'].idxmin()
        
        # 開始点
        ax1.scatter(df.iloc[0]['x'], corrected_y[0], color='green', s=100, zorder=5)
        ax1.annotate(f'開始: 0', (df.iloc[0]['x'], corrected_y[0]),
                    xytext=(-30, -20), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 最大値
        ax1.scatter(df.iloc[max_idx]['x'], corrected_y[max_idx], color='red', s=100, zorder=5)
        ax1.annotate(f'最大: {df.iloc[max_idx]["corrected_value"]:.0f}\n(実際: {actual["actual_max"]:.0f})', 
                    (df.iloc[max_idx]['x'], corrected_y[max_idx]),
                    xytext=(20, -30), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.5', fc='pink', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 最小値（負の場合）
        if df.iloc[min_idx]['corrected_value'] < 0:
            ax1.scatter(df.iloc[min_idx]['x'], corrected_y[min_idx], color='blue', s=100, zorder=5)
            ax1.annotate(f'最小: {df.iloc[min_idx]["corrected_value"]:.0f}', 
                        (df.iloc[min_idx]['x'], corrected_y[min_idx]),
                        xytext=(20, 20), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.5', fc='lightblue', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 終了点
        ax1.scatter(df.iloc[-1]['x'], corrected_y[-1], color='purple', s=100, zorder=5)
        ax1.annotate(f'終了: {df.iloc[-1]["corrected_value"]:.0f}\n(実際: {actual["actual_final"]:.0f})', 
                    (df.iloc[-1]['x'], corrected_y[-1]),
                    xytext=(30, 20), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.5', fc='lavender', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # タイトルと凡例
        ax1.set_title(f'{base_name} - オーバーレイ分析', fontsize=14, fontweight='bold')
        ax1.legend(loc='upper right')
        ax1.set_xlim(0, img.shape[1])
        ax1.set_ylim(img.shape[0], 0)
        
        # 下部のグラフ（値の推移）
        ax2.plot(df['x'], df['smoothed_value'], 'r-', linewidth=1, alpha=0.5, label='生データ')
        ax2.plot(df['x'], df['corrected_value'], 'b-', linewidth=2, label='ゼロ開始補正')
        ax2.axhline(y=0, color='green', linestyle='--', alpha=0.5)
        ax2.axhline(y=actual['actual_max'], color='red', linestyle=':', alpha=0.5, label=f'実際の最大: {actual["actual_max"]:.0f}')
        ax2.axhline(y=actual['actual_final'], color='purple', linestyle=':', alpha=0.5, label=f'実際の最終: {actual["actual_final"]:.0f}')
        
        ax2.set_xlabel('X座標')
        ax2.set_ylabel('値')
        ax2.set_title('値の推移')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        # 統計情報を追加
        stats_text = f"""統計情報:
        開始値補正: {initial_value:.0f}
        最大値: {df['corrected_value'].max():.0f} (実際: {actual['actual_max']:.0f})
        最終値: {df['corrected_value'].iloc[-1]:.0f} (実際: {actual['actual_final']:.0f})
        精度: {100 - abs(df['corrected_value'].iloc[-1] - actual['actual_final']) / 300:.1f}%"""
        
        fig.text(0.02, 0.02, stats_text, fontsize=10, 
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        
        # 保存
        output_path = os.path.join(output_dir, f'{base_name}_zero_start_overlay.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def process_all_images(self):
        """すべての画像を処理"""
        output_dir = 'graphs/zero_start_overlay'
        os.makedirs(output_dir, exist_ok=True)
        
        # 処理対象のファイルを取得
        csv_dir = 'graphs/accurate_extracted_data'
        csv_files = [f for f in os.listdir(csv_dir) 
                    if f.endswith('_accurate_data.csv')]
        
        processed = 0
        for csv_file in sorted(csv_files):
            base_name = csv_file.replace('_optimal_accurate_data.csv', '')
            image_path = f'graphs/cropped/{base_name}_optimal.png'
            csv_path = os.path.join(csv_dir, csv_file)
            
            if os.path.exists(image_path):
                print(f"処理中: {base_name}")
                result = self.create_rich_overlay(image_path, csv_path, output_dir)
                if result:
                    processed += 1
        
        print(f"\n✓ 完了: {processed}枚のオーバーレイ画像を生成")
        print(f"  結果は {output_dir}/ に保存されました")

def main():
    """メイン処理"""
    generator = ZeroStartOverlayGenerator()
    generator.process_all_images()

if __name__ == "__main__":
    main()