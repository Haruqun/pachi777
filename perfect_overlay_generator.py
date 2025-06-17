#!/usr/bin/env python3
"""
完全一致を目指すオーバーレイ画像生成ツール
0地点（スタート）と終了地点の完全一致を重視
"""

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import glob

# 日本語フォントの設定（macOS）
def setup_japanese_font():
    """macOS用の日本語フォントを設定"""
    # 推奨フォントを優先的に使用
    recommended_fonts = [
        'Osaka',
        'Hiragino Sans',
        'Hiragino Maru Gothic Pro',
        'Hiragino Kaku Gothic Pro',
        'Hiragino Mincho Pro'
    ]
    
    # システムにインストールされているフォントを確認
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    
    # 日本語フォントを探す
    font_found = None
    for jp_font in recommended_fonts:
        if jp_font in available_fonts:
            font_found = jp_font
            print(f"日本語フォント '{jp_font}' を使用します")
            break
    
    if font_found:
        plt.rcParams['font.family'] = font_found
    else:
        # フォントが見つからない場合はフォントパスを直接指定
        print("警告: 推奨フォントが見つかりません。代替フォントを探します...")
        font_paths = [
            '/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc',
            '/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc',
            '/System/Library/Fonts/Osaka.ttf',
            '/System/Library/Fonts/Hiragino Sans GB.ttc'
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                prop = fm.FontProperties(fname=font_path)
                font_name = prop.get_name()
                plt.rcParams['font.family'] = font_name
                print(f"代替フォント '{font_name}' を使用します")
                break
    
    # 負の記号の表示設定
    plt.rcParams['axes.unicode_minus'] = False

# フォント設定を適用
setup_japanese_font()

class PerfectOverlayGenerator:
    """完全一致オーバーレイ生成器"""
    
    def __init__(self):
        # 最適な境界設定（689×558画像用）
        self.boundaries = {
            "start_x": 36,
            "end_x": 620,
            "top_y": 26,
            "bottom_y": 523,
            "zero_y": 274
        }
        
        # 出力ディレクトリ
        self.output_dir = "graphs/perfect_overlay"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def load_actual_values(self):
        """results.txtから実際の値を読み込み"""
        import csv
        results = {}
        with open('results.txt', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                base_name = row['画像名'].replace('.jpg', '')
                if row['実際の最大値'] and row['実際の最終差玉']:
                    results[base_name] = {
                        'max_value': float(row['実際の最大値'].replace(',', '')),
                        'final_value': float(row['実際の最終差玉'].replace(',', ''))
                    }
        return results
    
    def adjust_for_perfect_match(self, extracted_data, actual_values):
        """0地点と終了地点を完全一致させるための調整"""
        if not extracted_data or len(extracted_data) == 0:
            return extracted_data
            
        # 実際の最終値
        actual_final = actual_values['final_value']
        
        # 抽出データの最初と最後
        extracted_final = extracted_data[-1]['value']
        
        # スケーリング係数を計算（終了地点を合わせる）
        if extracted_final != 0:
            scale_factor = actual_final / extracted_final
        else:
            scale_factor = 1.0
            
        # 0地点は必ず0になるように調整
        adjusted_data = []
        for i, point in enumerate(extracted_data):
            adjusted_point = point.copy()
            
            if i == 0:
                # 最初の点は必ず0
                adjusted_point['adjusted_value'] = 0.0
            else:
                # スケーリングを適用
                adjusted_point['adjusted_value'] = point['value'] * scale_factor
                
            adjusted_data.append(adjusted_point)
            
        # 最終点を実際の値に完全一致させる
        if len(adjusted_data) > 0:
            adjusted_data[-1]['adjusted_value'] = actual_final
            
        return adjusted_data
    
    def create_perfect_overlay(self, image_path, csv_path, actual_values):
        """完全一致オーバーレイを作成"""
        # 画像を読み込み
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Cannot load image {image_path}")
            return
            
        # CSVデータを読み込み
        df = pd.read_csv(csv_path)
        
        # 調整前のデータを準備
        original_data = []
        for _, row in df.iterrows():
            original_data.append({
                'x': row['x'],
                'y': row['y'],
                'value': row['smoothed_value'] if 'smoothed_value' in row else row['value']
            })
        
        # 完全一致のための調整
        adjusted_data = self.adjust_for_perfect_match(original_data, actual_values)
        
        # オーバーレイ画像を作成
        height, width = img.shape[:2]
        
        # 図を作成（3パネル）
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # 1. 元画像
        axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        axes[0].set_title('元画像')
        axes[0].axis('off')
        
        # ゼロラインを表示
        axes[0].axhline(y=self.boundaries['zero_y'], color='green', linestyle='--', alpha=0.5)
        
        # 2. 調整前後の比較
        x_values = [d['x'] for d in adjusted_data]
        original_values = [d['value'] for d in adjusted_data]
        adjusted_values = [d['adjusted_value'] for d in adjusted_data]
        
        # 最大値と最小値を見つける
        max_idx = np.argmax(adjusted_values)
        min_idx = np.argmin(adjusted_values)
        max_value = adjusted_values[max_idx]
        min_value = adjusted_values[min_idx]
        max_x = x_values[max_idx]
        min_x = x_values[min_idx]
        
        axes[1].plot(x_values, original_values, 'b-', alpha=0.5, label='抽出値（調整前）', linewidth=2)
        axes[1].plot(x_values, adjusted_values, 'r-', label='調整後', linewidth=2)
        
        # 重要なラインを追加
        axes[1].axhline(y=0, color='green', linestyle='--', alpha=0.5, label='ゼロライン')
        axes[1].axhline(y=actual_values['final_value'], color='orange', linestyle='--', alpha=0.7, label=f"最終値: {actual_values['final_value']:.0f}")
        axes[1].axhline(y=max_value, color='red', linestyle=':', alpha=0.7, label=f"最大値: {max_value:.0f}")
        axes[1].axhline(y=min_value, color='blue', linestyle=':', alpha=0.7, label=f"最小値: {min_value:.0f}")
        
        # 垂直線も追加（最大値・最小値の位置）
        axes[1].axvline(x=max_x, color='red', linestyle=':', alpha=0.3)
        axes[1].axvline(x=min_x, color='blue', linestyle=':', alpha=0.3)
        
        # 開始点と終了点を強調
        axes[1].scatter([x_values[0]], [adjusted_values[0]], color='green', s=100, zorder=5, label='開始点 (0)')
        axes[1].scatter([x_values[-1]], [adjusted_values[-1]], color='orange', s=100, zorder=5, label=f'終了点 ({actual_values["final_value"]:.0f})')
        
        # 最大値・最小値の点も強調
        axes[1].scatter([max_x], [max_value], color='red', s=100, marker='^', zorder=5)
        axes[1].scatter([min_x], [min_value], color='blue', s=100, marker='v', zorder=5)
        
        axes[1].set_title('値の調整')
        axes[1].set_xlabel('X座標')
        axes[1].set_ylabel('値')
        axes[1].legend(loc='best', fontsize=8)
        axes[1].grid(True, alpha=0.3)
        
        # 3. オーバーレイ画像
        overlay_img = img.copy()
        
        # 調整後のY座標を計算
        adjusted_y_coords = []
        for point in adjusted_data:
            # 調整後の値からY座標を逆算
            value = point['adjusted_value']
            if value >= 0:
                y = self.boundaries['zero_y'] - (value / 30000) * (self.boundaries['zero_y'] - self.boundaries['top_y'])
            else:
                y = self.boundaries['zero_y'] - (value / 30000) * (self.boundaries['bottom_y'] - self.boundaries['zero_y'])
            adjusted_y_coords.append(int(y))
        
        # 最大値・最小値のY座標を計算
        if max_value >= 0:
            max_y = int(self.boundaries['zero_y'] - (max_value / 30000) * (self.boundaries['zero_y'] - self.boundaries['top_y']))
        else:
            max_y = int(self.boundaries['zero_y'] - (max_value / 30000) * (self.boundaries['bottom_y'] - self.boundaries['zero_y']))
            
        if min_value >= 0:
            min_y = int(self.boundaries['zero_y'] - (min_value / 30000) * (self.boundaries['zero_y'] - self.boundaries['top_y']))
        else:
            min_y = int(self.boundaries['zero_y'] - (min_value / 30000) * (self.boundaries['bottom_y'] - self.boundaries['zero_y']))
        
        # 最終値のY座標
        final_y = adjusted_y_coords[-1] if adjusted_y_coords else self.boundaries['zero_y']
        
        # 重要な水平ラインを描画（グラフより先に描画）
        # 最大値ライン（赤の点線）
        for x in range(self.boundaries['start_x'], self.boundaries['end_x'], 10):
            cv2.line(overlay_img, (x, max_y), (x + 5, max_y), (0, 0, 255), 2)
        
        # 最小値ライン（青の点線）
        for x in range(self.boundaries['start_x'], self.boundaries['end_x'], 10):
            cv2.line(overlay_img, (x, min_y), (x + 5, min_y), (255, 0, 0), 2)
        
        # 最終値ライン（オレンジの破線）
        for x in range(self.boundaries['start_x'], self.boundaries['end_x'], 15):
            cv2.line(overlay_img, (x, final_y), (x + 8, final_y), (0, 165, 255), 2)
        
        # ゼロライン（緑の実線）
        cv2.line(overlay_img, (self.boundaries['start_x'], self.boundaries['zero_y']), 
                (self.boundaries['end_x'], self.boundaries['zero_y']), (0, 255, 0), 1)
        
        # 各ラインに数値を表示（OpenCVで日本語フォントが使えないため、数値のみ）
        # フォント設定
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        
        # 最大値の数値（右端に表示）
        max_text = f"{max_value:.0f}"
        text_size = cv2.getTextSize(max_text, font, font_scale, thickness)[0]
        text_x = self.boundaries['end_x'] - text_size[0] - 5
        text_y = max_y + 5
        # 背景を描画
        cv2.rectangle(overlay_img, (text_x - 3, text_y - text_size[1] - 3), 
                     (text_x + text_size[0] + 3, text_y + 3), (255, 255, 255), -1)
        cv2.putText(overlay_img, max_text, (text_x, text_y), 
                   font, font_scale, (0, 0, 255), thickness)
        
        # 最小値の数値（右端に表示）
        min_text = f"{min_value:.0f}"
        text_size = cv2.getTextSize(min_text, font, font_scale, thickness)[0]
        text_x = self.boundaries['end_x'] - text_size[0] - 5
        text_y = min_y + 5
        # 背景を描画
        cv2.rectangle(overlay_img, (text_x - 3, text_y - text_size[1] - 3), 
                     (text_x + text_size[0] + 3, text_y + 3), (255, 255, 255), -1)
        cv2.putText(overlay_img, min_text, (text_x, text_y), 
                   font, font_scale, (255, 0, 0), thickness)
        
        # 最終値の数値（右端に表示）
        final_text = f"{actual_values['final_value']:.0f}"
        text_size = cv2.getTextSize(final_text, font, font_scale, thickness)[0]
        text_x = self.boundaries['end_x'] - text_size[0] - 5
        text_y = final_y + 5
        # 背景を描画
        cv2.rectangle(overlay_img, (text_x - 3, text_y - text_size[1] - 3), 
                     (text_x + text_size[0] + 3, text_y + 3), (255, 255, 255), -1)
        cv2.putText(overlay_img, final_text, (text_x, text_y), 
                   font, font_scale, (0, 165, 255), thickness)
        
        # ゼロの数値（左端に表示）
        text_size = cv2.getTextSize("0", font, font_scale, thickness)[0]
        text_x = self.boundaries['start_x'] - 25
        text_y = self.boundaries['zero_y'] + 5
        # 背景を描画
        cv2.rectangle(overlay_img, (text_x - 3, text_y - text_size[1] - 3), 
                     (text_x + text_size[0] + 3, text_y + 3), (255, 255, 255), -1)
        cv2.putText(overlay_img, "0", (text_x, text_y), 
                   font, font_scale, (0, 255, 0), thickness)
        
        # グラフラインを描画
        for i in range(len(adjusted_data) - 1):
            pt1 = (int(adjusted_data[i]['x']), adjusted_y_coords[i])
            pt2 = (int(adjusted_data[i+1]['x']), adjusted_y_coords[i+1])
            cv2.line(overlay_img, pt1, pt2, (0, 255, 0), 3)  # 緑色の太線
        
        # 開始点と終了点を強調
        if len(adjusted_data) > 0:
            # 開始点（緑の大きな円）
            cv2.circle(overlay_img, (int(adjusted_data[0]['x']), adjusted_y_coords[0]), 8, (0, 255, 0), -1)
            cv2.circle(overlay_img, (int(adjusted_data[0]['x']), adjusted_y_coords[0]), 10, (0, 128, 0), 2)
            
            # 終了点（オレンジの大きな円）
            cv2.circle(overlay_img, (int(adjusted_data[-1]['x']), adjusted_y_coords[-1]), 8, (0, 165, 255), -1)
            cv2.circle(overlay_img, (int(adjusted_data[-1]['x']), adjusted_y_coords[-1]), 10, (0, 100, 200), 2)
            
            # 最大値点（赤の上向き三角）
            max_point = (int(x_values[max_idx]), adjusted_y_coords[max_idx])
            triangle_pts = np.array([
                [max_point[0], max_point[1] - 10],
                [max_point[0] - 8, max_point[1] + 5],
                [max_point[0] + 8, max_point[1] + 5]
            ], np.int32)
            cv2.fillPoly(overlay_img, [triangle_pts], (0, 0, 255))
            
            # 最小値点（青の下向き三角）
            min_point = (int(x_values[min_idx]), adjusted_y_coords[min_idx])
            triangle_pts = np.array([
                [min_point[0], min_point[1] + 10],
                [min_point[0] - 8, min_point[1] - 5],
                [min_point[0] + 8, min_point[1] - 5]
            ], np.int32)
            cv2.fillPoly(overlay_img, [triangle_pts], (255, 0, 0))
        
        axes[2].imshow(cv2.cvtColor(overlay_img, cv2.COLOR_BGR2RGB))
        axes[2].set_title('完全一致オーバーレイ')
        axes[2].axis('off')
        
        # 情報テキストを追加
        info_text = f"開始: 0 → 終了: {actual_values['final_value']:.0f}\n最大: {max_value:.0f} | 最小: {min_value:.0f}"
        axes[2].text(10, height-10, info_text, color='white', fontsize=10, 
                    bbox=dict(boxstyle='round', facecolor='black', alpha=0.7),
                    verticalalignment='bottom')
        
        plt.tight_layout()
        
        # 保存
        base_name = os.path.basename(image_path).replace('_optimal.png', '')
        output_path = os.path.join(self.output_dir, f"{base_name}_perfect_overlay.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        # 個別のオーバーレイ画像も保存
        overlay_only_path = os.path.join(self.output_dir, f"{base_name}_overlay_only.png")
        cv2.imwrite(overlay_only_path, overlay_img)
        
        print(f"完全一致オーバーレイ作成: {base_name}")
        print(f"  開始値: 0 (完全一致)")
        print(f"  終了値: {actual_values['final_value']:.0f} (完全一致)")
        print(f"  調整係数: {actual_values['final_value'] / original_values[-1] if original_values[-1] != 0 else 1:.4f}")
        
        return output_path
    
    def process_all(self):
        """全画像を処理"""
        # 実際の値を読み込み
        actual_values_dict = self.load_actual_values()
        
        # 画像とCSVのペアを処理
        image_files = sorted(glob.glob('graphs/cropped/*_optimal.png'))
        
        print(f"完全一致オーバーレイ生成開始")
        print(f"処理対象: {len(image_files)}枚")
        print("="*60)
        
        for image_path in image_files:
            base_name = os.path.basename(image_path).replace('_optimal.png', '')
            csv_path = f'graphs/stable_extracted_data/{base_name}_optimal_stable_data.csv'
            
            if os.path.exists(csv_path) and base_name in actual_values_dict:
                self.create_perfect_overlay(image_path, csv_path, actual_values_dict[base_name])
            else:
                print(f"スキップ: {base_name} (データ不足)")
        
        print("\n完全一致オーバーレイ生成完了")
        print(f"出力先: {self.output_dir}")

def main():
    generator = PerfectOverlayGenerator()
    generator.process_all()

if __name__ == "__main__":
    main()