#!/usr/bin/env python3
"""
精密グラフ切り取りツール
- グラフ描画領域のみを正確に抽出
- 無駄な要素（ヘッダー、ボタン、ラベル）を除外
- グリッド線と0ラインを基準に正確な境界検出
"""

import os
import numpy as np
from PIL import Image
import cv2
from typing import Tuple, Optional, Dict
from datetime import datetime

class PreciseGraphCropper:
    """精密グラフ切り取りシステム"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        # グラフ内部の描画領域のみのサイズ（推定）
        self.GRAPH_WIDTH = 700  # 左右のラベルを除く
        self.GRAPH_HEIGHT = 600  # ヘッダーとボタンを除く
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            timestamp = datetime.now().strftime("%H:%M:%S")
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{timestamp}] {message}")
    
    def detect_grid_lines(self, img_array: np.ndarray) -> Dict[str, list]:
        """グリッド線を検出してグラフ領域を特定"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # エッジ検出
        edges = cv2.Canny(gray, 30, 100)
        
        # 水平線検出（グリッド線）
        horizontal_lines = []
        min_line_length = width * 0.3  # 画面幅の30%以上の長さ
        
        for y in range(height):
            line_pixels = np.where(edges[y, :] > 0)[0]
            if len(line_pixels) > min_line_length:
                # 連続性チェック
                if len(line_pixels) > 0:
                    diff = np.diff(line_pixels)
                    if np.max(diff) < 50:  # 途切れが50px未満
                        horizontal_lines.append(y)
        
        # 垂直線検出（左右の境界）
        vertical_lines = []
        min_line_length = height * 0.3
        
        for x in range(width):
            line_pixels = np.where(edges[:, x] > 0)[0]
            if len(line_pixels) > min_line_length:
                vertical_lines.append(x)
        
        return {
            "horizontal": horizontal_lines,
            "vertical": vertical_lines
        }
    
    def detect_zero_line(self, img_array: np.ndarray, horizontal_lines: list) -> Optional[int]:
        """0ラインを検出（最も濃い水平線）"""
        if not horizontal_lines:
            return None
        
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        height, width = gray.shape
        
        # 各水平線の濃さを評価
        line_scores = []
        for y in horizontal_lines:
            if 0 < y < height - 1:
                # ライン周辺のピクセル値を取得
                line_region = gray[max(0, y-2):min(height, y+3), :]
                darkness_score = np.mean(255 - line_region)  # 暗いほど高スコア
                line_scores.append((y, darkness_score))
        
        if line_scores:
            # 最も濃い線を0ラインとする
            line_scores.sort(key=lambda x: x[1], reverse=True)
            return line_scores[0][0]
        
        return None
    
    def find_graph_boundaries(self, img_array: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """グラフの正確な境界を検出"""
        height, width = img_array.shape[:2]
        
        # グリッド線検出
        grid_lines = self.detect_grid_lines(img_array)
        
        # 水平グリッド線からグラフの上下境界を推定
        h_lines = sorted(grid_lines["horizontal"])
        if len(h_lines) >= 2:
            # 最初と最後のグリッド線をグラフ境界とする
            graph_top = h_lines[0]
            graph_bottom = h_lines[-1]
        else:
            # フォールバック：色の変化を検出
            graph_top, graph_bottom = self.detect_graph_area_by_color(img_array)
        
        # 垂直境界の検出
        v_lines = sorted(grid_lines["vertical"])
        if len(v_lines) >= 2:
            # グラフエリアの左右境界
            # Y軸ラベル（BACK/NEXT）を除外
            potential_left = [x for x in v_lines if x > width * 0.1]
            potential_right = [x for x in v_lines if x < width * 0.9]
            
            if potential_left and potential_right:
                graph_left = min(potential_left)
                graph_right = max(potential_right)
            else:
                graph_left = int(width * 0.15)
                graph_right = int(width * 0.85)
        else:
            graph_left = int(width * 0.15)
            graph_right = int(width * 0.85)
        
        # 0ライン検出
        zero_line_y = self.detect_zero_line(img_array, h_lines)
        if zero_line_y:
            self.log(f"0ライン検出: Y={zero_line_y}", "SUCCESS")
        
        return (graph_left, graph_top, graph_right, graph_bottom)
    
    def detect_graph_area_by_color(self, img_array: np.ndarray) -> Tuple[int, int]:
        """色の変化でグラフ領域を検出"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 上部境界：オレンジヘッダーの下を探す
        graph_top = 0
        for y in range(int(height * 0.1), int(height * 0.4)):
            row_std = np.std(gray[y, :])
            if row_std > 10:  # 変化がある行
                graph_top = y
                break
        
        # 下部境界：ボタン領域の上を探す
        graph_bottom = height
        for y in range(int(height * 0.9), int(height * 0.6), -1):
            row_std = np.std(gray[y, :])
            if row_std > 20:  # ボタンなどの要素
                graph_bottom = y - 10
                break
        
        return graph_top, graph_bottom
    
    def crop_precise_graph(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str], Dict]:
        """精密なグラフ切り取りを実行"""
        try:
            self.log(f"🎯 精密グラフ切り取り開始: {os.path.basename(image_path)}", "INFO")
            
            # 画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # グラフ境界検出
            bounds = self.find_graph_boundaries(img_array)
            if bounds is None:
                return False, None, {"error": "境界検出失敗"}
            
            left, top, right, bottom = bounds
            
            # 切り取り実行
            cropped_img = img.crop(bounds)
            
            # 出力パス生成
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"{base_name}_precise.png"
            
            # 保存
            cropped_img.save(output_path, "PNG", optimize=True)
            
            # 詳細情報
            actual_width = right - left
            actual_height = bottom - top
            
            details = {
                "original_size": img.size,
                "cropped_size": (actual_width, actual_height),
                "boundaries": bounds,
                "success": True
            }
            
            self.log(f"✅ 切り取り成功: {actual_width}×{actual_height}", "SUCCESS")
            
            return True, output_path, details
            
        except Exception as e:
            self.log(f"❌ エラー: {str(e)}", "ERROR")
            return False, None, {"error": str(e)}

def main():
    """テスト実行"""
    print("🎯 精密グラフ切り取りツール")
    
    # 入出力フォルダ設定
    input_folder = "graphs/cropped_perfect"
    output_folder = "graphs/precise"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 画像ファイルを取得
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith('.png')]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    cropper = PreciseGraphCropper(debug_mode=False)
    
    # 最初の画像でテスト
    test_file = image_files[0]
    input_path = os.path.join(input_folder, test_file)
    output_path = os.path.join(output_folder, f"{os.path.splitext(test_file)[0]}_precise.png")
    
    success, output_file, details = cropper.crop_precise_graph(input_path, output_path)
    
    if success:
        print(f"✅ テスト成功: {details['cropped_size']}")
        print(f"📁 出力: {output_path}")
    else:
        print(f"❌ テスト失敗: {details.get('error')}")

if __name__ == "__main__":
    main()