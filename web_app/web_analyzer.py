#!/usr/bin/env python3
"""
Web環境対応版 パチンコグラフ解析モジュール
ファイルパスを柔軟に扱える設計

Version: 1.0.61 (Build c3d265d)
Last Updated: 2025-06-30
"""

__version__ = "1.0.61"
__build__ = "c3d265d"

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
import platform

# 日本語フォント設定
if platform.system() == 'Darwin':  # macOS
    plt.rcParams['font.family'] = 'Hiragino Sans GB'
else:
    # Windows/Linuxの場合
    plt.rcParams['font.family'] = ['DejaVu Sans', 'sans-serif']

# 日本語が正しく表示されるようにfallbackも設定
plt.rcParams['font.sans-serif'] = ['Hiragino Sans GB', 'Arial Unicode MS', 'Noto Sans CJK JP', 'DejaVu Sans']

class WebCompatibleAnalyzer:
    """Web環境対応の解析クラス"""
    
    def __init__(self, work_dir=None):
        self.work_dir = work_dir or "."
        self.zero_y = 250
        self.target_30k_y = 4
        # グラフの実際の領域に基づいてスケールを計算
        # 0ラインから上下に250ピクセルずつで、±30,000相当
        self.scale = 30000 / 250  # 120玉/ピクセル
        
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
        
        # 非線形スケール用の設定
        self.use_nonlinear_scale = False
        self.scale_points = None  # [(y_position, value), ...]
    
    def set_nonlinear_scale(self, scale_points):
        """非線形スケールを設定
        scale_points: [(y_position, value), ...] の形式で、各グリッドラインの位置と値のペア
        """
        self.use_nonlinear_scale = True
        self.scale_points = sorted(scale_points, key=lambda x: x[0])  # Y位置でソート
    
    def calculate_value_nonlinear(self, y_pixel):
        """非線形スケールを使用してY座標から値を計算"""
        if not self.use_nonlinear_scale or not self.scale_points:
            # 通常の線形計算
            return (self.zero_y - y_pixel) * self.scale
        
        # 非線形補間
        # y_pixelがどの区間にあるかを判定
        for i in range(len(self.scale_points) - 1):
            y1, val1 = self.scale_points[i]
            y2, val2 = self.scale_points[i + 1]
            
            if y1 <= y_pixel <= y2 or y2 <= y_pixel <= y1:
                # この区間で線形補間
                if y1 != y2:
                    ratio = (y_pixel - y1) / (y2 - y1)
                    return val1 + ratio * (val2 - val1)
        
        # 範囲外の場合は最も近い区間で外挿
        if y_pixel < min(self.scale_points, key=lambda x: x[0])[0]:
            # 最上部より上
            y1, val1 = self.scale_points[0]
            y2, val2 = self.scale_points[1]
            if y1 != y2:
                scale = (val2 - val1) / (y2 - y1)
                return val1 + (y_pixel - y1) * scale
        else:
            # 最下部より下
            y1, val1 = self.scale_points[-2]
            y2, val2 = self.scale_points[-1]
            if y1 != y2:
                scale = (val2 - val1) / (y2 - y1)
                return val2 + (y_pixel - y2) * scale
        
        # フォールバック
        return (self.zero_y - y_pixel) * self.scale
    
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
        """グラフ領域の切り抜き（Pattern3: Zero Line Based）"""
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
        
        # オレンジバーの下端を正確に見つける
        if orange_bottom > 0:
            for y in range(orange_bottom, min(orange_bottom + 100, height)):
                if np.sum(orange_mask[y, :]) < width * 0.1 * 255:
                    orange_bottom = y
                    break
        else:
            # デフォルト値を使用
            orange_bottom = 150
        
        # 2. ゼロライン検出（Pattern3の核心部分）
        search_start = orange_bottom + 50
        search_end = min(height - 100, orange_bottom + 400)
        
        best_score = 0
        zero_line_y = (search_start + search_end) // 2
        
        for y in range(search_start, search_end):
            row = gray[y, 100:width-100]
            # 暗い水平線を探す
            darkness = 1.0 - (np.mean(row) / 255.0)
            uniformity = 1.0 - (np.std(row) / 128.0)
            score = darkness * 0.5 + uniformity * 0.5
            
            if score > best_score:
                best_score = score
                zero_line_y = y
        
        # 3. ゼロラインから上下に拡張（Pattern3のアプローチ）
        graph_top = max(orange_bottom + 20, zero_line_y - 250)
        graph_bottom = min(height - 50, zero_line_y + 250)
        graph_left = 100
        graph_right = width - 100
        
        # 4. 切り抜き
        if graph_bottom > graph_top and graph_right > graph_left:
            cropped = img[graph_top:graph_bottom, graph_left:graph_right]
            
            # 保存用：オリジナルサイズで保存
            cropped_path = os.path.join(self.work_dir, f"cropped_{os.path.basename(image_path)}")
            cv2.imwrite(cropped_path, cropped)
            
            # ゼロライン位置を相対座標で保存
            self.zero_y = zero_line_y - graph_top
            
            # BGRフォーマットを確認
            if len(cropped.shape) == 3 and cropped.shape[2] == 3:
                return cropped
            else:
                print(f"Warning: Unexpected image format after crop: {cropped.shape}")
                return None
        
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
        # 画像の有効性チェック
        if img is None or img.size == 0:
            return 'unknown', None
            
        # 画像が3チャンネルか確認
        if len(img.shape) != 3 or img.shape[2] != 3:
            return 'unknown', None
            
        height, width = img.shape[:2]
        
        # 境界チェック
        if x < 2 or x >= width - 2:
            return 'unknown', None
            
        try:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        except Exception as e:
            print(f"Error converting to HSV: {e}")
            return 'unknown', None
        
        # 安全な範囲でカラムを取得
        start_x = max(0, x - 2)
        end_x = min(width, x + 3)
        column_hsv = hsv[:, start_x:end_x, :]
        
        # カラムが空でないことを確認
        if column_hsv.size == 0:
            return 'unknown', None
        
        for color_name, color_range in self.color_ranges.items():
            try:
                mask = cv2.inRange(column_hsv, color_range['lower'], color_range['upper'])
                if cv2.countNonZero(mask) > 10:
                    return color_name, mask
            except Exception as e:
                print(f"Error in color detection for {color_name}: {e}")
                continue
        
        return 'unknown', None
    
    def extract_graph_data(self, img):
        """グラフデータの抽出（production版と同じロジック）"""
        # 文字列（ファイルパス）が渡された場合は画像を読み込む
        if isinstance(img, str):
            img = cv2.imread(img)
            if img is None:
                return [], "なし", self.zero_y
        
        # numpy配列でない場合やサイズが0の場合
        if img is None or not hasattr(img, 'shape') or img.size == 0:
            return [], "なし", self.zero_y
            
        height, width = img.shape[:2]
        
        # サイズチェック
        if width < 10 or height < 10:
            return [], "なし", self.zero_y
        
        # 0ライン検出
        detected_zero = self.detect_zero_line(img)
        if detected_zero != self.zero_y:
            self.zero_y = detected_zero
            self.scale = 30000 / max(1, (self.zero_y - self.target_30k_y))
        
        # HSV変換
        try:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        except:
            return [], "なし", detected_zero
        
        best_result = []
        best_color = "なし"
        max_points = 0
        
        # 各色でデータ抽出を試みる
        for color_name, color_range in self.color_ranges.items():
            try:
                mask = cv2.inRange(hsv, color_range['lower'], color_range['upper'])
                
                data_points = []
                for x in range(0, width, 2):  # production版と同じ2ピクセルステップ
                    col_mask = mask[:, x]
                    colored_pixels = np.where(col_mask > 0)[0]
                    
                    if len(colored_pixels) > 0:
                        avg_y = np.mean(colored_pixels)
                        # 非線形スケールを使用する場合
                        if self.use_nonlinear_scale:
                            value = self.calculate_value_nonlinear(avg_y)
                        else:
                            value = (detected_zero - avg_y) * self.scale
                        # 値を±30,000の範囲にクリップ
                        value = max(-30000, min(30000, value))
                        data_points.append((x, value))
                
                if len(data_points) > max_points:
                    max_points = len(data_points)
                    best_result = data_points
                    best_color = color_name
            except:
                continue
        
        return best_result, best_color, detected_zero
    
    def analyze_values(self, data_points):
        """値の分析（data_pointsは(x, value)のタプルリスト）"""
        if not data_points:
            return {
                'max_value': 0,
                'max_index': 0,
                'min_value': 0,
                'min_index': 0,
                'first_hit_index': -1,
                'first_hit_value': 0,
                'final_value': 0
            }
        
        # タプルから値のリストを抽出
        values = [p[1] for p in data_points]
        
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
    
    def calculate_rotation_metrics(self, data_points, analysis, total_start, graph_width):
        """回転率を計算
        
        Args:
            data_points: グラフデータポイント [(x, value), ...]
            analysis: analyze_values()の結果
            total_start: OCRで読み取った累計スタート（総回転数）
            graph_width: グラフの横幅（ピクセル）
            
        Returns:
            dict: 回転率メトリクス
        """
        if not data_points or not total_start or graph_width <= 0:
            return {
                'spins_per_pixel': 0,
                'first_hit_spins': 0,
                'first_hit_balls': 0,
                'rotation_rate_1': 0,  # 初当たりまでの回転率
                'rotation_rate_2': 0,  # 通常時全体の回転率
                'normal_decline_spins': 0,
                'normal_decline_balls': 0
            }
        
        try:
            # 累計スタートを数値に変換
            total_spins = int(total_start)
            
            # 1ピクセルあたりの回転数
            spins_per_pixel = total_spins / graph_width
            
            # 初当たりまでの計算
            first_hit_spins = 0
            first_hit_balls = 0
            rotation_rate_1 = 0
            
            if analysis['first_hit_index'] > 0:
                # 初当たりまでの回転数
                first_hit_spins = int(analysis['first_hit_index'] * spins_per_pixel)
                # 初当たりまでの使用玉数（マイナス値の絶対値）
                first_hit_balls = abs(analysis['first_hit_value'])
                # 回転率①（1000円 = 250玉）
                # 正しい計算式：(回転数 ÷ 使用玉数) × 250
                if first_hit_balls > 0:
                    rotation_rate_1 = round((first_hit_spins / first_hit_balls) * 250, 1)
            
            # 通常時（下降区間）の回転率計算
            rotation_rate_2 = 0
            normal_decline_spins = 0
            normal_decline_balls = 0
            
            # 下降区間を検出（連続して下降している部分）
            values = [p[1] for p in data_points]
            decline_segments = []
            current_segment = []
            
            for i in range(1, len(values)):
                if values[i] < values[i-1] - 5:  # 5玉以上の下降
                    if not current_segment:
                        current_segment = [i-1]
                    current_segment.append(i)
                else:
                    if len(current_segment) > 10:  # 10点以上の連続下降
                        decline_segments.append(current_segment)
                    current_segment = []
            
            if len(current_segment) > 10:
                decline_segments.append(current_segment)
            
            # 全下降区間の合計を計算
            total_decline_balls = 0
            total_decline_pixels = 0
            
            for segment in decline_segments:
                start_idx = segment[0]
                end_idx = segment[-1]
                # 区間での玉数減少
                balls_decline = values[start_idx] - values[end_idx]
                # 区間のピクセル数（回転数に比例）
                pixels = data_points[end_idx][0] - data_points[start_idx][0]
                
                if balls_decline > 0 and pixels > 0:
                    total_decline_balls += balls_decline
                    total_decline_pixels += pixels
            
            # 通常時の回転率を計算
            if total_decline_balls > 0 and total_decline_pixels > 0:
                normal_decline_spins = int(total_decline_pixels * spins_per_pixel)
                normal_decline_balls = int(total_decline_balls)
                # 正しい計算式：(回転数 ÷ 使用玉数) × 250
                rotation_rate_2 = round((normal_decline_spins / normal_decline_balls) * 250, 1)
            
            return {
                'spins_per_pixel': round(spins_per_pixel, 2),
                'first_hit_spins': first_hit_spins,
                'first_hit_balls': first_hit_balls,
                'rotation_rate_1': rotation_rate_1,
                'rotation_rate_2': rotation_rate_2,
                'normal_decline_spins': normal_decline_spins,
                'normal_decline_balls': normal_decline_balls
            }
            
        except Exception as e:
            print(f"回転率計算エラー: {e}")
            return {
                'spins_per_pixel': 0,
                'first_hit_spins': 0,
                'first_hit_balls': 0,
                'rotation_rate_1': 0,
                'rotation_rate_2': 0,
                'normal_decline_spins': 0,
                'normal_decline_balls': 0
            }
    
    def create_analysis_image(self, cropped_img, data_points, detected_color, detected_zero, analysis, output_path):
        """解析結果の可視化画像作成（production版と同じオーバーレイ形式）"""
        if not data_points:
            return
            
        height, width = cropped_img.shape[:2]
        img_rgb = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB)
        
        # production版と同じく1枚の画像で表示
        fig, ax = plt.subplots(figsize=(20, 14))
        ax.imshow(img_rgb)
        
        # 0ライン（太く明確に）
        ax.axhline(y=detected_zero, color='#2C3E50', linewidth=6, 
                  label=f'基準ライン (0)', alpha=0.9, linestyle='-')
        
        # ±30,000ライン（0ラインを基準に対称配置）
        plus_30k_y = detected_zero - (30000 / self.scale)
        minus_30k_y = detected_zero + (30000 / self.scale)
        
        if plus_30k_y >= 0:
            ax.axhline(y=plus_30k_y, color='#E74C3C', linewidth=4, 
                      label='+30,000', alpha=0.85, linestyle='--')
        if minus_30k_y <= height:
            ax.axhline(y=minus_30k_y, color='#E74C3C', linewidth=4, 
                      label='-30,000', alpha=0.85, linestyle='--')
        
        # 補助グリッドライン
        grid_values = [25000, 20000, 15000, 10000, 5000]
        for value in grid_values:
            plus_y = detected_zero - (value / self.scale)
            minus_y = detected_zero + (value / self.scale)
            
            # グリッドライン個別調整
            if value == 20000:
                plus_adjustment = -1
                minus_adjustment = 1
            else:
                plus_adjustment = 0
                minus_adjustment = 0
            plus_y += plus_adjustment
            minus_y += minus_adjustment
            
            alpha = 0.6 if value >= 20000 else 0.3
            linewidth = 2 if value >= 20000 else 1
            
            if 0 <= plus_y <= height:
                ax.axhline(y=plus_y, color='#3498DB', linewidth=linewidth, 
                          alpha=alpha, linestyle=':')
            
            if 0 <= minus_y <= height:
                ax.axhline(y=minus_y, color='#3498DB', linewidth=linewidth, 
                          alpha=alpha, linestyle=':')
        
        # 抽出されたグラフデータをオーバーレイ
        if data_points:
            x_coords = [p[0] for p in data_points]
            y_coords = [detected_zero - (p[1] / self.scale) for p in data_points]
            values = [p[1] for p in data_points]
            
            # グラフ線を強調表示
            ax.plot(x_coords, y_coords, color='#F39C12', linewidth=4, 
                   alpha=0.9, label=f'データ抽出結果 ({detected_color})')
            
            # 重要ポイントのマーク
            if analysis['max_value'] > 0 and analysis['max_index'] < len(data_points):
                max_point = data_points[analysis['max_index']]
                max_y = detected_zero - (max_point[1] / self.scale)
                ax.plot(max_point[0], max_y, 'o', color='#FFD700', markersize=20, 
                       markeredgecolor='#B8860B', markeredgewidth=3)
                ax.annotate(f'最高値\n{analysis["max_value"]:,}玉', 
                           xy=(max_point[0], max_y),
                           xytext=(30, -30), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.8),
                           fontsize=16, fontweight='bold',
                           arrowprops=dict(arrowstyle='->', color='black', lw=2))
            
            # 初当たりマーク
            if analysis['first_hit_index'] >= 0 and analysis['first_hit_index'] < len(data_points):
                hit_point = data_points[analysis['first_hit_index']]
                hit_y = detected_zero - (hit_point[1] / self.scale)
                ax.plot(hit_point[0], hit_y, 'o', color='#32CD32', markersize=20,
                       markeredgecolor='#228B22', markeredgewidth=3)
                ax.annotate(f'初当たり\n{analysis["first_hit_value"]:,}玉',
                           xy=(hit_point[0], hit_y),
                           xytext=(-50, 30), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', fc='lightgreen', alpha=0.8),
                           fontsize=16, fontweight='bold',
                           arrowprops=dict(arrowstyle='->', color='black', lw=2))
        
        # グラフ設定
        ax.set_xlim(0, width)
        ax.set_ylim(height, 0)
        ax.set_title(f'パチンコグラフ解析結果 - {detected_color}検出', fontsize=24, pad=20)
        ax.legend(loc='upper right', fontsize=14)
        ax.grid(False)
        
        # 余白を最小化
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
    
    def process_single_image(self, image_path, output_dir):
        """単一画像の処理"""
        try:
            print(f"Processing: {image_path}")
            
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
            
            print(f"Cropped image shape: {cropped.shape}")
            
            # 切り抜いた画像を保存（デバッグ用）
            base_name = Path(image_path).stem
            cropped_path = os.path.join(output_dir, f"cropped_{base_name}.png")
            cv2.imwrite(cropped_path, cropped)
            print(f"Saved cropped image to: {cropped_path}")
            
            # データ抽出（production版形式）
            data_points, detected_color, detected_zero = self.extract_graph_data(cropped)
            print(f"Extracted {len(data_points)} data points, color: {detected_color}")
            
            if not data_points or len(data_points) < 10:
                print(f"Warning: Insufficient data extracted from {image_path}")
                error_result = {
                    'filename': os.path.basename(image_path),
                    'error': f'データ抽出が不十分（{len(data_points)}点）',
                    'analysis': self.analyze_values(data_points),
                    'data_points': len(data_points),
                    'visualization': None,
                    'detected_color': detected_color
                }
                return error_result
            
            # 分析
            analysis = self.analyze_values(data_points)
            
            # 結果画像作成（production版と同じファイル名）
            vis_path = os.path.join(output_dir, f"professional_analysis_{base_name}.png")
            self.create_analysis_image(cropped, data_points, detected_color, detected_zero, analysis, vis_path)
            
            # 結果を保存
            result = {
                'filename': os.path.basename(image_path),
                'analysis': analysis,
                'data_points': len(data_points),
                'visualization': os.path.basename(vis_path),
                'detected_color': detected_color,
                'error': None,
                'cropped_image': os.path.basename(cropped_path)
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
                            <tr>
                                <td>検出色</td>
                                <td>{result.get('detected_color', 'なし')}</td>
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
            <p style="font-size: 0.8em; opacity: 0.7;">Version {__version__} (Build {__build__})</p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path