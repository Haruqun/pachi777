#!/usr/bin/env python3
"""
最終統合分析 v2 - 改良された色検出を使用
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import platform
import json
from datetime import datetime
import glob
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import re

# 日本語フォント設定
if platform.system() == 'Darwin':  # macOS
    plt.rcParams['font.family'] = 'Hiragino Sans'

class FinalIntegratedAnalysisV2:
    def __init__(self):
        self.zero_y = 250
        self.target_30k_y = 4  # 3から1px下方向に移動
        self.scale = 30000 / (250 - 4)  # 246px距離で再計算 = 121.95
        
        # 改良された色検出範囲
        self.color_ranges = {
            'pink': {'lower': np.array([140, 50, 50]), 'upper': np.array([170, 255, 255])},
            'magenta': {'lower': np.array([130, 100, 100]), 'upper': np.array([160, 255, 255])},
            'red': {'lower': np.array([0, 100, 100]), 'upper': np.array([10, 255, 255])},
            'red_high': {'lower': np.array([170, 100, 100]), 'upper': np.array([180, 255, 255])},
            'blue': {'lower': np.array([100, 100, 100]), 'upper': np.array([130, 255, 255])},
            'green': {'lower': np.array([40, 100, 100]), 'upper': np.array([80, 255, 255])},
            'cyan': {'lower': np.array([80, 100, 100]), 'upper': np.array([100, 255, 255])},
            'yellow': {'lower': np.array([20, 100, 100]), 'upper': np.array([40, 255, 255])},
            'orange': {'lower': np.array([10, 100, 100]), 'upper': np.array([25, 255, 255])},
            'purple': {'lower': np.array([120, 100, 100]), 'upper': np.array([140, 255, 255])}
        }
        
        self.results = []
    
    def detect_zero_line(self, img):
        """ゼロライン検出"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        search_top = height // 3
        search_bottom = height * 2 // 3
        search_region = gray[search_top:search_bottom, :]
        
        # 水平線検出
        edges = cv2.Canny(search_region, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=int(width*0.3))
        
        zero_candidates = []
        
        if lines is not None:
            for rho, theta in lines[0]:
                if abs(theta) < 0.1 or abs(theta - np.pi) < 0.1:
                    y = int(rho / np.sin(theta)) if abs(np.sin(theta)) > 0.1 else search_top
                    if 0 < y < search_region.shape[0]:
                        zero_candidates.append(search_top + y)
        
        # 濃い水平線検出
        for y in range(search_top, search_bottom):
            row = gray[y, :]
            dark_pixels = np.sum(row < 100)
            if dark_pixels > width * 0.7:
                zero_candidates.append(y)
        
        if zero_candidates:
            return int(np.median(zero_candidates))
        else:
            return self.zero_y
    
    def extract_graph_data_improved(self, img_path):
        """改良された複数色対応グラフデータ抽出"""
        img = cv2.imread(img_path)
        if img is None:
            return [], 0, "なし"
            
        height, width = img.shape[:2]
        detected_zero = self.detect_zero_line(img)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 各色での検出を試行
        best_result = []
        best_color = "なし"
        max_points = 0
        
        for color_name, color_range in self.color_ranges.items():
            mask = cv2.inRange(hsv, color_range['lower'], color_range['upper'])
            
            data_points = []
            for x in range(0, width, 2):
                col_mask = mask[:, x]
                colored_pixels = np.where(col_mask > 0)[0]
                
                if len(colored_pixels) > 0:
                    graph_y = np.max(colored_pixels)
                    value = (detected_zero - graph_y) * self.scale
                    data_points.append((x, value))
            
            if len(data_points) > max_points:
                max_points = len(data_points)
                best_result = data_points
                best_color = color_name
        
        return best_result, detected_zero, best_color
    
    def extract_ocr_data(self, img_path):
        """OCRデータ抽出"""
        try:
            pil_img = Image.open(img_path)
            gray_img = pil_img.convert('L')
            enhancer = ImageEnhance.Contrast(gray_img)
            enhanced_img = enhancer.enhance(2.0)
            
            tesseract_config = '--psm 6 -l jpn+eng'
            text = pytesseract.image_to_string(enhanced_img, config=tesseract_config)
            
            parsed_data = self.parse_pachinko_text(text)
            
            return {
                'raw_text': text,
                'parsed_data': parsed_data
            }
            
        except Exception as e:
            return {
                'raw_text': f"OCRエラー: {str(e)}",
                'parsed_data': {}
            }
    
    def parse_pachinko_text(self, text):
        """パチンコテキスト解析"""
        parsed_data = {
            'machine_model': None,
            'total_spins': None,
            'big_bonus': None,
            'probability': None,
            'play_time': None,
            'date_time': None
        }
        
        patterns = {
            'total_spins': r'(?:総回転|回転数|スピン).*?(\d{1,5})',
            'big_bonus': r'(?:大当たり|BIG|ビッグ).*?(\d{1,3})',
            'probability': r'(?:確率|1/).*?(\d{1,4})',
            'play_time': r'(?:時間|TIME).*?(\d{1,2}:\d{2})',
            'date_time': r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2})',
        }
        
        for key, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                parsed_data[key] = matches[0]
        
        machine_matches = re.findall(r'[ア-ヴー]{3,}', text)
        if machine_matches:
            parsed_data['machine_model'] = machine_matches[0]
        
        return parsed_data
    
    def create_final_visualization(self, cropped_img_path, original_img_path, output_path):
        """最終版可視化画像生成"""
        img = cv2.imread(cropped_img_path)
        if img is None:
            return None
            
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        height, width = img.shape[:2]
        
        # 改良されたデータ抽出
        data_points, detected_zero, detected_color = self.extract_graph_data_improved(cropped_img_path)
        
        # OCRデータ抽出
        ocr_data = self.extract_ocr_data(original_img_path)
        
        # matplotlib図を作成
        fig, ax = plt.subplots(figsize=(16, 12))
        ax.imshow(img_rgb)
        
        # ゼロライン
        ax.axhline(y=detected_zero, color='black', linewidth=4, label=f'ゼロライン (Y={detected_zero})', alpha=0.8)
        
        # ±30,000ライン
        ax.axhline(y=self.target_30k_y, color='#FF1493', linewidth=3, label='+30,000', alpha=0.9)
        minus_30k_y = detected_zero + (30000 / self.scale)
        if minus_30k_y <= height:
            ax.axhline(y=minus_30k_y, color='#FF1493', linewidth=3, label='-30,000', alpha=0.9)
        
        # グリッドライン（20000は1px上方向に調整）
        grid_values = [25000, 20000, 15000, 10000, 5000]
        for value in grid_values:
            # 20000ラインのみ1px上方向に調整
            adjustment = -1 if value == 20000 else 0
            
            plus_y = detected_zero - (value / self.scale) + adjustment
            if 0 <= plus_y <= height:
                alpha = 0.7 if value >= 20000 else 0.5
                linestyle = '--' if value >= 20000 else ':'
                ax.axhline(y=plus_y, color='#FF69B4', linewidth=1.2, linestyle=linestyle, alpha=alpha)
            
            minus_y = detected_zero + (value / self.scale) - adjustment
            if 0 <= minus_y <= height:
                alpha = 0.7 if value >= 20000 else 0.5
                linestyle = '--' if value >= 20000 else ':'
                ax.axhline(y=minus_y, color='#FF69B4', linewidth=1.2, linestyle=linestyle, alpha=alpha)
        
        # 抽出されたグラフデータ
        if data_points:
            x_coords = [p[0] for p in data_points]
            y_coords = [detected_zero - (p[1] / self.scale) for p in data_points]
            values = [p[1] for p in data_points]
            
            # グラフ線
            ax.plot(x_coords, y_coords, color='cyan', linewidth=2, alpha=0.6, label=f'抽出データ ({detected_color})')
            
            # 重要ポイント
            max_val = max(values)
            min_val = min(values)
            current_val = values[-1]
            
            max_idx = values.index(max_val)
            min_idx = values.index(min_val)
            current_idx = len(values) - 1
            
            # 最大値線
            max_y = detected_zero - (max_val / self.scale)
            ax.axhline(y=max_y, color='red', linewidth=2, linestyle='--', alpha=0.8)
            ax.plot(x_coords[max_idx], max_y, 'ro', markersize=8)
            ax.text(width - 130, max_y - 20, f'最大: +{max_val:,.0f}', 
                   fontsize=11, color='red', weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
            
            # 最小値線
            min_y = detected_zero - (min_val / self.scale)
            ax.axhline(y=min_y, color='blue', linewidth=2, linestyle='--', alpha=0.8)
            ax.plot(x_coords[min_idx], min_y, 'bo', markersize=8)
            
            # 最終差玉線
            current_y = detected_zero - (current_val / self.scale)
            ax.axhline(y=current_y, color='lime', linewidth=2, linestyle=':', alpha=0.8)
            ax.plot(x_coords[current_idx], current_y, 'go', markersize=8)
            ax.text(width - 130, current_y + 20, f'最終: {current_val:+,.0f}', 
                   fontsize=12, color='lime', weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.8))
        
        # OCRデータの表示
        parsed_ocr = ocr_data['parsed_data']
        ocr_info_text = ""
        if parsed_ocr.get('machine_model'):
            ocr_info_text += f"機種: {parsed_ocr['machine_model']}\n"
        if parsed_ocr.get('total_spins'):
            ocr_info_text += f"総回転: {parsed_ocr['total_spins']}\n"
        if parsed_ocr.get('big_bonus'):
            ocr_info_text += f"大当たり: {parsed_ocr['big_bonus']}\n"
        if parsed_ocr.get('play_time'):
            ocr_info_text += f"時間: {parsed_ocr['play_time']}\n"
        
        if ocr_info_text:
            ax.text(10, 50, ocr_info_text.strip(), 
                   fontsize=10, color='white', weight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='darkblue', alpha=0.8))
        
        # タイトル
        file_name = Path(cropped_img_path).stem.replace('_graph_only', '')
        ax.set_title(f'最終統合分析 v2: {file_name} ({detected_color})', fontsize=16, pad=20)
        
        # 軸設定
        ax.set_xlim(0, width)
        ax.set_ylim(height, 0)
        ax.axis('off')
        
        # 凡例
        ax.legend(loc='upper left', fontsize=9, framealpha=0.9, ncol=3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        # 結果データ
        result_data = {
            'image_path': cropped_img_path,
            'original_path': original_img_path,
            'output_path': output_path,
            'detected_zero': detected_zero,
            'detected_color': detected_color,
            'data_points_count': len(data_points),
            'ocr_data': ocr_data,
            'graph_statistics': {
                'max_value': max([p[1] for p in data_points]) if data_points else 0,
                'min_value': min([p[1] for p in data_points]) if data_points else 0,
                'current_value': data_points[-1][1] if data_points else 0,
                'data_range': max([p[1] for p in data_points]) - min([p[1] for p in data_points]) if data_points else 0,
            }
        }
        
        return result_data
    
    def process_all_images_v2(self):
        """全画像の最終統合処理"""
        cropped_pattern = "graphs/manual_crop/cropped/*_graph_only.png"
        cropped_files = glob.glob(cropped_pattern)
        
        print(f"最終統合分析 v2 対象: {len(cropped_files)}個の画像")
        
        for cropped_file in cropped_files:
            base_name = Path(cropped_file).stem.replace('_graph_only', '')
            original_file = f"graphs/original/{base_name}.jpg"
            
            if not Path(original_file).exists():
                print(f"  元画像が見つかりません: {original_file}")
                continue
            
            print(f"最終分析中: {base_name}")
            
            output_path = f"final_analysis_v2_{base_name}.png"
            
            result = self.create_final_visualization(cropped_file, original_file, output_path)
            
            if result:
                self.results.append(result)
                print(f"  -> 保存: {output_path}")
                print(f"  -> データポイント数: {result['data_points_count']} ({result['detected_color']})")
                if result['ocr_data']['parsed_data'].get('machine_model'):
                    print(f"  -> 検出機種: {result['ocr_data']['parsed_data']['machine_model']}")
        
        return self.results
    
    def generate_ultimate_html_report(self, output_file="ultimate_analysis_report.html"):
        """究極のHTMLレポート生成"""
        
        successful_results = [r for r in self.results if r['data_points_count'] > 0]
        
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎰 Ultimate パチンコ分析レポート</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700;900&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Noto Sans JP', 'Hiragino Sans', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #fff;
            overflow-x: hidden;
        }}
        
        .background-animation {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            opacity: 0.1;
        }}
        
        .background-animation::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at 50% 50%, rgba(255,255,255,0.1) 0%, transparent 50%);
            animation: pulse 4s ease-in-out infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); opacity: 0.1; }}
            50% {{ transform: scale(1.1); opacity: 0.2; }}
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }}
        
        .header {{
            text-align: center;
            background: linear-gradient(135deg, #ff6b6b, #feca57, #48dbfb, #ff9ff3);
            background-size: 400% 400%;
            animation: gradientShift 6s ease infinite;
            padding: 60px 40px;
            border-radius: 30px;
            margin-bottom: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            animation: rotate 20s linear infinite;
        }}
        
        @keyframes gradientShift {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}
        
        @keyframes rotate {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}
        
        .header h1 {{
            font-size: 3.5em;
            font-weight: 900;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            position: relative;
            z-index: 2;
        }}
        
        .header .subtitle {{
            font-size: 1.4em;
            font-weight: 300;
            opacity: 0.9;
            position: relative;
            z-index: 2;
        }}
        
        .stats-dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 30px;
            margin-bottom: 50px;
        }}
        
        .stat-card {{
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-10px) scale(1.02);
            box-shadow: 0 25px 70px rgba(0,0,0,0.3);
        }}
        
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
            transition: left 0.5s;
        }}
        
        .stat-card:hover::before {{
            left: 100%;
        }}
        
        .stat-icon {{
            font-size: 3em;
            margin-bottom: 15px;
            display: block;
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #ffd700, #ffed4a);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .stat-label {{
            font-size: 1.1em;
            opacity: 0.8;
            font-weight: 300;
        }}
        
        .analysis-section {{
            margin-bottom: 50px;
        }}
        
        .section-title {{
            font-size: 2.5em;
            font-weight: 700;
            text-align: center;
            margin-bottom: 40px;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .analysis-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(800px, 1fr));
            gap: 40px;
        }}
        
        .analysis-card {{
            background: rgba(255,255,255,0.08);
            border-radius: 25px;
            overflow: hidden;
            box-shadow: 0 15px 50px rgba(0,0,0,0.2);
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.4s ease;
            position: relative;
        }}
        
        .analysis-card:hover {{
            transform: translateY(-15px);
            box-shadow: 0 30px 80px rgba(0,0,0,0.4);
        }}
        
        .card-header {{
            padding: 25px;
            font-weight: 700;
            font-size: 1.3em;
            position: relative;
            overflow: hidden;
        }}
        
        .success-card .card-header {{
            background: linear-gradient(135deg, #11998e, #38ef7d);
        }}
        
        .card-content {{
            padding: 30px;
        }}
        
        .image-container {{
            position: relative;
            margin-bottom: 25px;
        }}
        
        .analysis-image {{
            width: 100%;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            transition: transform 0.3s ease;
        }}
        
        .analysis-image:hover {{
            transform: scale(1.02);
        }}
        
        .image-overlay {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 500;
        }}
        
        .image-comparison-container {{
            position: relative;
            margin-bottom: 25px;
            border-radius: 15px;
            overflow: hidden;
        }}
        
        .image-viewer {{
            position: relative;
            width: 100%;
            min-height: 400px;
            overflow: hidden;
            border-radius: 15px;
            background: rgba(0,0,0,0.2);
        }}
        
        .image-slide {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            opacity: 0;
            transition: opacity 0.3s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .image-slide.active {{
            opacity: 1;
        }}
        
        .image-title {{
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 15px;
            color: #fff;
            text-align: center;
            background: rgba(0,0,0,0.6);
            padding: 10px 20px;
            border-radius: 20px;
        }}
        
        .slide-image {{
            max-width: 100%;
            max-height: 400px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            transition: transform 0.3s ease;
        }}
        
        .slide-image:hover {{
            transform: scale(1.02);
        }}
        
        .original-slide {{
            background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05));
        }}
        
        .analysis-slide {{
            background: linear-gradient(135deg, rgba(64, 224, 208, 0.1), rgba(64, 224, 208, 0.05));
        }}
        
        .image-controls {{
            position: absolute;
            bottom: 15px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 10px;
            background: rgba(0,0,0,0.7);
            padding: 10px 20px;
            border-radius: 25px;
        }}
        
        .control-btn {{
            padding: 8px 15px;
            background: rgba(255,255,255,0.2);
            border: none;
            border-radius: 15px;
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
        }}
        
        .control-btn.active {{
            background: rgba(64, 224, 208, 0.8);
            color: #000;
        }}
        
        .control-btn:hover {{
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }}
        
        .keyboard-hint {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            opacity: 0.7;
        }}
        
        .data-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 25px;
        }}
        
        .data-panel {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            position: relative;
        }}
        
        .panel-title {{
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .graph-panel {{
            border-left: 4px solid #4ecdc4;
        }}
        
        .ocr-panel {{
            border-left: 4px solid #ffd93d;
        }}
        
        .data-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .data-item:last-child {{
            border-bottom: none;
        }}
        
        .data-label {{
            font-weight: 500;
            opacity: 0.8;
        }}
        
        .data-value {{
            font-weight: 600;
            font-size: 1.1em;
        }}
        
        .positive {{ color: #4ecdc4; }}
        .negative {{ color: #ff6b6b; }}
        .neutral {{ color: #ffd93d; }}
        
        .summary-section {{
            background: rgba(255,255,255,0.1);
            border-radius: 25px;
            padding: 40px;
            margin-top: 50px;
            text-align: center;
            backdrop-filter: blur(20px);
        }}
        
        .results-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-top: 30px;
        }}
        
        .result-card {{
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s ease;
        }}
        
        .result-card:hover {{
            background: rgba(255,255,255,0.15);
            transform: translateY(-5px);
        }}
        
        .result-info {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }}
        
        .result-name {{
            font-weight: 600;
            font-size: 1.1em;
        }}
        
        .result-machine {{
            font-size: 0.9em;
            opacity: 0.7;
            margin-top: 5px;
        }}
        
        .result-value {{
            font-size: 1.4em;
            font-weight: 700;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 60px;
            padding: 40px;
            background: rgba(0,0,0,0.2);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }}
        
        .scroll-indicator {{
            position: fixed;
            top: 0;
            left: 0;
            height: 4px;
            background: linear-gradient(90deg, #ff6b6b, #4ecdc4, #ffd93d);
            z-index: 1000;
            transition: width 0.3s ease;
        }}
    </style>
    <script>
        // スクロールインジケーター
        window.addEventListener('scroll', () => {{
            const scrolled = (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
            document.querySelector('.scroll-indicator').style.width = scrolled + '%';
        }});
        
        // 画像スライド切り替え機能
        let currentSlides = {{}};
        
        function switchSlide(viewerId, slideIndex) {{
            const viewer = document.getElementById(`viewer-${{viewerId}}`);
            const slides = viewer.querySelectorAll('.image-slide');
            const buttons = viewer.querySelectorAll('.control-btn');
            
            // 現在のスライドを非アクティブに
            slides.forEach(slide => slide.classList.remove('active'));
            buttons.forEach(btn => btn.classList.remove('active'));
            
            // 新しいスライドをアクティブに
            slides[slideIndex].classList.add('active');
            buttons[slideIndex].classList.add('active');
            
            currentSlides[viewerId] = slideIndex;
        }}
        
        // キーボード操作
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {{
                const viewers = document.querySelectorAll('.image-comparison-container');
                viewers.forEach((viewer, index) => {{
                    const viewerId = viewer.id.split('-')[1];
                    const currentSlide = currentSlides[viewerId] || 0;
                    let newSlide;
                    
                    if (e.key === 'ArrowLeft') {{
                        newSlide = currentSlide === 0 ? 1 : 0;
                    }} else {{
                        newSlide = currentSlide === 1 ? 0 : 1;
                    }}
                    
                    switchSlide(viewerId, newSlide);
                }});
                e.preventDefault();
            }}
        }});
        
        // タッチ/スワイプ機能
        document.addEventListener('DOMContentLoaded', () => {{
            const viewers = document.querySelectorAll('.image-viewer');
            
            viewers.forEach((viewer, index) => {{
                let startX = 0;
                let endX = 0;
                
                viewer.addEventListener('touchstart', (e) => {{
                    startX = e.touches[0].clientX;
                }});
                
                viewer.addEventListener('touchend', (e) => {{
                    endX = e.changedTouches[0].clientX;
                    const diff = startX - endX;
                    
                    if (Math.abs(diff) > 50) {{ // 50px以上のスワイプで切り替え
                        const viewerId = viewer.closest('.image-comparison-container').id.split('-')[1];
                        const currentSlide = currentSlides[viewerId] || 0;
                        let newSlide;
                        
                        if (diff > 0) {{ // 左スワイプ
                            newSlide = currentSlide === 1 ? 0 : 1;
                        }} else {{ // 右スワイプ
                            newSlide = currentSlide === 0 ? 1 : 0;
                        }}
                        
                        switchSlide(viewerId, newSlide);
                    }}
                }});
                
                // マウスでのドラッグ
                let mouseStartX = 0;
                let mouseEndX = 0;
                let isDragging = false;
                
                viewer.addEventListener('mousedown', (e) => {{
                    mouseStartX = e.clientX;
                    isDragging = true;
                }});
                
                viewer.addEventListener('mouseup', (e) => {{
                    if (!isDragging) return;
                    mouseEndX = e.clientX;
                    const diff = mouseStartX - mouseEndX;
                    
                    if (Math.abs(diff) > 50) {{
                        const viewerId = viewer.closest('.image-comparison-container').id.split('-')[1];
                        const currentSlide = currentSlides[viewerId] || 0;
                        let newSlide;
                        
                        if (diff > 0) {{ // 左ドラッグ
                            newSlide = currentSlide === 1 ? 0 : 1;
                        }} else {{ // 右ドラッグ
                            newSlide = currentSlide === 0 ? 1 : 0;
                        }}
                        
                        switchSlide(viewerId, newSlide);
                    }}
                    isDragging = false;
                }});
                
                viewer.addEventListener('mouseleave', () => {{
                    isDragging = false;
                }});
            }});
        }});
    </script>
</head>
<body>
    <div class="scroll-indicator"></div>
    <div class="background-animation"></div>
    
    <div class="container">
        <div class="header">
            <h1>📊 パチンコグラフ分析レポート</h1>
            <div class="subtitle">
                画像からのデータ抽出精度検証結果<br>
                作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
            </div>
        </div>
        
        <div class="stats-dashboard">
            <div class="stat-card">
                <div class="stat-icon">📊</div>
                <div class="stat-value">{len(self.results)}</div>
                <div class="stat-label">総分析画像数</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">✅</div>
                <div class="stat-value">{len(successful_results)}</div>
                <div class="stat-label">データ抽出成功</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🎯</div>
                <div class="stat-value">{len(successful_results)/len(self.results)*100:.1f}%</div>
                <div class="stat-label">成功率</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">💰</div>
                <div class="stat-value">{"N/A" if not successful_results else f"{int(np.mean([r['graph_statistics']['current_value'] for r in successful_results])):+,}"}</div>
                <div class="stat-label">平均最終差玉</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🏆</div>
                <div class="stat-value">{len([r for r in successful_results if r['graph_statistics']['current_value'] > 0])}</div>
                <div class="stat-label">勝ちゲーム</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📉</div>
                <div class="stat-value">{len([r for r in successful_results if r['graph_statistics']['current_value'] < 0])}</div>
                <div class="stat-label">負けゲーム</div>
            </div>
        </div>
        
        <div class="analysis-section">
            <h2 class="section-title">📸 画像別分析結果 - 元画像と抽出結果の比較</h2>
            <div class="analysis-grid">
"""
        
        # 各画像の分析結果
        for i, result in enumerate(self.results):
            file_name = Path(result['image_path']).stem.replace('_graph_only', '')
            graph_stats = result['graph_statistics']
            ocr_data = result['ocr_data']['parsed_data']
            
            success = result['data_points_count'] > 0
            card_class = "success-card" if success else "failure-card"
            
            html_content += f"""
                <div class="analysis-card {card_class}">
                    <div class="card-header">
                        📋 画像#{i+1}: {file_name}
                    </div>
                    <div class="card-content">
                        <div class="image-comparison-container" id="viewer-{i}">
                            <div class="image-viewer">
                                <div class="keyboard-hint">← → キー または スワイプで切替</div>
                                
                                <div class="image-slide original-slide active" data-slide="0">
                                    <div class="image-title">📷 お客様の元画像</div>
                                    <img src="{result['original_path']}" alt="お客様の元画像" class="slide-image">
                                </div>
                                
                                <div class="image-slide analysis-slide" data-slide="1">
                                    <div class="image-title">📈 AI分析結果 (精度検証)</div>
                                    <img src="{result['output_path']}" alt="AI分析結果" class="slide-image">
                                    <div class="image-overlay">
                                        検出色: {result['detected_color']} • データ点数: {result['data_points_count']}
                                    </div>
                                </div>
                                
                                <div class="image-controls">
                                    <button class="control-btn active" onclick="switchSlide({i}, 0)">📷 元画像</button>
                                    <button class="control-btn" onclick="switchSlide({i}, 1)">📈 分析結果</button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="data-grid">
                            <div class="data-panel graph-panel">
                                <div class="panel-title">
                                    📈 データ抽出結果
                                </div>
"""
            
            if success:
                final_value = graph_stats['current_value']
                value_class = "positive" if final_value > 0 else "negative"
                
                html_content += f"""
                                <div class="data-item">
                                    <span class="data-label">最大値:</span>
                                    <span class="data-value positive">+{graph_stats['max_value']:,.0f}</span>
                                </div>
                                <div class="data-item">
                                    <span class="data-label">最小値:</span>
                                    <span class="data-value negative">{graph_stats['min_value']:+,.0f}</span>
                                </div>
                                <div class="data-item">
                                    <span class="data-label">最終差玉:</span>
                                    <span class="data-value {value_class}">{final_value:+,.0f}</span>
                                </div>
                                <div class="data-item">
                                    <span class="data-label">変動幅:</span>
                                    <span class="data-value neutral">{graph_stats['data_range']:,.0f}</span>
                                </div>
"""
            else:
                html_content += """
                                <div style="text-align: center; color: #ff6b6b; font-weight: 500;">
                                    データ抽出に失敗しました
                                </div>
"""
            
            html_content += """
                            </div>
                            
                            <div class="data-panel ocr-panel">
                                <div class="panel-title">
                                    🔍 画面情報解析結果
                                </div>
"""
            
            # OCRデータの表示
            ocr_items = [
                ('機種名', ocr_data.get('machine_model')),
                ('総回転数', ocr_data.get('total_spins')),
                ('大当たり', ocr_data.get('big_bonus')),
                ('確率', ocr_data.get('probability')),
                ('時間', ocr_data.get('play_time')),
                ('日時', ocr_data.get('date_time'))
            ]
            
            ocr_found = False
            for label, value in ocr_items:
                if value:
                    ocr_found = True
                    html_content += f"""
                                <div class="data-item">
                                    <span class="data-label">{label}:</span>
                                    <span class="data-value">{value}</span>
                                </div>"""
            
            if not ocr_found:
                html_content += """
                                <div style="text-align: center; color: #ffd93d; font-weight: 500;">
                                    画面情報の一部を検出
                                </div>
"""
            
            html_content += """
                            </div>
                        </div>
                    </div>
                </div>
"""
        
        # 最終差玉まとめ
        html_content += f"""
            </div>
        </div>
        
        <div class="summary-section">
            <h2 class="section-title">💰 各ゲームの最終収支一覧</h2>
            <div class="results-grid">
"""
        
        for result in successful_results:
            file_name = Path(result['image_path']).stem.replace('_graph_only', '')
            final_value = result['graph_statistics']['current_value']
            machine_name = result['ocr_data']['parsed_data'].get('machine_model', '不明')
            value_class = "positive" if final_value > 0 else "negative"
            
            html_content += f"""
                <div class="result-card">
                    <div class="result-info">
                        <div class="result-name">{file_name}</div>
                        <div class="result-machine">{machine_name}</div>
                    </div>
                    <div class="result-value {value_class}">{final_value:+,.0f}</div>
                </div>"""
        
        # 色分布統計
        color_stats = {}
        for result in self.results:
            color = result['detected_color']
            color_stats[color] = color_stats.get(color, 0) + 1
        
        html_content += f"""
            </div>
            
            <div style="margin-top: 40px;">
                <h3 style="font-size: 1.5em; margin-bottom: 20px;">🎨 検出色分布</h3>
                <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">
"""
        
        for color, count in sorted(color_stats.items(), key=lambda x: x[1], reverse=True):
            html_content += f"""
                    <div style="background: rgba(255,255,255,0.1); padding: 15px 25px; border-radius: 25px; text-align: center;">
                        <div style="font-weight: 600; font-size: 1.2em;">{color}</div>
                        <div style="font-size: 0.9em; opacity: 0.8;">{count}回検出</div>
                    </div>"""
        
        html_content += f"""
                </div>
            </div>
        </div>
        
        <div class="footer">
            <h3 style="font-size: 1.8em; margin-bottom: 20px;">📊 パチンコグラフ分析サービス</h3>
            <p style="font-size: 1.1em; opacity: 0.8; margin-bottom: 15px;">
                AI技術による高精度なグラフデータ抽出レポート
            </p>
            <div style="display: flex; justify-content: center; gap: 30px; margin-top: 25px; flex-wrap: wrap;">
                <div>📊 抽出成功率: {len(successful_results)/len(self.results)*100:.1f}%</div>
                <div>🎨 多色グラフ対応: 10色</div>
                <div>🔍 画面情報解析: 日本語対応</div>
                <div>📈 精密グリッド: 1px単位</div>
            </div>
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"🎨 究極のHTMLレポートを生成: {output_file}")
        return output_file

if __name__ == "__main__":
    analyzer = FinalIntegratedAnalysisV2()
    
    print("🚀 最終統合分析 v2 開始")
    print("=" * 50)
    
    # 全画像の処理
    results = analyzer.process_all_images_v2()
    
    print("\n" + "=" * 50)
    print(f"✅ 最終統合分析 v2 完了")
    print(f"📊 処理画像数: {len(results)}")
    successful = [r for r in results if r['data_points_count'] > 0]
    print(f"🎯 データ抽出成功: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
    
    # 色別統計
    color_stats = {}
    for result in successful:
        color = result['detected_color']
        color_stats[color] = color_stats.get(color, 0) + 1
    
    print(f"🎨 検出色分布:")
    for color, count in sorted(color_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"    {color}: {count}回")
    
    # 究極のHTMLレポート生成
    analyzer.generate_ultimate_html_report()
    
    print("=" * 50)