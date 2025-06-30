#!/usr/bin/env python3
"""
統合分析パイプライン - グラフ分析とOCRデータを統合
最終的な包括レポートを生成
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

class IntegratedAnalysisPipeline:
    def __init__(self):
        self.zero_y = 250
        self.target_30k_y = 3  # 5から2px上方向に移動
        self.scale = 30000 / (250 - 3)  # 247px距離で再計算 = 121.5
        self.graph_results = []
        self.ocr_results = []
        self.integrated_results = []
        
    def detect_zero_line(self, img):
        """ゼロライン検出（複数手法）"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # 中央部分を検索範囲とする
        search_top = height // 3
        search_bottom = height * 2 // 3
        search_region = gray[search_top:search_bottom, :]
        
        # 手法1: 水平線検出（Hough変換）
        edges = cv2.Canny(search_region, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=int(width*0.3))
        
        zero_candidates = []
        
        if lines is not None:
            for rho, theta in lines[0]:
                # 水平線のみ（theta ≈ 0 or π）
                if abs(theta) < 0.1 or abs(theta - np.pi) < 0.1:
                    y = int(rho / np.sin(theta)) if abs(np.sin(theta)) > 0.1 else search_top
                    if 0 < y < search_region.shape[0]:
                        zero_candidates.append(search_top + y)
        
        # 手法2: 濃い水平線検出
        for y in range(search_top, search_bottom):
            row = gray[y, :]
            dark_pixels = np.sum(row < 100)
            if dark_pixels > width * 0.7:  # 70%以上が濃い
                zero_candidates.append(y)
        
        # 最も可能性の高い位置を選択
        if zero_candidates:
            return int(np.median(zero_candidates))
        else:
            return self.zero_y  # デフォルト値
    
    def extract_graph_data(self, img_path):
        """グラフからデータを抽出"""
        img = cv2.imread(img_path)
        if img is None:
            return [], 0
            
        height, width = img.shape[:2]
        
        # 検出されたゼロライン
        detected_zero = self.detect_zero_line(img)
        
        # HSVに変換してピンク色のグラフ線を検出
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # ピンク色の範囲（HSV）
        lower_pink = np.array([140, 50, 50])
        upper_pink = np.array([170, 255, 255])
        
        # マスクを作成
        mask = cv2.inRange(hsv, lower_pink, upper_pink)
        
        # グラフデータポイントを抽出
        data_points = []
        
        for x in range(0, width, 2):  # 2ピクセルおきにサンプリング
            col_mask = mask[:, x]
            pink_pixels = np.where(col_mask > 0)[0]
            
            if len(pink_pixels) > 0:
                # 最も下のピンクピクセル（グラフ線の位置）
                graph_y = np.max(pink_pixels)
                
                # Y座標を値に変換
                value = (detected_zero - graph_y) * self.scale
                data_points.append((x, value))
        
        return data_points, detected_zero
    
    def extract_ocr_data(self, img_path):
        """OCRでテキストデータを抽出"""
        try:
            # PIL Imageで読み込み
            pil_img = Image.open(img_path)
            
            # グレースケール変換
            gray_img = pil_img.convert('L')
            
            # コントラスト強化
            enhancer = ImageEnhance.Contrast(gray_img)
            enhanced_img = enhancer.enhance(2.0)
            
            # OCR実行
            tesseract_config = '--psm 6 -l jpn+eng'
            text = pytesseract.image_to_string(enhanced_img, config=tesseract_config)
            
            # パチンコ固有データの解析
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
        """パチンコテキストの解析"""
        parsed_data = {
            'machine_model': None,
            'total_spins': None,
            'big_bonus': None,
            'probability': None,
            'play_time': None,
            'date_time': None
        }
        
        # パターンマッチング
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
        
        # 機種名の推定
        machine_matches = re.findall(r'[ア-ヴー]{3,}', text)
        if machine_matches:
            parsed_data['machine_model'] = machine_matches[0]
        
        return parsed_data
    
    def create_enhanced_visualization(self, cropped_img_path, original_img_path, output_path):
        """強化された可視化画像を生成"""
        img = cv2.imread(cropped_img_path)
        if img is None:
            return None
            
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        height, width = img.shape[:2]
        
        # データ抽出
        data_points, detected_zero = self.extract_graph_data(cropped_img_path)
        
        # OCRデータ抽出
        ocr_data = self.extract_ocr_data(original_img_path)
        
        # matplotlib図を作成
        fig, ax = plt.subplots(figsize=(16, 12))
        ax.imshow(img_rgb)
        
        # 検出されたゼロライン
        ax.axhline(y=detected_zero, color='black', linewidth=4, label=f'ゼロライン (Y={detected_zero})', alpha=0.8)
        
        # ±30,000ライン
        ax.axhline(y=self.target_30k_y, color='#FF1493', linewidth=3, label='+30,000', alpha=0.9)
        minus_30k_y = detected_zero + (30000 / self.scale)
        if minus_30k_y <= height:
            ax.axhline(y=minus_30k_y, color='#FF1493', linewidth=3, label='-30,000', alpha=0.9)
        
        # グリッドライン
        grid_values = [25000, 20000, 15000, 10000, 5000]
        for value in grid_values:
            # プラス側
            plus_y = detected_zero - (value / self.scale)
            if 0 <= plus_y <= height:
                alpha = 0.7 if value >= 20000 else 0.5
                linestyle = '--' if value >= 20000 else ':'
                ax.axhline(y=plus_y, color='#FF69B4', linewidth=1.2, linestyle=linestyle, alpha=alpha)
            
            # マイナス側
            minus_y = detected_zero + (value / self.scale)
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
            ax.plot(x_coords, y_coords, color='cyan', linewidth=2, alpha=0.6, label='抽出データ')
            
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
            ax.text(width - 120, max_y - 20, f'最大: +{max_val:,.0f}', 
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
            ax.text(width - 120, current_y + 20, f'最終: {current_val:+,.0f}', 
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
        ax.set_title(f'統合分析結果: {file_name}', fontsize=16, pad=20)
        
        # 軸設定
        ax.set_xlim(0, width)
        ax.set_ylim(height, 0)
        ax.axis('off')
        
        # 凡例
        ax.legend(loc='upper left', fontsize=9, framealpha=0.9, ncol=3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        # 結果データの準備
        result_data = {
            'image_path': cropped_img_path,
            'original_path': original_img_path,
            'output_path': output_path,
            'detected_zero': detected_zero,
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
    
    def process_all_images(self):
        """全画像の統合処理"""
        # cropped画像のパターン
        cropped_pattern = "graphs/manual_crop/cropped/*_graph_only.png"
        cropped_files = glob.glob(cropped_pattern)
        
        print(f"統合分析対象: {len(cropped_files)}個の画像")
        
        for cropped_file in cropped_files:
            # 対応する元画像のパスを構築
            base_name = Path(cropped_file).stem.replace('_graph_only', '')
            original_file = f"graphs/original/{base_name}.jpg"
            
            if not Path(original_file).exists():
                print(f"  元画像が見つかりません: {original_file}")
                continue
            
            print(f"統合分析中: {base_name}")
            
            # 出力ファイル名
            output_path = f"integrated_analysis_{base_name}.png"
            
            # 統合分析実行
            result = self.create_enhanced_visualization(cropped_file, original_file, output_path)
            
            if result:
                self.integrated_results.append(result)
                print(f"  -> 保存: {output_path}")
                print(f"  -> データポイント数: {result['data_points_count']}")
                if result['ocr_data']['parsed_data'].get('machine_model'):
                    print(f"  -> 検出機種: {result['ocr_data']['parsed_data']['machine_model']}")
        
        return self.integrated_results
    
    def generate_integrated_report(self, output_file="integrated_analysis_report.html"):
        """統合分析レポートのHTML生成"""
        
        # データ抽出成功画像のフィルタリング
        successful_results = [r for r in self.integrated_results if r['data_points_count'] > 0]
        
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>統合分析レポート - グラフ分析 + OCRデータ</title>
    <style>
        body {{
            font-family: 'Hiragino Sans', 'Meiryo', sans-serif;
            background: linear-gradient(135deg, #0f3460, #16537e);
            color: #fff;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            background: linear-gradient(45deg, #e74c3c, #f39c12, #2ecc71);
            padding: 40px;
            border-radius: 20px;
            margin-bottom: 30px;
            box-shadow: 0 12px 40px rgba(0,0,0,0.4);
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }}
        
        .summary-card {{
            background: rgba(255,255,255,0.1);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            backdrop-filter: blur(15px);
            border: 2px solid rgba(255,255,255,0.2);
            transition: transform 0.3s ease;
        }}
        
        .summary-card:hover {{
            transform: translateY(-5px);
        }}
        
        .summary-card h3 {{
            margin: 0 0 15px 0;
            color: #4CAF50;
            font-size: 1.1em;
        }}
        
        .summary-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #fff;
        }}
        
        .analysis-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(800px, 1fr));
            gap: 40px;
        }}
        
        .analysis-item {{
            background: rgba(255,255,255,0.08);
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 12px 40px rgba(0,0,0,0.4);
            backdrop-filter: blur(15px);
            border: 2px solid rgba(255,255,255,0.1);
            transition: transform 0.3s ease;
        }}
        
        .analysis-item:hover {{
            transform: translateY(-10px);
        }}
        
        .analysis-header {{
            background: linear-gradient(45deg, #3498db, #2980b9);
            padding: 20px;
            font-weight: bold;
            font-size: 1.3em;
        }}
        
        .analysis-content {{
            padding: 25px;
        }}
        
        .analysis-image {{
            width: 100%;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.3);
        }}
        
        .data-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin-top: 20px;
        }}
        
        .graph-stats {{
            background: rgba(46, 204, 113, 0.2);
            padding: 20px;
            border-radius: 15px;
            border-left: 6px solid #2ecc71;
        }}
        
        .ocr-data {{
            background: rgba(52, 152, 219, 0.2);
            padding: 20px;
            border-radius: 15px;
            border-left: 6px solid #3498db;
        }}
        
        .stat-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .stat-label {{
            font-weight: bold;
            color: #2ecc71;
        }}
        
        .stat-value {{
            color: #ecf0f1;
            font-weight: bold;
        }}
        
        .ocr-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .ocr-label {{
            font-weight: bold;
            color: #3498db;
        }}
        
        .ocr-value {{
            color: #ecf0f1;
            font-weight: bold;
        }}
        
        .detection-info {{
            background: rgba(241, 196, 15, 0.2);
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            border-left: 6px solid #f1c40f;
        }}
        
        .final-results {{
            background: rgba(155, 89, 182, 0.2);
            padding: 25px;
            border-radius: 15px;
            margin-top: 40px;
            border-left: 6px solid #9b59b6;
        }}
        
        .results-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .result-item {{
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            font-family: monospace;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .result-name {{
            font-weight: bold;
        }}
        
        .result-value {{
            font-size: 1.2em;
            font-weight: bold;
        }}
        
        .positive {{ color: #2ecc71; }}
        .negative {{ color: #e74c3c; }}
        
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding: 30px;
            background: rgba(255,255,255,0.08);
            border-radius: 15px;
            color: #bdc3c7;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎰 統合分析レポート 🎰</h1>
            <h2>グラフ分析 + OCRデータ統合</h2>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>総分析画像数</h3>
                <div class="value">{len(self.integrated_results)}</div>
            </div>
            <div class="summary-card">
                <h3>データ抽出成功</h3>
                <div class="value">{len(successful_results)}</div>
            </div>
            <div class="summary-card">
                <h3>平均最終差玉</h3>
                <div class="value">{"N/A" if not successful_results else f"{int(np.mean([r['graph_statistics']['current_value'] for r in successful_results])):+,}"}</div>
            </div>
            <div class="summary-card">
                <h3>OCR機種検出</h3>
                <div class="value">{len([r for r in self.integrated_results if r['ocr_data']['parsed_data'].get('machine_model')])}</div>
            </div>
            <div class="summary-card">
                <h3>勝ちゲーム</h3>
                <div class="value">{len([r for r in successful_results if r['graph_statistics']['current_value'] > 0])}</div>
            </div>
            <div class="summary-card">
                <h3>負けゲーム</h3>
                <div class="value">{len([r for r in successful_results if r['graph_statistics']['current_value'] < 0])}</div>
            </div>
        </div>
        
        <div class="analysis-grid">
"""
        
        # 各画像の統合分析結果
        for i, result in enumerate(self.integrated_results):
            file_name = Path(result['image_path']).stem.replace('_graph_only', '')
            graph_stats = result['graph_statistics']
            ocr_data = result['ocr_data']['parsed_data']
            
            html_content += f"""
            <div class="analysis-item">
                <div class="analysis-header">
                    #{i+1}: {file_name}
                </div>
                <div class="analysis-content">
                    <div style="margin-bottom: 20px;">
                        <h4 style="margin: 5px 0; color: #ecf0f1;">📷 元画像:</h4>
                        <img src="{result['original_path']}" alt="元画像" style="width: 100%; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <h4 style="margin: 5px 0; color: #ecf0f1;">📊 分析結果:</h4>
                        <img src="{result['output_path']}" alt="統合分析結果" class="analysis-image">
                    </div>
                    
                    <div class="detection-info">
                        <strong>検出情報:</strong> ゼロライン Y={result['detected_zero']} | 
                        データポイント数: {result['data_points_count']} | 
                        {"OCR成功" if ocr_data.get('machine_model') else "OCR部分的"}
                    </div>
                    
                    <div class="data-section">
                        <div class="graph-stats">
                            <h4>📊 グラフ分析結果</h4>
"""
            
            if result['data_points_count'] > 0:
                html_content += f"""
                            <div class="stat-item">
                                <span class="stat-label">最大値:</span>
                                <span class="stat-value">+{graph_stats['max_value']:,.0f}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">最小値:</span>
                                <span class="stat-value">{graph_stats['min_value']:+,.0f}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">最終差玉:</span>
                                <span class="stat-value {'positive' if graph_stats['current_value'] > 0 else 'negative'}">{graph_stats['current_value']:+,.0f}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">変動幅:</span>
                                <span class="stat-value">{graph_stats['data_range']:,.0f}</span>
                            </div>
"""
            else:
                html_content += """
                            <p style="color: #e74c3c;">データ抽出に失敗しました</p>
"""
            
            html_content += """
                        </div>
                        
                        <div class="ocr-data">
                            <h4>📝 OCR抽出データ</h4>
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
            
            for label, value in ocr_items:
                if value:
                    html_content += f"""
                            <div class="ocr-item">
                                <span class="ocr-label">{label}:</span>
                                <span class="ocr-value">{value}</span>
                            </div>"""
            
            if not any(item[1] for item in ocr_items):
                html_content += """
                            <p style="color: #e74c3c;">OCRデータ抽出に失敗しました</p>
"""
            
            html_content += """
                        </div>
                    </div>
                </div>
            </div>
"""
        
        # 最終差玉まとめ
        html_content += """
        </div>
        
        <div class="final-results">
            <h3>🎯 最終差玉まとめ</h3>
            <div class="results-grid">
"""
        
        for result in successful_results:
            file_name = Path(result['image_path']).stem.replace('_graph_only', '')
            final_value = result['graph_statistics']['current_value']
            machine_name = result['ocr_data']['parsed_data'].get('machine_model', '不明')
            
            html_content += f"""
                <div class="result-item">
                    <div>
                        <div class="result-name">{file_name}</div>
                        <div style="font-size: 0.8em; color: #bdc3c7;">{machine_name}</div>
                    </div>
                    <div class="result-value {'positive' if final_value > 0 else 'negative'}">{final_value:+,.0f}</div>
                </div>"""
        
        html_content += f"""
            </div>
        </div>
        
        <div class="footer">
            <p>🤖 統合分析システムによって自動生成されました</p>
            <p>グラフ分析スケール: 1px = {self.scale} | OCR言語: 日本語+英語</p>
            <p>成功率: グラフ分析 {len(successful_results)}/{len(self.integrated_results)} ({len(successful_results)/len(self.integrated_results)*100:.1f}%) | 
               OCR検出 {len([r for r in self.integrated_results if r['ocr_data']['parsed_data'].get('machine_model')])}/{len(self.integrated_results)} 
               ({len([r for r in self.integrated_results if r['ocr_data']['parsed_data'].get('machine_model')])/len(self.integrated_results)*100:.1f}%)</p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"統合レポートを生成: {output_file}")
        return output_file
    
    def save_results_json(self, output_file="integrated_results.json"):
        """結果をJSONで保存"""
        export_data = {
            "analysis_date": datetime.now().isoformat(),
            "total_images": len(self.integrated_results),
            "successful_extractions": len([r for r in self.integrated_results if r['data_points_count'] > 0]),
            "ocr_detections": len([r for r in self.integrated_results if r['ocr_data']['parsed_data'].get('machine_model')]),
            "results": self.integrated_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"統合結果をJSON保存: {output_file}")
        return output_file

if __name__ == "__main__":
    pipeline = IntegratedAnalysisPipeline()
    
    print("🚀 統合分析パイプライン開始")
    print("=" * 50)
    
    # 全画像の統合処理
    results = pipeline.process_all_images()
    
    # 統合レポート生成
    html_file = pipeline.generate_integrated_report()
    
    # JSON結果保存
    json_file = pipeline.save_results_json()
    
    print("\n" + "=" * 50)
    print(f"✅ 統合分析完了")
    print(f"📊 処理画像数: {len(results)}")
    print(f"🎯 成功抽出数: {len([r for r in results if r['data_points_count'] > 0])}")
    print(f"📝 OCR検出数: {len([r for r in results if r['ocr_data']['parsed_data'].get('machine_model')])}")
    print(f"📄 HTMLレポート: {html_file}")
    print(f"💾 JSONデータ: {json_file}")
    print("=" * 50)