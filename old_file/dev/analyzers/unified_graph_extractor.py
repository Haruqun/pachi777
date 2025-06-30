#!/usr/bin/env python3
"""
統合グラフデータ抽出システム - 最終値精度改善版
- 終端領域の特別処理
- 外挿法による最終値予測
- 適応的検出感度調整
"""

import os
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import cv2
import pandas as pd
from typing import Tuple, List, Dict, Optional
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d, UnivariateSpline
from scipy.signal import savgol_filter, medfilt
from scipy.ndimage import gaussian_filter1d
import warnings
warnings.filterwarnings('ignore')

class UnifiedGraphExtractor:
    """統合グラフデータ抽出システム"""
    
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
        
        # 終端処理のパラメータ
        self.edge_margin = 30  # 終端からの特別処理領域
        self.extrapolation_points = 20  # 外挿に使用するポイント数
        
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
            print(f"[{level}] {message}")
    
    def detect_graph_color_enhanced(self, img_array: np.ndarray) -> Tuple[str, np.ndarray, Dict]:
        """改善された色検出（終端領域での感度向上）"""
        # BGRからHSVに変換
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        
        # 色範囲の定義（HSV）- より広い範囲で検出
        color_ranges = {
            "pink": [(140, 20, 20), (175, 255, 255)],  # 彩度とを下げて検出感度UP
            "purple": [(120, 20, 20), (150, 255, 255)],
            "blue": [(85, 20, 20), (125, 255, 255)],
            "cyan": [(75, 20, 20), (105, 255, 255)]
        }
        
        # グラフ領域内でサンプリング
        roi_hsv = img_hsv[
            self.boundaries["top_y"]:self.boundaries["bottom_y"],
            self.boundaries["start_x"]:self.boundaries["end_x"]-self.edge_margin
        ]
        
        color_counts = {}
        best_mask = None
        best_color = None
        best_count = 0
        color_properties = {}
        
        for color_name, (lower, upper) in color_ranges.items():
            lower = np.array(lower)
            upper = np.array(upper)
            
            # HSVマスク
            mask_roi = cv2.inRange(roi_hsv, lower, upper)
            count = np.sum(mask_roi > 0)
            color_counts[color_name] = count
            
            if count > best_count:
                best_count = count
                best_color = color_name
                # フルサイズのマスクを作成
                best_mask = cv2.inRange(img_hsv, lower, upper)
                
                # 色の特性を保存
                masked_pixels = roi_hsv[mask_roi > 0]
                if len(masked_pixels) > 0:
                    color_properties[color_name] = {
                        "mean_hue": np.mean(masked_pixels[:, 0]),
                        "mean_saturation": np.mean(masked_pixels[:, 1]),
                        "mean_value": np.mean(masked_pixels[:, 2]),
                        "std_hue": np.std(masked_pixels[:, 0]),
                        "lower": lower.tolist(),
                        "upper": upper.tolist()
                    }
        
        # ノイズ除去
        kernel = np.ones((3, 3), np.uint8)
        best_mask = cv2.morphologyEx(best_mask, cv2.MORPH_CLOSE, kernel)
        best_mask = cv2.morphologyEx(best_mask, cv2.MORPH_OPEN, kernel)
        
        self.log(f"色検出結果: {color_counts}", "DEBUG")
        
        return best_color, best_mask, color_properties
    
    def extract_line_with_edge_handling(self, img_array: np.ndarray, mask: np.ndarray, 
                                      color_type: str, color_props: Dict) -> List[Tuple[float, float]]:
        """エッジ処理を強化したライン抽出"""
        points = []
        edge_points = []  # 終端領域の特別処理用
        
        # エッジ検出でグラフラインを強調
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        
        # 終端領域の開始位置
        edge_start = self.boundaries["end_x"] - self.edge_margin
        
        # 通常領域のスキャン
        for x in range(self.boundaries["start_x"], edge_start):
            y_point = self._detect_line_at_x(x, mask, edges, adaptive=False)
            if y_point is not None:
                points.append((float(x), y_point))
        
        # 終端領域の特別処理
        if color_type in color_props:
            # 終端領域ではより感度を上げて検出
            props = color_props[color_type]
            
            # より広い色範囲でマスクを再作成
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            
            # 彩度と明度の範囲を広げる
            lower_adaptive = np.array([
                props["lower"][0] - 5,  # 色相を少し広げる
                max(10, props["lower"][1] - 10),  # 彩度を下げる
                max(10, props["lower"][2] - 10)   # 明度を下げる
            ])
            upper_adaptive = np.array([
                props["upper"][0] + 5,
                255,
                255
            ])
            
            # 終端領域用の適応的マスク
            adaptive_mask = cv2.inRange(img_hsv, lower_adaptive, upper_adaptive)
            
            # 終端領域をスキャン
            for x in range(edge_start, self.boundaries["end_x"] + 10):  # 少しオーバーランさせる
                if x >= img_array.shape[1]:
                    break
                
                # 複数の方法で検出を試みる
                y_point = self._detect_line_at_x_adaptive(x, mask, adaptive_mask, edges)
                if y_point is not None:
                    edge_points.append((float(x), y_point))
        
        # 終端領域でポイントが見つからない場合は外挿
        if len(edge_points) < 5 and len(points) > self.extrapolation_points:
            self.log("終端領域でのライン検出が不十分。外挿を実行します。", "WARNING")
            extrapolated_points = self._extrapolate_to_edge(points)
            edge_points.extend(extrapolated_points)
        
        # 結合
        all_points = points + edge_points
        
        # ソートして重複を除去
        all_points = sorted(list(set(all_points)), key=lambda p: p[0])
        
        return all_points
    
    def _detect_line_at_x(self, x: int, mask: np.ndarray, edges: np.ndarray, 
                         adaptive: bool = False) -> Optional[float]:
        """X座標でのライン検出"""
        # グラフ領域内でマスクをチェック
        column_mask = mask[self.boundaries["top_y"]:self.boundaries["bottom_y"], x]
        column_edge = edges[self.boundaries["top_y"]:self.boundaries["bottom_y"], x]
        
        # エッジ情報を優先的に使用
        if np.any(column_edge > 0):
            y_indices = np.where(column_edge > 0)[0]
        else:
            y_indices = np.where(column_mask > 0)[0]
        
        if len(y_indices) == 0 and adaptive:
            # 適応的検出：しきい値を下げて再検出
            column_gray = cv2.cvtColor(
                mask[self.boundaries["top_y"]:self.boundaries["bottom_y"], x:x+1], 
                cv2.COLOR_GRAY2BGR
            )[:, 0, 0]
            y_indices = np.where(column_gray > 20)[0]  # より低いしきい値
        
        if len(y_indices) > 0:
            # 連続した領域をグループ化
            groups = self._group_consecutive_indices(y_indices)
            
            if groups:
                # 最大のグループを選択
                largest_group = max(groups, key=len)
                
                # サブピクセル精度で位置を計算
                if len(largest_group) > 1:
                    y_subpixel = self._gaussian_subpixel_peak(column_mask, largest_group)
                else:
                    y_subpixel = float(largest_group[0])
                
                # 実際のY座標に変換
                y_actual = float(self.boundaries["top_y"]) + y_subpixel
                return y_actual
        
        return None
    
    def _detect_line_at_x_adaptive(self, x: int, mask: np.ndarray, 
                                  adaptive_mask: np.ndarray, edges: np.ndarray) -> Optional[float]:
        """適応的なライン検出（終端領域用）"""
        # 複数のマスクを試す
        masks_to_try = [mask, adaptive_mask, edges]
        
        for current_mask in masks_to_try:
            if x < current_mask.shape[1]:
                y_point = self._detect_line_at_x(x, current_mask, edges, adaptive=True)
                if y_point is not None:
                    return y_point
        
        return None
    
    def _group_consecutive_indices(self, indices: np.ndarray) -> List[List[int]]:
        """連続したインデックスをグループ化"""
        if len(indices) == 0:
            return []
        
        groups = []
        current_group = [indices[0]]
        
        for i in range(1, len(indices)):
            if indices[i] - indices[i-1] <= 3:
                current_group.append(indices[i])
            else:
                groups.append(current_group)
                current_group = [indices[i]]
        groups.append(current_group)
        
        return groups
    
    def _gaussian_subpixel_peak(self, column_data: np.ndarray, indices: List[int]) -> float:
        """ガウシアンフィッティングによるサブピクセル位置推定"""
        if len(indices) < 3:
            return float(np.mean(indices))
        
        # インデックス周辺のデータを取得
        min_idx = max(0, min(indices) - 2)
        max_idx = min(len(column_data), max(indices) + 3)
        
        y_range = np.arange(min_idx, max_idx)
        values = column_data[min_idx:max_idx].astype(float)
        
        if np.sum(values) == 0:
            return float(np.mean(indices))
        
        # 重み付き平均でピーク位置を推定
        peak_pos = np.average(y_range, weights=values)
        
        return peak_pos
    
    def _extrapolate_to_edge(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """最終値を外挿で推定"""
        # 最後のN点を使用
        recent_points = points[-self.extrapolation_points:]
        x_vals = np.array([p[0] for p in recent_points])
        y_vals = np.array([p[1] for p in recent_points])
        
        # 線形回帰で傾向を推定
        coeffs = np.polyfit(x_vals, y_vals, deg=2)  # 2次多項式でフィット
        poly = np.poly1d(coeffs)
        
        # 終端まで外挿
        extrapolated_points = []
        last_x = int(points[-1][0])
        
        for x in range(last_x + 1, self.boundaries["end_x"] + 5):
            if x > self.boundaries["end_x"] + 10:  # 過度な外挿を防ぐ
                break
            y_pred = poly(x)
            # Y座標が妥当な範囲内かチェック
            if self.boundaries["top_y"] <= y_pred <= self.boundaries["bottom_y"]:
                extrapolated_points.append((float(x), float(y_pred)))
        
        self.log(f"外挿により{len(extrapolated_points)}点を追加", "INFO")
        
        return extrapolated_points
    
    def adaptive_smoothing_with_edge_protection(self, points: List[Tuple[float, float]], 
                                              color_type: str) -> List[Tuple[float, float]]:
        """エッジ保護を強化した適応的スムージング"""
        if len(points) < 5:
            return points
        
        x_vals = np.array([p[0] for p in points])
        y_vals = np.array([p[1] for p in points])
        
        # 終端領域の識別
        edge_start_idx = np.where(x_vals >= self.boundaries["end_x"] - self.edge_margin)[0]
        
        if len(edge_start_idx) > 0:
            # 終端領域とそれ以外を分離
            edge_start = edge_start_idx[0]
            
            # 通常領域のスムージング
            if edge_start > 5:
                normal_x = x_vals[:edge_start]
                normal_y = y_vals[:edge_start]
                
                # 通常のスムージング
                normal_y_smooth = self._robust_smooth(normal_x, normal_y, color_type)
                
                # 終端領域は最小限の処理
                edge_x = x_vals[edge_start:]
                edge_y = y_vals[edge_start:]
                
                # 終端領域は軽いメディアンフィルタのみ
                if len(edge_y) > 3:
                    edge_y_smooth = medfilt(edge_y, kernel_size=3)
                else:
                    edge_y_smooth = edge_y
                
                # 結合
                y_smooth = np.concatenate([normal_y_smooth, edge_y_smooth])
            else:
                # ほとんどが終端領域の場合
                y_smooth = medfilt(y_vals, kernel_size=3) if len(y_vals) > 3 else y_vals
        else:
            # 終端領域がない場合（通常のスムージング）
            y_smooth = self._robust_smooth(x_vals, y_vals, color_type)
        
        return list(zip(x_vals, y_smooth))
    
    def _robust_smooth(self, x_vals: np.ndarray, y_vals: np.ndarray, color_type: str) -> np.ndarray:
        """ロバストなスムージング"""
        # 外れ値除去
        y_cleaned = self._hampel_filter(y_vals)
        
        # 色タイプに応じた処理
        if color_type == "pink":
            # ピンクグラフは変動が大きいので保守的に
            window_size = min(7, len(y_vals) // 8)
        else:
            # 青系グラフは積極的に
            window_size = min(11, len(y_vals) // 5)
        
        if window_size % 2 == 0:
            window_size += 1
        
        if window_size >= 3 and len(y_cleaned) >= window_size:
            try:
                # Savitzky-Golayフィルタ
                y_smooth = savgol_filter(y_cleaned, window_size, 2)
                return y_smooth
            except:
                return y_cleaned
        
        return y_cleaned
    
    def _hampel_filter(self, y_vals: np.ndarray, window_size: int = 7, n_sigmas: float = 3.0) -> np.ndarray:
        """Hampelフィルタによる外れ値除去"""
        y_cleaned = y_vals.copy()
        
        if window_size % 2 == 0:
            window_size += 1
        
        if len(y_vals) >= window_size:
            for i in range(len(y_vals)):
                # ウィンドウ内のデータ
                start = max(0, i - window_size // 2)
                end = min(len(y_vals), i + window_size // 2 + 1)
                window = y_vals[start:end]
                
                # 中央値と絶対偏差中央値（MAD）
                median = np.median(window)
                mad = np.median(np.abs(window - median))
                
                # 外れ値判定
                if mad > 0:
                    if np.abs(y_vals[i] - median) > n_sigmas * 1.4826 * mad:
                        y_cleaned[i] = median
        
        return y_cleaned
    
    def y_to_value(self, y: float) -> float:
        """Y座標を差枚数に変換"""
        height = float(self.boundaries["bottom_y"] - self.boundaries["top_y"])
        value = 30000.0 - (y - float(self.boundaries["top_y"])) * 60000.0 / height
        return np.clip(value, -30000.0, 30000.0)
    
    def extract_graph_data(self, image_path: str) -> Dict:
        """統合手法でグラフデータを抽出"""
        self.log(f"処理開始: {os.path.basename(image_path)}")
        
        try:
            # 画像読み込み
            img = Image.open(image_path)
            
            # 画像前処理
            img = img.filter(ImageFilter.MedianFilter(size=3))
            img_array = np.array(img)
            
            # 色検出（改善版）
            color_type, mask, color_props = self.detect_graph_color_enhanced(img_array)
            self.log(f"グラフ色: {color_type}", "INFO")
            
            # 最大値を取得（簡略化）
            max_rotation = 50000
            
            # エッジ処理を強化したライン抽出
            raw_points = self.extract_line_with_edge_handling(img_array, mask, color_type, color_props)
            self.log(f"検出点数（生データ）: {len(raw_points)}", "INFO")
            
            # エッジ保護付きスムージング
            smooth_points = self.adaptive_smoothing_with_edge_protection(raw_points, color_type)
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
            
            # 最終値の情報
            if data:
                final_x = data[-1]["x"]
                final_value = data[-1]["value"]
                distance_from_edge = self.boundaries["end_x"] - final_x
                self.log(f"最終値: {final_value:.1f} (X={final_x:.1f}, 端から{distance_from_edge:.1f}px)", "INFO")
            
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
                    "method": "unified_with_edge_handling",
                    "raw_points": len(raw_points),
                    "smooth_points": len(smooth_points),
                    "final_x": data[-1]["x"] if data else None,
                    "distance_from_edge": distance_from_edge if data else None
                }
            }
            
        except Exception as e:
            self.log(f"エラーが発生しました: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()
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
        
        # 最終値が端に近いかチェック
        final_x = data[-1]["x"]
        distance_from_edge = self.boundaries["end_x"] - final_x
        if distance_from_edge > 50:
            return False, f"最終値が端から離れすぎています: {distance_from_edge:.0f}px"
        
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
        
        # 終端処理領域を表示
        edge_start = self.boundaries["end_x"] - self.edge_margin
        draw.rectangle(
            [(edge_start, self.boundaries["top_y"]),
             (self.boundaries["end_x"], self.boundaries["bottom_y"])],
            outline=(255, 165, 0), width=1
        )
        
        # 抽出したポイントを描画
        if result["data"]:
            points = [(int(round(d["x"])), int(round(d["y"]))) for d in result["data"]]
            if len(points) > 1:
                draw.line(points, fill=(0, 0, 255), width=3)
            
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
        draw.text((img.width-400, info_y), f"Points: {result.get('points', 0)}", fill=(0, 0, 0))
        info_y += 20
        draw.text((img.width-400, info_y), f"Color: {result.get('color_type', 'N/A')}", fill=(0, 0, 0))
        info_y += 20
        draw.text((img.width-400, info_y), f"Method: Unified+Edge", fill=(0, 0, 255))
        
        if "processing" in result and result["processing"].get("distance_from_edge") is not None:
            info_y += 20
            distance = result["processing"]["distance_from_edge"]
            color = (0, 128, 0) if distance < 30 else (255, 165, 0) if distance < 50 else (255, 0, 0)
            draw.text((img.width-400, info_y), f"Edge Distance: {distance:.0f}px", fill=color)
        
        if "quality" in result:
            info_y += 20
            quality_color = (0, 128, 0) if result["quality"]["is_valid"] else (255, 0, 0)
            draw.text((img.width-400, info_y), f"Quality: {result['quality']['message']}", fill=quality_color)
        
        # 保存
        img.save(output_path)
        self.log(f"可視化画像を保存: {output_path}", "SUCCESS")

def main():
    """メイン処理"""
    print("統合グラフデータ抽出システム - 最終値精度改善版")
    print("エッジ処理と外挿法により高精度な最終値読み取りを実現")
    
    # 入出力フォルダ設定
    input_folder = "graphs/cropped"
    output_folder = "graphs/unified_extracted_data"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 抽出器を初期化
    extractor = UnifiedGraphExtractor()
    
    # すべての画像を処理
    image_files = [f for f in os.listdir(input_folder) if f.endswith('.png')]
    
    success_count = 0
    error_count = 0
    edge_distances = []
    
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
        
        # エッジ距離を記録
        if "processing" in result and result["processing"].get("distance_from_edge") is not None:
            edge_distances.append(result["processing"]["distance_from_edge"])
        
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
            print(f"\n抽出結果:")
            print(f"  最大値: {max(values):.1f}")
            print(f"  最終値: {values[-1]:.1f}")
            if "processing" in result and result["processing"].get("distance_from_edge") is not None:
                print(f"  端からの距離: {result['processing']['distance_from_edge']:.1f}px")
            print(f"  品質: {result['quality']['message']}")
    
    # 全体サマリー
    print(f"\n{'='*60}")
    print(f"処理完了: 成功 {success_count}/{len(image_files)}, エラー {error_count}/{len(image_files)}")
    
    if edge_distances:
        print(f"\n終端精度統計:")
        print(f"  平均距離: {np.mean(edge_distances):.1f}px")
        print(f"  標準偏差: {np.std(edge_distances):.1f}px")
        print(f"  最大距離: {max(edge_distances):.1f}px")
        print(f"  30px以内: {sum(1 for d in edge_distances if d < 30)}/{len(edge_distances)}")

if __name__ == "__main__":
    main()