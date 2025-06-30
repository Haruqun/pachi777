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
        """グラフ領域の切り抜き（production版と同じロジック）"""
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Could not read image {image_path}")
            return None
            
        height, width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 1. オレンジバーを検出
        orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
        orange_bottom = 0
        
        # オレンジバーの最下端を検出
        for y in range(height//2):
            if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
                orange_bottom = y
        
        if orange_bottom == 0:
            print(f"Warning: Could not detect orange bar in {image_path}")
            # デフォルト値を使用
            orange_bottom = int(height * 0.1)
        
        # 2. Y軸ラベル領域を推定
        y_label_top = orange_bottom + 50  # デフォルト
        search_area = gray[orange_bottom+20:min(orange_bottom+200, height), :width//3]
        
        if search_area.size > 0:
            for y in range(search_area.shape[0]):
                row_variance = np.var(search_area[y, :])
                if row_variance > 500:  # テキストがある
                    y_label_top = orange_bottom + 20 + y
                    break
        
        # 3. グラフの境界を定義（固定オフセット）
        graph_top = y_label_top + 40 + 30 - 200
        graph_left = 90 + 30 + 2  # 122px
        graph_right = width - 90 + 40 - 100  # width - 150px
        
        # 境界チェック
        graph_top = max(0, graph_top)
        graph_left = max(0, graph_left)
        graph_right = min(width, graph_right)
        
        # 4. ゼロラインを検出
        if graph_top < height and graph_right > graph_left:
            graph_region = gray[graph_top:min(graph_top+600, height), graph_left:graph_right]
            
            best_zero_y = 250  # デフォルト
            if graph_region.size > 0:
                best_score = -1
                
                for y in range(100, min(500, graph_region.shape[0]-100)):
                    if y < graph_region.shape[0]:
                        row = graph_region[y, :]
                        darkness = 1.0 - (np.mean(row) / 255.0)
                        uniformity = 1.0 - (np.std(row) / 128.0)
                        score = darkness * 0.5 + uniformity * 0.5
                        
                        if score > best_score:
                            best_score = score
                            best_zero_y = y
        else:
            best_zero_y = 250
        
        # 5. グラフの下端を決定（ゼロラインから+250px）
        graph_bottom = graph_top + best_zero_y + 250
        graph_bottom = min(graph_bottom, height)
        
        # 6. 切り抜き
        if graph_bottom > graph_top and graph_right > graph_left:
            cropped = img[graph_top:graph_bottom, graph_left:graph_right]
            
            # サイズチェック
            if cropped.shape[0] > 10 and cropped.shape[1] > 10:
                # 最適サイズ（689×558px）にリサイズ
                target_width = 689
                target_height = 558
                cropped = cv2.resize(cropped, (target_width, target_height), interpolation=cv2.INTER_CUBIC)
                
                # ゼロライン位置を更新（リサイズ後）
                resize_ratio = target_height / (graph_bottom - graph_top)
                self.zero_y = int(best_zero_y * resize_ratio)
                
                return cropped
        
        print(f"Warning: Invalid crop dimensions for {image_path}")
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
        height, width = img.shape[:2]
        
        # 境界チェック
        if x < 2 or x >= width - 2:
            return 'unknown', None
            
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 安全な範囲でカラムを取得
        start_x = max(0, x - 2)
        end_x = min(width, x + 3)
        column_hsv = hsv[:, start_x:end_x, :]
        
        # カラムが空でないことを確認
        if column_hsv.size == 0:
            return 'unknown', None
        
        for color_name, color_range in self.color_ranges.items():
            mask = cv2.inRange(column_hsv, color_range['lower'], color_range['upper'])
            if cv2.countNonZero(mask) > 10:
                return color_name, mask
        
        return 'unknown', None
    
    def extract_graph_data(self, img):
        """グラフデータの抽出"""
        if img is None or img.size == 0:
            return []
            
        height, width = img.shape[:2]
        
        # サイズチェック
        if width < 10 or height < 10:
            return []
        
        # 0ライン検出
        detected_zero = self.detect_zero_line(img)
        if detected_zero != self.zero_y:
            self.zero_y = detected_zero
            self.scale = 30000 / max(1, (self.zero_y - self.target_30k_y))
        
        # データ抽出
        values = []
        step = max(1, width // 200)  # 最大200点程度にサンプリング
        
        for x in range(0, width, step):
            if x >= width:
                break
                
            color_name, mask = self.detect_graph_color(img, x)
            
            if mask is not None and mask.size > 0:
                # マスクの中央列を安全に取得
                col_idx = min(mask.shape[1]//2, mask.shape[1]-1)
                if col_idx >= 0 and col_idx < mask.shape[1]:
                    y_coords = np.where(mask[:, col_idx] > 0)[0]
                    if len(y_coords) > 0:
                        graph_y = int(np.mean(y_coords))
                        value = (self.zero_y - graph_y) * self.scale
                        values.append(value)
                    else:
                        values.append(0)
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
                'first_hit_value': 0,
                'final_value': 0
            }
        
        # 最大値・最小値
        max_val = max(values)
        min_val = min(values)
        current_val = values[-1]
        
        # 最初の数点は無視して、安定した部分から最高値を探す
        if len(values) > 10:
            stable_values = values[5:]  # 最初の5点を除外
            max_val = max(stable_values)
            # 最高値が負の場合は0に最も近い値を探す
            if max_val < 0:
                # グラフが一度もプラスにならない場合は最大値を0とする
                max_val = 0
                max_idx = 0  # インデックスも0に設定
            else:
                max_idx = values.index(max_val)
        else:
            max_idx = values.index(max_val)
            if max_val < 0:
                max_val = 0
                max_idx = 0
        
        min_idx = values.index(min_val)
        
        # 初当たり検出（production版と同じロジック）
        first_hit_idx = -1
        first_hit_val = 0
        min_payout = 100  # 最低払い出し玉数を100に変更
        
        # 方法1: シンプルな増加検出
        for i in range(1, min(len(values)-2, 150)):  # 最大150点まで探索
            current_increase = values[i+1] - values[i]
            
            # 100玉以上の増加を検出
            if current_increase > min_payout:
                # 次の点も上昇または維持していることを確認
                if values[i+2] >= values[i+1] - 50:
                    # 重要：初当たりは必ずマイナス値でなければならない
                    if values[i] < 0:  # マイナス値のみを初当たりとして検出
                        first_hit_idx = i
                        first_hit_val = values[i]
                        break
        
        # 方法2: 通常パターン（減少→上昇）の検出
        if first_hit_idx == -1:
            window_size = 5
            for i in range(window_size, len(values)-1):
                # 過去の傾向を計算
                past_window = values[max(0, i-window_size):i]
                if len(past_window) >= 2:
                    avg_slope = (past_window[-1] - past_window[0]) / len(past_window)
                    
                    # 現在の変化
                    current_change = values[i+1] - values[i]
                    
                    # 下降傾向から急上昇への転換を検出
                    if avg_slope < -20 and current_change > min_payout:
                        if values[i] < 0:  # マイナス値のみ
                            first_hit_idx = i
                            first_hit_val = values[i]
                            break
        
        return {
            'max_value': int(max_val),
            'max_index': max_idx,
            'min_value': int(min_val),
            'min_index': min_idx,
            'first_hit_index': first_hit_idx,
            'first_hit_value': int(first_hit_val),
            'final_value': int(current_val)
        }
    
    def create_analysis_image(self, cropped_img, values, analysis, output_path):
        """解析結果の可視化画像作成（グリッドライン付き）"""
        height, width = cropped_img.shape[:2]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [3, 2]})
        
        # グラフ画像表示（グリッドライン付き）
        ax1.imshow(cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB))
        ax1.set_title('グラフ画像（解析グリッド付き）', fontsize=16)
        
        # グリッドラインを描画
        # 0ライン
        ax1.axhline(y=self.zero_y, color='red', linewidth=3, alpha=0.8, label='0ライン')
        
        # ±30,000ライン（1px上調整）
        plus_30k_y = self.zero_y - (30000 / self.scale) - 1
        minus_30k_y = self.zero_y + (30000 / self.scale) - 1
        if 0 <= plus_30k_y <= height:
            ax1.axhline(y=plus_30k_y, color='#E74C3C', linewidth=2.5, 
                       label='+30,000', alpha=0.85, linestyle='--')
        if 0 <= minus_30k_y <= height:
            ax1.axhline(y=minus_30k_y, color='#E74C3C', linewidth=2.5, 
                       label='-30,000', alpha=0.85, linestyle='--')
        
        # 補助グリッドライン
        grid_values = [25000, 20000, 15000, 10000, 5000]
        for value in grid_values:
            plus_y = self.zero_y - (value / self.scale)
            minus_y = self.zero_y + (value / self.scale)
            
            # グリッドライン個別調整（production版と同じ）
            if value == 20000:
                plus_adjustment = -1  # +20000ラインは2px上方向に調整
                minus_adjustment = 1  # -20000ラインは2px下方向に調整
            else:
                plus_adjustment = 0
                minus_adjustment = 0
            plus_y += plus_adjustment
            minus_y += minus_adjustment
            
            alpha = 0.6 if value >= 20000 else 0.3
            linewidth = 2 if value >= 20000 else 1
            
            if 0 <= plus_y <= height:
                ax1.axhline(y=plus_y, color='#3498DB', linewidth=linewidth, 
                          alpha=alpha, linestyle=':')
            
            if 0 <= minus_y <= height:
                ax1.axhline(y=minus_y, color='#3498DB', linewidth=linewidth, 
                          alpha=alpha, linestyle=':')
        
        ax1.set_xlim(0, width)
        ax1.set_ylim(height, 0)
        ax1.grid(False)
        
        # データプロット
        x_points = list(range(len(values)))
        ax2.plot(x_points, values, color='#F39C12', linewidth=3, label='玉数推移', alpha=0.9)
        ax2.axhline(y=0, color='red', linestyle='-', linewidth=2, alpha=0.8)
        
        # グリッドライン（データプロット側）
        for value in [30000, 20000, 10000, -10000, -20000, -30000]:
            ax2.axhline(y=value, color='gray', linestyle=':', linewidth=1, alpha=0.5)
        
        ax2.grid(True, alpha=0.3, which='both')
        
        # 重要ポイントのマーク
        if analysis['max_value'] > 0:
            ax2.plot(analysis['max_index'], analysis['max_value'], 'ro', markersize=12)
            ax2.annotate(f'最高値: {analysis["max_value"]:,}玉', 
                        xy=(analysis['max_index'], analysis['max_value']),
                        xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.8),
                        fontsize=11, fontweight='bold')
        
        if analysis['first_hit_index'] >= 0:
            ax2.plot(analysis['first_hit_index'], analysis['first_hit_value'], 'go', markersize=12)
            ax2.annotate(f'初当たり: {analysis["first_hit_value"]:,}玉', 
                        xy=(analysis['first_hit_index'], analysis['first_hit_value']),
                        xytext=(10, -30), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.5', fc='lightgreen', alpha=0.8),
                        fontsize=11, fontweight='bold')
        
        # 最終値マーク
        final_idx = len(values) - 1
        ax2.plot(final_idx, analysis['final_value'], 'ko', markersize=8)
        ax2.annotate(f'最終: {analysis["final_value"]:,}玉', 
                    xy=(final_idx, analysis['final_value']),
                    xytext=(-80, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.5', fc='lightblue', alpha=0.8),
                    fontsize=10)
        
        ax2.set_xlabel('回転数 (スピン)', fontsize=12)
        ax2.set_ylabel('差玉数', fontsize=12)
        ax2.set_title('抽出データ分析', fontsize=16)
        ax2.legend(loc='best', fontsize=11)
        
        # Y軸の範囲を適切に設定
        y_margin = 5000
        y_min = min(min(values), -30000) - y_margin
        y_max = max(max(values), 30000) + y_margin
        ax2.set_ylim(y_min, y_max)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
    
    def process_single_image(self, image_path, output_dir):
        """単一画像の処理"""
        try:
            # グラフ領域の切り抜き
            cropped = self.crop_graph_area(image_path)
            if cropped is None:
                print(f"Warning: Could not crop graph area from {image_path}")
                # エラー情報を含む結果を返す
                error_result = {
                    'filename': os.path.basename(image_path),
                    'error': 'グラフ領域の検出に失敗',
                    'analysis': {
                        'max_value': 0,
                        'max_index': 0,
                        'min_value': 0,
                        'min_index': 0,
                        'first_hit_index': -1,
                        'first_hit_value': 0,
                        'final_value': 0
                    },
                    'data_points': 0,
                    'visualization': None
                }
                return error_result
            
            # データ抽出
            values = self.extract_graph_data(cropped)
            if not values or len(values) < 10:
                print(f"Warning: Insufficient data extracted from {image_path}")
                error_result = {
                    'filename': os.path.basename(image_path),
                    'error': 'データ抽出が不十分',
                    'analysis': self.analyze_values(values),
                    'data_points': len(values) if values else 0,
                    'visualization': None
                }
                return error_result
            
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
                'visualization': os.path.basename(vis_path),
                'error': None
            }
            
            self.results.append(result)
            return result
            
        except Exception as e:
            print(f"Error processing {image_path}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # エラー情報を含む結果を返す
            error_result = {
                'filename': os.path.basename(image_path),
                'error': f'処理エラー: {str(e)}',
                'analysis': {
                    'max_value': 0,
                    'max_index': 0,
                    'min_value': 0,
                    'min_index': 0,
                    'first_hit_index': -1,
                    'first_hit_value': 0,
                    'final_value': 0
                },
                'data_points': 0,
                'visualization': None
            }
            return error_result
    
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