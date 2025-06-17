#!/usr/bin/env python3
"""
改良版グラフ境界検出ツール
- グラフの終了点をより正確に検出
- 連続性チェックで確実な終端検出
"""

import os
import numpy as np
from PIL import Image, ImageDraw
import cv2
from typing import Tuple, Optional, Dict, List

class ImprovedBoundaryDetector:
    """改良版グラフ境界検出システム"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        # 前回の検出結果を利用
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
    
    def detect_graph_line_colors(self, img_array: np.ndarray, x: int, y_start: int, y_end: int) -> bool:
        """指定したX座標にグラフラインの色があるかチェック"""
        for y in range(y_start, y_end):
            if 0 <= y < img_array.shape[0]:
                r, g, b = img_array[y, x]
                
                # グラフラインの色判定（より厳密に）
                # ピンク系
                is_pink = (r > 200 and g < 180 and b > 150 and r > b)
                # 紫系
                is_purple = (r > 140 and b > 140 and g < 120 and abs(r - b) < 50)
                # 青系
                is_blue = (b > 180 and r < 150 and g < 180 and b > r and b > g)
                
                if is_pink or is_purple or is_blue:
                    return True
        return False
    
    def trace_graph_line(self, img_array: np.ndarray) -> Tuple[int, int]:
        """グラフラインをトレースして開始点と終了点を見つける"""
        height, width = img_array.shape[:2]
        
        # 0ライン周辺でスキャン
        zero_y = self.y_lines["zero"]
        scan_height = 150  # スキャン範囲を広げる
        y_start = max(0, zero_y - scan_height // 2)
        y_end = min(height, zero_y + scan_height // 2)
        
        # 開始点の検出（左から右へ）
        graph_start = None
        for x in range(50, width // 3):  # 左側1/3で探索
            if self.detect_graph_line_colors(img_array, x, y_start, y_end):
                graph_start = x
                self.log(f"グラフ開始点候補: X={x}", "DEBUG")
                break
        
        if graph_start is None:
            graph_start = 50  # デフォルト値
            self.log("グラフ開始点が見つからず、デフォルト値を使用", "WARNING")
        
        # 終了点の検出（連続性チェック）
        graph_end = None
        consecutive_empty = 0
        required_empty = 10  # 10ピクセル連続で色がなければ終了と判定
        
        # 開始点から右へスキャン
        for x in range(graph_start + 50, width - 20):
            has_color = self.detect_graph_line_colors(img_array, x, y_start, y_end)
            
            if has_color:
                consecutive_empty = 0
                graph_end = x  # 最後に色があった位置を更新
            else:
                consecutive_empty += 1
                
            # 連続して色がない場合は終了
            if consecutive_empty >= required_empty and graph_end is not None:
                self.log(f"グラフ終了点確定: X={graph_end} (連続空白: {consecutive_empty}px)", "DEBUG")
                break
        
        # 終了点が見つからない場合
        if graph_end is None:
            # X軸の数値表示位置から推定
            graph_end = self.estimate_end_from_text(img_array)
            
        return graph_start, graph_end
    
    def estimate_end_from_text(self, img_array: np.ndarray) -> int:
        """X軸のテキスト位置から終了点を推定"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 右下のテキスト領域（X軸の数値）
        text_y_start = int(height * 0.85)
        text_region = gray[text_y_start:, int(width * 0.6):]
        
        # エッジ検出でテキストを見つける
        edges = cv2.Canny(text_region, 50, 150)
        
        # 左から右へスキャンしてテキストの開始位置を探す
        for x in range(text_region.shape[1]):
            column_sum = np.sum(edges[:, x])
            if column_sum > edges.shape[0] * 0.3:  # 縦の30%以上にエッジがある
                # テキストの左端から少し左をグラフ終了点とする
                return int(width * 0.6) + x - 30
        
        # デフォルト値
        return width - 100
    
    def analyze_graph_width(self, img_array: np.ndarray, start_x: int, end_x: int) -> Dict:
        """グラフ幅の詳細分析"""
        # グラフエリアのサンプリング
        sample_y_positions = [
            self.y_lines["top"] + 50,
            self.y_lines["zero"],
            self.y_lines["bottom"] - 50
        ]
        
        color_densities = []
        for y in sample_y_positions:
            row_colors = 0
            for x in range(start_x, end_x):
                if self.detect_graph_line_colors(img_array, x, y-5, y+5):
                    row_colors += 1
            density = row_colors / (end_x - start_x) if end_x > start_x else 0
            color_densities.append(density)
        
        return {
            "avg_density": np.mean(color_densities),
            "min_density": np.min(color_densities),
            "max_density": np.max(color_densities)
        }
    
    def create_improved_overlay(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str]]:
        """改良版オーバーレイを作成"""
        try:
            self.log(f"処理開始: {os.path.basename(image_path)}")
            
            # 画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            width, height = img.size
            
            # グラフラインをトレース
            graph_start, graph_end = self.trace_graph_line(img_array)
            
            self.log(f"グラフ開始: X={graph_start}px", "SUCCESS")
            self.log(f"グラフ終了: X={graph_end}px", "SUCCESS")
            
            # グラフ幅を計算
            graph_width = graph_end - graph_start
            self.log(f"グラフ幅: {graph_width}px", "INFO")
            
            # グラフ幅の分析
            width_analysis = self.analyze_graph_width(img_array, graph_start, graph_end)
            self.log(f"グラフ密度: 平均{width_analysis['avg_density']:.2%}", "DEBUG")
            
            # オーバーレイ描画
            draw = ImageDraw.Draw(img)
            
            # 水平基準線
            # +30,000ライン（青色）
            y = self.y_lines["top"]
            draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=2)
            draw.text((10, y-20), f"+30,000", fill=(0, 0, 255))
            
            # 0ライン（赤色）
            y = self.y_lines["zero"]
            draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=3)
            draw.text((10, y-20), "0", fill=(255, 0, 0))
            
            # -30,000ライン（青色）
            y = self.y_lines["bottom"]
            draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=2)
            draw.text((10, y+5), "-30,000", fill=(0, 0, 255))
            
            # 垂直境界線
            # グラフ開始線（緑色）
            draw.line([(graph_start, 0), (graph_start, height)], fill=(0, 255, 0), width=2)
            draw.text((graph_start+5, 10), "START", fill=(0, 255, 0))
            draw.text((graph_start+5, height-30), f"X={graph_start}", fill=(0, 255, 0))
            
            # グラフ終了線（オレンジ色）
            draw.line([(graph_end, 0), (graph_end, height)], fill=(255, 165, 0), width=2)
            draw.text((graph_end-40, 10), "END", fill=(255, 165, 0))
            draw.text((graph_end-50, height-30), f"X={graph_end}", fill=(255, 165, 0))
            
            # グラフ領域の枠
            draw.rectangle(
                [(graph_start, self.y_lines["top"]), (graph_end, self.y_lines["bottom"])],
                outline=(128, 128, 128),
                width=1
            )
            
            # 情報表示
            info_x = width - 200
            info_y = 20
            
            draw.text((info_x, info_y), f"Width: {graph_width}px", fill=(0, 0, 0))
            info_y += 20
            draw.text((info_x, info_y), f"Range: X {graph_start}-{graph_end}", fill=(0, 0, 0))
            info_y += 20
            draw.text((info_x, info_y), f"Density: {width_analysis['avg_density']:.1%}", fill=(0, 0, 0))
            
            # 出力パス生成
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"{base_name}_improved_boundaries.png"
            
            # 保存
            img.save(output_path, "PNG")
            
            self.log(f"改良版オーバーレイ画像を保存: {output_path}", "SUCCESS")
            
            return True, output_path
            
        except Exception as e:
            self.log(f"エラー: {str(e)}", "ERROR")
            return False, None

def main():
    """メイン処理"""
    print("🎯 改良版グラフ境界検出ツール")
    print("📊 より正確なグラフ終了点検出を実行します")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal_v2"
    output_folder = "graphs/improved_boundaries"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # テスト用に最初の5枚を処理
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith('.png')][:5]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    detector = ImprovedBoundaryDetector(debug_mode=True)
    
    success_count = 0
    
    # 各画像を処理
    for i, file in enumerate(image_files, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(image_files)}] 処理中: {file}")
        
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, 
                                   f"{os.path.splitext(file)[0]}_improved.png")
        
        success, _ = detector.create_improved_overlay(input_path, output_path)
        
        if success:
            success_count += 1
    
    print(f"\n✨ 処理完了: {success_count}/{len(image_files)} 成功")

if __name__ == "__main__":
    main()