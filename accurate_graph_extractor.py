#!/usr/bin/env python3
"""
高精度グラフデータ抽出ツール
- 日本語フォント完全対応
- 異常値（急上昇・急下降）の検出と除去
- グラフ開始位置の正確な検出
"""

import os
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
import pandas as pd
from typing import Tuple, List, Dict, Optional
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform

class AccurateGraphDataExtractor:
    """高精度グラフデータ抽出システム"""
    
    def __init__(self):
        # 境界値設定
        self.boundaries = {
            "start_x": 36,  # 初期値（自動調整される）
            "end_x": 620,
            "top_y": 29,
            "zero_y": 274,
            "bottom_y": 520
        }
        self.debug_mode = True
        
        # 日本語フォント設定
        self.setup_japanese_font()
        
        # 異常値検出パラメータ
        self.spike_threshold = 10000  # 1フレームで10000以上の変化は異常
        self.smoothing_window = 5     # スムージングウィンドウサイズ
        
    def setup_japanese_font(self):
        """日本語フォントの設定"""
        system = platform.system()
        
        # matplotlib用フォント設定
        if system == 'Darwin':  # macOS
            font_paths = [
                'Hiragino Sans GB', 
                'Hiragino Kaku Gothic Pro',
                'Yu Gothic',
                'Arial Unicode MS'
            ]
        elif system == 'Windows':
            font_paths = [
                'Yu Gothic',
                'MS Gothic',
                'Meiryo'
            ]
        else:  # Linux
            font_paths = [
                'Noto Sans CJK JP',
                'VL Gothic',
                'IPAGothic'
            ]
        
        # matplotlibフォント設定
        available_fonts = []
        for font in font_paths:
            try:
                plt.rcParams['font.family'] = font
                available_fonts.append(font)
                break
            except:
                continue
        
        # 最後にデフォルトフォントを追加
        plt.rcParams['font.family'] = available_fonts + ['sans-serif']
        
        # PIL用フォント設定
        self.pil_font = None
        try:
            if system == 'Darwin':
                self.pil_font = ImageFont.truetype('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc', 16)
            elif system == 'Windows':
                self.pil_font = ImageFont.truetype('C:\\Windows\\Fonts\\yugothic.ttc', 16)
        except:
            self.pil_font = None
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{level}] {message}")
    
    def detect_actual_start(self, img_array: np.ndarray, color_type: str) -> int:
        """グラフの実際の開始位置を検出"""
        height, width = img_array.shape[:2]
        
        # 左から右へスキャンして最初のグラフ点を見つける
        for x in range(10, min(100, width)):  # 左端から100ピクセルまでチェック
            # ゼロライン付近をチェック
            y_range = range(max(0, self.boundaries["zero_y"]-50), 
                          min(height, self.boundaries["zero_y"]+50))
            
            for y in y_range:
                r, g, b = img_array[y, x]
                if self.is_graph_color(r, g, b, color_type):
                    # グラフ色が見つかったら、少し左にマージンを取る
                    return max(x - 5, 0)
        
        # デフォルト値
        return self.boundaries["start_x"]
    
    def detect_graph_color(self, img_array: np.ndarray) -> str:
        """グラフの主要な色を判定"""
        # グラフ領域内でサンプリング
        roi = img_array[
            self.boundaries["zero_y"]-30:self.boundaries["zero_y"]+30,
            self.boundaries["start_x"]:self.boundaries["end_x"]
        ]
        
        pink_count = 0
        purple_count = 0
        blue_count = 0
        
        for y in range(roi.shape[0]):
            for x in range(roi.shape[1]):
                r, g, b = roi[y, x]
                
                # ピンク系
                if r > 180 and g < 160 and b > 120 and r > b:
                    pink_count += 1
                # 紫系
                elif r > 120 and b > 120 and g < 100 and abs(r - b) < 60:
                    purple_count += 1
                # 青系
                elif b > 160 and r < 140 and g < 160 and b > r and b > g:
                    blue_count += 1
        
        if pink_count >= purple_count and pink_count >= blue_count:
            return "pink"
        elif purple_count >= blue_count:
            return "purple"
        else:
            return "blue"
    
    def is_graph_color(self, r: int, g: int, b: int, color_type: str) -> bool:
        """指定した色タイプかチェック"""
        if color_type == "pink":
            return r > 180 and g < 170 and b > 120 and r > b
        elif color_type == "purple":
            return r > 100 and b > 100 and g < 120 and abs(r - b) < 80
        elif color_type == "blue":
            return b > 140 and r < 160 and g < 170
        else:
            # 全ての色を許容
            return (r > 180 and g < 170 and b > 120) or \
                   (r > 100 and b > 100 and g < 120) or \
                   (b > 140 and r < 160 and g < 170)
    
    def find_data_endpoint(self, img_array: np.ndarray, color_type: str) -> int:
        """グラフデータが実際に終わるX座標を検出"""
        height, width = img_array.shape[:2]
        
        # 境界を画像サイズに合わせて調整
        max_x = min(width-1, self.boundaries["end_x"])
        max_y = min(height-1, self.boundaries["bottom_y"])
        min_y = max(0, self.boundaries["top_y"])
        
        # 右端から左へスキャンして、最後のグラフ点を見つける
        for x in range(max_x, self.boundaries["start_x"], -1):
            # Y座標をスキャン
            for y in range(min_y, max_y):
                if x < width and y < height:  # 境界チェック
                    r, g, b = img_array[y, x]
                    if self.is_graph_color(r, g, b, color_type):
                        return x
        
        return self.boundaries["start_x"]
    
    def remove_spikes(self, points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """異常値（急激な変化）を除去"""
        if len(points) < 3:
            return points
        
        filtered_points = [points[0]]  # 最初の点は保持
        
        for i in range(1, len(points) - 1):
            prev_y = points[i-1][1]
            curr_y = points[i][1]
            next_y = points[i+1][1]
            
            # 前後の点との差を計算
            diff_prev = abs(self.y_to_value(curr_y) - self.y_to_value(prev_y))
            diff_next = abs(self.y_to_value(next_y) - self.y_to_value(curr_y))
            
            # 急激な変化を検出
            if diff_prev > self.spike_threshold and diff_next > self.spike_threshold:
                # スパイクとして除外（前の値で補間）
                interpolated_y = prev_y
                filtered_points.append((points[i][0], interpolated_y))
                self.log(f"異常値検出: x={points[i][0]}, 元y={curr_y}, 補間y={interpolated_y}", "WARNING")
            else:
                filtered_points.append(points[i])
        
        filtered_points.append(points[-1])  # 最後の点は保持
        
        return filtered_points
    
    def smooth_data(self, points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """データのスムージング（移動平均）"""
        if len(points) < self.smoothing_window:
            return points
        
        smoothed_points = []
        half_window = self.smoothing_window // 2
        
        for i in range(len(points)):
            start_idx = max(0, i - half_window)
            end_idx = min(len(points), i + half_window + 1)
            
            # 近傍の点の平均を計算
            window_points = points[start_idx:end_idx]
            avg_y = int(np.mean([p[1] for p in window_points]))
            
            smoothed_points.append((points[i][0], avg_y))
        
        return smoothed_points
    
    def trace_graph_line(self, img_array: np.ndarray, color_type: str, start_x: int, end_x: int) -> List[Tuple[int, int]]:
        """グラフラインをトレース（改良版）"""
        points = []
        height, width = img_array.shape[:2]
        
        # 境界を画像サイズに合わせて調整
        max_y = min(height, self.boundaries["bottom_y"])
        min_y = max(0, self.boundaries["top_y"])
        
        # X座標ごとにスキャン
        for x in range(start_x, min(end_x + 1, self.boundaries["end_x"], width)):
            # Y座標の候補を収集
            y_candidates = []
            
            # グラフ領域内でスキャン
            for y in range(min_y, max_y):
                if x < width and y < height:  # 境界チェック
                    r, g, b = img_array[y, x]
                    
                    if self.is_graph_color(r, g, b, color_type):
                        y_candidates.append(y)
            
            # 候補がある場合
            if y_candidates:
                # 連続した領域の中心を取る
                if len(y_candidates) == 1:
                    points.append((x, y_candidates[0]))
                else:
                    # 連続した領域をグループ化
                    groups = []
                    current_group = [y_candidates[0]]
                    
                    for i in range(1, len(y_candidates)):
                        if y_candidates[i] - y_candidates[i-1] <= 2:
                            current_group.append(y_candidates[i])
                        else:
                            groups.append(current_group)
                            current_group = [y_candidates[i]]
                    groups.append(current_group)
                    
                    # 最大のグループの中心を選択
                    largest_group = max(groups, key=len)
                    center_y = int(np.mean(largest_group))
                    points.append((x, center_y))
        
        return points
    
    def y_to_value(self, y: int) -> float:
        """Y座標を差枚数に変換"""
        height = self.boundaries["bottom_y"] - self.boundaries["top_y"]
        value = 30000 - (y - self.boundaries["top_y"]) * 60000 / height
        return value
    
    def x_to_rotation(self, x: int, max_rotation: int) -> int:
        """X座標を回転数に変換"""
        width = self.boundaries["end_x"] - self.boundaries["start_x"]
        rotation = int((x - self.boundaries["start_x"]) * max_rotation / width)
        return rotation
    
    def extract_max_rotation(self, img_array: np.ndarray) -> int:
        """X軸の最大回転数を読み取る"""
        # デフォルト値
        return 80000
    
    def extract_graph_data(self, image_path: str) -> Dict:
        """グラフデータを抽出（高精度版）"""
        self.log(f"処理開始: {os.path.basename(image_path)}")
        
        # 画像読み込み
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # グラフの色を判定
        color_type = self.detect_graph_color(img_array)
        self.log(f"グラフ色: {color_type}", "INFO")
        
        # 実際の開始位置を検出
        actual_start_x = self.detect_actual_start(img_array, color_type)
        self.log(f"実際の開始位置: x={actual_start_x}", "INFO")
        
        # 最大回転数を取得
        max_rotation = self.extract_max_rotation(img_array)
        self.log(f"最大回転数: {max_rotation}", "INFO")
        
        # データの終端を検出
        data_end_x = self.find_data_endpoint(img_array, color_type)
        self.log(f"データ終端: x={data_end_x}", "INFO")
        
        # データ終端での回転数を計算
        data_end_rotation = self.x_to_rotation(data_end_x, max_rotation)
        self.log(f"データ終端の回転数: {data_end_rotation}", "INFO")
        
        # グラフラインをトレース
        raw_points = self.trace_graph_line(img_array, color_type, actual_start_x, data_end_x)
        self.log(f"検出点数（生データ）: {len(raw_points)}", "INFO")
        
        # 異常値除去
        filtered_points = self.remove_spikes(raw_points)
        self.log(f"異常値除去後: {len(filtered_points)}点", "INFO")
        
        # スムージング
        smoothed_points = self.smooth_data(filtered_points)
        self.log(f"スムージング後: {len(smoothed_points)}点", "INFO")
        
        # データ変換
        data = []
        for x, y in smoothed_points:
            rotation = self.x_to_rotation(x, max_rotation)
            value = self.y_to_value(y)
            data.append({
                "rotation": rotation,
                "value": value,
                "x": x,
                "y": y
            })
        
        return {
            "image": os.path.basename(image_path),
            "color_type": color_type,
            "max_rotation": max_rotation,
            "actual_start_x": actual_start_x,
            "data_end_x": data_end_x,
            "data_end_rotation": data_end_rotation,
            "points": len(smoothed_points),
            "raw_points": len(raw_points),
            "data": data
        }
    
    def save_to_csv(self, result: Dict, output_path: str):
        """抽出データをCSVに保存"""
        df = pd.DataFrame(result["data"])
        df.to_csv(output_path, index=False, encoding='utf-8-sig')  # BOM付きUTF-8
        self.log(f"CSVファイルを保存: {output_path}", "SUCCESS")
    
    def create_visualization(self, image_path: str, result: Dict, output_path: str):
        """抽出結果を可視化（日本語対応）"""
        # 元画像を読み込み
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        # 境界線を描画
        width, height = img.size
        
        # グラフ領域（全体）
        draw.rectangle(
            [(self.boundaries["start_x"], self.boundaries["top_y"]),
             (self.boundaries["end_x"], self.boundaries["bottom_y"])],
            outline=(255, 0, 0), width=2
        )
        
        # 実際のデータ範囲
        draw.rectangle(
            [(result["actual_start_x"], self.boundaries["top_y"]),
             (result["data_end_x"], self.boundaries["bottom_y"])],
            outline=(0, 255, 0), width=2
        )
        
        # 開始線
        draw.line(
            [(result["actual_start_x"], self.boundaries["top_y"]),
             (result["actual_start_x"], self.boundaries["bottom_y"])],
            fill=(0, 255, 0), width=3
        )
        
        # データ終端ライン
        if result["data_end_x"] < self.boundaries["end_x"]:
            draw.line(
                [(result["data_end_x"], self.boundaries["top_y"]),
                 (result["data_end_x"], self.boundaries["bottom_y"])],
                fill=(0, 255, 0), width=3
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
        
        # 情報表示（日本語）
        font = self.pil_font
        info_y = 20
        info_x = width - 350
        
        texts = [
            f"検出点数: {result['points']}点",
            f"生データ: {result['raw_points']}点",
            f"色: {result['color_type']}",
            f"最大回転数: {result['max_rotation']:,}",
            f"データ終了: {result['data_end_rotation']:,}回転"
        ]
        
        for text in texts:
            if font:
                draw.text((info_x, info_y), text, fill=(0, 0, 0), font=font)
            else:
                draw.text((info_x, info_y), text, fill=(0, 0, 0))
            info_y += 25
        
        # 保存
        img.save(output_path)
        self.log(f"可視化画像を保存: {output_path}", "SUCCESS")
    
    def create_graph_plot(self, result: Dict, output_path: str):
        """抽出データをグラフとしてプロット（日本語対応）"""
        if not result["data"]:
            return
        
        # データを準備
        df = pd.DataFrame(result["data"])
        
        # プロット作成
        plt.figure(figsize=(12, 8))
        
        # 元のグラフラインをプロット
        plt.plot(df["rotation"], df["value"], linewidth=2, 
                label=f"{result['color_type']}色グラフ")
        
        # データ終端を表示
        if result["data_end_rotation"] < result["max_rotation"]:
            plt.axvline(x=result["data_end_rotation"], color='green', 
                       linestyle='--', alpha=0.7, 
                       label=f'データ終端 ({result["data_end_rotation"]:,}回転)')
        
        # 0ラインを表示
        plt.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='ゼロライン')
        
        # グリッド
        plt.grid(True, alpha=0.3)
        
        # ラベル
        plt.xlabel("回転数", fontsize=12)
        plt.ylabel("差枚数", fontsize=12)
        plt.title(f"抽出グラフデータ - {result['image']}", fontsize=14)
        
        # 範囲設定
        plt.ylim(-30000, 30000)
        plt.xlim(0, result["max_rotation"])
        
        # X軸のフォーマット
        ax = plt.gca()
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'{int(y):,}'))
        
        # 凡例
        plt.legend(loc='best')
        
        # 保存
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        self.log(f"グラフを保存: {output_path}", "SUCCESS")

def main():
    """メイン処理"""
    print("🎯 高精度グラフデータ抽出ツール")
    print("📊 日本語対応・異常値除去・開始位置自動検出")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal"
    output_folder = "graphs/accurate_extracted_data"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 抽出器を初期化
    extractor = AccurateGraphDataExtractor()
    
    # テスト画像を処理（まずは1枚）
    test_file = "S__78209130_optimal.png"
    
    input_path = os.path.join(input_folder, test_file)
    if os.path.exists(input_path):
        print(f"\n{'='*60}")
        print(f"処理中: {test_file}")
        
        # データ抽出
        result = extractor.extract_graph_data(input_path)
        
        # ベースファイル名
        base_name = os.path.splitext(test_file)[0]
        
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
            print(f"  データ点数: {len(result['data'])}")
            print(f"  開始位置: x={result['actual_start_x']}")
            print(f"  データ範囲: 0 - {result['data_end_rotation']:,}回転")
            print(f"  最大値: {max(values):,.0f}")
            print(f"  最小値: {min(values):,.0f}")
            print(f"  最終値: {values[-1]:,.0f}")

if __name__ == "__main__":
    main()