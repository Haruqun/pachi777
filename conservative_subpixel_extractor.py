#!/usr/bin/env python3
"""
保守的なサブピクセル精度グラフデータ抽出システム
- エッジ部分の保護
- 控えめなスムージング
- データの連続性を重視
"""

import os
import json
import numpy as np
from PIL import Image, ImageDraw
import cv2
import pandas as pd
from typing import Tuple, List, Dict, Optional
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
import warnings
warnings.filterwarnings('ignore')

class ConservativeSubpixelExtractor:
    """保守的なサブピクセル精度抽出システム"""
    
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
    
    def detect_graph_color_hsv(self, img_array: np.ndarray) -> Tuple[str, np.ndarray]:
        """HSV色空間での色検出（improved_graph_data_extractorと同じ）"""
        # BGRからHSVに変換
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        
        # グラフ領域内でサンプリング
        roi = img_hsv[
            self.boundaries["zero_y"]-50:self.boundaries["zero_y"]+50,
            self.boundaries["start_x"]:self.boundaries["end_x"]
        ]
        
        # 色範囲の定義（HSV）
        color_ranges = {
            "pink": [(140, 30, 30), (170, 255, 255)],
            "purple": [(120, 30, 30), (150, 255, 255)],
            "blue": [(90, 30, 30), (120, 255, 255)],
            "cyan": [(80, 30, 30), (100, 255, 255)]
        }
        
        color_counts = {}
        best_mask = None
        best_color = None
        best_count = 0
        
        for color_name, (lower, upper) in color_ranges.items():
            lower = np.array(lower)
            upper = np.array(upper)
            mask_roi = cv2.inRange(roi, lower, upper)
            count = np.sum(mask_roi > 0)
            color_counts[color_name] = count
            
            if count > best_count:
                best_count = count
                best_color = color_name
                # フルサイズのマスクを作成
                best_mask = cv2.inRange(img_hsv, lower, upper)
        
        self.log(f"色検出結果: {color_counts}", "DEBUG")
        
        return best_color, best_mask
    
    def extract_line_with_subpixel(self, img_array: np.ndarray, mask: np.ndarray) -> List[Tuple[float, float]]:
        """サブピクセル精度でライン抽出（保守的アプローチ）"""
        points = []
        
        # X座標ごとにスキャン
        for x in range(self.boundaries["start_x"], self.boundaries["end_x"]):
            # グラフ領域内でマスクをチェック
            column_mask = mask[self.boundaries["top_y"]:self.boundaries["bottom_y"], x]
            y_indices = np.where(column_mask > 0)[0]
            
            if len(y_indices) > 0:
                # 連続した領域をグループ化
                groups = []
                current_group = [y_indices[0]]
                
                for i in range(1, len(y_indices)):
                    if y_indices[i] - y_indices[i-1] <= 3:
                        current_group.append(y_indices[i])
                    else:
                        groups.append(current_group)
                        current_group = [y_indices[i]]
                groups.append(current_group)
                
                # 最大のグループを選択
                largest_group = max(groups, key=len)
                
                # グループの重み付き中心を計算（サブピクセル精度）
                if len(largest_group) > 1:
                    # ピクセル値で重み付け
                    weights = []
                    for y_idx in largest_group:
                        pixel_value = column_mask[y_idx]
                        weights.append(pixel_value)
                    
                    weights = np.array(weights, dtype=float)
                    if np.sum(weights) > 0:
                        y_subpixel = np.average(largest_group, weights=weights)
                    else:
                        y_subpixel = float(np.mean(largest_group))
                else:
                    y_subpixel = float(largest_group[0])
                
                # 実際のY座標に変換
                y_actual = float(self.boundaries["top_y"]) + y_subpixel
                points.append((float(x), y_actual))
        
        return points
    
    def conservative_smoothing(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """保守的なスムージング処理"""
        if len(points) < 5:
            return points
        
        x_vals = np.array([p[0] for p in points])
        y_vals = np.array([p[1] for p in points])
        
        # 1. まず大きな外れ値のみを除去（非常に保守的）
        # 移動中央値を使用
        window_size = min(21, len(y_vals) // 3)
        if window_size >= 3 and window_size % 2 == 0:
            window_size += 1
        
        if window_size >= 3:
            # 移動中央値
            med_filtered = np.zeros_like(y_vals)
            half_window = window_size // 2
            
            for i in range(len(y_vals)):
                start = max(0, i - half_window)
                end = min(len(y_vals), i + half_window + 1)
                med_filtered[i] = np.median(y_vals[start:end])
            
            # 大きな逸脱のみを修正
            deviation = np.abs(y_vals - med_filtered)
            threshold = np.percentile(deviation, 95)  # 95パーセンタイルを閾値に
            
            y_cleaned = y_vals.copy()
            outlier_mask = deviation > threshold
            if np.any(outlier_mask):
                # 外れ値を中央値で置換
                y_cleaned[outlier_mask] = med_filtered[outlier_mask]
        else:
            y_cleaned = y_vals
        
        # 2. エッジ部分を保護しながらスムージング
        # エッジ部分（最初と最後の10%）は元の値を重視
        edge_size = max(5, int(len(points) * 0.1))
        
        # Savitzky-Golayフィルタで軽いスムージング
        window_length = min(11, len(y_cleaned) // 4 * 2 + 1)
        if window_length >= 5 and window_length % 2 == 1:
            try:
                y_smooth = savgol_filter(y_cleaned, window_length, 2)  # 2次多項式
                
                # エッジ部分は元の値と混合
                blend_weights = np.ones(len(y_smooth))
                # 最初の部分
                for i in range(edge_size):
                    blend_weights[i] = i / edge_size
                # 最後の部分
                for i in range(edge_size):
                    blend_weights[-(i+1)] = i / edge_size
                
                # ブレンド
                y_final = y_cleaned * (1 - blend_weights) + y_smooth * blend_weights
                
                return list(zip(x_vals, y_final))
                
            except Exception as e:
                self.log(f"スムージングエラー: {e}", "WARNING")
                return points
        else:
            return list(zip(x_vals, y_cleaned))
    
    def y_to_value(self, y: float) -> float:
        """Y座標を差枚数に変換（浮動小数点精度）"""
        height = float(self.boundaries["bottom_y"] - self.boundaries["top_y"])
        value = 30000.0 - (y - float(self.boundaries["top_y"])) * 60000.0 / height
        return np.clip(value, -30000.0, 30000.0)
    
    def extract_graph_data(self, image_path: str) -> Dict:
        """保守的なサブピクセル精度でグラフデータを抽出"""
        self.log(f"処理開始: {os.path.basename(image_path)}")
        
        try:
            # 画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # グラフの色を判定（HSV使用）
            color_type, mask = self.detect_graph_color_hsv(img_array)
            self.log(f"グラフ色: {color_type}", "INFO")
            
            # 最大値を取得
            max_rotation = 50000  # 簡略化
            self.log(f"最大回転数: {max_rotation}", "INFO")
            
            # サブピクセル精度でライン抽出
            raw_points = self.extract_line_with_subpixel(img_array, mask)
            self.log(f"検出点数（生データ）: {len(raw_points)}", "INFO")
            
            # 保守的なスムージング
            smooth_points = self.conservative_smoothing(raw_points)
            self.log(f"スムージング後の点数: {len(smooth_points)}", "INFO")
            
            # データ変換
            data = []
            for x, y in smooth_points:
                rotation = (x - float(self.boundaries["start_x"])) * max_rotation / \
                          float(self.boundaries["end_x"] - self.boundaries["start_x"])
                value = self.y_to_value(y)
                data.append({
                    "rotation": rotation,
                    "value": value,
                    "x": x,
                    "y": y
                })
            
            # データ品質チェック
            is_valid, quality_msg = self.validate_data_quality(data)
            
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
                    "method": "conservative_subpixel",
                    "raw_points": len(raw_points),
                    "smooth_points": len(smooth_points)
                }
            }
            
        except Exception as e:
            self.log(f"エラーが発生しました: {str(e)}", "ERROR")
            return {
                "image": os.path.basename(image_path),
                "error": str(e),
                "data": []
            }
    
    def validate_data_quality(self, data: List[dict]) -> Tuple[bool, str]:
        """データ品質をチェック"""
        if not data:
            return False, "データが空です"
        
        if len(data) < 10:
            return False, f"データポイントが少なすぎます: {len(data)}点"
        
        # 値の範囲チェック
        values = [d["value"] for d in data]
        if all(v == values[0] for v in values):
            return False, "すべての値が同一です"
        
        # 最初と最後の値の差をチェック
        if len(values) >= 2:
            first_last_diff = abs(values[0] - values[-1])
            if first_last_diff < 100:
                return False, "値の変動が小さすぎます"
        
        return True, "データ品質OK"
    
    def save_to_csv(self, result: Dict, output_path: str):
        """抽出データをCSVに保存"""
        if "error" in result:
            self.log(f"エラーのためCSV保存をスキップ: {result['error']}", "ERROR")
            return
        
        df = pd.DataFrame(result["data"])
        df.to_csv(output_path, index=False, float_format='%.2f')
        self.log(f"CSVファイルを保存: {output_path}", "SUCCESS")
    
    def create_visualization(self, image_path: str, result: Dict, output_path: str):
        """抽出結果を可視化"""
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
            # 浮動小数点座標を整数に変換
            points = [(int(round(d["x"])), int(round(d["y"]))) for d in result["data"]]
            if len(points) > 1:
                draw.line(points, fill=(0, 255, 0), width=3)
            
            # 始点と終点を強調
            if points:
                # 始点
                draw.ellipse(
                    [(points[0][0]-5, points[0][1]-5),
                     (points[0][0]+5, points[0][1]+5)],
                    fill=(0, 255, 0), outline=(0, 0, 0)
                )
                # 終点
                draw.ellipse(
                    [(points[-1][0]-5, points[-1][1]-5),
                     (points[-1][0]+5, points[-1][1]+5)],
                    fill=(255, 0, 0), outline=(0, 0, 0)
                )
        
        # 情報表示
        info_y = 20
        draw.text((img.width-350, info_y), f"Points: {result.get('points', 0)}", fill=(0, 0, 0))
        info_y += 20
        draw.text((img.width-350, info_y), f"Color: {result.get('color_type', 'N/A')}", fill=(0, 0, 0))
        info_y += 20
        draw.text((img.width-350, info_y), f"Method: Conservative Subpixel", fill=(0, 0, 128))
        
        if "quality" in result:
            info_y += 20
            quality_color = (0, 128, 0) if result["quality"]["is_valid"] else (255, 0, 0)
            draw.text((img.width-350, info_y), f"Quality: {result['quality']['message']}", fill=quality_color)
        
        # 保存
        img.save(output_path)
        self.log(f"可視化画像を保存: {output_path}", "SUCCESS")

def main():
    """メイン処理"""
    print("🎯 保守的サブピクセル精度グラフデータ抽出システム")
    print("📊 安定性を重視した高精度抽出を行います")
    
    # 入出力フォルダ設定
    input_folder = "graphs/cropped"
    output_folder = "graphs/conservative_subpixel_data"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 抽出器を初期化
    extractor = ConservativeSubpixelExtractor()
    
    # すべての画像を処理
    image_files = [f for f in os.listdir(input_folder) if f.endswith('.png')]
    
    success_count = 0
    error_count = 0
    
    for file in sorted(image_files):
        input_path = os.path.join(input_folder, file)
        
        print(f"\n{'='*60}")
        print(f"処理中: {file}")
        
        # データ抽出
        result = extractor.extract_graph_data(input_path)
        
        if "error" in result:
            error_count += 1
            continue
        
        success_count += 1
        
        # ベースファイル名
        base_name = os.path.splitext(file)[0]
        
        # CSV保存
        csv_path = os.path.join(output_folder, f"{base_name}_data.csv")
        extractor.save_to_csv(result, csv_path)
        
        # 可視化
        vis_path = os.path.join(output_folder, f"{base_name}_visualization.png")
        extractor.create_visualization(input_path, result, vis_path)
        
        # 結果サマリー
        if result["data"]:
            values = [d["value"] for d in result["data"]]
            print(f"\n📊 抽出結果:")
            print(f"  最大値: {max(values):.1f}")
            print(f"  最終値: {values[-1]:.1f}")
            print(f"  品質: {result['quality']['message']}")
    
    # 全体サマリー
    print(f"\n{'='*60}")
    print(f"処理完了: 成功 {success_count}/{len(image_files)}, エラー {error_count}/{len(image_files)}")

if __name__ == "__main__":
    main()