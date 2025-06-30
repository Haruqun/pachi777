#!/usr/bin/env python3
"""
グラフ分析オーバーレイツール
取得した画像に0ライン、最大値、最小値、最終値の線と数値を追加
"""

import cv2
import numpy as np
import pandas as pd
import os
import glob
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import platform

class GraphAnalyzerOverlay:
    """グラフ分析オーバーレイクラス"""
    
    def __init__(self, 
                 image_dir="graphs/manual_crop/cropped",
                 csv_dir="graphs/extracted_data/csv", 
                 output_dir="graphs/analysis_overlay"):
        self.image_dir = image_dir
        self.csv_dir = csv_dir
        self.output_dir = output_dir
        
        # 出力ディレクトリ作成
        os.makedirs(output_dir, exist_ok=True)
        
        # 1ピクセルあたりの値（仮定値）
        self.pixel_to_value = 120  # 1ピクセル = 120の値
        
        # 日本語フォントの設定
        self.font_path = None
        if platform.system() == 'Darwin':  # macOS
            font_candidates = [
                '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
                '/System/Library/Fonts/Hiragino Sans GB W3.ttc',
                '/Library/Fonts/Arial Unicode.ttf'
            ]
            for font in font_candidates:
                if os.path.exists(font):
                    self.font_path = font
                    break
    
    def load_csv_data(self, base_name):
        """CSVデータを読み込み"""
        csv_files = glob.glob(os.path.join(self.csv_dir, f"{base_name}_*.csv"))
        
        all_data = {}
        for csv_file in csv_files:
            # 色名を抽出
            color_name = os.path.basename(csv_file).replace(f"{base_name}_", "").replace(".csv", "")
            
            # データ読み込み
            df = pd.read_csv(csv_file)
            if not df.empty:
                all_data[color_name] = df
                print(f"  {color_name}データ読み込み: {len(df)}点")
        
        return all_data
    
    def analyze_data(self, data_dict):
        """データを分析して最大値、最小値、最終値を取得"""
        analysis_results = {}
        
        for color_name, df in data_dict.items():
            if df.empty:
                continue
            
            # 最大値
            max_idx = df['value'].idxmax()
            max_point = {
                'x': int(df.loc[max_idx, 'x']),
                'y': int(df.loc[max_idx, 'y']),
                'value': float(df.loc[max_idx, 'value'])
            }
            
            # 最小値
            min_idx = df['value'].idxmin()
            min_point = {
                'x': int(df.loc[min_idx, 'x']),
                'y': int(df.loc[min_idx, 'y']),
                'value': float(df.loc[min_idx, 'value'])
            }
            
            # 最終値（最後のx座標のデータ）
            last_idx = df['x'].idxmax()
            final_point = {
                'x': int(df.loc[last_idx, 'x']),
                'y': int(df.loc[last_idx, 'y']),
                'value': float(df.loc[last_idx, 'value'])
            }
            
            analysis_results[color_name] = {
                'max': max_point,
                'min': min_point,
                'final': final_point,
                'zero_line': int(df['y'].iloc[0] - df['relative_y'].iloc[0])  # ゼロライン位置
            }
            
            print(f"  {color_name}分析:")
            print(f"    最大値: {max_point['value']:.0f} at x={max_point['x']}")
            print(f"    最小値: {min_point['value']:.0f} at x={min_point['x']}")
            print(f"    最終値: {final_point['value']:.0f}")
        
        return analysis_results
    
    def draw_japanese_text(self, img, text, position, font_size=20, color=(0, 0, 0), bg_color=None):
        """日本語テキストを描画"""
        if not self.font_path:
            # フォントが見つからない場合は通常のOpenCV描画
            cv2.putText(img, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_size/30, color, 2)
            return img
        
        # OpenCV画像をPIL画像に変換
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        # フォント設定
        font = ImageFont.truetype(self.font_path, font_size)
        
        # テキストサイズを取得
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 背景を描画（必要な場合）
        if bg_color is not None:
            x, y = position
            draw.rectangle([x-2, y-text_height-2, x+text_width+2, y+2], fill=bg_color)
        
        # テキストを描画
        draw.text(position, text, font=font, fill=color[::-1])  # BGRからRGBに変換
        
        # PIL画像をOpenCV画像に変換
        img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        return img
    
    def create_analysis_overlay(self, img, analysis_results):
        """分析結果のオーバーレイを作成"""
        overlay = img.copy()
        height, width = img.shape[:2]
        
        # フォント設定
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        
        # 色の定義
        colors = {
            'zero': (0, 0, 0),          # 黒
            'max': (0, 0, 255),         # 赤
            'min': (255, 0, 0),         # 青
            'final': (0, 165, 255),     # オレンジ
            'pink': (255, 100, 200),    # ピンク
            'orange': (0, 165, 255)     # オレンジ
        }
        
        # 各色のデータに対して処理
        for color_name, results in analysis_results.items():
            zero_y = results['zero_line']
            
            # 1. ゼロライン（黒い細線）
            cv2.line(overlay, (0, zero_y), (width, zero_y), colors['zero'], 1)
            cv2.putText(overlay, "0", (width - 50, zero_y - 5), 
                       font, font_scale, colors['zero'], thickness)
            
            # 1.5. 10000, 20000, 30000のライン（薄いグレー）
            # 1ピクセル = 120.24の値なので、より正確な位置に
            value_lines = [10000, 20000, 30000, -10000, -20000, -30000]
            for value in value_lines:
                pixel_offset = int(value / self.pixel_to_value)
                y_pos = zero_y - pixel_offset  # 上がプラス
                
                # 画面内に収まる場合のみ描画
                if 0 <= y_pos <= height:
                    # 薄いグレーの破線
                    for x in range(0, width, 20):
                        cv2.line(overlay, (x, y_pos), (min(x + 10, width), y_pos), 
                                (200, 200, 200), 1)
                    
                    # 数値ラベル（右端）
                    cv2.putText(overlay, str(value), (width - 70, y_pos + 5), 
                               font, 0.5, (150, 150, 150), 1)
            
            # 2. 最大値ライン（赤い線）
            max_point = results['max']
            cv2.line(overlay, (0, max_point['y']), (width, max_point['y']), 
                    colors['max'], 1, cv2.LINE_AA)
            
            # 最大値の位置にマーカー
            cv2.circle(overlay, (max_point['x'], max_point['y']), 3, colors['max'], -1)
            
            # 最大値のラベル（右端）
            label_max = f"最大値: {max_point['value']:.0f}"
            overlay = self.draw_japanese_text(overlay, label_max, 
                                            (width - 145, max_point['y'] - 10), 
                                            font_size=16, color=colors['max'])
            
            # 3. 最小値ライン（青い線）
            min_point = results['min']
            cv2.line(overlay, (0, min_point['y']), (width, min_point['y']), 
                    colors['min'], 1, cv2.LINE_AA)
            
            # 最小値の位置にマーカー
            cv2.circle(overlay, (min_point['x'], min_point['y']), 3, colors['min'], -1)
            
            # 最小値のラベル（右端）
            label_min = f"最小値: {min_point['value']:.0f}"
            overlay = self.draw_japanese_text(overlay, label_min, 
                                            (width - 145, min_point['y'] + 20), 
                                            font_size=16, color=colors['min'])
            
            # 4. 最終値（垂直線とラベル）
            final_point = results['final']
            cv2.line(overlay, (final_point['x'], 0), (final_point['x'], height), 
                    colors['final'], 1, cv2.LINE_AA)
            
            # 最終値の水平線も追加
            cv2.line(overlay, (0, final_point['y']), (width, final_point['y']), 
                    colors['final'], 1, cv2.LINE_AA)
            
            # 最終値の位置にマーカー
            cv2.circle(overlay, (final_point['x'], final_point['y']), 3, colors['final'], -1)
            
            # 最終値のラベル（下部）
            label_final = f"最終値: {final_point['value']:.0f}"
            label_x = final_point['x'] - 70
            if label_x < 10:
                label_x = 10
            elif label_x > width - 150:
                label_x = width - 150
                
            overlay = self.draw_japanese_text(overlay, label_final, 
                                            (label_x + 5, height - 20), 
                                            font_size=16, color=colors['final'])
            
            # 最終値の水平線にもラベルを追加（左端）
            overlay = self.draw_japanese_text(overlay, f"{final_point['value']:.0f}", 
                                            (10, final_point['y'] + 5), 
                                            font_size=16, color=colors['final'])
            
            # 5. グラフの色情報（左上）
            info_text = f"グラフ: {color_name}"
            overlay = self.draw_japanese_text(overlay, info_text, 
                                            (15, 30), 
                                            font_size=16, color=colors.get(color_name, (0, 0, 0)))
            
            # 6. 統計情報（左下）
            stats_y = height - 100
            stats = [
                f"変動幅: {max_point['value'] - min_point['value']:.0f}",
                f"0から最終値: {final_point['value']:.0f}"
            ]
            
            for i, stat in enumerate(stats):
                overlay = self.draw_japanese_text(overlay, stat, 
                                                (15, stats_y + 20 + i*25), 
                                                font_size=14, color=(0, 0, 0))
        
        return overlay
    
    def process_image(self, image_path):
        """単一画像を処理"""
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        print(f"\n処理中: {base_name}")
        
        # 画像読み込み
        img = cv2.imread(image_path)
        if img is None:
            print(f"エラー: 画像を読み込めません: {image_path}")
            return None
        
        # CSVデータ読み込み
        data_dict = self.load_csv_data(base_name)
        if not data_dict:
            print(f"  データなし: {base_name}")
            return None
        
        # データ分析
        analysis_results = self.analyze_data(data_dict)
        
        # オーバーレイ作成
        overlay_img = self.create_analysis_overlay(img, analysis_results)
        
        # 保存
        output_path = os.path.join(self.output_dir, f"{base_name}_analysis.png")
        cv2.imwrite(output_path, overlay_img)
        print(f"  保存: {output_path}")
        
        return {
            'image': base_name,
            'analysis': analysis_results,
            'output_path': output_path
        }
    
    def process_all(self):
        """すべての画像を処理"""
        # 画像ファイルを取得
        image_files = glob.glob(os.path.join(self.image_dir, "*.png"))
        image_files.sort()
        
        print(f"グラフ分析オーバーレイ開始")
        print(f"対象: {len(image_files)}枚")
        
        results = []
        processed = 0
        
        for image_path in image_files:
            result = self.process_image(image_path)
            if result:
                results.append(result)
                processed += 1
        
        # サマリー
        print(f"\n処理完了:")
        print(f"  成功: {processed}枚")
        print(f"  スキップ: {len(image_files) - processed}枚")
        
        # レポート保存
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_images': len(image_files),
            'processed': processed,
            'results': results
        }
        
        report_path = os.path.join(self.output_dir, 
                                 f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\nレポート保存: {report_path}")
        
        return results

def main():
    """メイン処理"""
    analyzer = GraphAnalyzerOverlay()
    results = analyzer.process_all()

if __name__ == "__main__":
    main()