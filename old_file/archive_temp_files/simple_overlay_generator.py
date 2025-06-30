#!/usr/bin/env python3
"""
シンプルなオーバーレイ生成器
"""

import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os
import csv

class SimpleOverlayGenerator:
    """シンプルなオーバーレイ生成"""
    
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
            '/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc'
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font_prop = font_manager.FontProperties(fname=font_path)
                    plt.rcParams['font.family'] = font_prop.get_name()
                    plt.rcParams['font.size'] = 12
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
    
    def create_simple_overlay(self, image_path, csv_path, output_dir):
        """シンプルなオーバーレイを作成"""
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
        fig, ax = plt.subplots(1, 1, figsize=(10, 7))
        
        # 背景画像
        ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        # ゼロライン
        ax.axhline(y=self.boundaries["zero_y"], color='green', linewidth=2, 
                   linestyle='--', alpha=0.7)
        
        # 抽出データをオーバーレイ
        ax.plot(df['x'], df['y'], 'r-', linewidth=3, alpha=0.9)
        
        # 最大値と最終値の点のみ表示
        max_idx = df['corrected_value'].idxmax()
        
        # 最大値
        ax.scatter(df.iloc[max_idx]['x'], df.iloc[max_idx]['y'], 
                  color='yellow', s=150, edgecolor='black', linewidth=2, zorder=5)
        ax.text(df.iloc[max_idx]['x'], df.iloc[max_idx]['y'] - 20, 
               f'最大\n{df.iloc[max_idx]["corrected_value"]:.0f}', 
               ha='center', va='bottom', fontsize=14, fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.8))
        
        # 最終値
        ax.scatter(df.iloc[-1]['x'], df.iloc[-1]['y'], 
                  color='cyan', s=150, edgecolor='black', linewidth=2, zorder=5)
        ax.text(df.iloc[-1]['x'] - 30, df.iloc[-1]['y'], 
               f'最終\n{df.iloc[-1]["corrected_value"]:.0f}', 
               ha='right', va='center', fontsize=14, fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.3', fc='cyan', alpha=0.8))
        
        # 実際の値を右上に表示
        info_text = f"実際の最大: {actual['actual_max']:.0f}\n実際の最終: {actual['actual_final']:.0f}"
        ax.text(0.98, 0.05, info_text, transform=ax.transAxes,
               ha='right', va='bottom', fontsize=12,
               bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))
        
        # タイトル
        ax.set_title(f'{base_name}', fontsize=16, fontweight='bold', pad=20)
        
        # 軸の設定
        ax.set_xlim(0, img.shape[1])
        ax.set_ylim(img.shape[0], 0)
        ax.axis('off')
        
        plt.tight_layout()
        
        # 保存
        output_path = os.path.join(output_dir, f'{base_name}_simple_overlay.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def process_all_images(self):
        """すべての画像を処理"""
        output_dir = 'graphs/simple_overlay'
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
                result = self.create_simple_overlay(image_path, csv_path, output_dir)
                if result:
                    processed += 1
        
        print(f"\n✓ 完了: {processed}枚のシンプルなオーバーレイ画像を生成")
        print(f"  結果は {output_dir}/ に保存されました")

def main():
    """メイン処理"""
    generator = SimpleOverlayGenerator()
    generator.process_all_images()

if __name__ == "__main__":
    main()