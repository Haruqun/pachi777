#!/usr/bin/env python3
"""
サブピクセル精度グラフデータ抽出システム
- 浮動小数点座標での処理
- スプライン補間による滑らかな曲線
- エッジ検出の最適化
"""

import os
import json
import numpy as np
from PIL import Image, ImageDraw
import cv2
import pandas as pd
from typing import Tuple, List, Dict, Optional
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline, interp1d
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d
import warnings
warnings.filterwarnings('ignore')

class SubpixelGraphExtractor:
    """サブピクセル精度のグラフデータ抽出システム"""
    
    def __init__(self, config_path="graph_boundaries_final_config.json"):
        """初期化"""
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
            self.boundaries = self.config["boundaries"]
        except FileNotFoundError:
            print(f"警告: 設定ファイル {config_path} が見つかりません。デフォルト値を使用します。")
            self.boundaries = self._get_default_boundaries()
        
        self.debug_mode = True
        
    def _get_default_boundaries(self) -> dict:
        """デフォルトの境界値を返す"""
        return {
            "start_x": 36,
            "end_x": 620,
            "top_y": 29,
            "bottom_y": 520,
            "zero_y": 274
        }
    
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{level}] {message}")
    
    def detect_graph_color_advanced(self, img_array: np.ndarray) -> Tuple[str, np.ndarray]:
        """高度な色検出とマスク生成"""
        # BGRからHSVに変換
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        
        # より精密な色範囲の定義
        color_ranges = {
            "pink": [
                [(140, 30, 100), (170, 255, 255)],  # 明るいピンク
                [(160, 20, 150), (180, 255, 255)]   # 薄いピンク
            ],
            "purple": [
                [(120, 30, 80), (150, 255, 255)],   # 紫
                [(130, 20, 100), (145, 255, 255)]   # 薄紫
            ],
            "blue": [
                [(90, 30, 100), (120, 255, 255)],   # 青
                [(100, 20, 150), (115, 255, 255)]   # 明るい青
            ],
            "cyan": [
                [(80, 30, 100), (100, 255, 255)],   # シアン
                [(85, 20, 150), (95, 255, 255)]     # 明るいシアン
            ]
        }
        
        # 各色のマスクを生成して最適なものを選択
        best_color = None
        best_count = 0
        best_mask = None
        
        roi = img_hsv[
            self.boundaries["zero_y"]-50:self.boundaries["zero_y"]+50,
            self.boundaries["start_x"]:self.boundaries["end_x"]
        ]
        
        for color_name, ranges_list in color_ranges.items():
            combined_mask = np.zeros(roi.shape[:2], dtype=np.uint8)
            
            for lower, upper in ranges_list:
                mask = cv2.inRange(roi, np.array(lower), np.array(upper))
                combined_mask = cv2.bitwise_or(combined_mask, mask)
            
            count = np.sum(combined_mask > 0)
            
            if count > best_count:
                best_count = count
                best_color = color_name
                # フルサイズのマスクを作成
                full_mask = np.zeros(img_hsv.shape[:2], dtype=np.uint8)
                for lower, upper in ranges_list:
                    mask = cv2.inRange(img_hsv, np.array(lower), np.array(upper))
                    full_mask = cv2.bitwise_or(full_mask, mask)
                best_mask = full_mask
        
        self.log(f"検出色: {best_color} (ピクセル数: {best_count})", "DEBUG")
        
        # モルフォロジー処理でノイズ除去
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        best_mask = cv2.morphologyEx(best_mask, cv2.MORPH_CLOSE, kernel)
        best_mask = cv2.morphologyEx(best_mask, cv2.MORPH_OPEN, kernel)
        
        return best_color, best_mask
    
    def extract_subpixel_line(self, img_array: np.ndarray, mask: np.ndarray) -> List[Tuple[float, float]]:
        """サブピクセル精度でグラフラインを抽出"""
        points = []
        
        # エッジ検出を使用してより精密な位置を特定
        edges = cv2.Canny(mask, 50, 150)
        
        # X座標ごとにスキャン
        for x in range(self.boundaries["start_x"], self.boundaries["end_x"]):
            # グラフ領域内でエッジを探す
            column_edges = edges[self.boundaries["top_y"]:self.boundaries["bottom_y"], x]
            column_mask = mask[self.boundaries["top_y"]:self.boundaries["bottom_y"], x]
            
            y_indices = np.where(column_mask > 0)[0]
            
            if len(y_indices) > 0:
                # エッジがある場合は優先的に使用
                edge_indices = np.where(column_edges > 0)[0]
                
                if len(edge_indices) > 0:
                    # エッジの重心を計算（サブピクセル精度）
                    weights = column_edges[edge_indices].astype(float)
                    y_subpixel = np.average(edge_indices, weights=weights)
                else:
                    # マスクの重心を計算
                    intensity = column_mask[y_indices].astype(float)
                    y_subpixel = np.average(y_indices, weights=intensity)
                
                # 実際のY座標に変換（浮動小数点）
                y_actual = float(self.boundaries["top_y"]) + y_subpixel
                points.append((float(x), y_actual))
        
        return points
    
    def apply_advanced_smoothing(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """高度なスムージング処理"""
        if len(points) < 10:
            return points
        
        x_vals = np.array([p[0] for p in points])
        y_vals = np.array([p[1] for p in points])
        
        # 1. 外れ値の除去（MAD法）
        median_y = np.median(y_vals)
        mad = np.median(np.abs(y_vals - median_y))
        threshold = 3 * mad
        
        valid_mask = np.abs(y_vals - median_y) < threshold
        x_valid = x_vals[valid_mask]
        y_valid = y_vals[valid_mask]
        
        if len(x_valid) < 10:
            return points
        
        # 2. スプライン補間（サブピクセル精度）
        # 平滑化パラメータを動的に調整
        smoothing_factor = len(x_valid) * 0.5
        
        try:
            # UnivariateSplineで滑らかな曲線を生成
            spline = UnivariateSpline(x_valid, y_valid, s=smoothing_factor)
            
            # 元のX座標に加えて、中間点も生成（2倍の密度）
            x_dense = np.linspace(x_vals.min(), x_vals.max(), len(x_vals) * 2)
            y_smooth = spline(x_dense)
            
            # 3. Savitzky-Golayフィルタで追加の平滑化
            window_length = min(51, len(y_smooth) // 4 * 2 + 1)  # 奇数にする
            if window_length >= 5:
                y_smooth = savgol_filter(y_smooth, window_length, 3)
            
            # 元のX座標での値を補間
            f_interp = interp1d(x_dense, y_smooth, kind='cubic', fill_value='extrapolate')
            y_final = f_interp(x_vals)
            
            return list(zip(x_vals, y_final))
            
        except Exception as e:
            self.log(f"スプライン補間エラー: {e}", "WARNING")
            # フォールバック: ガウシアンフィルタ
            y_smooth = gaussian_filter1d(y_vals, sigma=2.0)
            return list(zip(x_vals, y_smooth))
    
    def subpixel_y_to_value(self, y: float) -> float:
        """サブピクセルY座標を差枚数に変換"""
        height = float(self.boundaries["bottom_y"] - self.boundaries["top_y"])
        value = 30000.0 - (y - float(self.boundaries["top_y"])) * 60000.0 / height
        return np.clip(value, -30000.0, 30000.0)
    
    def extract_graph_data(self, image_path: str) -> Dict:
        """サブピクセル精度でグラフデータを抽出"""
        self.log(f"処理開始: {os.path.basename(image_path)}")
        
        try:
            # 画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # 高度な色検出とマスク生成
            color_type, mask = self.detect_graph_color_advanced(img_array)
            self.log(f"グラフ色: {color_type}", "INFO")
            
            # 最大回転数を取得（OCR部分は従来通り）
            max_rotation = 50000  # 簡略化
            
            # サブピクセル精度でライン抽出
            raw_points = self.extract_subpixel_line(img_array, mask)
            self.log(f"検出点数（生データ）: {len(raw_points)}", "INFO")
            
            # 高度なスムージング
            smooth_points = self.apply_advanced_smoothing(raw_points)
            self.log(f"スムージング後の点数: {len(smooth_points)}", "INFO")
            
            # データ変換（浮動小数点精度を維持）
            data = []
            for x, y in smooth_points:
                rotation = (x - float(self.boundaries["start_x"])) * max_rotation / \
                          float(self.boundaries["end_x"] - self.boundaries["start_x"])
                value = self.subpixel_y_to_value(y)
                data.append({
                    "rotation": rotation,
                    "value": value,
                    "x": x,
                    "y": y
                })
            
            # データ品質チェック
            is_valid = True
            quality_msg = "データ品質OK"
            
            if len(data) < 50:
                is_valid = False
                quality_msg = f"データポイントが少なすぎます: {len(data)}点"
            else:
                values = [d["value"] for d in data]
                value_std = np.std(values)
                if value_std < 100:
                    is_valid = False
                    quality_msg = "値の変動が小さすぎます"
            
            return {
                "image": os.path.basename(image_path),
                "color_type": color_type,
                "max_rotation": max_rotation,
                "points": len(smooth_points),
                "data": data,
                "quality": {
                    "is_valid": is_valid,
                    "message": quality_msg
                },
                "processing": {
                    "raw_points": len(raw_points),
                    "smooth_points": len(smooth_points),
                    "subpixel": True
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
        """抽出データをCSVに保存（高精度）"""
        if "error" in result:
            self.log(f"エラーのためCSV保存をスキップ: {result['error']}", "ERROR")
            return
        
        df = pd.DataFrame(result["data"])
        # 浮動小数点精度を保持
        df.to_csv(output_path, index=False, float_format='%.3f')
        self.log(f"CSVファイルを保存: {output_path}", "SUCCESS")
    
    def create_visualization(self, image_path: str, result: Dict, output_path: str):
        """抽出結果を可視化（サブピクセル精度を表示）"""
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
        
        # 抽出したポイントを描画（サブピクセル精度を考慮）
        if result["data"]:
            # 浮動小数点座標を整数に変換（描画用）
            points = [(int(d["x"]), int(d["y"])) for d in result["data"]]
            
            # 滑らかな線として描画
            if len(points) > 1:
                # アンチエイリアシング効果のために複数の線を描画
                for offset in [-0.5, 0, 0.5]:
                    offset_points = [(int(x + offset), int(y + offset)) for x, y in 
                                   [(d["x"], d["y"]) for d in result["data"]]]
                    alpha = int(255 * (1 - abs(offset)))
                    draw.line(offset_points, fill=(0, alpha, 0), width=2)
        
        # 情報表示
        info_y = 20
        draw.text((img.width-350, info_y), f"Points: {result.get('points', 0)}", fill=(0, 0, 0))
        info_y += 20
        draw.text((img.width-350, info_y), f"Color: {result.get('color_type', 'N/A')}", fill=(0, 0, 0))
        info_y += 20
        draw.text((img.width-350, info_y), f"Subpixel: Yes", fill=(0, 128, 0))
        
        if "processing" in result:
            info_y += 20
            draw.text((img.width-350, info_y), 
                     f"Raw/Smooth: {result['processing']['raw_points']}/{result['processing']['smooth_points']}", 
                     fill=(0, 0, 0))
        
        # 保存
        img.save(output_path)
        self.log(f"可視化画像を保存: {output_path}", "SUCCESS")

def main():
    """メイン処理"""
    print("🎯 サブピクセル精度グラフデータ抽出システム")
    print("📊 より高精度な抽出を目指します")
    
    # 入出力フォルダ設定
    input_folder = "graphs/cropped"
    output_folder = "graphs/subpixel_extracted_data"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 抽出器を初期化
    extractor = SubpixelGraphExtractor()
    
    # 精度向上が期待できる画像を処理
    test_images = [
        "S__78209160_optimal.png",  # 現在-16玉（最高精度）
        "S__78209132_optimal.png",  # 現在+87玉
        "S__78209128_optimal.png",  # 現在-111玉
        "S__78209174_optimal.png",  # 現在-118玉
        "S__78209088_optimal.png",  # 現在-131玉
    ]
    
    for file in test_images:
        input_path = os.path.join(input_folder, file)
        if not os.path.exists(input_path):
            continue
        
        print(f"\n{'='*60}")
        print(f"処理中: {file}")
        
        # データ抽出
        result = extractor.extract_graph_data(input_path)
        
        # ベースファイル名
        base_name = os.path.splitext(file)[0]
        
        # CSV保存
        csv_path = os.path.join(output_folder, f"{base_name}_subpixel_data.csv")
        extractor.save_to_csv(result, csv_path)
        
        # 可視化
        vis_path = os.path.join(output_folder, f"{base_name}_subpixel_visualization.png")
        extractor.create_visualization(input_path, result, vis_path)
        
        # 結果サマリー
        if result["data"]:
            values = [d["value"] for d in result["data"]]
            print(f"\n📊 抽出結果:")
            print(f"  最大値: {max(values):.1f}")
            print(f"  最終値: {values[-1]:.1f}")
            print(f"  品質: {result['quality']['message']}")

if __name__ == "__main__":
    main()