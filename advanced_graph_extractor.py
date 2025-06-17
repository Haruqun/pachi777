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
        
        # グラフ領域内でサンプリング
        roi_hsv = img_hsv[
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
        """高度なライン抽出（エッジ強調とサブピクセル精度）"""
        points = []
        
        # エッジ検出でグラフラインを強調
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        
        # マスクとエッジの組み合わせ
        combined_mask = cv2.bitwise_and(mask, edges)
        
        # X座標ごとにスキャン
        for x in range(self.boundaries["start_x"], self.boundaries["end_x"]):
            # グラフ領域内でマスクをチェック
            column_mask = mask[self.boundaries["top_y"]:self.boundaries["bottom_y"], x]
            column_edge = combined_mask[self.boundaries["top_y"]:self.boundaries["bottom_y"], x]
            
            # エッジ情報を優先的に使用
            if np.any(column_edge > 0):
                y_indices = np.where(column_edge > 0)[0]
            else:
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
                
                # サブピクセル精度で位置を計算
                if len(largest_group) > 1:
                    # ガウシアンフィッティングでサブピクセル位置を推定
                    y_subpixel = self._gaussian_subpixel_peak(column_mask, largest_group)
                else:
                    y_subpixel = float(largest_group[0])
                
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
        """適応的スムージング（グラフパターンに応じた処理）"""
        if len(points) < 5:
            return points
        
        x_vals = np.array([p[0] for p in points])
        y_vals = np.array([p[1] for p in points])
        
        # グラフの特性を分析
        y_diff = np.diff(y_vals)
        volatility = np.std(y_diff)
        
        # ボラティリティに基づいてスムージング強度を調整
        if volatility > 5:  # 変動が大きい場合
            # より保守的なスムージング
            window_size = min(7, len(y_vals) // 6)
        else:  # 変動が小さい場合
            # より積極的なスムージング
            window_size = min(15, len(y_vals) // 4)
        
        if window_size % 2 == 0:
            window_size += 1
        
        # 多段階スムージング
        # 1. 外れ値除去（ロバスト推定）
        y_cleaned = self._robust_outlier_removal(y_vals)
        
        # 2. 色タイプに応じた処理
        if color_type == "pink":
            # ピンクグラフは通常変動が大きいので、より慎重に
            y_smooth = self._conservative_smooth(x_vals, y_cleaned)
        else:
            # 青系グラフは比較的安定しているので、より積極的に
            y_smooth = self._aggressive_smooth(x_vals, y_cleaned)
        
        # 3. エッジ保護
        y_final = self._protect_edges(y_cleaned, y_smooth, edge_ratio=0.15)
        
        return list(zip(x_vals, y_final))
    
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
    
    def y_to_value(self, y: float) -> float:
        """Y座標を差枚数に変換（浮動小数点精度）"""
        height = float(self.boundaries["bottom_y"] - self.boundaries["top_y"])
        value = 30000.0 - (y - float(self.boundaries["top_y"])) * 60000.0 / height
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
        draw.text((img.width-350, info_y), f"Points: {result.get('points', 0)}", fill=(0, 0, 0))
        info_y += 20
        draw.text((img.width-350, info_y), f"Color: {result.get('color_type', 'N/A')}", fill=(0, 0, 0))
        info_y += 20
        draw.text((img.width-350, info_y), f"Method: Advanced", fill=(0, 0, 255))
        
        if "quality" in result:
            info_y += 20
            quality_color = (0, 128, 0) if result["quality"]["is_valid"] else (255, 0, 0)
            draw.text((img.width-350, info_y), f"Quality: {result['quality']['message']}", fill=quality_color)
        
        # 保存
        img.save(output_path)
        self.log(f"可視化画像を保存: {output_path}", "SUCCESS")

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