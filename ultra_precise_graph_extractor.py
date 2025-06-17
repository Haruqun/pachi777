#!/usr/bin/env python3
"""
超高精度グラフデータ抽出システム
特に最大値検出の精度を極限まで高める
"""

import os
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import cv2
import pandas as pd
from typing import Tuple, List, Dict, Optional
from scipy.signal import find_peaks, savgol_filter
from scipy.ndimage import gaussian_filter1d
import warnings
warnings.filterwarnings('ignore')

class UltraPreciseGraphExtractor:
    """超高精度グラフデータ抽出システム"""
    
    def __init__(self, config_path="graph_boundaries_final_config.json"):
        """初期化"""
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
            self.boundaries = self.config["boundaries"]
        except FileNotFoundError:
            print(f"警告: 設定ファイル {config_path} が見つかりません。デフォルト値を使用します。")
            self.boundaries = {
                "start_x": 36,
                "end_x": 620,
                "top_y": 29,
                "bottom_y": 520,
                "zero_y": 274
            }
        
        self.debug_mode = True
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{level}] {message}")
    
    def detect_graph_color_ultra(self, img_array: np.ndarray) -> Tuple[str, np.ndarray, Dict]:
        """超高精度色検出（ピンク特化）"""
        # BGRからHSVに変換
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        
        # グラフ領域全体でサンプリング
        roi_hsv = img_hsv[
            self.boundaries["top_y"]:self.boundaries["bottom_y"],
            self.boundaries["start_x"]:self.boundaries["end_x"]
        ]
        
        # ピンク検出を最適化（複数の範囲で試行）
        pink_ranges = [
            [(150, 30, 80), (170, 255, 255)],   # 標準ピンク
            [(155, 25, 70), (175, 255, 255)],   # より広いピンク
            [(145, 35, 90), (165, 255, 255)],   # より濃いピンク
            [(160, 20, 60), (180, 255, 255)],   # 薄いピンク
        ]
        
        best_mask = None
        best_count = 0
        best_range_idx = 0
        
        # 最適なピンク範囲を見つける
        for idx, (lower, upper) in enumerate(pink_ranges):
            lower_np = np.array(lower)
            upper_np = np.array(upper)
            
            mask_roi = cv2.inRange(roi_hsv, lower_np, upper_np)
            count = np.sum(mask_roi > 0)
            
            if count > best_count:
                best_count = count
                best_mask = cv2.inRange(img_hsv, lower_np, upper_np)
                best_range_idx = idx
        
        # 他の色も検出
        other_colors = {
            "purple": [(120, 40, 80), (150, 255, 255)],
            "blue": [(90, 40, 80), (120, 255, 255)],
            "cyan": [(80, 40, 80), (100, 255, 255)]
        }
        
        color_counts = {"pink": best_count}
        for color_name, (lower, upper) in other_colors.items():
            mask_roi = cv2.inRange(roi_hsv, np.array(lower), np.array(upper))
            color_counts[color_name] = np.sum(mask_roi > 0)
        
        # 最も多い色を選択
        detected_color = max(color_counts, key=color_counts.get)
        
        if detected_color != "pink":
            # ピンク以外の場合は通常の処理
            lower, upper = other_colors[detected_color]
            best_mask = cv2.inRange(img_hsv, np.array(lower), np.array(upper))
        
        # ノイズ除去（より繊細に）
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        best_mask = cv2.morphologyEx(best_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        # 細い線の保護
        best_mask = cv2.dilate(best_mask, np.ones((2, 2), np.uint8), iterations=1)
        
        self.log(f"色検出結果: {color_counts}, 使用範囲: {best_range_idx}", "DEBUG")
        
        return detected_color, best_mask, {"counts": color_counts, "range_idx": best_range_idx}
    
    def extract_line_ultra_precise(self, img_array: np.ndarray, mask: np.ndarray, color_type: str) -> List[Tuple[float, float]]:
        """超高精度ライン抽出（ピーク保護重視）"""
        points = []
        
        # 各X座標で最も強いピンク/紫のピクセルを検出
        for x in range(self.boundaries["start_x"], self.boundaries["end_x"]):
            column_mask = mask[self.boundaries["top_y"]:self.boundaries["bottom_y"], x]
            column_img = img_array[self.boundaries["top_y"]:self.boundaries["bottom_y"], x]
            
            y_indices = np.where(column_mask > 0)[0]
            
            if len(y_indices) > 0:
                if color_type == "pink":
                    # ピンクラインの強度計算（より精密に）
                    intensities = []
                    for y_idx in y_indices:
                        if y_idx < len(column_img):
                            pixel = column_img[y_idx]
                            if len(pixel) >= 3:
                                r, g, b = float(pixel[0]), float(pixel[1]), float(pixel[2])
                                # ピンクの特徴をより正確に捉える
                                pink_score = r - 0.6 * g - 0.4 * b
                                # 明るさも考慮
                                brightness = (r + g + b) / 3
                                intensity = pink_score * (brightness / 255)
                                intensities.append(intensity)
                            else:
                                intensities.append(0.0)
                    
                    if intensities and max(intensities) > 0:
                        # 複数のピークがある場合の処理
                        max_intensity = max(intensities)
                        threshold = max_intensity * 0.5  # 50%以上の強度
                        
                        # 候補ピクセルを取得
                        candidates = [(y_indices[i], intensities[i]) 
                                    for i in range(len(intensities)) 
                                    if intensities[i] >= threshold]
                        
                        if candidates:
                            # 重み付き平均でサブピクセル位置を計算
                            weighted_y = sum(y * (intensity ** 3) for y, intensity in candidates)
                            weight_sum = sum(intensity ** 3 for _, intensity in candidates)
                            
                            if weight_sum > 0:
                                y_subpixel = weighted_y / weight_sum
                                
                                # ピーク近傍での微調整
                                peak_idx = intensities.index(max_intensity)
                                if 1 < peak_idx < len(intensities) - 1:
                                    # 3点パラボラフィッティング
                                    y1 = intensities[peak_idx - 1]
                                    y2 = intensities[peak_idx]
                                    y3 = intensities[peak_idx + 1]
                                    
                                    if y1 < y2 > y3 and y2 > 0:
                                        # パラボラの頂点を計算
                                        a = (y1 - 2*y2 + y3) / 2
                                        b = (y3 - y1) / 2
                                        if a < 0:  # 上に凸
                                            offset = -b / (2 * a)
                                            # オフセットを制限
                                            offset = np.clip(offset, -0.5, 0.5)
                                            y_subpixel = y_indices[peak_idx] + offset
                                
                                y_actual = float(self.boundaries["top_y"]) + y_subpixel
                                points.append((float(x), y_actual))
                else:
                    # ピンク以外の色の処理
                    if len(y_indices) > 1:
                        # 連続した領域の中心を使用
                        y_center = np.mean(y_indices)
                    else:
                        y_center = float(y_indices[0])
                    
                    y_actual = float(self.boundaries["top_y"]) + y_center
                    points.append((float(x), y_actual))
        
        return points
    
    def find_true_maximum(self, points: List[Tuple[float, float]]) -> Tuple[float, int]:
        """真の最大値を見つける（ノイズ耐性）"""
        if not points:
            return 0.0, -1
        
        y_values = np.array([p[1] for p in points])
        
        # Y座標を値に変換（小さいY = 大きい値）
        values = [self.y_to_value(y) for y in y_values]
        values_array = np.array(values)
        
        # 1. 単純な最大値
        simple_max_idx = np.argmax(values_array)
        simple_max = values_array[simple_max_idx]
        
        # 2. 移動平均での最大値（ノイズ除去）
        if len(values_array) > 10:
            window_size = min(11, len(values_array) // 3)
            if window_size % 2 == 0:
                window_size += 1
            
            if window_size >= 3:
                smoothed = savgol_filter(values_array, window_size, 2)
                smooth_max_idx = np.argmax(smoothed)
                smooth_max = smoothed[smooth_max_idx]
            else:
                smooth_max = simple_max
                smooth_max_idx = simple_max_idx
        else:
            smooth_max = simple_max
            smooth_max_idx = simple_max_idx
        
        # 3. ピーク検出での最大値
        if len(values_array) > 5:
            # ピークを検出（プロミネンスを使用）
            peaks, properties = find_peaks(values_array, 
                                         prominence=100,  # 最小100玉の突出
                                         distance=5)      # 最小5点の間隔
            
            if len(peaks) > 0:
                # ピークの中で最大値を選択
                peak_values = values_array[peaks]
                peak_max_idx = peaks[np.argmax(peak_values)]
                peak_max = values_array[peak_max_idx]
            else:
                peak_max = simple_max
                peak_max_idx = simple_max_idx
        else:
            peak_max = simple_max
            peak_max_idx = simple_max_idx
        
        # 最も信頼できる最大値を選択
        # 通常はピーク検出の結果を優先
        if abs(peak_max - simple_max) < 500:  # 差が小さければピーク検出を信頼
            return peak_max, peak_max_idx
        else:
            # 差が大きい場合は慎重に判断
            return max(simple_max, smooth_max, peak_max), simple_max_idx
    
    def minimal_smoothing(self, points: List[Tuple[float, float]], max_idx: int) -> List[Tuple[float, float]]:
        """最小限のスムージング（最大値付近は保護）"""
        if len(points) < 5:
            return points
        
        x_vals = np.array([p[0] for p in points])
        y_vals = np.array([p[1] for p in points])
        
        # 最大値付近の範囲を保護（前後10点）
        protected_start = max(0, max_idx - 10)
        protected_end = min(len(points), max_idx + 11)
        
        # 軽微なスムージング
        y_smooth = y_vals.copy()
        
        for i in range(1, len(y_vals) - 1):
            if protected_start <= i <= protected_end:
                # 最大値付近は触らない
                continue
            
            # 3点移動平均（軽い）
            y_smooth[i] = 0.5 * y_vals[i] + 0.25 * y_vals[i-1] + 0.25 * y_vals[i+1]
        
        return list(zip(x_vals, y_smooth))
    
    def y_to_value(self, y: float) -> float:
        """Y座標を差枚数に変換"""
        height = float(self.boundaries["bottom_y"] - self.boundaries["top_y"])
        value = 30000.0 - (y - float(self.boundaries["top_y"])) * 60000.0 / height
        return np.clip(value, -30000.0, 30000.0)
    
    def extract_graph_data(self, image_path: str) -> Dict:
        """超高精度でグラフデータを抽出"""
        self.log(f"処理開始: {os.path.basename(image_path)}")
        
        try:
            # 画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # 超高精度色検出
            color_type, mask, color_props = self.detect_graph_color_ultra(img_array)
            self.log(f"グラフ色: {color_type}", "INFO")
            
            # 超高精度ライン抽出
            raw_points = self.extract_line_ultra_precise(img_array, mask, color_type)
            self.log(f"検出点数: {len(raw_points)}", "INFO")
            
            # 真の最大値を見つける
            true_max, max_idx = self.find_true_maximum(raw_points)
            self.log(f"検出最大値: {true_max:.1f}玉 (位置: {max_idx})", "SUCCESS")
            
            # 最小限のスムージング（最大値保護）
            smooth_points = self.minimal_smoothing(raw_points, max_idx)
            
            # データ変換
            data = []
            max_rotation = 50000  # 仮定
            
            for i, (x, y) in enumerate(smooth_points):
                rotation = (x - float(self.boundaries["start_x"])) * max_rotation / \
                          float(self.boundaries["end_x"] - self.boundaries["start_x"])
                value = self.y_to_value(y)
                
                data.append({
                    "rotation": rotation,
                    "value": value,
                    "x": x,
                    "y": y,
                    "is_max": i == max_idx
                })
            
            # 抽出された最大値を再確認
            extracted_values = [d["value"] for d in data]
            extracted_max = max(extracted_values)
            extracted_final = extracted_values[-1] if extracted_values else 0
            
            return {
                "image": os.path.basename(image_path),
                "color_type": color_type,
                "max_rotation": max_rotation,
                "points": len(smooth_points),
                "data": data,
                "extracted_max": extracted_max,
                "extracted_final": extracted_final,
                "max_index": max_idx,
                "quality": {
                    "is_valid": True,
                    "message": f"最大値: {extracted_max:.1f}玉"
                },
                "processing": {
                    "method": "ultra_precise",
                    "color_props": color_props
                }
            }
            
        except Exception as e:
            self.log(f"エラーが発生しました: {str(e)}", "ERROR")
            return {
                "image": os.path.basename(image_path),
                "error": str(e),
                "data": []
            }
    
    def save_to_csv(self, result: Dict, output_path: str):
        """抽出データをCSVに保存"""
        if "error" in result:
            return
        
        df = pd.DataFrame(result["data"])
        df.to_csv(output_path, index=False, float_format='%.2f')
        self.log(f"CSVファイルを保存: {output_path}", "SUCCESS")
    
    def create_visualization(self, image_path: str, result: Dict, output_path: str):
        """抽出結果を可視化（最大値を強調）"""
        if "error" in result:
            return
        
        # 元画像を読み込み
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        # 境界線を描画
        draw.rectangle(
            [(self.boundaries["start_x"], self.boundaries["top_y"]),
             (self.boundaries["end_x"], self.boundaries["bottom_y"])],
            outline=(255, 0, 0), width=2
        )
        
        # ゼロライン
        draw.line(
            [(self.boundaries["start_x"], self.boundaries["zero_y"]),
             (self.boundaries["end_x"], self.boundaries["zero_y"])],
            fill=(0, 255, 0), width=1
        )
        
        # 抽出したポイントを描画
        if result["data"]:
            points = [(int(round(d["x"])), int(round(d["y"]))) for d in result["data"]]
            if len(points) > 1:
                draw.line(points, fill=(0, 0, 255), width=3)
            
            # 最大値点を強調
            if "max_index" in result and 0 <= result["max_index"] < len(points):
                max_point = points[result["max_index"]]
                draw.ellipse(
                    [(max_point[0]-8, max_point[1]-8),
                     (max_point[0]+8, max_point[1]+8)],
                    fill=(255, 255, 0), outline=(255, 0, 0), width=2
                )
                # 最大値ラベル
                draw.text((max_point[0]+10, max_point[1]-10), 
                         f"MAX: {result['extracted_max']:.0f}", 
                         fill=(255, 0, 0))
            
            # 始点と終点
            if points:
                draw.ellipse(
                    [(points[0][0]-5, points[0][1]-5),
                     (points[0][0]+5, points[0][1]+5)],
                    fill=(0, 255, 0), outline=(0, 0, 0)
                )
                draw.ellipse(
                    [(points[-1][0]-5, points[-1][1]-5),
                     (points[-1][0]+5, points[-1][1]+5)],
                    fill=(255, 0, 0), outline=(0, 0, 0)
                )
        
        # 情報表示
        info_y = 20
        draw.text((img.width-400, info_y), f"Points: {result.get('points', 0)}", fill=(0, 0, 0))
        info_y += 20
        draw.text((img.width-400, info_y), f"Max: {result.get('extracted_max', 0):.0f}", fill=(255, 0, 0))
        info_y += 20
        draw.text((img.width-400, info_y), f"Final: {result.get('extracted_final', 0):.0f}", fill=(0, 0, 255))
        info_y += 20
        draw.text((img.width-400, info_y), f"Method: Ultra Precise", fill=(128, 0, 128))
        
        # 保存
        img.save(output_path)
        self.log(f"可視化画像を保存: {output_path}", "SUCCESS")

def main():
    """メイン処理"""
    print("🚀 超高精度グラフデータ抽出システム")
    print("📊 最大値検出を極限まで最適化")
    
    # 入出力フォルダ設定
    input_folder = "graphs/cropped"
    output_folder = "graphs/ultra_precise_extracted"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 抽出器を初期化
    extractor = UltraPreciseGraphExtractor()
    
    # 特に最大値の精度が悪かったファイルを優先的に処理
    priority_files = [
        "S__78209088_optimal.png",  # 誤差505玉
        "S__78209166_optimal.png",  # 誤差576玉
        "S__78209168_optimal.png",  # 誤差612玉
        "S__78209170_optimal.png",  # 誤差432玉
    ]
    
    # まず優先ファイルを処理
    for file in priority_files:
        if os.path.exists(os.path.join(input_folder, file)):
            print(f"\n{'='*60}")
            print(f"優先処理: {file}")
            
            input_path = os.path.join(input_folder, file)
            result = extractor.extract_graph_data(input_path)
            
            if "error" not in result:
                base_name = os.path.splitext(file)[0]
                
                # CSV保存
                csv_path = os.path.join(output_folder, f"{base_name}_data.csv")
                extractor.save_to_csv(result, csv_path)
                
                # 可視化
                vis_path = os.path.join(output_folder, f"{base_name}_visualization.png")
                extractor.create_visualization(input_path, result, vis_path)
                
                print(f"\n📊 抽出結果:")
                print(f"  最大値: {result['extracted_max']:.1f}玉")
                print(f"  最終値: {result['extracted_final']:.1f}玉")
    
    print(f"\n{'='*60}")
    print("超高精度抽出完了！")

if __name__ == "__main__":
    main()