#!/usr/bin/env python3
"""
調整版グラフ境界設定ツール
- 開始点: もう少し右側へ
- 終了点: もう少し右側へ
"""

import os
import numpy as np
from PIL import Image, ImageDraw
import cv2
from typing import Tuple, Optional, Dict

class AdjustedGraphBoundaries:
    """調整版グラフ境界設定システム"""
    
    def __init__(self):
        # 調整前の境界値
        self.old_boundaries = {
            "start_x": 8,
            "end_x": 585,
            "top_y": 29,
            "zero_y": 274,
            "bottom_y": 520
        }
        
        # 新しい境界値（初期値）
        self.boundaries = {
            "start_x": None,
            "end_x": None,
            "top_y": 29,
            "zero_y": 274,
            "bottom_y": 520
        }
        
    def analyze_start_position(self, img_array: np.ndarray) -> int:
        """より正確な開始位置を分析"""
        height, width = img_array.shape[:2]
        
        # グラフエリア内で最初の垂直線を探す
        # Y軸ラベル（BACK）の右側を開始点とする
        
        # グレースケール変換
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 垂直エッジ検出
        edges = cv2.Canny(gray, 50, 150)
        
        # グラフエリア内で検索（Y軸の範囲内）
        search_area = edges[self.boundaries["top_y"]:self.boundaries["bottom_y"], :width//4]
        
        # 強い垂直線を探す
        for x in range(20, search_area.shape[1]):
            column_sum = np.sum(search_area[:, x])
            if column_sum > search_area.shape[0] * 0.7:  # 高さの70%以上のエッジ
                # もう少し右にオフセット（Y軸ラベルを避ける）
                return x + 15
        
        # デフォルト: 以前より右側
        return 35
    
    def analyze_end_position(self, img_array: np.ndarray) -> int:
        """より正確な終了位置を分析"""
        height, width = img_array.shape[:2]
        
        # X軸の数値（80,000など）の位置を検出
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 下部のテキスト領域
        text_y = int(height * 0.88)
        text_region = gray[text_y:text_y+40, int(width*0.7):]
        
        # エッジ検出でテキストを探す
        edges = cv2.Canny(text_region, 50, 150)
        
        # 左から右へスキャンしてテキストの開始を探す
        text_start = None
        for x in range(text_region.shape[1]):
            if np.sum(edges[:, x]) > edges.shape[0] * 0.3:
                text_start = x
                break
        
        if text_start is not None:
            # テキストの左端から少し左をグラフ終了点とする
            # より右側に設定
            return int(width * 0.7) + text_start - 10
        
        # デフォルト: 画像幅の90%位置
        return int(width * 0.90)
    
    def determine_optimal_boundaries(self, sample_images: list):
        """複数の画像から最適な境界を決定"""
        start_positions = []
        end_positions = []
        
        print("\n境界位置の分析:")
        for img_path in sample_images:
            img = Image.open(img_path)
            img_array = np.array(img)
            
            start_x = self.analyze_start_position(img_array)
            end_x = self.analyze_end_position(img_array)
            
            start_positions.append(start_x)
            end_positions.append(end_x)
            
            print(f"  {os.path.basename(img_path)}: 開始={start_x}, 終了={end_x}")
        
        # 中央値を採用
        self.boundaries["start_x"] = int(np.median(start_positions))
        self.boundaries["end_x"] = int(np.median(end_positions))
        
        print(f"\n調整後の境界:")
        print(f"  開始X: {self.old_boundaries['start_x']} → {self.boundaries['start_x']}px")
        print(f"  終了X: {self.old_boundaries['end_x']} → {self.boundaries['end_x']}px")
    
    def create_comparison_overlay(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str]]:
        """新旧の境界を比較表示"""
        try:
            # 画像読み込み
            img = Image.open(image_path)
            width, height = img.size
            
            # オーバーレイ描画
            draw = ImageDraw.Draw(img)
            
            # 水平線（Y軸）- 変更なし
            y = self.boundaries["top_y"]
            draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=2)
            draw.text((10, y-20), "+30,000", fill=(0, 0, 255))
            
            y = self.boundaries["zero_y"]
            draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=3)
            draw.text((10, y-20), "0", fill=(255, 0, 0))
            
            y = self.boundaries["bottom_y"]
            draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=2)
            draw.text((10, y+5), "-30,000", fill=(0, 0, 255))
            
            # 旧境界（薄い線）
            # 旧開始線
            x = self.old_boundaries["start_x"]
            draw.line([(x, 0), (x, height)], fill=(200, 200, 200), width=1)
            draw.text((x+5, 50), "OLD", fill=(150, 150, 150))
            
            # 旧終了線
            x = self.old_boundaries["end_x"]
            draw.line([(x, 0), (x, height)], fill=(200, 200, 200), width=1)
            draw.text((x-30, 50), "OLD", fill=(150, 150, 150))
            
            # 新境界（太い線）
            # 新開始線（緑色）
            x = self.boundaries["start_x"]
            draw.line([(x, 0), (x, height)], fill=(0, 255, 0), width=3)
            draw.text((x+5, 10), "START", fill=(0, 255, 0))
            draw.text((x+5, height-30), f"X={x}", fill=(0, 255, 0))
            
            # 新終了線（オレンジ色）
            x = self.boundaries["end_x"]
            draw.line([(x, 0), (x, height)], fill=(255, 165, 0), width=3)
            draw.text((x-40, 10), "END", fill=(255, 165, 0))
            draw.text((x-50, height-30), f"X={x}", fill=(255, 165, 0))
            
            # グラフ領域の枠
            draw.rectangle(
                [(self.boundaries["start_x"], self.boundaries["top_y"]), 
                 (self.boundaries["end_x"], self.boundaries["bottom_y"])],
                outline=(255, 0, 0),
                width=2
            )
            
            # 情報表示
            info_x = width - 250
            info_y = 20
            
            # 新旧比較
            draw.text((info_x, info_y), "📊 境界調整", fill=(0, 0, 0))
            info_y += 20
            draw.text((info_x, info_y), f"開始: {self.old_boundaries['start_x']} → {self.boundaries['start_x']}px", fill=(0, 0, 0))
            info_y += 20
            draw.text((info_x, info_y), f"終了: {self.old_boundaries['end_x']} → {self.boundaries['end_x']}px", fill=(0, 0, 0))
            info_y += 30
            
            # 新しいサイズ
            new_width = self.boundaries["end_x"] - self.boundaries["start_x"]
            draw.text((info_x, info_y), f"幅: {new_width}px", fill=(0, 0, 0))
            
            # 出力パス生成
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"{base_name}_adjusted.png"
            
            # 保存
            img.save(output_path, "PNG")
            
            return True, output_path
            
        except Exception as e:
            print(f"エラー: {str(e)}")
            return False, None

def main():
    """メイン処理"""
    print("🎯 調整版グラフ境界設定ツール")
    print("📊 開始点と終了点を右側に調整します")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal_v2"
    output_folder = "graphs/adjusted_boundaries"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 画像ファイルを取得
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith('.png')]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    # AdjustedGraphBoundariesインスタンス作成
    boundaries = AdjustedGraphBoundaries()
    
    # サンプル画像から最適な境界を決定
    sample_images = [os.path.join(input_folder, f) for f in image_files[:5]]
    boundaries.determine_optimal_boundaries(sample_images)
    
    # 確定した境界値を表示
    print("\n✅ 調整後のグラフ境界:")
    print(f"  開始X: {boundaries.boundaries['start_x']}px")
    print(f"  終了X: {boundaries.boundaries['end_x']}px")
    print(f"  上端Y: {boundaries.boundaries['top_y']}px (+30,000)")
    print(f"  中央Y: {boundaries.boundaries['zero_y']}px (0)")
    print(f"  下端Y: {boundaries.boundaries['bottom_y']}px (-30,000)")
    
    graph_width = boundaries.boundaries['end_x'] - boundaries.boundaries['start_x']
    graph_height = boundaries.boundaries['bottom_y'] - boundaries.boundaries['top_y']
    print(f"\n  グラフサイズ: {graph_width} × {graph_height}px")
    
    # テスト画像を処理
    print(f"\n{'='*60}")
    test_files = image_files[:3]
    
    for i, file in enumerate(test_files, 1):
        print(f"[{i}/{len(test_files)}] 処理中: {file}")
        
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, 
                                   f"{os.path.splitext(file)[0]}_adjusted.png")
        
        success, _ = boundaries.create_comparison_overlay(input_path, output_path)
        
        if success:
            print(f"  ✅ 成功")
        else:
            print(f"  ❌ 失敗")

if __name__ == "__main__":
    main()