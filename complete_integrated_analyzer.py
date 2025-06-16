#!/usr/bin/env python3
"""
統合パチンコ分析ツール - 完全版
- 画像の自動切り抜き
- グラフデータ抽出  
- 回転数・ベース分析
- 全自動処理対応
"""

import os
import sys
from datetime import datetime
import json
import shutil

# 基本ライブラリ
from PIL import Image
import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.signal import find_peaks
import re

# オプショナルライブラリ
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    PLOT_AVAILABLE = True
except ImportError:
    PLOT_AVAILABLE = False


class IntegratedPachinkoAnalyzer:
    """統合パチンコ分析システム"""
    
    def __init__(self):
        self.current_step = 0
        self.total_steps = 0
        self.results = {}
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbols = {
            "INFO": "📋", 
            "SUCCESS": "✅", 
            "WARNING": "⚠️", 
            "ERROR": "❌", 
            "PROGRESS": "🔄"
        }
        print(f"{symbols.get(level, '📋')} [{timestamp}] {message}")
    
    def progress(self, message):
        """進捗表示"""
        self.current_step += 1
        progress_bar = f"[{self.current_step}/{self.total_steps}]"
        self.log(f"{progress_bar} {message}", "PROGRESS")
    
    # =====================================
    # 1. 画像切り抜き機能
    # =====================================
    
    def hex_to_rgb(self, hex_color):
        """16進数カラーコードをRGBに変換"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def find_graph_by_smart_analysis(self, image_path, target_color="#f5ece7"):
        """スマート分析でグラフエリアを検出"""
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        target_rgb = np.array(self.hex_to_rgb(target_color))
        graph_rows = []
        
        # 各行について、ターゲット色の密度を計算
        for y in range(height):
            row = img_array[y, :, :3]
            distances = np.sqrt(np.sum((row - target_rgb) ** 2, axis=1))
            target_pixels = np.sum(distances <= 15)
            density = target_pixels / width
            
            if density > 0.1:
                graph_rows.append((y, density, target_pixels))
        
        if not graph_rows:
            return None
        
        # 連続するグラフエリアを見つける
        graph_rows.sort(key=lambda x: x[0])
        
        best_region = None
        current_region = []
        max_region_size = 0
        
        for y, density, pixels in graph_rows:
            if not current_region or y - current_region[-1][0] <= 5:
                current_region.append((y, density, pixels))
            else:
                if len(current_region) > max_region_size:
                    max_region_size = len(current_region)
                    best_region = current_region.copy()
                current_region = [(y, density, pixels)]
        
        if len(current_region) > max_region_size:
            best_region = current_region
        
        if not best_region:
            return None
        
        # 境界決定
        top = max(0, best_region[0][0] - 20)
        bottom = min(height - 1, best_region[-1][0] + 20)
        
        # 左右境界
        graph_cols = []
        for x in range(width):
            col = img_array[top:bottom, x, :3]
            distances = np.sqrt(np.sum((col - target_rgb) ** 2, axis=1))
            target_pixels = np.sum(distances <= 15)
            density = target_pixels / (bottom - top)
            
            if density > 0.05:
                graph_cols.append((x, density, target_pixels))
        
        if not graph_cols:
            left = int(width * 0.05)
            right = int(width * 0.95)
        else:
            graph_cols.sort(key=lambda x: x[0])
            left = max(0, graph_cols[0][0] - 20)
            right = min(width - 1, graph_cols[-1][0] + 20)
        
        return (left, top, right, bottom)
    
    def find_graph_by_layout_analysis(self, image_path):
        """レイアウト分析でグラフエリアを推定"""
        img = Image.open(image_path)
        width, height = img.size
        
        if height > 2000:
            left = int(width * 0.07)
            right = int(width * 0.93)
            top = int(height * 0.28)
            bottom = int(height * 0.59)
        else:
            left = int(width * 0.08)
            right = int(width * 0.92)
            top = int(height * 0.30)
            bottom = int(height * 0.65)
        
        return (left, top, right, bottom)
    
    def crop_graph_auto(self, image_path, output_path):
        """自動グラフ切り抜き"""
        try:
            # 複数手法を試す
            methods = [
                ("スマート分析", self.find_graph_by_smart_analysis),
                ("レイアウト分析", self.find_graph_by_layout_analysis)
            ]
            
            results = []
            img = Image.open(image_path)
            
            for method_name, method_func in methods:
                try:
                    bounds = method_func(image_path)
                    if bounds:
                        left, top, right, bottom = bounds
                        area = (right - left) * (bottom - top)
                        results.append((method_name, bounds, area))
                except Exception:
                    continue
            
            if not results:
                return False
            
            # 中央値の結果を選択
            results.sort(key=lambda x: x[2])
            chosen = results[len(results)//2] if len(results) >= 2 else results[0]
            
            # 切り抜き実行
            chosen_bounds = chosen[1]
            cropped_img = img.crop(chosen_bounds)
            cropped_img.save(output_path)
            
            return True
            
        except Exception as e:
            self.log(f"切り抜きエラー: {e}", "ERROR")
            return False
    
    # =====================================
    # 2. グラフデータ抽出機能
    # =====================================
    
    def extract_max_value_from_graph(self, image_path):
        """OCRで最大値を抽出"""
        if not OCR_AVAILABLE:
            return None
        
        try:
            img = Image.open(image_path)
            width, height = img.size
            bottom_area = img.crop((0, height * 0.7, width, height))
            
            text = pytesseract.image_to_string(bottom_area, lang='jpn+eng', config='--psm 6')
            
            # パターン検索
            max_patterns = [
                r'最大値[：:]\s*(\d{1,6})',
                r'最高値[：:]\s*(\d{1,6})',
                r'max[：:]\s*(\d{1,6})',
                r'MAX[：:]\s*(\d{1,6})',
                r'最大[：:]\s*(\d{1,6})'
            ]
            
            for pattern in max_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    return float(matches[0])
            
            # 数値のみ検索
            numbers = re.findall(r'\d{3,6}', text)
            valid_numbers = [float(num) for num in numbers if 100 <= float(num) <= 100000]
            
            return max(valid_numbers) if valid_numbers else None
            
        except Exception:
            return None
    
    def detect_pink_line(self, image_path, tolerance=40):
        """ピンク線検出"""
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        # ピンク色検出
        pink_colors = ["#fe17ce", "#ff1493", "#ff69b4", "#e91e63"]
        combined_mask = np.zeros((height, width), dtype=bool)
        
        for color in pink_colors:
            target_rgb = np.array(self.hex_to_rgb(color))
            reshaped = img_array[:, :, :3].reshape(-1, 3).astype(np.float64)
            distances = np.sqrt(np.sum((reshaped - target_rgb) ** 2, axis=1))
            mask = distances <= tolerance
            mask_2d = mask.reshape(height, width)
            combined_mask = combined_mask | mask_2d
        
        # ノイズ除去
        cleaned_mask = ndimage.binary_opening(combined_mask, structure=np.ones((2,2)))
        cleaned_mask = ndimage.binary_closing(cleaned_mask, structure=np.ones((3,3)))
        
        return cleaned_mask if np.sum(cleaned_mask) >= 50 else None
    
    def extract_data_points(self, mask):
        """データポイント抽出"""
        height, width = mask.shape
        data_points = []
        
        for x in range(width):
            column = mask[:, x]
            y_coords = np.where(column)[0]
            
            if len(y_coords) > 0:
                y = int(np.median(y_coords))
                data_points.append((x, y))
        
        return data_points
    
    def detect_zero_line(self, image_path):
        """ゼロライン検出"""
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        gray = np.mean(img_array[:, :, :3], axis=2)
        line_scores = []
        
        for y in range(height):
            row = gray[y, :]
            mean_val = np.mean(row)
            min_val = np.min(row)
            std_val = np.std(row)
            
            darkness_score = (255 - mean_val) / 255
            uniformity_score = 1 / (1 + std_val)
            min_darkness_score = (255 - min_val) / 255
            
            total_score = darkness_score * 0.4 + uniformity_score * 0.3 + min_darkness_score * 0.3
            line_scores.append((y, total_score, mean_val))
        
        # 中央付近を優先
        center_y = height // 2
        best_lines = sorted(line_scores, key=lambda x: x[1], reverse=True)[:5]
        center_lines = [line for line in best_lines if abs(line[0] - center_y) < height * 0.3]
        
        zero_line = center_lines[0] if center_lines else best_lines[0]
        return zero_line[0]
    
    def convert_with_pixel_ratio(self, points, zero_line_y, max_value):
        """座標変換"""
        if not points or max_value is None:
            return []
        
        y_coords = [p[1] for p in points]
        graph_top = min(y_coords)
        graph_bottom = max(y_coords)
        
        up_distance = zero_line_y - graph_top
        down_distance = graph_bottom - zero_line_y
        
        if up_distance > 0:
            estimated_min = -max_value * (down_distance / up_distance)
        else:
            estimated_min = -max_value
        
        converted_points = []
        for x_pixel, y_pixel in points:
            distance_from_zero = y_pixel - zero_line_y
            
            if distance_from_zero <= 0:
                if up_distance > 0:
                    ratio = abs(distance_from_zero) / up_distance
                    value = ratio * max_value
                else:
                    value = 0
            else:
                if down_distance > 0:
                    ratio = distance_from_zero / down_distance
                    value = ratio * estimated_min
                else:
                    value = 0
            
            converted_points.append((x_pixel, int(value)))
        
        return converted_points
    
    def extract_graph_data(self, image_path, output_csv=None):
        """グラフデータ抽出"""
        try:
            # OCRで最大値取得
            max_value = self.extract_max_value_from_graph(image_path)
            if max_value is None:
                self.log("最大値を手動入力してください", "WARNING")
                try:
                    max_value = float(input("最大値を入力: "))
                except ValueError:
                    return None
            
            # ピンク線検出
            mask = self.detect_pink_line(image_path)
            if mask is None:
                self.log("ピンク線検出失敗", "ERROR")
                return None
            
            # データポイント抽出
            points = self.extract_data_points(mask)
            if not points:
                self.log("データポイント抽出失敗", "ERROR")
                return None
            
            # ゼロライン検出
            zero_line_y = self.detect_zero_line(image_path)
            
            # 座標変換
            converted_points = self.convert_with_pixel_ratio(points, zero_line_y, max_value)
            if not converted_points:
                return None
            
            # DataFrame作成
            df = pd.DataFrame(converted_points, columns=['x_pixel', 'y_value'])
            
            # X座標正規化
            if df['x_pixel'].max() > df['x_pixel'].min():
                df['x_normalized'] = (df['x_pixel'] - df['x_pixel'].min()) / (df['x_pixel'].max() - df['x_pixel'].min())
            else:
                df['x_normalized'] = 0
            
            # CSV保存
            if output_csv:
                df.to_csv(output_csv, index=False)
            
            # 結果保存
            extraction_result = {
                'max_value': max_value,
                'zero_line_y': zero_line_y,
                'data_points_count': len(df),
                'value_range': [df['y_value'].min(), df['y_value'].max()],
                'accuracy': (df['y_value'].max() / max_value * 100) if max_value > 0 else 0
            }
            
            return df, extraction_result
            
        except Exception as e:
            self.log(f"データ抽出エラー: {e}", "ERROR")
            return None
    
    # =====================================
    # 3. 回転数分析機能
    # =====================================
    
    def detect_jackpots(self, data, min_rise=1000, min_distance=10):
        """大当り検出"""
        diff = np.diff(data['y_value'])
        peaks, _ = find_peaks(diff, height=min_rise, distance=min_distance)
        
        jackpots = []
        for idx in peaks + 1:
            if idx < len(data):
                time_col = 'time_index' if 'time_index' in data.columns else 'x_normalized'
                jackpots.append({
                    'index': idx,
                    'time': data.iloc[idx][time_col],
                    'balance': data.iloc[idx]['y_value'],
                    'rise_amount': diff[idx-1] if idx > 0 else 0
                })
        
        return jackpots
    
    def calculate_base_rate(self, data, jackpots, ball_cost=4):
        """ベース計算"""
        if not jackpots:
            # 大当りがない場合は全体を分析
            total_loss = abs(data['y_value'].min())
            total_points = len(data)
            
            if total_loss > 0:
                # 簡易ベース計算
                estimated_rotations = (total_loss / ball_cost)
                base_per_1000 = (1000 / ball_cost) * (estimated_rotations / total_loss) if total_loss > 0 else 0
                base_per_1000 = max(10, min(base_per_1000, 500))  # 現実的な範囲
            else:
                base_per_1000 = 100  # デフォルト値
        else:
            # 大当り間隔から計算
            jackpot_indices = [jp['index'] for jp in jackpots]
            
            # 各区間を分析
            prev_idx = 0
            total_loss = 0
            total_points = 0
            
            for jp_idx in jackpot_indices:
                segment_data = data.iloc[prev_idx:jp_idx]
                if len(segment_data) > 5:
                    start_val = segment_data.iloc[0]['y_value']
                    end_val = segment_data.iloc[-1]['y_value']
                    loss = start_val - end_val
                    
                    if loss > 0:
                        total_loss += loss
                        total_points += len(segment_data)
                
                prev_idx = jp_idx
            
            if total_loss > 0 and total_points > 0:
                # 平均的な損失率から計算
                avg_loss_rate = total_loss / total_points
                base_per_1000 = (1000 / ball_cost) / avg_loss_rate if avg_loss_rate > 0 else 100
                base_per_1000 = max(10, min(base_per_1000, 500))
            else:
                base_per_1000 = 100
        
        return {
            'base_rate': base_per_1000,
            'calculation_method': 'jackpot_interval' if jackpots else 'overall_loss'
        }
    
    def calculate_rotation_efficiency(self, data, jackpots, base_result):
        """回転効率計算"""
        total_investment = abs(data['y_value'].min())
        net_result = data['y_value'].iloc[-1] - data['y_value'].iloc[0]
        
        # 推定総回転数
        estimated_rotations = (total_investment / 1000) * base_result['base_rate']
        
        # 各種効率
        jackpot_efficiency = len(jackpots) / (estimated_rotations / 1000) if estimated_rotations > 0 else 0
        investment_efficiency = (net_result / total_investment * 100) if total_investment > 0 else 0
        
        return {
            'total_investment': total_investment,
            'net_result': net_result,
            'estimated_total_rotations': estimated_rotations,
            'jackpot_count': len(jackpots),
            'jackpot_efficiency': jackpot_efficiency,
            'investment_efficiency': investment_efficiency
        }
    
    def analyze_rotation_data(self, data, ball_cost=4, min_jackpot_rise=1000):
        """回転数分析"""
        try:
            # 時間軸の確保
            if 'time_index' not in data.columns:
                if 'x_normalized' in data.columns:
                    data['time_index'] = data['x_normalized']
                else:
                    data['time_index'] = np.linspace(0, 1, len(data))
            
            # 大当り検出
            jackpots = self.detect_jackpots(data, min_jackpot_rise)
            
            # ベース計算
            base_result = self.calculate_base_rate(data, jackpots, ball_cost)
            
            # 効率計算
            efficiency = self.calculate_rotation_efficiency(data, jackpots, base_result)
            
            return {
                'jackpots': jackpots,
                'base_result': base_result,
                'efficiency': efficiency,
                'settings': {
                    'ball_cost': ball_cost,
                    'min_jackpot_rise': min_jackpot_rise
                }
            }
            
        except Exception as e:
            self.log(f"回転数分析エラー: {e}", "ERROR")
            return None
    
    # =====================================
    # 4. 統合処理機能
    # =====================================
    
    def process_single_image(self, image_path, ball_cost=4, min_jackpot_rise=1000):
        """単一画像の完全処理"""
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 出力パス設定
        cropped_folder = "graphs/cropped_auto"
        os.makedirs(cropped_folder, exist_ok=True)
        
        cropped_path = os.path.join(cropped_folder, f"{base_name}_cropped.png")
        csv_path = os.path.join(cropped_folder, f"{base_name}_data.csv")
        
        results = {
            'input_image': image_path,
            'timestamp': timestamp,
            'steps': {}
        }
        
        self.log(f"🎰 画像処理開始: {os.path.basename(image_path)}")
        
        # ステップ1: 画像切り抜き
        self.progress("画像からグラフエリアを切り抜き中...")
        if not self.crop_graph_auto(image_path, cropped_path):
            self.log("画像切り抜きに失敗しました", "ERROR")
            return None
        
        results['steps']['crop'] = {
            'status': 'success',
            'output_path': cropped_path
        }
        
        # ステップ2: データ抽出
        self.progress("グラフからデータを抽出中...")
        extraction_result = self.extract_graph_data(cropped_path, csv_path)
        if extraction_result is None:
            self.log("データ抽出に失敗しました", "ERROR")
            return None
        
        data_df, extraction_info = extraction_result
        results['steps']['extraction'] = {
            'status': 'success',
            'output_path': csv_path,
            'info': extraction_info
        }
        
        # ステップ3: 回転数分析
        self.progress("回転数・ベースを分析中...")
        rotation_result = self.analyze_rotation_data(data_df, ball_cost, min_jackpot_rise)
        if rotation_result is None:
            self.log("回転数分析に失敗しました", "ERROR")
            # データ抽出まで成功していれば部分的な結果を返す
            results['status'] = 'partial_success'
            return results
        
        results['steps']['rotation'] = {
            'status': 'success',
            'analysis': rotation_result
        }
        
        # 結果サマリー
        jackpots = rotation_result['jackpots']
        base_rate = rotation_result['base_result']['base_rate']
        efficiency = rotation_result['efficiency']
        
        results['summary'] = {
            'data_points': len(data_df),
            'max_value': extraction_info['max_value'],
            'accuracy': extraction_info['accuracy'],
            'jackpot_count': len(jackpots),
            'base_rate': base_rate,
            'estimated_rotations': efficiency['estimated_total_rotations'],
            'investment_efficiency': efficiency['investment_efficiency'],
            'final_balance': efficiency['net_result']
        }
        
        results['status'] = 'success'
        return results
    
    def process_batch(self, input_folder="graphs", ball_cost=4, min_jackpot_rise=1000):
        """バッチ処理"""
        if not os.path.exists(input_folder):
            self.log(f"入力フォルダが見つかりません: {input_folder}", "ERROR")
            return None
        
        # 対象画像ファイルを検索
        image_files = []
        for file in os.listdir(input_folder):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                # 既に処理済みファイルは除外
                if not file.endswith('_cropped.png') and not file.endswith('_comparison.png'):
                    image_files.append(file)
        
        if not image_files:
            self.log("処理対象の画像ファイルが見つかりません", "ERROR")
            return None
        
        self.log(f"🚀 バッチ処理開始: {len(image_files)}個のファイル")
        self.total_steps = len(image_files) * 3  # 各画像につき3ステップ
        self.current_step = 0
        
        batch_results = {
            'start_time': datetime.now().isoformat(),
            'settings': {
                'ball_cost': ball_cost,
                'min_jackpot_rise': min_jackpot_rise
            },
            'results': {},
            'summary': {
                'total_files': len(image_files),
                'successful': 0,
                'failed': 0,
                'partial': 0
            }
        }
        
        # 各画像を処理
        for i, filename in enumerate(image_files, 1):
            image_path = os.path.join(input_folder, filename)
            self.log(f"\n{'='*50}")
            self.log(f"[{i}/{len(image_files)}] 処理中: {filename}")
            self.log(f"{'='*50}")
            
            result = self.process_single_image(image_path, ball_cost, min_jackpot_rise)
            
            if result is None:
                batch_results['summary']['failed'] += 1
                batch_results['results'][filename] = {'status': 'failed'}
                self.log(f"❌ 処理失敗: {filename}")
            elif result.get('status') == 'partial_success':
                batch_results['summary']['partial'] += 1
                batch_results['results'][filename] = result
                self.log(f"⚠️ 部分成功: {filename}")
            else:
                batch_results['summary']['successful'] += 1
                batch_results['results'][filename] = result
                self.log(f"✅ 処理完了: {filename}")
        
        batch_results['end_time'] = datetime.now().isoformat()
        
        # バッチ結果を保存
        report_path = f"batch_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(batch_results, f, ensure_ascii=False, indent=2)
        
        self.log(f"\n📋 バッチ処理完了レポート: {report_path}")
        return batch_results
    
    def print_summary(self, batch_results):
        """結果サマリーの表示"""
        summary = batch_results['summary']
        
        print(f"\n{'='*60}")
        print(f"📊 バッチ処理結果サマリー")
        print(f"{'='*60}")
        print(f"📁 処理対象: {summary['total_files']}ファイル")
        print(f"✅ 成功: {summary['successful']}ファイル")
        print(f"⚠️ 部分成功: {summary['partial']}ファイル")
        print(f"❌ 失敗: {summary['failed']}ファイル")
        print(f"🎯 成功率: {(summary['successful'] / summary['total_files'] * 100):.1f}%")
        
        if summary['successful'] > 0:
            print(f"\n🎰 成功した分析結果:")
            
            successful_results = []
            for filename, result in batch_results['results'].items():
                if result.get('status') == 'success' and 'summary' in result:
                    successful_results.append((filename, result['summary']))
            
            if successful_results:
                print(f"{'ファイル名':<25} {'大当り':<6} {'ベース':<8} {'推定回転数':<10} {'投資効率'}")
                print(f"{'-'*65}")
                
                total_jackpots = 0
                total_base = 0
                
                for filename, summary in successful_results:
                    short_name = filename[:20] + "..." if len(filename) > 20 else filename
                    jackpots = summary['jackpot_count']
                    base = summary['base_rate']
                    rotations = summary['estimated_rotations']
                    efficiency = summary['investment_efficiency']
                    
                    print(f"{short_name:<25} {jackpots:<6} {base:<8.1f} {rotations:<10.0f} {efficiency:<+7.1f}%")
                    
                    total_jackpots += jackpots
                    total_base += base
                
                avg_base = total_base / len(successful_results)
                avg_jackpots = total_jackpots / len(successful_results)
                
                print(f"{'-'*65}")
                print(f"{'平均':<25} {avg_jackpots:<6.1f} {avg_base:<8.1f}")
                
                # ベース評価
                if avg_base >= 100:
                    base_rating = "🟢 優秀"
                elif avg_base >= 80:
                    base_rating = "🟡 普通"
                else:
                    base_rating = "🔴 厳しい"
                
                print(f"\n🏆 総合評価:")
                print(f"   平均ベース: {avg_base:.1f}回転/1000円 {base_rating}")
                print(f"   平均大当り: {avg_jackpots:.1f}回/セッション")
        
        print(f"\n📁 出力ファイル:")
        print(f"   切り抜き画像: graphs/cropped_auto/")
        print(f"   抽出データ: graphs/cropped_auto/*_data.csv")
        print(f"   詳細レポート: batch_analysis_report_*.json")


def main():
    """メイン処理"""
    analyzer = IntegratedPachinkoAnalyzer()
    
    print("=" * 60)
    print("🎰 統合パチンコ分析ツール")
    print("=" * 60)
    print("📋 機能:")
    print("   1. 画像からグラフエリアを自動切り抜き")
    print("   2. グラフからデータを自動抽出")
    print("   3. 回転数・ベースを自動分析")
    print("   4. 一括処理対応")
    
    # 入力フォルダチェック
    input_folder = "graphs"
    if not os.path.exists(input_folder):
        analyzer.log(f"入力フォルダが見つかりません: {input_folder}", "ERROR")
        analyzer.log("1. 'graphs' フォルダを作成してください", "INFO")
        analyzer.log("2. パチンコのグラフ画像を配置してください", "INFO")
        return
    
    # 画像ファイルチェック
    image_files = [f for f in os.listdir(input_folder) 
                  if f.lower().endswith(('.png', '.jpg', '.jpeg')) 
                  and not f.endswith('_cropped.png') 
                  and not f.endswith('_comparison.png')]
    
    if not image_files:
        analyzer.log("処理対象の画像ファイルが見つかりません", "ERROR")
        analyzer.log(f"'{input_folder}' フォルダに画像ファイルを配置してください", "INFO")
        return
    
    print(f"\n📁 見つかった画像ファイル ({len(image_files)}個):")
    for i, file in enumerate(image_files, 1):
        print(f"   {i}. {file}")
    
    # 処理モード選択
    print(f"\n🎯 処理モードを選択してください:")
    print("1. 🚀 全自動処理（推奨）")
    print("2. 📷 単一ファイル処理")
    print("3. ⚙️ 設定変更して処理")
    
    try:
        choice = input("\n選択 (1-3): ").strip()
        
        # デフォルト設定
        ball_cost = 4
        min_jackpot_rise = 1000
        
        if choice == "1":
            # 全自動処理
            analyzer.log("🚀 全自動処理を開始します")
            batch_results = analyzer.process_batch(input_folder, ball_cost, min_jackpot_rise)
            
            if batch_results:
                analyzer.print_summary(batch_results)
            
        elif choice == "2":
            # 単一ファイル処理
            try:
                file_num = int(input("処理するファイル番号を選択: "))
                if 1 <= file_num <= len(image_files):
                    selected_file = image_files[file_num - 1]
                    image_path = os.path.join(input_folder, selected_file)
                    
                    analyzer.total_steps = 3
                    analyzer.current_step = 0
                    
                    result = analyzer.process_single_image(image_path, ball_cost, min_jackpot_rise)
                    
                    if result and result.get('status') == 'success':
                        summary = result['summary']
                        
                        print(f"\n🎉 処理完了: {selected_file}")
                        print(f"=" * 50)
                        print(f"📊 分析結果:")
                        print(f"   データポイント数: {summary['data_points']}")
                        print(f"   最大値: {summary['max_value']}")
                        print(f"   抽出精度: {summary['accuracy']:.1f}%")
                        print(f"   大当り回数: {summary['jackpot_count']}")
                        print(f"   ベース: {summary['base_rate']:.1f}回転/1000円")
                        print(f"   推定総回転数: {summary['estimated_rotations']:.0f}回転")
                        print(f"   投資効率: {summary['investment_efficiency']:+.1f}%")
                        print(f"   最終収支: {summary['final_balance']:+.0f}円")
                        
                        # ベース評価
                        base = summary['base_rate']
                        if base >= 100:
                            base_rating = "🟢 優秀"
                        elif base >= 80:
                            base_rating = "🟡 普通"
                        else:
                            base_rating = "🔴 厳しい"
                        print(f"   総合評価: {base_rating}")
                    else:
                        analyzer.log("処理に失敗しました", "ERROR")
                        
                else:
                    analyzer.log("無効なファイル番号です", "ERROR")
            except ValueError:
                analyzer.log("数字を入力してください", "ERROR")
                
        elif choice == "3":
            # 設定変更
            print(f"\n⚙️ 設定変更:")
            
            # 玉単価設定
            cost_input = input("玉単価 (1円パチンコ=1, 4円パチンコ=4, デフォルト=4): ").strip()
            if cost_input:
                try:
                    ball_cost = int(cost_input)
                except ValueError:
                    analyzer.log("無効な玉単価です。デフォルト値を使用します", "WARNING")
            
            # 大当り判定額設定
            rise_input = input("大当り判定の最小上昇額 (デフォルト=1000円): ").strip()
            if rise_input:
                try:
                    min_jackpot_rise = int(rise_input)
                except ValueError:
                    analyzer.log("無効な上昇額です。デフォルト値を使用します", "WARNING")
            
            print(f"\n📋 設定確認:")
            print(f"   玉単価: {ball_cost}円")
            print(f"   大当り判定: {min_jackpot_rise}円以上の上昇")
            
            # 処理実行
            process_all = input("\n全ファイルを処理しますか？ (y/n, デフォルト=y): ").strip().lower()
            
            if process_all != 'n':
                batch_results = analyzer.process_batch(input_folder, ball_cost, min_jackpot_rise)
                if batch_results:
                    analyzer.print_summary(batch_results)
            else:
                # 単一ファイル処理
                try:
                    file_num = int(input("処理するファイル番号を選択: "))
                    if 1 <= file_num <= len(image_files):
                        selected_file = image_files[file_num - 1]
                        image_path = os.path.join(input_folder, selected_file)
                        
                        analyzer.total_steps = 3
                        analyzer.current_step = 0
                        
                        result = analyzer.process_single_image(image_path, ball_cost, min_jackpot_rise)
                        
                        if result and result.get('status') == 'success':
                            summary = result['summary']
                            analyzer.log(f"✅ 処理完了 - ベース: {summary['base_rate']:.1f}回転/1000円")
                except ValueError:
                    analyzer.log("数字を入力してください", "ERROR")
        else:
            analyzer.log("無効な選択です", "ERROR")
            
    except KeyboardInterrupt:
        analyzer.log("\n処理が中断されました", "WARNING")
    except Exception as e:
        analyzer.log(f"予期しないエラー: {e}", "ERROR")
    
    print(f"\n✨ 処理完了")


if __name__ == "__main__":
    main()
                