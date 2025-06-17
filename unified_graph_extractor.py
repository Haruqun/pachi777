#!/usr/bin/env python3
"""
統一グラフ境界抽出システム
S__78209128_optimal_visualization.pngの仕様に合わせた実装
- 固定境界値による安定した切り抜き
- 全画像で一貫した結果
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

class UnifiedGraphExtractor:
    """統一仕様グラフ抽出システム"""
    
    def __init__(self):
        # S__78209128の成功例に基づく固定境界値
        self.boundaries = {
            "start_x": 35,    # グラフ開始位置（Y軸の右側）
            "end_x": 585,     # グラフ終了位置（80,000の手前）
            "top_y": 29,      # +30,000の位置
            "zero_y": 274,    # ゼロラインの位置
            "bottom_y": 520   # -30,000の位置
        }
        
        # グラフ領域のサイズ
        self.graph_width = self.boundaries["end_x"] - self.boundaries["start_x"]  # 550px
        self.graph_height = self.boundaries["bottom_y"] - self.boundaries["top_y"]  # 491px
        
        self.debug_mode = True
        
        # 日本語フォント設定
        self.setup_japanese_font()
        
        # 異常値検出パラメータ
        self.spike_threshold = 8000  # 急激な変化の閾値を下げる
        self.smoothing_window = 3    # スムージングを軽くする
        
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
                
                # ピンク系（より幅広く検出）
                if r > 170 and g < 170 and b > 100 and r > b:
                    pink_count += 1
                # 紫系
                elif r > 120 and b > 120 and g < 100 and abs(r - b) < 60:
                    purple_count += 1
                # 青系
                elif b > 150 and r < 150 and g < 160 and b > r and b > g:
                    blue_count += 1
        
        if pink_count >= purple_count and pink_count >= blue_count:
            return "pink"
        elif purple_count >= blue_count:
            return "purple"
        else:
            return "blue"
    
    def is_graph_color(self, r: int, g: int, b: int, color_type: str) -> bool:
        """指定した色タイプかチェック（より寛容な設定）"""
        if color_type == "pink":
            return r > 160 and g < 180 and b > 90 and r > b
        elif color_type == "purple":
            return r > 100 and b > 100 and g < 130 and abs(r - b) < 100
        elif color_type == "blue":
            return b > 130 and r < 170 and g < 180
        else:
            # 全ての色を許容
            return (r > 160 and g < 180 and b > 90) or \
                   (r > 100 and b > 100 and g < 130) or \
                   (b > 130 and r < 170 and g < 180)
    
    def trace_graph_line(self, img_array: np.ndarray, color_type: str) -> List[Tuple[int, int]]:
        """グラフラインをトレース（全範囲）"""
        points = []
        height, width = img_array.shape[:2]
        
        # 境界を画像サイズに合わせて調整
        max_y = min(height, self.boundaries["bottom_y"])
        min_y = max(0, self.boundaries["top_y"])
        
        # X座標ごとにスキャン（全範囲）
        for x in range(self.boundaries["start_x"], min(self.boundaries["end_x"], width)):
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
                        if y_candidates[i] - y_candidates[i-1] <= 3:  # 許容差を増やす
                            current_group.append(y_candidates[i])
                        else:
                            groups.append(current_group)
                            current_group = [y_candidates[i]]
                    groups.append(current_group)
                    
                    # 最大のグループの中心を選択
                    largest_group = max(groups, key=len)
                    center_y = int(np.mean(largest_group))
                    points.append((x, center_y))
            else:
                # データがない場合、前の点から補間
                if points and len(points) > 0:
                    # 最後の有効な値を使用
                    points.append((x, points[-1][1]))
        
        return points
    
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
            else:
                filtered_points.append(points[i])
        
        filtered_points.append(points[-1])  # 最後の点は保持
        
        return filtered_points
    
    def y_to_value(self, y: int) -> float:
        """Y座標を差枚数に変換（固定スケール）"""
        # +30,000 から -30,000 の範囲（合計60,000）
        value = 30000 - (y - self.boundaries["top_y"]) * 60000 / self.graph_height
        return value
    
    def x_to_rotation(self, x: int) -> int:
        """X座標を回転数に変換（0-80,000の固定範囲）"""
        # 0から80,000の範囲
        rotation = int((x - self.boundaries["start_x"]) * 80000 / self.graph_width)
        return max(0, min(80000, rotation))  # 範囲制限
    
    def extract_graph_data(self, image_path: str) -> Dict:
        """グラフデータを抽出（統一仕様）"""
        self.log(f"処理開始: {os.path.basename(image_path)}")
        
        # 画像読み込み
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # グラフの色を判定
        color_type = self.detect_graph_color(img_array)
        self.log(f"グラフ色: {color_type}", "INFO")
        
        # グラフラインをトレース
        raw_points = self.trace_graph_line(img_array, color_type)
        self.log(f"検出点数（生データ）: {len(raw_points)}", "INFO")
        
        # 異常値除去
        filtered_points = self.remove_spikes(raw_points)
        self.log(f"異常値除去後: {len(filtered_points)}点", "INFO")
        
        # データ変換
        data = []
        for x, y in filtered_points:
            rotation = self.x_to_rotation(x)
            value = self.y_to_value(y)
            data.append({
                "rotation": rotation,
                "value": value,
                "x": x,
                "y": y
            })
        
        # 最終値の情報
        final_value = data[-1]["value"] if data else 0
        final_rotation = data[-1]["rotation"] if data else 0
        
        return {
            "image": os.path.basename(image_path),
            "color_type": color_type,
            "max_rotation": 80000,  # 固定
            "final_rotation": final_rotation,
            "final_value": final_value,
            "points": len(filtered_points),
            "data": data
        }
    
    def save_to_csv(self, result: Dict, output_path: str):
        """抽出データをCSVに保存"""
        df = pd.DataFrame(result["data"])
        df.to_csv(output_path, index=False, encoding='utf-8-sig')  # BOM付きUTF-8
        self.log(f"CSVファイルを保存: {output_path}", "SUCCESS")
    
    def create_visualization(self, image_path: str, result: Dict, output_path: str):
        """抽出結果を可視化（S__78209128仕様）"""
        # 元画像を読み込み
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        # 境界線を描画（赤い枠）
        draw.rectangle(
            [(self.boundaries["start_x"], self.boundaries["top_y"]),
             (self.boundaries["end_x"], self.boundaries["bottom_y"])],
            outline=(255, 0, 0), width=2
        )
        
        # 抽出したポイントを描画（緑の線）
        if result["data"]:
            points = [(d["x"], d["y"]) for d in result["data"]]
            if len(points) > 1:
                # 太い緑の線でグラフを描画
                draw.line(points, fill=(0, 255, 0), width=3)
            
            # 始点（緑の丸）
            if points:
                draw.ellipse(
                    [(points[0][0]-5, points[0][1]-5),
                     (points[0][0]+5, points[0][1]+5)],
                    fill=(0, 255, 0), outline=(0, 0, 0)
                )
                
            # 終点（赤の丸）
            if points:
                draw.ellipse(
                    [(points[-1][0]-5, points[-1][1]-5),
                     (points[-1][0]+5, points[-1][1]+5)],
                    fill=(255, 0, 0), outline=(0, 0, 0)
                )
        
        # 情報表示（右上）
        width, height = img.size
        font = self.pil_font
        info_x = width - 150
        info_y = 20
        
        # 背景なしで直接テキスト描画
        texts = [
            f"Points: {result['points']}",
            f"Color: {result['color_type']}",
            f"Max: {result['max_rotation']}"
        ]
        
        for text in texts:
            draw.text((info_x, info_y), text, fill=(0, 0, 0), font=font)
            info_y += 20
        
        # 保存
        img.save(output_path)
        self.log(f"可視化画像を保存: {output_path}", "SUCCESS")
    
    def create_graph_plot(self, result: Dict, output_path: str):
        """抽出データをグラフとしてプロット"""
        if not result["data"]:
            return
        
        # データを準備
        df = pd.DataFrame(result["data"])
        
        # プロット作成
        plt.figure(figsize=(12, 8))
        
        # グラフラインをプロット
        plt.plot(df["rotation"], df["value"], linewidth=2, 
                label=f"{result['color_type']}色グラフ", color='green')
        
        # 0ラインを表示
        plt.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='ゼロライン')
        
        # グリッド
        plt.grid(True, alpha=0.3)
        
        # ラベル
        plt.xlabel("回転数", fontsize=12)
        plt.ylabel("差枚数", fontsize=12)
        plt.title(f"抽出グラフデータ - {result['image']}", fontsize=14)
        
        # 範囲設定（固定）
        plt.ylim(-30000, 30000)
        plt.xlim(0, 80000)
        
        # X軸のフォーマット
        ax = plt.gca()
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'{int(y):,}'))
        
        # 最終値を表示
        final_point = result["data"][-1]
        plt.annotate(f'最終値: {final_point["value"]:,.0f}枚\n({final_point["rotation"]:,}回転)', 
                    xy=(final_point["rotation"], final_point["value"]),
                    xytext=(final_point["rotation"] - 10000, final_point["value"] + 5000),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.2'))
        
        # 凡例
        plt.legend(loc='best')
        
        # 保存
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        self.log(f"グラフを保存: {output_path}", "SUCCESS")

def main():
    """メイン処理"""
    print("🎯 統一グラフ抽出システム")
    print("📊 S__78209128の成功例に基づく統一仕様")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal"
    output_folder = "graphs/unified_extracted_data"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 抽出器を初期化
    extractor = UnifiedGraphExtractor()
    
    # 問題のあった画像を優先的に処理
    priority_files = [
        "S__78209130_optimal.png",  # 誤差 -8,997玉
        "S__78209170_optimal.png",  # 誤差 -21,805玉
        "S__78209128_optimal.png",  # 良い例
    ]
    
    for file in priority_files:
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
            print(f"  最終回転数: {result['final_rotation']:,}")
            print(f"  最大値: {max(values):,.0f}")
            print(f"  最小値: {min(values):,.0f}")
            print(f"  最終値: {result['final_value']:,.0f}")

if __name__ == "__main__":
    main()