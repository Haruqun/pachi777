#!/usr/bin/env python3
"""
グラフ境界検出ツール
- グラフの開始点（左端）を検出
- グラフの終了点（右端）を検出
- 基準線と共にオーバーレイ表示
"""

import os
import numpy as np
from PIL import Image, ImageDraw
import cv2
from typing import Tuple, Optional, Dict, List

class GraphBoundaryDetector:
    """グラフ境界検出システム"""
    
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
    
    def detect_graph_start(self, img_array: np.ndarray) -> Optional[int]:
        """グラフの開始点（左端）を検出"""
        height, width = img_array.shape[:2]
        
        # グラフライン（ピンク/紫/青）を検出するため、0ライン付近を重点的に調査
        zero_y = self.y_lines["zero"]
        search_height = 100  # 0ラインの上下50px
        
        start_y = max(0, zero_y - search_height // 2)
        end_y = min(height, zero_y + search_height // 2)
        
        # 左から右へスキャンして、グラフラインの色を探す
        for x in range(width // 4):  # 左側1/4の範囲で探索
            for y in range(start_y, end_y):
                r, g, b = img_array[y, x]
                
                # グラフラインの色判定
                # ピンク系 (R > G, B)
                is_pink = r > 200 and g < 150 and b > 150
                # 紫系
                is_purple = r > 150 and b > 150 and g < 100
                # 青系
                is_blue = b > 200 and r < 150 and g < 200
                
                if is_pink or is_purple or is_blue:
                    # グラフラインの開始を検出
                    self.log(f"グラフ開始点検出: X={x}", "DEBUG")
                    return x
        
        # フォールバック: 垂直線検出
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 垂直エッジの投影
        vertical_projection = np.sum(edges[:, :width//4], axis=0)
        
        # 最初の明確な垂直線を探す
        for x in range(10, width//4):
            if vertical_projection[x] > height * 0.3:  # 高さの30%以上のエッジ
                return x
        
        # デフォルト値
        return 50
    
    def detect_graph_end(self, img_array: np.ndarray) -> Optional[int]:
        """グラフの終了点（右端）を検出"""
        height, width = img_array.shape[:2]
        
        # グラフライン（ピンク/紫/青）を検出
        zero_y = self.y_lines["zero"]
        search_height = 100
        
        start_y = max(0, zero_y - search_height // 2)
        end_y = min(height, zero_y + search_height // 2)
        
        # 右から左へスキャンして、グラフラインの色を探す
        last_graph_x = None
        
        for x in range(width - 1, 3 * width // 4, -1):  # 右側1/4の範囲で探索
            has_graph_color = False
            
            for y in range(start_y, end_y):
                r, g, b = img_array[y, x]
                
                # グラフラインの色判定
                is_pink = r > 200 and g < 150 and b > 150
                is_purple = r > 150 and b > 150 and g < 100
                is_blue = b > 200 and r < 150 and g < 200
                
                if is_pink or is_purple or is_blue:
                    has_graph_color = True
                    last_graph_x = x
                    break
            
            # グラフの色が途切れたら終了
            if last_graph_x and not has_graph_color:
                self.log(f"グラフ終了点検出: X={last_graph_x}", "DEBUG")
                return last_graph_x
        
        # フォールバック: テキスト検出（X軸の数値）
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 右下のテキスト領域を検索
        text_region = gray[int(height * 0.8):, int(width * 0.7):]
        
        # テキストのエッジを検出
        edges = cv2.Canny(text_region, 30, 100)
        vertical_sum = np.sum(edges, axis=0)
        
        # テキストの左端を探す
        for i, val in enumerate(vertical_sum):
            if val > edges.shape[0] * 0.2:
                return int(width * 0.7) + i - 20  # 少し左にオフセット
        
        # デフォルト値
        return width - 50
    
    def create_boundary_overlay(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str]]:
        """グラフ境界をオーバーレイ表示"""
        try:
            self.log(f"処理開始: {os.path.basename(image_path)}")
            
            # 画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            width, height = img.size
            
            # グラフの開始点と終了点を検出
            graph_start = self.detect_graph_start(img_array)
            graph_end = self.detect_graph_end(img_array)
            
            if graph_start:
                self.log(f"グラフ開始: X={graph_start}px", "SUCCESS")
            if graph_end:
                self.log(f"グラフ終了: X={graph_end}px", "SUCCESS")
            
            # グラフ幅を計算
            if graph_start and graph_end:
                graph_width = graph_end - graph_start
                self.log(f"グラフ幅: {graph_width}px", "INFO")
            
            # オーバーレイ描画
            draw = ImageDraw.Draw(img)
            
            # 既存の基準線を描画
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
            
            # グラフ開始線（緑色）
            if graph_start:
                draw.line([(graph_start, 0), (graph_start, height)], fill=(0, 255, 0), width=2)
                draw.text((graph_start+5, 10), "START", fill=(0, 255, 0))
            
            # グラフ終了線（緑色）
            if graph_end:
                draw.line([(graph_end, 0), (graph_end, height)], fill=(0, 255, 0), width=2)
                draw.text((graph_end-40, 10), "END", fill=(0, 255, 0))
            
            # グラフ領域を半透明で強調（オプション）
            if graph_start and graph_end:
                # グラフ領域の枠を描画
                draw.rectangle(
                    [(graph_start, self.y_lines["top"]), (graph_end, self.y_lines["bottom"])],
                    outline=(0, 255, 0),
                    width=1
                )
            
            # 情報テキストを追加
            info_y = 20
            if graph_start and graph_end:
                info_text = f"Width: {graph_end - graph_start}px"
                draw.text((width-150, info_y), info_text, fill=(0, 0, 0))
                info_y += 20
                
                # X座標情報
                draw.text((width-150, info_y), f"X: {graph_start}-{graph_end}", fill=(0, 0, 0))
            
            # 出力パス生成
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"{base_name}_boundaries.png"
            
            # 保存
            img.save(output_path, "PNG")
            
            self.log(f"境界オーバーレイ画像を保存: {output_path}", "SUCCESS")
            
            return True, output_path
            
        except Exception as e:
            self.log(f"エラー: {str(e)}", "ERROR")
            return False, None

def main():
    """メイン処理"""
    print("🎯 グラフ境界検出ツール")
    print("📊 グラフの開始点と終了点を検出してオーバーレイ表示します")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal_v2"
    output_folder = "graphs/boundary_detection"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 画像ファイルを取得
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith('.png')]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    detector = GraphBoundaryDetector(debug_mode=False)
    
    success_count = 0
    
    # すべての画像を処理
    for i, file in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] 処理中: {file}")
        
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, 
                                   f"{os.path.splitext(file)[0]}_boundaries.png")
        
        success, _ = detector.create_boundary_overlay(input_path, output_path)
        
        if success:
            success_count += 1
            print(f"✅ 成功")
        else:
            print(f"❌ 失敗")
    
    print(f"\n✨ 処理完了: {success_count}/{len(image_files)} 成功")

if __name__ == "__main__":
    main()