#!/usr/bin/env python3
"""
最終版グラフ境界設定ツール
- 開始点: X=8px（検出済み）
- 終了点: 固定位置（右側の適切な位置）
- Y軸: 既存の検出結果を使用
"""

import os
import numpy as np
from PIL import Image, ImageDraw
import cv2
from typing import Tuple, Optional, Dict

class FinalGraphBoundaries:
    """最終版グラフ境界設定システム"""
    
    def __init__(self):
        # 確定した境界値
        self.boundaries = {
            "start_x": 8,      # 開始X座標（固定）
            "end_x": None,     # 終了X座標（画像から計算）
            "top_y": 29,       # +30,000ライン
            "zero_y": 274,     # 0ライン
            "bottom_y": 520    # -30,000ライン
        }
        
    def analyze_right_side(self, img_array: np.ndarray) -> int:
        """右側の適切な終了位置を分析"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 右側のテキスト領域を検出
        # X軸の数値（例: 80,000）の左端を探す
        right_region = gray[:, int(width * 0.7):]
        
        # エッジ検出
        edges = cv2.Canny(right_region, 50, 150)
        
        # 下部（X軸数値がある領域）でテキストを探す
        text_region = edges[int(height * 0.85):, :]
        vertical_sum = np.sum(text_region, axis=0)
        
        # テキストの開始位置を検出
        text_start = None
        for x in range(text_region.shape[1]):
            if vertical_sum[x] > text_region.shape[0] * 0.3:
                text_start = x
                break
        
        if text_start is not None:
            # テキストの左端から少し左をグラフ終了点とする
            end_x = int(width * 0.7) + text_start - 20
        else:
            # デフォルト: 画像幅の85%位置
            end_x = int(width * 0.85)
        
        return end_x
    
    def determine_fixed_end_position(self, sample_images: list) -> int:
        """複数の画像から適切な終了位置を決定"""
        end_positions = []
        
        for img_path in sample_images:
            img = Image.open(img_path)
            img_array = np.array(img)
            end_x = self.analyze_right_side(img_array)
            end_positions.append(end_x)
            print(f"  {os.path.basename(img_path)}: 終了候補 X={end_x}")
        
        # 中央値を採用（外れ値に強い）
        fixed_end = int(np.median(end_positions))
        print(f"\n固定終了位置: X={fixed_end} (中央値)")
        
        return fixed_end
    
    def create_final_overlay(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str]]:
        """最終的な境界線オーバーレイを作成"""
        try:
            # 画像読み込み
            img = Image.open(image_path)
            width, height = img.size
            
            # 終了位置が未設定の場合は計算
            if self.boundaries["end_x"] is None:
                img_array = np.array(img)
                self.boundaries["end_x"] = self.analyze_right_side(img_array)
            
            # オーバーレイ描画
            draw = ImageDraw.Draw(img)
            
            # 水平線（Y軸）
            # +30,000ライン（青色）
            y = self.boundaries["top_y"]
            draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=2)
            draw.text((10, y-20), "+30,000", fill=(0, 0, 255))
            
            # 0ライン（赤色）
            y = self.boundaries["zero_y"]
            draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=3)
            draw.text((10, y-20), "0", fill=(255, 0, 0))
            
            # -30,000ライン（青色）
            y = self.boundaries["bottom_y"]
            draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=2)
            draw.text((10, y+5), "-30,000", fill=(0, 0, 255))
            
            # 垂直線（X軸）
            # 開始線（緑色）
            x = self.boundaries["start_x"]
            draw.line([(x, 0), (x, height)], fill=(0, 255, 0), width=3)
            draw.text((x+5, 10), "START", fill=(0, 255, 0))
            
            # 終了線（オレンジ色）
            x = self.boundaries["end_x"]
            draw.line([(x, 0), (x, height)], fill=(255, 165, 0), width=3)
            draw.text((x-40, 10), "END", fill=(255, 165, 0))
            
            # グラフ領域の枠（太め）
            draw.rectangle(
                [(self.boundaries["start_x"], self.boundaries["top_y"]), 
                 (self.boundaries["end_x"], self.boundaries["bottom_y"])],
                outline=(255, 0, 0),
                width=2
            )
            
            # 座標情報を表示
            info_x = width - 250
            info_y = 20
            
            # グラフ領域のサイズ
            graph_width = self.boundaries["end_x"] - self.boundaries["start_x"]
            graph_height = self.boundaries["bottom_y"] - self.boundaries["top_y"]
            
            draw.text((info_x, info_y), "📊 グラフ領域", fill=(0, 0, 0))
            info_y += 20
            draw.text((info_x, info_y), f"X: {self.boundaries['start_x']} → {self.boundaries['end_x']} ({graph_width}px)", fill=(0, 0, 0))
            info_y += 20
            draw.text((info_x, info_y), f"Y: {self.boundaries['top_y']} → {self.boundaries['bottom_y']} ({graph_height}px)", fill=(0, 0, 0))
            info_y += 30
            
            # スケール情報
            draw.text((info_x, info_y), "📏 スケール", fill=(0, 0, 0))
            info_y += 20
            draw.text((info_x, info_y), f"Y: {graph_height/60000:.4f} px/unit", fill=(0, 0, 0))
            
            # 出力パス生成
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"{base_name}_final_boundaries.png"
            
            # 保存
            img.save(output_path, "PNG")
            
            return True, output_path
            
        except Exception as e:
            print(f"エラー: {str(e)}")
            return False, None

def main():
    """メイン処理"""
    print("🎯 最終版グラフ境界設定ツール")
    print("📊 統一された境界線でグラフ領域を定義します")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal_v2"
    output_folder = "graphs/final_boundaries"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 画像ファイルを取得
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith('.png')]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    # FinalGraphBoundariesインスタンス作成
    boundaries = FinalGraphBoundaries()
    
    # サンプル画像から終了位置を決定
    print("\n終了位置の分析:")
    sample_images = [os.path.join(input_folder, f) for f in image_files[:5]]
    fixed_end_x = boundaries.determine_fixed_end_position(sample_images)
    boundaries.boundaries["end_x"] = fixed_end_x
    
    # 確定した境界値を表示
    print("\n✅ 確定したグラフ境界:")
    print(f"  開始X: {boundaries.boundaries['start_x']}px")
    print(f"  終了X: {boundaries.boundaries['end_x']}px")
    print(f"  上端Y: {boundaries.boundaries['top_y']}px (+30,000)")
    print(f"  中央Y: {boundaries.boundaries['zero_y']}px (0)")
    print(f"  下端Y: {boundaries.boundaries['bottom_y']}px (-30,000)")
    
    graph_width = boundaries.boundaries['end_x'] - boundaries.boundaries['start_x']
    graph_height = boundaries.boundaries['bottom_y'] - boundaries.boundaries['top_y']
    print(f"\n  グラフサイズ: {graph_width} × {graph_height}px")
    
    # すべての画像を処理
    print(f"\n{'='*60}")
    success_count = 0
    
    for i, file in enumerate(image_files, 1):
        print(f"[{i}/{len(image_files)}] 処理中: {file}")
        
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, 
                                   f"{os.path.splitext(file)[0]}_final.png")
        
        success, _ = boundaries.create_final_overlay(input_path, output_path)
        
        if success:
            success_count += 1
            print(f"  ✅ 成功")
        else:
            print(f"  ❌ 失敗")
    
    print(f"\n✨ 処理完了: {success_count}/{len(image_files)} 成功")
    
    # 設定をJSONに保存
    import json
    config = {
        "boundaries": boundaries.boundaries,
        "graph_size": {
            "width": graph_width,
            "height": graph_height
        },
        "scale": {
            "x_pixels_per_unit": "TBD",  # X軸の単位は画像により異なる
            "y_pixels_per_unit": graph_height / 60000
        }
    }
    
    with open("graph_boundaries_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 設定を保存: graph_boundaries_config.json")

if __name__ == "__main__":
    main()