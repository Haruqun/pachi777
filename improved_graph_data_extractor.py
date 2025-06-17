#!/usr/bin/env python3
"""
改良版グラフデータ抽出ツール
- HSV色空間での色検出
- OCRによる最大値読み取り
- エラーハンドリングの強化
- データ品質チェック機能
"""

import os
import json
import numpy as np
from PIL import Image, ImageDraw
import cv2
import pandas as pd
from typing import Tuple, List, Dict, Optional
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pytesseract
from scipy.interpolate import interp1d

class ImprovedGraphDataExtractor:
    """改良版グラフデータ抽出システム"""
    
    def __init__(self, config_path="graph_boundaries_final_config.json"):
        """初期化"""
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
            self.boundaries = self.config["boundaries"]
        except FileNotFoundError:
            print(f"警告: 設定ファイル {config_path} が見つかりません。デフォルト値を使用します。")
            self.boundaries = self._get_default_boundaries()
        except json.JSONDecodeError:
            print(f"エラー: 設定ファイル {config_path} の解析に失敗しました。")
            raise
        
        self.debug_mode = True
        
    def _get_default_boundaries(self) -> dict:
        """デフォルトの境界値を返す"""
        return {
            "start_x": 90,
            "end_x": 820,
            "top_y": 100,
            "bottom_y": 700,
            "zero_y": 400
        }
    
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{level}] {message}")
    
    def detect_graph_color_hsv(self, img_array: np.ndarray) -> str:
        """HSV色空間でグラフの主要な色を判定"""
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
            "pink": [(140, 50, 50), (170, 255, 255)],      # ピンク
            "purple": [(120, 50, 50), (150, 255, 255)],    # 紫
            "blue": [(90, 50, 50), (120, 255, 255)],       # 青
            "cyan": [(80, 50, 50), (100, 255, 255)]        # シアン
        }
        
        color_counts = {}
        
        for color_name, (lower, upper) in color_ranges.items():
            lower = np.array(lower)
            upper = np.array(upper)
            mask = cv2.inRange(roi, lower, upper)
            count = np.sum(mask > 0)
            color_counts[color_name] = count
            
        # 最も多い色を返す
        detected_color = max(color_counts, key=color_counts.get)
        self.log(f"色検出結果: {color_counts}", "DEBUG")
        
        return detected_color
    
    def create_color_mask(self, img_hsv: np.ndarray, color_type: str) -> np.ndarray:
        """指定色のマスクを作成"""
        # 色範囲の定義（より広範囲に調整）
        color_ranges = {
            "pink": [(140, 30, 30), (170, 255, 255)],
            "purple": [(120, 30, 30), (150, 255, 255)],
            "blue": [(90, 30, 30), (120, 255, 255)],
            "cyan": [(80, 30, 30), (100, 255, 255)]
        }
        
        if color_type not in color_ranges:
            # 全ての色を含むマスクを作成
            masks = []
            for lower, upper in color_ranges.values():
                mask = cv2.inRange(img_hsv, np.array(lower), np.array(upper))
                masks.append(mask)
            return np.bitwise_or.reduce(masks)
        
        lower, upper = color_ranges[color_type]
        return cv2.inRange(img_hsv, np.array(lower), np.array(upper))
    
    def extract_max_value_ocr(self, img_array: np.ndarray) -> int:
        """OCRを使用して右側の最大値を読み取る"""
        height, width = img_array.shape[:2]
        
        # 右側の数値領域を切り出し（複数の候補領域）
        roi_candidates = [
            img_array[int(height*0.85):int(height*0.95), int(width*0.85):width],  # 右下
            img_array[int(height*0.1):int(height*0.2), int(width*0.85):width],    # 右上
        ]
        
        for i, roi in enumerate(roi_candidates):
            try:
                # グレースケール変換
                gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
                
                # 二値化
                _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                
                # OCR実行
                text = pytesseract.image_to_string(binary, config='--psm 7 -c tessedit_char_whitelist=0123456789,')
                
                # 数値を抽出
                numbers = []
                for part in text.replace(',', '').split():
                    try:
                        num = int(part)
                        if 10000 <= num <= 100000:  # 妥当な範囲の数値のみ
                            numbers.append(num)
                    except ValueError:
                        continue
                
                if numbers:
                    max_val = max(numbers)
                    self.log(f"OCRで検出した最大値: {max_val}", "SUCCESS")
                    return max_val
                    
            except Exception as e:
                self.log(f"OCR候補領域{i+1}でエラー: {str(e)}", "WARNING")
                continue
        
        # OCRが失敗した場合、グラフの幅から推定
        graph_width = self.boundaries["end_x"] - self.boundaries["start_x"]
        if graph_width > 600:
            return 80000
        elif graph_width > 400:
            return 50000
        else:
            return 30000
    
    def trace_graph_line_improved(self, img_array: np.ndarray, color_type: str) -> List[Tuple[int, int]]:
        """改良版グラフライントレース"""
        # HSVに変換
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        
        # カラーマスクを作成
        mask = self.create_color_mask(img_hsv, color_type)
        
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
                
                # 最大のグループの中心を選択
                largest_group = max(groups, key=len)
                center_y = int(np.mean(largest_group)) + self.boundaries["top_y"]
                
                # 前のポイントとの連続性チェック
                if points:
                    last_y = points[-1][1]
                    # 急激な変化を避ける（ノイズ除去）
                    if abs(center_y - last_y) > 100:  # 100ピクセル以上の急激な変化
                        # 線形補間で推定
                        if len(points) >= 2:
                            y_pred = 2 * points[-1][1] - points[-2][1]
                            if abs(center_y - y_pred) > 150:
                                continue  # このポイントをスキップ
                
                points.append((x, center_y))
        
        # データの補間とスムージング
        if len(points) > 10:
            points = self.smooth_data(points)
        
        return points
    
    def smooth_data(self, points: List[Tuple[int, int]], window_size: int = 5) -> List[Tuple[int, int]]:
        """データのスムージング"""
        if len(points) < window_size:
            return points
        
        x_vals = [p[0] for p in points]
        y_vals = [p[1] for p in points]
        
        # 移動平均でスムージング
        smoothed_y = []
        for i in range(len(y_vals)):
            start = max(0, i - window_size // 2)
            end = min(len(y_vals), i + window_size // 2 + 1)
            smoothed_y.append(int(np.mean(y_vals[start:end])))
        
        return list(zip(x_vals, smoothed_y))
    
    def interpolate_missing_data(self, points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """欠損データの補間"""
        if len(points) < 2:
            return points
        
        x_vals = [p[0] for p in points]
        y_vals = [p[1] for p in points]
        
        # 全X座標範囲を生成
        all_x = list(range(self.boundaries["start_x"], self.boundaries["end_x"]))
        
        # 補間関数を作成
        f = interp1d(x_vals, y_vals, kind='linear', fill_value='extrapolate')
        
        # 補間実行
        interpolated_y = f(all_x)
        
        return list(zip(all_x, interpolated_y.astype(int)))
    
    def y_to_value(self, y: int) -> float:
        """Y座標を差枚数に変換（30000上限）"""
        height = self.boundaries["bottom_y"] - self.boundaries["top_y"]
        value = 30000 - (y - self.boundaries["top_y"]) * 60000 / height
        
        # 30000を超える値をクリップ
        return np.clip(value, -30000, 30000)
    
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
        
        # 異常な跳躍をチェック
        jumps = []
        for i in range(1, len(values)):
            jump = abs(values[i] - values[i-1])
            if jump > 10000:  # 10000以上の急激な変化
                jumps.append((i, jump))
        
        if len(jumps) > len(data) * 0.1:  # 10%以上が異常
            return False, f"異常な跳躍が多すぎます: {len(jumps)}箇所"
        
        return True, "データ品質OK"
    
    def extract_graph_data(self, image_path: str) -> Dict:
        """グラフデータを抽出（改良版）"""
        self.log(f"処理開始: {os.path.basename(image_path)}")
        
        try:
            # 画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # グラフの色を判定（HSV使用）
            color_type = self.detect_graph_color_hsv(img_array)
            self.log(f"グラフ色: {color_type}", "INFO")
            
            # 最大値を取得（OCR使用）
            max_rotation = self.extract_max_value_ocr(img_array)
            self.log(f"最大回転数: {max_rotation}", "INFO")
            
            # グラフラインをトレース（改良版）
            points = self.trace_graph_line_improved(img_array, color_type)
            self.log(f"検出点数: {len(points)}", "INFO")
            
            # データ変換
            data = []
            for x, y in points:
                rotation = int((x - self.boundaries["start_x"]) * max_rotation / 
                             (self.boundaries["end_x"] - self.boundaries["start_x"]))
                value = self.y_to_value(y)
                data.append({
                    "rotation": rotation,
                    "value": value,
                    "x": x,
                    "y": y
                })
            
            # データ品質チェック
            is_valid, quality_msg = self.validate_data_quality(data)
            if not is_valid:
                self.log(f"データ品質警告: {quality_msg}", "WARNING")
            
            return {
                "image": os.path.basename(image_path),
                "color_type": color_type,
                "max_rotation": max_rotation,
                "points": len(points),
                "data": data,
                "quality": {
                    "is_valid": is_valid,
                    "message": quality_msg
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
            self.log(f"エラーのためCSV保存をスキップ: {result['error']}", "ERROR")
            return
        
        df = pd.DataFrame(result["data"])
        df.to_csv(output_path, index=False)
        self.log(f"CSVファイルを保存: {output_path}", "SUCCESS")
    
    def create_visualization(self, image_path: str, result: Dict, output_path: str):
        """抽出結果を可視化"""
        if "error" in result:
            return
        
        # 元画像を読み込み
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        # 境界線を描画
        width, height = img.size
        
        # グラフ領域
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
            # 線として描画
            points = [(d["x"], d["y"]) for d in result["data"]]
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
        draw.text((width-300, info_y), f"Points: {result.get('points', 0)}", fill=(0, 0, 0))
        info_y += 20
        draw.text((width-300, info_y), f"Color: {result.get('color_type', 'N/A')}", fill=(0, 0, 0))
        info_y += 20
        draw.text((width-300, info_y), f"Max: {result.get('max_rotation', 'N/A')}", fill=(0, 0, 0))
        
        if "quality" in result:
            info_y += 20
            quality_color = (0, 128, 0) if result["quality"]["is_valid"] else (255, 0, 0)
            draw.text((width-300, info_y), f"Quality: {result['quality']['message']}", fill=quality_color)
        
        # 保存
        img.save(output_path)
        self.log(f"可視化画像を保存: {output_path}", "SUCCESS")
    
    def create_graph_plot(self, result: Dict, output_path: str):
        """抽出データをグラフとしてプロット"""
        if not result.get("data"):
            return
        
        # データを準備
        df = pd.DataFrame(result["data"])
        
        # プロット作成
        plt.figure(figsize=(12, 8))
        
        # 元のグラフラインをプロット
        plt.plot(df["rotation"], df["value"], linewidth=2, 
                label=f"{result['color_type']}色グラフ")
        
        # 0ラインを表示
        plt.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        
        # グリッド
        plt.grid(True, alpha=0.3)
        
        # ラベル
        plt.xlabel("回転数", fontsize=12)
        plt.ylabel("差枚数", fontsize=12)
        plt.title(f"抽出グラフデータ - {result['image']}", fontsize=14)
        
        # 範囲設定（30000上限）
        plt.ylim(-30000, 30000)
        plt.xlim(0, result.get("max_rotation", 80000))
        
        # データ品質情報を表示
        if "quality" in result:
            quality_text = f"品質: {result['quality']['message']}"
            color = 'green' if result['quality']['is_valid'] else 'red'
            plt.text(0.02, 0.98, quality_text, transform=plt.gca().transAxes,
                    verticalalignment='top', color=color)
        
        # 統計情報を表示
        if df["value"].any():
            stats_text = f"最大: {df['value'].max():.0f}\n最小: {df['value'].min():.0f}\n最終: {df['value'].iloc[-1]:.0f}"
            plt.text(0.98, 0.02, stats_text, transform=plt.gca().transAxes,
                    verticalalignment='bottom', horizontalalignment='right',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 凡例
        plt.legend()
        
        # 保存
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        self.log(f"グラフを保存: {output_path}", "SUCCESS")

def main():
    """メイン処理"""
    print("🎯 改良版グラフデータ抽出ツール")
    print("📊 グラフラインをトレースしてデータを抽出します")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal_v2"
    output_folder = "graphs/improved_extracted_data"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 抽出器を初期化
    extractor = ImprovedGraphDataExtractor()
    
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
        
        # グラフプロット
        plot_path = os.path.join(output_folder, f"{base_name}_plot.png")
        extractor.create_graph_plot(result, plot_path)
        
        # 結果サマリー
        if result["data"]:
            values = [d["value"] for d in result["data"]]
            print(f"\n📊 抽出結果:")
            print(f"  最大値: {max(values):.0f}")
            print(f"  最小値: {min(values):.0f}")
            print(f"  最終値: {values[-1]:.0f}")
            print(f"  品質: {result['quality']['message']}")
    
    # 全体サマリー
    print(f"\n{'='*60}")
    print(f"処理完了: 成功 {success_count}/{len(image_files)}, エラー {error_count}/{len(image_files)}")

if __name__ == "__main__":
    main()