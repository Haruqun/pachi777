#!/usr/bin/env python3
"""
高度なグラフデータ抽出システム
- 適応的しきい値処理
- グラフパターン別の最適化
- エッジ強調アルゴリズム
- 多段階スムージング
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

class AdvancedGraphExtractor:
    """高度なグラフデータ抽出システム"""
    
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
    
    def detect_graph_color_advanced(self, img_array: np.ndarray) -> Tuple[str, np.ndarray, Dict]:
        """高度な色検出（複数の色空間を活用）"""
        # BGRからHSVに変換
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        img_lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        
        # グラフ領域全体でサンプリング（より広範囲で検出）
        roi_hsv = img_hsv[
            self.boundaries["top_y"]:self.boundaries["bottom_y"],
            self.boundaries["start_x"]:self.boundaries["end_x"]
        ]
        
        # より精密な色範囲の定義（HSV）- ピンク検出を強化
        color_ranges = {
            "pink": [(150, 40, 80), (170, 255, 255)],  # より厳密なピンク範囲
            "purple": [(120, 40, 80), (150, 255, 255)],
            "blue": [(90, 40, 80), (120, 255, 255)],
            "cyan": [(80, 40, 80), (100, 255, 255)]
        }
        
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
                        "std_hue": np.std(masked_pixels[:, 0])
                    }
        
        # 適応的しきい値の調整
        if best_color and best_color in color_properties:
            props = color_properties[best_color]
            # 色の特性に基づいてマスクを微調整
            if props["std_hue"] < 10:  # 色相が安定している場合
                # より厳密な範囲で再検出
                h_center = props["mean_hue"]
                h_range = max(5, props["std_hue"] * 2)
                lower_adaptive = np.array([h_center - h_range, 30, 30])
                upper_adaptive = np.array([h_center + h_range, 255, 255])
                best_mask = cv2.inRange(img_hsv, lower_adaptive, upper_adaptive)
        
        # ノイズ除去
        kernel = np.ones((3, 3), np.uint8)
        best_mask = cv2.morphologyEx(best_mask, cv2.MORPH_CLOSE, kernel)
        best_mask = cv2.morphologyEx(best_mask, cv2.MORPH_OPEN, kernel)
        
        self.log(f"色検出結果: {color_counts}", "DEBUG")
        
        return best_color, best_mask, color_properties
    
    def extract_line_advanced(self, img_array: np.ndarray, mask: np.ndarray, color_props: Dict) -> List[Tuple[float, float]]:
        """高度なライン抽出（ピーク検出重視）"""
        points = []
        
        # X座標ごとにスキャン
        for x in range(self.boundaries["start_x"], self.boundaries["end_x"]):
            # グラフ領域内でマスクをチェック
            column_mask = mask[self.boundaries["top_y"]:self.boundaries["bottom_y"], x]
            
            # マスクされたピクセルの重み付き中心を計算
            y_indices = np.where(column_mask > 0)[0]
            
            if len(y_indices) > 0:
                # 元画像から強度値を取得
                column_img = img_array[self.boundaries["top_y"]:self.boundaries["bottom_y"], x]
                
                # ピンクラインの強度を計算（RGB値の合計）
                intensities = []
                for y_idx in y_indices:
                    if y_idx < len(column_img):
                        pixel = column_img[y_idx]
                        # ピンクラインの特徴：R > G, R > B
                        if len(pixel) >= 3:
                            r, g, b = pixel[0], pixel[1], pixel[2]
                            intensity = float(r) - 0.5 * float(g) - 0.5 * float(b)  # ピンク強調
                            intensities.append(intensity)
                        else:
                            intensities.append(0.0)
                    else:
                        intensities.append(0.0)
                
                if intensities and max(intensities) > 0:
                    # 最大強度の位置を重み付き平均で精密に計算
                    max_intensity = max(intensities)
                    threshold = max_intensity * 0.7  # 最大強度の70%以上
                    
                    weighted_sum = 0.0
                    weight_sum = 0.0
                    
                    for i, intensity in enumerate(intensities):
                        if intensity >= threshold:
                            weight = intensity ** 2  # 二乗で重み付け
                            weighted_sum += y_indices[i] * weight
                            weight_sum += weight
                    
                    if weight_sum > 0:
                        y_subpixel = weighted_sum / weight_sum
                        
                        # ピーク位置の微調整
                        if len(intensities) > 2:
                            peak_idx = intensities.index(max_intensity)
                            if 0 < peak_idx < len(intensities) - 1:
                                # 3点パラボラフィッティングで真のピーク位置を推定
                                y1, y2, y3 = intensities[peak_idx-1], intensities[peak_idx], intensities[peak_idx+1]
                                if y1 != y3:  # 分母が0でない場合
                                    offset = 0.5 * (y1 - y3) / (y1 - 2*y2 + y3)
                                    y_subpixel = y_indices[peak_idx] + offset
                        
                        # 実際のY座標に変換
                        y_actual = float(self.boundaries["top_y"]) + y_subpixel
                        points.append((float(x), y_actual))
        
        return points
    
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
        
        # ガウシアンフィッティング（簡易版）
        if len(y_range) >= 5:
            try:
                # 対数変換してガウシアンの係数を推定
                log_values = np.log(values + 1e-10)
                coeffs = np.polyfit(y_range, log_values, 2)
                if coeffs[0] < 0:  # 上に凸の放物線
                    peak_pos = -coeffs[1] / (2 * coeffs[0])
                    peak_pos = np.clip(peak_pos, min_idx, max_idx - 1)
            except:
                pass
        
        return peak_pos
    
    def adaptive_smoothing(self, points: List[Tuple[float, float]], color_type: str) -> List[Tuple[float, float]]:
        """適応的スムージング（ピーク保護重視）"""
        if len(points) < 5:
            return points
        
        x_vals = np.array([p[0] for p in points])
        y_vals = np.array([p[1] for p in points])
        
        # ピークとボトムを検出して保護
        peaks = self._detect_peaks(y_vals)
        bottoms = self._detect_peaks(-y_vals)  # 反転してボトムを検出
        
        # 重要点（ピーク・ボトム）のインデックス
        important_indices = set(peaks) | set(bottoms)
        
        # 軽微なスムージングのみ適用（ピーク保護）
        y_smooth = y_vals.copy()
        
        # 重要点以外のみ軽くスムージング
        for i in range(2, len(y_vals) - 2):
            if i not in important_indices:
                # 5点移動平均（重み付き）
                weights = [0.1, 0.2, 0.4, 0.2, 0.1]
                window = y_vals[i-2:i+3]
                y_smooth[i] = np.average(window, weights=weights)
        
        # エッジ部分はそのまま保持
        y_smooth[0] = y_vals[0]
        y_smooth[1] = y_vals[1]
        y_smooth[-2] = y_vals[-2]
        y_smooth[-1] = y_vals[-1]
        
        return list(zip(x_vals, y_smooth))
    
    def _detect_peaks(self, y_vals: np.ndarray, min_distance: int = 5) -> List[int]:
        """ピーク検出"""
        peaks = []
        for i in range(1, len(y_vals) - 1):
            # 局所最大値を検出
            if y_vals[i] > y_vals[i-1] and y_vals[i] > y_vals[i+1]:
                # 前のピークとの距離をチェック
                if not peaks or i - peaks[-1] >= min_distance:
                    peaks.append(i)
        return peaks
    
    def _robust_outlier_removal(self, y_vals: np.ndarray) -> np.ndarray:
        """ロバストな外れ値除去"""
        # Hampel識別器を使用
        window_size = min(21, len(y_vals) // 3)
        if window_size % 2 == 0:
            window_size += 1
        
        y_cleaned = y_vals.copy()
        
        if window_size >= 3:
            for i in range(len(y_vals)):
                # ウィンドウ内の中央値と絶対偏差中央値（MAD）を計算
                start = max(0, i - window_size // 2)
                end = min(len(y_vals), i + window_size // 2 + 1)
                window = y_vals[start:end]
                
                median = np.median(window)
                mad = np.median(np.abs(window - median))
                
                # Hampel識別器のしきい値（3 * MAD）
                if mad > 0:
                    if np.abs(y_vals[i] - median) > 3 * mad:
                        y_cleaned[i] = median
        
        return y_cleaned
    
    def _conservative_smooth(self, x_vals: np.ndarray, y_vals: np.ndarray) -> np.ndarray:
        """保守的スムージング（変動の大きいグラフ用）"""
        # メディアンフィルタ → Savitzky-Golayフィルタ
        window_size = min(7, len(y_vals) // 6)
        if window_size % 2 == 0:
            window_size += 1
        
        if window_size >= 3:
            y_median = medfilt(y_vals, window_size)
            
            # Savitzky-Golayで軽くスムージング
            sg_window = min(9, len(y_vals) // 5)
            if sg_window % 2 == 0:
                sg_window += 1
            if sg_window >= 5:
                try:
                    y_smooth = savgol_filter(y_median, sg_window, 2)
                    return y_smooth
                except:
                    return y_median
            return y_median
        
        return y_vals
    
    def _aggressive_smooth(self, x_vals: np.ndarray, y_vals: np.ndarray) -> np.ndarray:
        """積極的スムージング（安定したグラフ用）"""
        # スプライン補間を使用
        try:
            # まずガウシアンフィルタで軽くスムージング
            y_gauss = gaussian_filter1d(y_vals, sigma=1.5)
            
            # スプライン補間
            spl = UnivariateSpline(x_vals, y_gauss, s=len(x_vals) * 2)
            y_smooth = spl(x_vals)
            
            return y_smooth
        except:
            # フォールバック
            return self._conservative_smooth(x_vals, y_vals)
    
    def _protect_edges(self, y_original: np.ndarray, y_smooth: np.ndarray, edge_ratio: float = 0.15) -> np.ndarray:
        """エッジ部分を保護しながらブレンド"""
        edge_size = max(5, int(len(y_original) * edge_ratio))
        
        # ブレンドウェイト
        weights = np.ones(len(y_smooth))
        
        # 開始部分
        for i in range(edge_size):
            weights[i] = (i / edge_size) ** 2  # 二次関数で滑らかに遷移
        
        # 終了部分
        for i in range(edge_size):
            weights[-(i+1)] = (i / edge_size) ** 2
        
        # ブレンド
        y_final = y_original * (1 - weights) + y_smooth * weights
        
        return y_final
    
    def y_to_value(self, y: float, is_peak: bool = False) -> float:
        """Y座標を差枚数に変換（線の太さを考慮）
        
        Args:
            y: Y座標
            is_peak: True=最大値（線の上端を読む）、False=通常
        """
        # 更新された境界値を使用
        height = float(self.boundaries["bottom_y"] - self.boundaries["top_y"])
        
        # 2ピクセル調整（線の太さを考慮）
        # 最大値は線の上端（2px上 = y値を小さく）
        # 最小値は線の下端（2px下 = y値を大きく）
        if is_peak:
            # ピーク検出時の特別な処理
            value_at_y = 30000.0 - (y - float(self.boundaries["top_y"])) * 60000.0 / height
            if value_at_y > 0:  # プラス領域の最大値
                adjusted_y = y - 2.0  # 2px上（Y座標を小さく）
            else:  # マイナス領域の最小値
                adjusted_y = y + 2.0  # 2px下（Y座標を大きく）
        else:
            # 通常の処理
            adjusted_y = y
        
        value = 30000.0 - (adjusted_y - float(self.boundaries["top_y"])) * 60000.0 / height
        return np.clip(value, -30000.0, 30000.0)
    
    def extract_graph_data(self, image_path: str) -> Dict:
        """高度な手法でグラフデータを抽出"""
        self.log(f"処理開始: {os.path.basename(image_path)}")
        
        try:
            # 画像読み込み
            img = Image.open(image_path)
            
            # 画像前処理（ノイズ除去）
            img = img.filter(ImageFilter.MedianFilter(size=3))
            img_array = np.array(img)
            
            # 高度な色検出
            color_type, mask, color_props = self.detect_graph_color_advanced(img_array)
            self.log(f"グラフ色: {color_type}", "INFO")
            
            # 最大値を取得
            max_rotation = 50000  # 簡略化
            self.log(f"最大回転数: {max_rotation}", "INFO")
            
            # 高度なライン抽出
            raw_points = self.extract_line_advanced(img_array, mask, color_props)
            self.log(f"検出点数（生データ）: {len(raw_points)}", "INFO")
            
            # 適応的スムージング
            smooth_points = self.adaptive_smoothing(raw_points, color_type)
            self.log(f"スムージング後の点数: {len(smooth_points)}", "INFO")
            
            # データ変換（最大値・最小値を特定）
            data = []
            values_for_peak = []
            
            # まず全データを一度変換して最大値・最小値の位置を特定
            for x, y in smooth_points:
                value = self.y_to_value(y, is_peak=False)
                values_for_peak.append(value)
            
            # 最大値と最小値のインデックスを見つける
            if values_for_peak:
                max_idx = np.argmax(values_for_peak)
                min_idx = np.argmin(values_for_peak)
            else:
                max_idx = min_idx = -1
            
            # 実際のデータ変換（最大値・最小値は2px調整）
            for i, (x, y) in enumerate(smooth_points):
                rotation = (x - float(self.boundaries["start_x"])) * max_rotation / \
                          float(self.boundaries["end_x"] - self.boundaries["start_x"])
                
                # 最大値または最小値の場合は特別な処理
                is_peak = (i == max_idx or i == min_idx)
                value = self.y_to_value(y, is_peak=is_peak)
                
                data.append({
                    "rotation": rotation,
                    "value": value,
                    "x": x,
                    "y": y,
                    "is_max": i == max_idx,
                    "is_min": i == min_idx
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
                    "method": "advanced",
                    "raw_points": len(raw_points),
                    "smooth_points": len(smooth_points),
                    "color_properties": color_props.get(color_type, {})
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
    
    def create_visualization(self, image_path: str, result: Dict, output_path: str, create_overlay: bool = True):
        """抽出結果を可視化（オーバーレイ画像も作成）"""
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
            fill=(0, 255, 0), width=2
        )
        
        # 抽出したポイントを描画
        if result["data"]:
            # 浮動小数点座標を整数に変換
            points = [(int(round(d["x"])), int(round(d["y"]))) for d in result["data"]]
            
            # 最大値と最小値のインデックスを取得
            max_idx = next((i for i, d in enumerate(result["data"]) if d.get("is_max")), -1)
            min_idx = next((i for i, d in enumerate(result["data"]) if d.get("is_min")), -1)
            
            if len(points) > 1:
                # メインライン
                draw.line(points, fill=(0, 0, 255), width=3)
            
            # 最大値点を強調
            if 0 <= max_idx < len(points):
                max_point = points[max_idx]
                max_value = result["data"][max_idx]["value"]
                # 大きな黄色い円
                draw.ellipse(
                    [(max_point[0]-10, max_point[1]-10),
                     (max_point[0]+10, max_point[1]+10)],
                    fill=(255, 255, 0), outline=(255, 0, 0), width=2
                )
                # 最大値ラベル
                draw.text((max_point[0]+15, max_point[1]-15), 
                         f"MAX: {max_value:.0f}", 
                         fill=(255, 0, 0))
                # 垂直線
                draw.line(
                    [(max_point[0], self.boundaries["top_y"]),
                     (max_point[0], self.boundaries["bottom_y"])],
                    fill=(255, 255, 0), width=1
                )
            
            # 最小値点を強調
            if 0 <= min_idx < len(points):
                min_point = points[min_idx]
                min_value = result["data"][min_idx]["value"]
                # 青い円
                draw.ellipse(
                    [(min_point[0]-8, min_point[1]-8),
                     (min_point[0]+8, min_point[1]+8)],
                    fill=(0, 0, 255), outline=(0, 0, 128), width=2
                )
                # 最小値ラベル
                draw.text((min_point[0]+10, min_point[1]+10), 
                         f"MIN: {min_value:.0f}", 
                         fill=(0, 0, 128))
            
            # 始点と終点を強調
            if points:
                # 始点（緑）
                draw.ellipse(
                    [(points[0][0]-6, points[0][1]-6),
                     (points[0][0]+6, points[0][1]+6)],
                    fill=(0, 255, 0), outline=(0, 128, 0), width=2
                )
                # 終点（赤）
                draw.ellipse(
                    [(points[-1][0]-6, points[-1][1]-6),
                     (points[-1][0]+6, points[-1][1]+6)],
                    fill=(255, 0, 0), outline=(128, 0, 0), width=2
                )
                
                # 最終値のラベル
                final_value = result["data"][-1]["value"]
                draw.text((points[-1][0]-80, points[-1][1]+15), 
                         f"FINAL: {final_value:.0f}", 
                         fill=(128, 0, 0))
        
        # 情報表示（背景付き）
        info_x = img.width - 400
        info_y = 20
        # 半透明の白背景
        info_bg = [(info_x-10, info_y-5), (img.width-10, info_y+120)]
        draw.rectangle(info_bg, fill=(255, 255, 255, 200))
        
        draw.text((info_x, info_y), f"Points: {result.get('points', 0)}", fill=(0, 0, 0))
        info_y += 25
        draw.text((info_x, info_y), f"Color: {result.get('color_type', 'N/A')}", fill=(128, 0, 128))
        info_y += 25
        draw.text((info_x, info_y), f"Method: Advanced (2px calibrated)", fill=(0, 0, 255))
        
        # 最大値と最終値の情報
        if "data" in result and result["data"]:
            values = [d["value"] for d in result["data"]]
            max_val = max(values)
            final_val = values[-1]
            info_y += 25
            draw.text((info_x, info_y), f"Max: {max_val:.0f} | Final: {final_val:.0f}", fill=(255, 0, 0))
        
        if "quality" in result:
            info_y += 25
            quality_color = (0, 128, 0) if result["quality"]["is_valid"] else (255, 0, 0)
            draw.text((info_x, info_y), f"Quality: {result['quality']['message']}", fill=quality_color)
        
        # 保存
        img.save(output_path)
        self.log(f"可視化画像を保存: {output_path}", "SUCCESS")
        
        # オーバーレイ画像も作成
        if create_overlay:
            overlay_path = output_path.replace("_visualization.png", "_overlay.png")
            self.create_detailed_overlay(image_path, result, overlay_path)
    
    def create_detailed_overlay(self, image_path: str, result: Dict, output_path: str):
        """詳細なオーバーレイ画像を作成"""
        # 元画像を読み込み
        img = Image.open(image_path)
        # アルファチャンネルを追加
        img = img.convert("RGBA")
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        if result["data"]:
            points = [(int(round(d["x"])), int(round(d["y"]))) for d in result["data"]]
            
            # 半透明の抽出ライン
            if len(points) > 1:
                for i in range(len(points) - 1):
                    draw.line([points[i], points[i+1]], fill=(0, 0, 255, 180), width=4)
            
            # データポイントを小さな円で表示
            for i, point in enumerate(points[::5]):  # 5点ごとに表示
                draw.ellipse(
                    [(point[0]-2, point[1]-2), (point[0]+2, point[1]+2)],
                    fill=(0, 255, 255, 200)
                )
        
        # 合成
        img = Image.alpha_composite(img, overlay)
        img.save(output_path)
        self.log(f"オーバーレイ画像を保存: {output_path}", "SUCCESS")

def main():
    """メイン処理"""
    print("🚀 高度なグラフデータ抽出システム")
    print("📊 最先端の画像処理技術で高精度抽出を実現")
    
    # 入出力フォルダ設定
    input_folder = "graphs/cropped"
    output_folder = "graphs/advanced_extracted_data"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 抽出器を初期化
    extractor = AdvancedGraphExtractor()
    
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