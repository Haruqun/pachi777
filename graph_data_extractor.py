#!/usr/bin/env python3
"""
グラフデータ抽出ツール
- 確定した境界内でグラフラインをトレース
- ピクセル座標から実際の値へ変換
- CSV形式でデータ出力
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

class GraphDataExtractor:
    """グラフデータ抽出システム"""
    
    def __init__(self, config_path="graph_boundaries_final_config.json"):
        # 設定ファイルを読み込み
        with open(config_path, "r") as f:
            self.config = json.load(f)
        
        self.boundaries = self.config["boundaries"]
        self.debug_mode = True
        
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
    
    def trace_graph_line(self, img_array: np.ndarray, color_type: str) -> List[Tuple[int, int]]:
        """グラフラインをトレース"""
        points = []
        
        # X座標ごとにスキャン
        for x in range(self.boundaries["start_x"], self.boundaries["end_x"]):
            # Y座標の候補を収集
            y_candidates = []
            
            # グラフ領域内でスキャン
            for y in range(self.boundaries["top_y"], self.boundaries["bottom_y"]):
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
        # value = 30000 - (y - top_y) * 60000 / height
        height = self.boundaries["bottom_y"] - self.boundaries["top_y"]
        value = 30000 - (y - self.boundaries["top_y"]) * 60000 / height
        return value
    
    def x_to_rotation(self, x: int, max_rotation: int) -> int:
        """X座標を回転数に変換"""
        # rotation = (x - start_x) * max_rotation / width
        width = self.boundaries["end_x"] - self.boundaries["start_x"]
        rotation = int((x - self.boundaries["start_x"]) * max_rotation / width)
        return rotation
    
    def extract_max_rotation(self, img_array: np.ndarray) -> int:
        """X軸の最大回転数を読み取る（簡易版）"""
        # 右下の数値を探す（例: 80,000）
        # 実装を簡略化し、一般的な値を返す
        height, width = img_array.shape[:2]
        
        # デフォルト値のマッピング
        # 画像のパターンに基づいて推定
        if width > 700:
            return 80000
        else:
            return 50000
    
    def extract_graph_data(self, image_path: str) -> Dict:
        """グラフデータを抽出"""
        self.log(f"処理開始: {os.path.basename(image_path)}")
        
        # 画像読み込み
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # グラフの色を判定
        color_type = self.detect_graph_color(img_array)
        self.log(f"グラフ色: {color_type}", "INFO")
        
        # 最大回転数を取得
        max_rotation = self.extract_max_rotation(img_array)
        self.log(f"最大回転数: {max_rotation}", "INFO")
        
        # グラフラインをトレース
        points = self.trace_graph_line(img_array, color_type)
        self.log(f"検出点数: {len(points)}", "INFO")
        
        # データ変換
        data = []
        for x, y in points:
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
            "points": len(points),
            "data": data
        }
    
    def save_to_csv(self, result: Dict, output_path: str):
        """抽出データをCSVに保存"""
        df = pd.DataFrame(result["data"])
        df.to_csv(output_path, index=False)
        self.log(f"CSVファイルを保存: {output_path}", "SUCCESS")
    
    def create_visualization(self, image_path: str, result: Dict, output_path: str):
        """抽出結果を可視化"""
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
        draw.text((width-250, info_y), f"Points: {result['points']}", fill=(0, 0, 0))
        info_y += 20
        draw.text((width-250, info_y), f"Color: {result['color_type']}", fill=(0, 0, 0))
        info_y += 20
        draw.text((width-250, info_y), f"Max: {result['max_rotation']}", fill=(0, 0, 0))
        
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
        
        # 範囲設定
        plt.ylim(-30000, 30000)
        plt.xlim(0, result["max_rotation"])
        
        # 凡例
        plt.legend()
        
        # 保存
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        self.log(f"グラフを保存: {output_path}", "SUCCESS")

def main():
    """メイン処理"""
    print("🎯 グラフデータ抽出ツール")
    print("📊 グラフラインをトレースしてデータを抽出します")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal_v2"
    output_folder = "graphs/extracted_data"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 抽出器を初期化
    extractor = GraphDataExtractor()
    
    # テスト画像を処理
    test_files = ["S__78209130_optimal.png", "S__78209132_optimal.png", "S__78209174_optimal.png"]
    
    for file in test_files:
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
            print(f"  最大値: {max(values):.0f}")
            print(f"  最小値: {min(values):.0f}")
            print(f"  最終値: {values[-1]:.0f}")

if __name__ == "__main__":
    main()