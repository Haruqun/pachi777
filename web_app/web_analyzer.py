#!/usr/bin/env python3
"""
Web環境対応版 パチンコグラフ解析モジュール
ファイルパスを柔軟に扱える設計
"""

import os
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')  # GUI不要のバックエンド
import matplotlib.pyplot as plt
from PIL import Image, ImageEnhance
import json
from datetime import datetime
from pathlib import Path
import re
import matplotlib.font_manager as fm

class WebCompatibleAnalyzer:
    """Web環境対応の解析クラス"""
    
    def __init__(self, work_dir=None):
        self.work_dir = work_dir or "."
        self.zero_y = 250
        self.target_30k_y = 4
        self.scale = 30000 / (self.zero_y - self.target_30k_y)
        
        # 10色対応の色検出範囲
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
        self.setup_font()
    
    def setup_font(self):
        """フォント設定"""
        try:
            # 日本語フォントの検索
            font_candidates = [
                'Noto Sans CJK JP',
                'Noto Sans JP',
                'TakaoGothic',
                'IPAGothic',
                'DejaVu Sans'
            ]
            
            self.font_path = None
            for font_name in font_candidates:
                try:
                    self.font_path = fm.findfont(fm.FontProperties(family=font_name))
                    if os.path.exists(self.font_path):
                        break
                except:
                    continue
            
            if self.font_path:
                matplotlib.rcParams['font.family'] = [fm.FontProperties(fname=self.font_path).get_name()]
        except:
            # フォント設定失敗時はデフォルトを使用
            pass
    
    def crop_graph_area(self, image_path):
        """グラフ領域の切り抜き"""
        img = cv2.imread(image_path)
        if img is None:
            return None
            
        height, width = img.shape[:2]
        
        # オレンジ色のバーを検出してグラフ領域を特定
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        orange_lower = np.array([10, 100, 100])
        orange_upper = np.array([25, 255, 255])
        mask = cv2.inRange(hsv, orange_lower, orange_upper)
        
        # Y方向のプロジェクション
        y_projection = np.sum(mask, axis=1)
        
        # オレンジバーの位置を検出
        threshold = width * 0.3
        orange_bars = []
        in_bar = False
        start_y = 0
        
        for y, count in enumerate(y_projection):
            if count > threshold and not in_bar:
                in_bar = True
                start_y = y
            elif count <= threshold and in_bar:
                in_bar = False
                if y - start_y > 5:
                    orange_bars.append((start_y, y))
        
        if len(orange_bars) >= 2:
            top_bar = orange_bars[0]
            bottom_bar = orange_bars[-1]
            
            # グラフ領域の切り抜き（最適サイズ: 689×558px）
            crop_top = top_bar[1] + 10
            crop_bottom = bottom_bar[0] - 10
            crop_left = int(width * 0.15)
            crop_right = int(width * 0.85)
            
            cropped = img[crop_top:crop_bottom, crop_left:crop_right]
            
            # 最適サイズにリサイズ
            target_width = 689
            target_height = 558
            cropped = cv2.resize(cropped, (target_width, target_height), interpolation=cv2.INTER_CUBIC)
            
            return cropped
        
        return None
    
    def detect_zero_line(self, img):
        """0ライン自動検出"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        search_top = height // 3
        search_bottom = height * 2 // 3
        search_region = gray[search_top:search_bottom, :]
        
        edges = cv2.Canny(search_region, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=int(width*0.3))
        
        zero_candidates = []
        
        if lines is not None:
            for rho, theta in lines[0]:
                if abs(theta) < 0.1 or abs(theta - np.pi) < 0.1:
                    y = int(rho / np.sin(theta)) if abs(np.sin(theta)) > 0.1 else search_top
                    if 0 < y < search_region.shape[0]:
                        zero_candidates.append(search_top + y)
        
        for y in range(search_top, search_bottom):
            row = gray[y, :]
            dark_pixels = np.sum(row < 100)
            if dark_pixels > width * 0.7:
                zero_candidates.append(y)
        
        if zero_candidates:
            detected = int(np.median(zero_candidates))
            return detected
        else:
            return self.zero_y
    
    def detect_graph_color(self, img, x):
        """グラフの色を検出"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        height = img.shape[0]
        
        column_hsv = hsv[:, x-2:x+3, :]
        
        for color_name, color_range in self.color_ranges.items():
            mask = cv2.inRange(column_hsv, color_range['lower'], color_range['upper'])
            if cv2.countNonZero(mask) > 10:
                return color_name, mask
        
        return 'unknown', None
    
    def extract_graph_data(self, img):
        """グラフデータの抽出"""
        height, width = img.shape[:2]
        
        # 0ライン検出
        detected_zero = self.detect_zero_line(img)
        if detected_zero != self.zero_y:
            self.zero_y = detected_zero
            self.scale = 30000 / (self.zero_y - self.target_30k_y)
        
        # データ抽出
        values = []
        for x in range(0, width, 5):  # 5ピクセルおきにサンプリング
            color_name, mask = self.detect_graph_color(img, x)
            
            if mask is not None:
                y_coords = np.where(mask[:, mask.shape[1]//2] > 0)[0]
                if len(y_coords) > 0:
                    graph_y = int(np.mean(y_coords))
                    value = (self.zero_y - graph_y) * self.scale
                    values.append(value)
                else:
                    values.append(0)
            else:
                values.append(0)
        
        return values
    
    def analyze_values(self, values):
        """値の分析"""
        if not values:
            return {
                'max_value': 0,
                'max_index': 0,
                'min_value': 0,
                'min_index': 0,
                'first_hit_index': -1,
                'final_value': 0
            }
        
        # 最大値・最小値
        max_val = max(values)
        max_idx = values.index(max_val)
        min_val = min(values)
        min_idx = values.index(min_val)
        
        # グラフが常に負の場合の処理
        if max_val < 0:
            max_val = 0
            max_idx = 0
        
        # 初当たり検出
        first_hit_idx = -1
        min_payout = 100
        for i in range(1, min(len(values)-2, 150)):
            current_increase = values[i+1] - values[i]
            if current_increase > min_payout:
                if values[i+2] >= values[i+1] - 50:
                    if values[i] < 2000:
                        first_hit_idx = i
                        break
        
        return {
            'max_value': int(max_val),
            'max_index': max_idx,
            'min_value': int(min_val),
            'min_index': min_idx,
            'first_hit_index': first_hit_idx,
            'final_value': int(values[-1]) if values else 0
        }
    
    def create_analysis_image(self, cropped_img, values, analysis, output_path):
        """解析結果の可視化画像作成"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 2]})
        
        # グラフ画像表示
        ax1.imshow(cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB))
        ax1.set_title('グラフ画像', fontsize=16)
        ax1.axis('off')
        
        # データプロット
        x_points = list(range(len(values)))
        ax2.plot(x_points, values, color='blue', linewidth=2, label='玉数推移')
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax2.grid(True, alpha=0.3)
        
        # 重要ポイントのマーク
        if analysis['max_value'] > 0:
            ax2.plot(analysis['max_index'], analysis['max_value'], 'ro', markersize=10)
            ax2.annotate(f'最高値: {analysis["max_value"]:,}玉', 
                        xy=(analysis['max_index'], analysis['max_value']),
                        xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7))
        
        if analysis['first_hit_index'] >= 0:
            ax2.plot(analysis['first_hit_index'], values[analysis['first_hit_index']], 'go', markersize=10)
            ax2.annotate(f'初当たり', 
                        xy=(analysis['first_hit_index'], values[analysis['first_hit_index']]),
                        xytext=(10, -20), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.5', fc='lightgreen', alpha=0.7))
        
        ax2.set_xlabel('回転数', fontsize=12)
        ax2.set_ylabel('差玉数', fontsize=12)
        ax2.set_title('抽出データ', fontsize=16)
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def process_single_image(self, image_path, output_dir):
        """単一画像の処理"""
        try:
            # グラフ領域の切り抜き
            cropped = self.crop_graph_area(image_path)
            if cropped is None:
                return None
            
            # データ抽出
            values = self.extract_graph_data(cropped)
            
            # 分析
            analysis = self.analyze_values(values)
            
            # 結果画像作成
            base_name = Path(image_path).stem
            vis_path = os.path.join(output_dir, f"{base_name}_analysis.png")
            self.create_analysis_image(cropped, values, analysis, vis_path)
            
            # 結果を保存
            result = {
                'filename': os.path.basename(image_path),
                'analysis': analysis,
                'data_points': len(values),
                'visualization': os.path.basename(vis_path)
            }
            
            self.results.append(result)
            return result
            
        except Exception as e:
            print(f"Error processing {image_path}: {str(e)}")
            return None
    
    def generate_html_report(self, output_path):
        """HTMLレポート生成"""
        timestamp = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
        
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>パチンコグラフ解析レポート - {timestamp}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans JP', sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .summary {{
            background: #f8f9fa;
            padding: 30px;
            margin: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
        }}
        
        .summary h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.8rem;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.12);
        }}
        
        .stat-icon {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #333;
            margin: 10px 0;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9rem;
        }}
        
        .analysis-section {{
            padding: 30px;
        }}
        
        .analysis-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 30px;
            margin-top: 30px;
        }}
        
        .analysis-card {{
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.08);
        }}
        
        .analysis-card img {{
            width: 100%;
            height: auto;
        }}
        
        .analysis-info {{
            padding: 20px;
        }}
        
        .analysis-info h3 {{
            color: #333;
            margin-bottom: 15px;
        }}
        
        .result-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        
        .result-table th,
        .result-table td {{
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        
        .result-table th {{
            background: #f5f5f5;
            font-weight: 600;
        }}
        
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
        
        .footer {{
            background: #333;
            color: white;
            text-align: center;
            padding: 30px;
            margin-top: 50px;
        }}
        
        @media (max-width: 768px) {{
            .analysis-grid {{
                grid-template-columns: 1fr;
            }}
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-chart-line"></i> パチンコグラフ解析レポート</h1>
            <p>AI高精度解析システム - 処理日時: {timestamp}</p>
        </div>
        
        <div class="summary">
            <h2><i class="fas fa-clipboard-list"></i> 処理結果サマリー</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-images"></i></div>
                    <div class="stat-value">{len(self.results)}</div>
                    <div class="stat-label">処理画像数</div>
                </div>
"""
        
        # 全体の統計を計算
        if self.results:
            all_max_values = [r['analysis']['max_value'] for r in self.results]
            all_min_values = [r['analysis']['min_value'] for r in self.results]
            overall_max = max(all_max_values)
            overall_min = min(all_min_values)
            success_count = sum(1 for r in self.results if r['analysis']['first_hit_index'] >= 0)
            
            html_content += f"""
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-arrow-up"></i></div>
                    <div class="stat-value positive">+{overall_max:,}</div>
                    <div class="stat-label">全体最高値</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-arrow-down"></i></div>
                    <div class="stat-value negative">{overall_min:,}</div>
                    <div class="stat-label">全体最低値</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-trophy"></i></div>
                    <div class="stat-value">{success_count}</div>
                    <div class="stat-label">初当たり検出数</div>
                </div>
"""
        
        html_content += """
            </div>
        </div>
        
        <div class="analysis-section">
            <h2><i class="fas fa-chart-bar"></i> 個別解析結果</h2>
            <div class="analysis-grid">
"""
        
        # 個別結果
        for result in self.results:
            analysis = result['analysis']
            max_class = 'positive' if analysis['max_value'] > 0 else ''
            
            html_content += f"""
                <div class="analysis-card">
                    <img src="images/{result['visualization']}" alt="{result['filename']}">
                    <div class="analysis-info">
                        <h3>{result['filename']}</h3>
                        <table class="result-table">
                            <tr>
                                <th>項目</th>
                                <th>値</th>
                            </tr>
                            <tr>
                                <td>最高値</td>
                                <td class="{max_class}">{analysis['max_value']:,}玉</td>
                            </tr>
                            <tr>
                                <td>最低値</td>
                                <td class="negative">{analysis['min_value']:,}玉</td>
                            </tr>
                            <tr>
                                <td>最終値</td>
                                <td>{analysis['final_value']:,}玉</td>
                            </tr>
                            <tr>
                                <td>初当たり</td>
                                <td>{'検出' if analysis['first_hit_index'] >= 0 else '未検出'}</td>
                            </tr>
                        </table>
                    </div>
                </div>
"""
        
        html_content += """
            </div>
        </div>
        
        <div class="footer">
            <p><i class="fas fa-lock"></i> セキュア処理 | <i class="fas fa-rocket"></i> 高速解析 | <i class="fas fa-chart-line"></i> 高精度</p>
            <p>© 2024 PPタウン様専用システム | 開発: ファイブナインデザイン</p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path