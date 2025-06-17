#!/usr/bin/env python3
"""
高精度開始点検出ツール
- グラフの開始点をピクセル単位で正確に検出
- 垂直グリッド線を基準に統一
"""

import os
import numpy as np
from PIL import Image, ImageDraw
import cv2
from typing import Tuple, Optional, Dict, List

class PreciseStartDetector:
    """高精度開始点検出システム"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        # 基準線
        self.y_lines = {
            "top": 29,
            "zero": 274,
            "bottom": 520
        }
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{level}] {message}")
    
    def detect_vertical_grid_lines(self, img_array: np.ndarray) -> List[int]:
        """垂直グリッド線を検出"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 垂直方向のエッジを検出
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_x_abs = np.abs(sobel_x)
        
        # グラフエリア内で垂直エッジの強度を計算
        graph_area = sobel_x_abs[self.y_lines["top"]:self.y_lines["bottom"], :]
        vertical_projection = np.mean(graph_area, axis=0)
        
        # しきい値以上のピークを検出
        threshold = np.mean(vertical_projection) + np.std(vertical_projection)
        peaks = []
        
        for x in range(1, width-1):
            if vertical_projection[x] > threshold:
                # 局所的なピークか確認
                if vertical_projection[x] > vertical_projection[x-1] and \
                   vertical_projection[x] > vertical_projection[x+1]:
                    peaks.append(x)
        
        # 近接したピークをマージ
        if not peaks:
            return []
        
        merged_peaks = []
        current_group = [peaks[0]]
        
        for i in range(1, len(peaks)):
            if peaks[i] - peaks[i-1] <= 3:
                current_group.append(peaks[i])
            else:
                merged_peaks.append(int(np.mean(current_group)))
                current_group = [peaks[i]]
        merged_peaks.append(int(np.mean(current_group)))
        
        return merged_peaks
    
    def detect_first_vertical_line(self, img_array: np.ndarray) -> int:
        """最初の垂直線（グラフ開始点）を検出"""
        height, width = img_array.shape[:2]
        
        # 垂直グリッド線を検出
        vertical_lines = self.detect_vertical_grid_lines(img_array)
        
        if vertical_lines:
            # 左側の候補線を選択（画面の左1/3以内）
            left_candidates = [x for x in vertical_lines if x < width // 3]
            
            if left_candidates:
                # 最初の明確な垂直線
                first_line = min(left_candidates)
                self.log(f"垂直グリッド線検出: X={first_line}", "DEBUG")
                return first_line
        
        # フォールバック: エッジ検出で最初の強い垂直線を探す
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        
        # グラフエリア内で検索
        search_area = edges[self.y_lines["top"]:self.y_lines["bottom"], :width//3]
        
        for x in range(20, search_area.shape[1]):
            column_sum = np.sum(search_area[:, x])
            if column_sum > search_area.shape[0] * 0.5:  # 高さの50%以上のエッジ
                self.log(f"エッジ検出による開始点: X={x}", "DEBUG")
                return x
        
        # デフォルト値
        return 35
    
    def detect_graph_start_precise(self, img_array: np.ndarray) -> int:
        """高精度でグラフ開始点を検出"""
        # 方法1: 垂直グリッド線
        grid_start = self.detect_first_vertical_line(img_array)
        
        # 方法2: グラフライン色の開始点
        color_start = self.detect_color_start(img_array)
        
        # 両方の結果を比較
        if abs(grid_start - color_start) < 10:
            # 近い場合は平均を取る
            final_start = (grid_start + color_start) // 2
        else:
            # 差が大きい場合はグリッド線を優先
            final_start = grid_start
        
        self.log(f"最終的な開始点: X={final_start} (グリッド: {grid_start}, 色: {color_start})", "INFO")
        
        return final_start
    
    def detect_color_start(self, img_array: np.ndarray) -> int:
        """グラフの色から開始点を検出"""
        height, width = img_array.shape[:2]
        
        # 0ライン周辺でスキャン
        scan_lines = [
            self.y_lines["zero"] - 50,
            self.y_lines["zero"],
            self.y_lines["zero"] + 50
        ]
        
        start_positions = []
        
        for y in scan_lines:
            if 0 <= y < height:
                for x in range(20, width // 3):
                    r, g, b = img_array[y, x]
                    
                    # グラフ色の検出（緩い条件）
                    is_graph = (r > 100 and g < 180 and b > 80) or \
                              (b > 120 and r < 180 and g < 180)
                    
                    if is_graph:
                        start_positions.append(x)
                        break
        
        if start_positions:
            # 中央値を返す
            return int(np.median(start_positions))
        
        return 35  # デフォルト
    
    def create_precise_start_overlay(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str], Dict]:
        """高精度開始点のオーバーレイを作成"""
        try:
            self.log(f"処理開始: {os.path.basename(image_path)}")
            
            # 画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            width, height = img.size
            
            # 開始点を検出
            graph_start = self.detect_graph_start_precise(img_array)
            
            # 垂直グリッド線も検出して表示
            vertical_lines = self.detect_vertical_grid_lines(img_array)
            
            # オーバーレイ描画
            draw = ImageDraw.Draw(img)
            
            # 水平基準線（既存）
            y = self.y_lines["top"]
            draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=2)
            
            y = self.y_lines["zero"]
            draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=3)
            
            y = self.y_lines["bottom"]
            draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=2)
            
            # 検出された垂直グリッド線を薄く表示
            for x in vertical_lines[:10]:  # 最初の10本のみ
                draw.line([(x, self.y_lines["top"]), (x, self.y_lines["bottom"])], 
                         fill=(200, 200, 200), width=1)
            
            # グラフ開始線（太い緑線）
            draw.line([(graph_start, 0), (graph_start, height)], fill=(0, 255, 0), width=3)
            draw.text((graph_start+5, 10), "START", fill=(0, 255, 0))
            draw.text((graph_start+5, height-30), f"X={graph_start}", fill=(0, 255, 0))
            
            # 情報表示
            info_y = 20
            draw.text((width-200, info_y), f"Start: X={graph_start}", fill=(0, 0, 0))
            info_y += 20
            draw.text((width-200, info_y), f"Grid lines: {len(vertical_lines)}", fill=(0, 0, 0))
            
            # 出力パス生成
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"{base_name}_precise_start.png"
            
            # 保存
            img.save(output_path, "PNG")
            
            self.log(f"オーバーレイ画像を保存: {output_path}", "SUCCESS")
            
            return True, output_path, {"start_x": graph_start, "vertical_lines": vertical_lines}
            
        except Exception as e:
            self.log(f"エラー: {str(e)}", "ERROR")
            return False, None, {}

def main():
    """メイン処理"""
    print("🎯 高精度開始点検出ツール")
    print("📊 グラフの開始点をピクセル単位で正確に検出します")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal_v2"
    output_folder = "graphs/precise_start"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 画像ファイルを取得
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith('.png')]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    detector = PreciseStartDetector(debug_mode=True)
    
    # 開始点の統計
    start_positions = []
    
    # 各画像を処理
    for i, file in enumerate(image_files, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(image_files)}] 処理中: {file}")
        
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, 
                                   f"{os.path.splitext(file)[0]}_start.png")
        
        success, _, info = detector.create_precise_start_overlay(input_path, output_path)
        
        if success and "start_x" in info:
            start_positions.append(info["start_x"])
    
    # 統計情報
    if start_positions:
        print(f"\n📊 開始点統計:")
        print(f"  最小: {min(start_positions)}px")
        print(f"  最大: {max(start_positions)}px")
        print(f"  平均: {np.mean(start_positions):.1f}px")
        print(f"  標準偏差: {np.std(start_positions):.1f}px")
        
        # ヒストグラム
        unique, counts = np.unique(start_positions, return_counts=True)
        print(f"\n  分布:")
        for pos, count in zip(unique, counts):
            print(f"    X={pos}: {'■' * count} ({count}枚)")

if __name__ == "__main__":
    main()