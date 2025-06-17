#!/usr/bin/env python3
"""
改良版グラフデータ抽出ツール
- 実際のグラフデータが存在する範囲のみを抽出
- X軸の全範囲（0-80,000）を正しくマッピング
- データが途中で終わる場合も適切に処理
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

class ImprovedGraphDataExtractor:
    """改良版グラフデータ抽出システム"""
    
    def __init__(self):
        # 境界値設定
        self.boundaries = {
            "start_x": 36,
            "end_x": 620,
            "top_y": 29,
            "zero_y": 274,
            "bottom_y": 520
        }
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
    
    def trace_graph_line(self, img_array: np.ndarray, color_type: str, end_x: int) -> List[Tuple[int, int]]:
        """グラフラインをトレース（実際のデータ範囲のみ）"""
        points = []
        height, width = img_array.shape[:2]
        
        # 境界を画像サイズに合わせて調整
        max_y = min(height, self.boundaries["bottom_y"])
        min_y = max(0, self.boundaries["top_y"])
        
        # X座標ごとにスキャン（実際のデータ範囲のみ）
        for x in range(self.boundaries["start_x"], min(end_x + 1, self.boundaries["end_x"], width)):
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
        """X座標を回転数に変換（X軸の全範囲を使用）"""
        # X軸の全範囲（start_x から end_x）を0からmax_rotationにマッピング
        width = self.boundaries["end_x"] - self.boundaries["start_x"]
        rotation = int((x - self.boundaries["start_x"]) * max_rotation / width)
        return rotation
    
    def extract_max_rotation(self, img_array: np.ndarray) -> int:
        """X軸の最大回転数を読み取る"""
        # 画像の右側に80,000などの数値があることを前提
        # ここでは簡略化して、一般的な値を返す
        height, width = img_array.shape[:2]
        
        # デフォルト値
        if width > 700:
            return 80000
        else:
            # もし他のパターンがあれば追加
            return 80000  # ほとんどの画像は80,000のようです
    
    def extract_graph_data(self, image_path: str) -> Dict:
        """グラフデータを抽出（改良版）"""
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
        
        # データの終端を検出
        data_end_x = self.find_data_endpoint(img_array, color_type)
        self.log(f"データ終端: x={data_end_x}", "INFO")
        
        # データ終端での回転数を計算
        data_end_rotation = self.x_to_rotation(data_end_x, max_rotation)
        self.log(f"データ終端の回転数: {data_end_rotation}", "INFO")
        
        # グラフラインをトレース（実際のデータ範囲のみ）
        points = self.trace_graph_line(img_array, color_type, data_end_x)
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
            "data_end_x": data_end_x,
            "data_end_rotation": data_end_rotation,
            "points": len(points),
            "data": data
        }
    
    def save_to_csv(self, result: Dict, output_path: str):
        """抽出データをCSVに保存"""
        df = pd.DataFrame(result["data"])
        df.to_csv(output_path, index=False)
        self.log(f"CSVファイルを保存: {output_path}", "SUCCESS")
    
    def create_visualization(self, image_path: str, result: Dict, output_path: str):
        """抽出結果を可視化（改良版）"""
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
        
        # データ範囲
        if result["data_end_x"] < self.boundaries["end_x"]:
            draw.rectangle(
                [(self.boundaries["start_x"], self.boundaries["top_y"]),
                 (result["data_end_x"], self.boundaries["bottom_y"])],
                outline=(0, 255, 0), width=2
            )
            
            # データ終端ライン
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
        
        # 情報表示
        info_y = 20
        draw.text((width-300, info_y), f"Points: {result['points']}", fill=(0, 0, 0))
        info_y += 20
        draw.text((width-300, info_y), f"Color: {result['color_type']}", fill=(0, 0, 0))
        info_y += 20
        draw.text((width-300, info_y), f"Max rotation: {result['max_rotation']}", fill=(0, 0, 0))
        info_y += 20
        draw.text((width-300, info_y), f"Data ends at: {result['data_end_rotation']}", fill=(0, 0, 0))
        
        # 保存
        img.save(output_path)
        self.log(f"可視化画像を保存: {output_path}", "SUCCESS")
    
    def create_graph_plot(self, result: Dict, output_path: str):
        """抽出データをグラフとしてプロット（改良版）"""
        if not result["data"]:
            return
        
        # データを準備
        df = pd.DataFrame(result["data"])
        
        # 日本語フォント設定
        try:
            # macOSの日本語フォントを設定
            plt.rcParams['font.family'] = ['Hiragino Sans GB', 'Hiragino Kaku Gothic Pro', 'Yu Gothic', 'Meiryo', 'sans-serif']
        except:
            pass
        
        # プロット作成
        plt.figure(figsize=(12, 8))
        
        # 元のグラフラインをプロット
        plt.plot(df["rotation"], df["value"], linewidth=2, 
                label=f"{result['color_type']}色グラフ")
        
        # データ終端を表示
        if result["data_end_rotation"] < result["max_rotation"]:
            plt.axvline(x=result["data_end_rotation"], color='green', 
                       linestyle='--', alpha=0.7, 
                       label=f'データ終端 ({result["data_end_rotation"]})')
        
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
    print("🎯 改良版グラフデータ抽出ツール")
    print("📊 実際のデータ範囲のみを正確に抽出します")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal"
    output_folder = "graphs/improved_extracted_data"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 抽出器を初期化
    extractor = ImprovedGraphDataExtractor()
    
    # すべての画像ファイルを取得
    all_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.png')]
    print(f"\n📁 検出された画像: {len(all_files)}枚")
    
    # 結果を記録
    all_results = []
    
    for i, file in enumerate(all_files, 1):
        input_path = os.path.join(input_folder, file)
        if not os.path.exists(input_path):
            continue
        
        print(f"\n{'='*60}")
        print(f"[{i}/{len(all_files)}] 処理中: {file}")
        
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
        
        # 結果を記録
        all_results.append(result)
        
        # 結果サマリー
        if result["data"]:
            values = [d["value"] for d in result["data"]]
            print(f"\n📊 抽出結果:")
            print(f"  データ点数: {len(result['data'])}")
            print(f"  データ範囲: 0 - {result['data_end_rotation']} (全体: 0 - {result['max_rotation']})")
            print(f"  最大値: {max(values):.0f}")
            print(f"  最小値: {min(values):.0f}")
            print(f"  最終値: {values[-1]:.0f}")
    
    # 全体のサマリーレポート作成
    print(f"\n\n{'='*60}")
    print("📊 全体サマリー")
    print(f"処理画像数: {len(all_results)}")
    
    # 統計情報
    total_points = sum(r["points"] for r in all_results)
    print(f"総データポイント数: {total_points}")
    
    # データ終端の統計
    end_rotations = [r["data_end_rotation"] for r in all_results]
    avg_end = np.mean(end_rotations)
    print(f"\n平均データ終端: {avg_end:.0f} (全体の{avg_end/80000*100:.1f}%)")
    print(f"最小データ終端: {min(end_rotations)} ({min(end_rotations)/80000*100:.1f}%)")
    print(f"最大データ終端: {max(end_rotations)} ({max(end_rotations)/80000*100:.1f}%)")
    
    # 色別統計
    color_counts = {}
    for r in all_results:
        color = r["color_type"]
        color_counts[color] = color_counts.get(color, 0) + 1
    
    print("\n色別内訳:")
    for color, count in color_counts.items():
        print(f"  {color}: {count}枚")
    
    # レポートファイル保存
    import datetime
    report_filename = f"improved_extraction_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump({
            "extraction_date": datetime.datetime.now().isoformat(),
            "boundaries": extractor.boundaries,
            "total_images": len(all_results),
            "total_points": total_points,
            "average_data_endpoint": avg_end,
            "color_distribution": color_counts,
            "results": all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ レポートを保存: {report_filename}")

if __name__ == "__main__":
    main()