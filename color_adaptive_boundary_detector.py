#!/usr/bin/env python3
"""
色適応型グラフ境界検出ツール
- グラフの色（ピンク/紫/青）に応じて検出パラメータを調整
- より正確な終了点検出
"""

import os
import numpy as np
from PIL import Image, ImageDraw
import cv2
from typing import Tuple, Optional, Dict, List

class ColorAdaptiveBoundaryDetector:
    """色適応型グラフ境界検出システム"""
    
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
    
    def detect_graph_color_type(self, img_array: np.ndarray) -> str:
        """グラフの主要な色を判定"""
        height, width = img_array.shape[:2]
        zero_y = self.y_lines["zero"]
        
        # 0ライン周辺でサンプリング
        sample_region = img_array[zero_y-30:zero_y+30, 100:width-100]
        
        pink_count = 0
        purple_count = 0
        blue_count = 0
        
        for y in range(sample_region.shape[0]):
            for x in range(sample_region.shape[1]):
                r, g, b = sample_region[y, x]
                
                # より緩い条件で色を判定
                if r > 180 and g < 160 and b > 120 and r > b:
                    pink_count += 1
                elif r > 120 and b > 120 and g < 100 and abs(r - b) < 60:
                    purple_count += 1
                elif b > 160 and r < 140 and g < 160 and b > r and b > g:
                    blue_count += 1
        
        total_count = pink_count + purple_count + blue_count
        if total_count == 0:
            return "unknown"
        
        # 最も多い色を返す
        if pink_count >= purple_count and pink_count >= blue_count:
            self.log(f"グラフ色: ピンク系 ({pink_count}/{total_count} pixels)", "INFO")
            return "pink"
        elif purple_count >= blue_count:
            self.log(f"グラフ色: 紫系 ({purple_count}/{total_count} pixels)", "INFO")
            return "purple"
        else:
            self.log(f"グラフ色: 青系 ({blue_count}/{total_count} pixels)", "INFO")
            return "blue"
    
    def detect_graph_line_by_color(self, img_array: np.ndarray, x: int, y_start: int, y_end: int, color_type: str) -> bool:
        """色タイプに応じてグラフラインを検出"""
        for y in range(y_start, y_end):
            if 0 <= y < img_array.shape[0]:
                r, g, b = img_array[y, x]
                
                if color_type == "pink":
                    # ピンク系（検出しやすい）
                    if r > 180 and g < 170 and b > 120 and r > b:
                        return True
                elif color_type == "purple":
                    # 紫系（より緩い条件）
                    if r > 100 and b > 100 and g < 120 and abs(r - b) < 80:
                        return True
                elif color_type == "blue":
                    # 青系（より緩い条件）
                    if b > 140 and r < 160 and g < 170:
                        return True
                else:
                    # 不明な場合は全ての色を検出
                    if (r > 180 and g < 170 and b > 120) or \
                       (r > 100 and b > 100 and g < 120) or \
                       (b > 140 and r < 160 and g < 170):
                        return True
        return False
    
    def trace_graph_with_color_adaptation(self, img_array: np.ndarray, color_type: str) -> Tuple[int, int]:
        """色に適応したグラフトレース"""
        height, width = img_array.shape[:2]
        
        # スキャン範囲
        zero_y = self.y_lines["zero"]
        scan_height = 150
        y_start = max(0, zero_y - scan_height // 2)
        y_end = min(height, zero_y + scan_height // 2)
        
        # 開始点の検出
        graph_start = None
        for x in range(30, width // 3):
            if self.detect_graph_line_by_color(img_array, x, y_start, y_end, color_type):
                graph_start = x
                break
        
        if graph_start is None:
            graph_start = 50
        
        # 終了点の検出（色タイプに応じて調整）
        if color_type == "pink":
            required_empty = 10  # ピンクは標準
            scan_step = 1
        elif color_type == "purple":
            required_empty = 15  # 紫は少し緩く
            scan_step = 2  # スキップしながら
        else:  # blue or unknown
            required_empty = 20  # 青は最も緩く
            scan_step = 2
        
        graph_end = None
        consecutive_empty = 0
        last_found = graph_start
        
        # より広い範囲をスキャン
        for x in range(graph_start + 50, width - 20, scan_step):
            has_color = self.detect_graph_line_by_color(img_array, x, y_start, y_end, color_type)
            
            if has_color:
                consecutive_empty = 0
                last_found = x
                graph_end = x
            else:
                consecutive_empty += scan_step
                
            # 色タイプに応じた終了判定
            if consecutive_empty >= required_empty and graph_end is not None:
                # 紫や青の場合はもう少し先も確認
                if color_type in ["purple", "blue"]:
                    # 先読みして本当に終了か確認
                    look_ahead = 30
                    found_ahead = False
                    for x2 in range(x, min(x + look_ahead, width - 20)):
                        if self.detect_graph_line_by_color(img_array, x2, y_start, y_end, color_type):
                            found_ahead = True
                            break
                    
                    if not found_ahead:
                        break
                else:
                    break
        
        # 終了点が見つからない場合は最後に見つかった位置を使用
        if graph_end is None:
            graph_end = last_found + 20
        
        return graph_start, graph_end
    
    def create_color_adaptive_overlay(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str]]:
        """色適応型オーバーレイを作成"""
        try:
            self.log(f"処理開始: {os.path.basename(image_path)}")
            
            # 画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            width, height = img.size
            
            # グラフの色を判定
            color_type = self.detect_graph_color_type(img_array)
            
            # 色に適応したトレース
            graph_start, graph_end = self.trace_graph_with_color_adaptation(img_array, color_type)
            
            self.log(f"グラフ開始: X={graph_start}px", "SUCCESS")
            self.log(f"グラフ終了: X={graph_end}px", "SUCCESS")
            
            # グラフ幅を計算
            graph_width = graph_end - graph_start
            self.log(f"グラフ幅: {graph_width}px", "INFO")
            
            # オーバーレイ描画
            draw = ImageDraw.Draw(img)
            
            # 色タイプを表示
            color_display = {
                "pink": "ピンク",
                "purple": "紫",
                "blue": "青",
                "unknown": "不明"
            }
            draw.text((10, height-50), f"検出色: {color_display[color_type]}", fill=(0, 0, 0))
            
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
            
            # グラフ終了線（色タイプに応じて変更）
            end_color = (255, 165, 0) if color_type == "pink" else (255, 0, 255)  # ピンクはオレンジ、その他はマゼンタ
            draw.line([(graph_end, 0), (graph_end, height)], fill=end_color, width=2)
            draw.text((graph_end-40, 10), "END", fill=end_color)
            draw.text((graph_end-50, height-30), f"X={graph_end}", fill=end_color)
            
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
            draw.text((info_x, info_y), f"Color: {color_type}", fill=(0, 0, 0))
            
            # 出力パス生成
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"{base_name}_color_adaptive.png"
            
            # 保存
            img.save(output_path, "PNG")
            
            self.log(f"色適応型オーバーレイ画像を保存: {output_path}", "SUCCESS")
            
            return True, output_path
            
        except Exception as e:
            self.log(f"エラー: {str(e)}", "ERROR")
            return False, None

def main():
    """メイン処理"""
    print("🎯 色適応型グラフ境界検出ツール")
    print("📊 グラフの色に応じて最適な検出を実行します")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal_v2"
    output_folder = "graphs/color_adaptive_boundaries"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # すべての画像を処理
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith('.png')]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    detector = ColorAdaptiveBoundaryDetector(debug_mode=True)
    
    success_count = 0
    
    # 各画像を処理
    for i, file in enumerate(image_files, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(image_files)}] 処理中: {file}")
        
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, 
                                   f"{os.path.splitext(file)[0]}_adaptive.png")
        
        success, _ = detector.create_color_adaptive_overlay(input_path, output_path)
        
        if success:
            success_count += 1
    
    print(f"\n✨ 処理完了: {success_count}/{len(image_files)} 成功")

if __name__ == "__main__":
    main()