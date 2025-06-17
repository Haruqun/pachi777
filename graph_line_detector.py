#!/usr/bin/env python3
"""
グラフ基準線検出ツール
- 0ライン（中央の横線）を検出
- ±30,000ライン（上下の境界線）を検出
- 検出結果をオーバーレイ表示
"""

import os
import numpy as np
from PIL import Image, ImageDraw
import cv2
from typing import Tuple, Optional, Dict, List
import matplotlib.pyplot as plt
import matplotlib.patches as patches

class GraphLineDetector:
    """グラフ基準線検出システム"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{level}] {message}")
    
    def detect_horizontal_lines(self, img_array: np.ndarray) -> List[int]:
        """水平線を検出（改良版）"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 複数の手法を組み合わせて検出
        lines = []
        
        # 手法1: Sobelフィルタによるエッジ検出
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        sobel_y = np.abs(sobel_y)
        
        # 各行のエッジ強度を計算
        edge_strength = np.mean(sobel_y, axis=1)
        
        # 局所的なピークを検出
        for y in range(1, height-1):
            if edge_strength[y] > edge_strength[y-1] and edge_strength[y] > edge_strength[y+1]:
                if edge_strength[y] > np.mean(edge_strength) * 1.5:  # 平均より高いピーク
                    lines.append(y)
        
        # 手法2: 色の変化を検出
        for y in range(1, height-1):
            # 上下のピクセルとの差分
            diff_above = np.mean(np.abs(gray[y, :].astype(float) - gray[y-1, :].astype(float)))
            diff_below = np.mean(np.abs(gray[y, :].astype(float) - gray[y+1, :].astype(float)))
            
            # 両側との差が大きい場合は線
            if diff_above > 10 and diff_below > 10:
                if y not in lines:
                    lines.append(y)
        
        # 近接した線をマージ
        lines.sort()
        merged_lines = []
        
        if lines:
            current_group = [lines[0]]
            for i in range(1, len(lines)):
                if lines[i] - lines[i-1] <= 3:
                    current_group.append(lines[i])
                else:
                    merged_lines.append(int(np.mean(current_group)))
                    current_group = [lines[i]]
            merged_lines.append(int(np.mean(current_group)))
        
        return merged_lines
    
    def detect_zero_line(self, img_array: np.ndarray, h_lines: List[int]) -> Optional[int]:
        """0ラインを検出（最も濃い/目立つ線）"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 中央付近の線を優先的に評価
        center_y = height // 2
        
        best_line = None
        best_score = -1
        
        for line_y in h_lines:
            # スコア計算（中央からの距離と線の濃さ）
            distance_from_center = abs(line_y - center_y) / (height / 2)
            center_score = 1 - distance_from_center  # 中央に近いほど高スコア
            
            # 線の濃さを評価
            if 0 < line_y < height:
                line_darkness = 255 - np.mean(gray[line_y, :])
                darkness_score = line_darkness / 255
            else:
                darkness_score = 0
            
            # 総合スコア（中央重視）
            total_score = center_score * 0.7 + darkness_score * 0.3
            
            if total_score > best_score:
                best_score = total_score
                best_line = line_y
        
        return best_line
    
    def detect_boundary_lines(self, img_array: np.ndarray, h_lines: List[int]) -> Tuple[Optional[int], Optional[int]]:
        """±30,000ライン（上下の境界線）を検出"""
        if len(h_lines) < 3:
            return None, None
        
        height = img_array.shape[0]
        
        # 上下のマージンを考慮して境界線を選択
        valid_top_lines = [y for y in h_lines if y < height * 0.4]  # 上部40%以内
        valid_bottom_lines = [y for y in h_lines if y > height * 0.6]  # 下部40%以内
        
        top_line = min(valid_top_lines) if valid_top_lines else None
        bottom_line = max(valid_bottom_lines) if valid_bottom_lines else None
        
        return top_line, bottom_line
    
    def analyze_graph_lines(self, image_path: str) -> Dict:
        """グラフの基準線を分析"""
        self.log(f"分析開始: {os.path.basename(image_path)}")
        
        # 画像読み込み
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # 水平線を検出
        h_lines = self.detect_horizontal_lines(img_array)
        self.log(f"検出された水平線: {len(h_lines)}本", "DEBUG")
        
        # 0ラインを検出
        zero_line = self.detect_zero_line(img_array, h_lines)
        
        # ±30,000ラインを検出
        top_line, bottom_line = self.detect_boundary_lines(img_array, h_lines)
        
        # 結果をログ出力
        if zero_line:
            self.log(f"0ライン: Y={zero_line}", "SUCCESS")
        else:
            self.log("0ライン検出失敗", "WARNING")
        
        if top_line and bottom_line:
            self.log(f"+30,000ライン: Y={top_line}", "SUCCESS")
            self.log(f"-30,000ライン: Y={bottom_line}", "SUCCESS")
        else:
            self.log("境界線検出失敗", "WARNING")
        
        return {
            "image_size": img.size,
            "horizontal_lines": h_lines,
            "zero_line": zero_line,
            "top_line": top_line,
            "bottom_line": bottom_line
        }
    
    def create_overlay(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str]]:
        """検出した線をオーバーレイ表示"""
        try:
            # 分析実行
            results = self.analyze_graph_lines(image_path)
            
            # 画像読み込み
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            
            width, height = img.size
            
            # 0ラインを描画（赤色）
            if results["zero_line"]:
                y = results["zero_line"]
                draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=3)
                draw.text((10, y-20), "0", fill=(255, 0, 0))
            
            # +30,000ラインを描画（青色）
            if results["top_line"]:
                y = results["top_line"]
                draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=2)
                draw.text((10, y-20), "+30,000", fill=(0, 0, 255))
            
            # -30,000ラインを描画（青色）
            if results["bottom_line"]:
                y = results["bottom_line"]
                draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=2)
                draw.text((10, y+5), "-30,000", fill=(0, 0, 255))
            
            # その他の検出された線を薄く描画（デバッグ用）
            if self.debug_mode:
                for y in results["horizontal_lines"]:
                    if y not in [results["zero_line"], results["top_line"], results["bottom_line"]]:
                        draw.line([(0, y), (width, y)], fill=(128, 128, 128), width=1)
            
            # 出力パス生成
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"{base_name}_overlay.png"
            
            # 保存
            img.save(output_path, "PNG")
            
            self.log(f"オーバーレイ画像を保存: {output_path}", "SUCCESS")
            
            return True, output_path
            
        except Exception as e:
            self.log(f"エラー: {str(e)}", "ERROR")
            return False, None

def main():
    """メイン処理"""
    print("🎯 グラフ基準線検出ツール")
    print("📊 0ラインと±30,000ラインを検出してオーバーレイ表示します")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal_v2"
    output_folder = "graphs/line_detection"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 画像ファイルを取得
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith('.png')]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    detector = GraphLineDetector(debug_mode=False)
    
    success_count = 0
    
    # すべての画像を処理
    for i, file in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] 処理中: {file}")
        
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, 
                                   f"{os.path.splitext(file)[0]}_overlay.png")
        
        success, _ = detector.create_overlay(input_path, output_path)
        
        if success:
            success_count += 1
            print(f"✅ 成功")
        else:
            print(f"❌ 失敗")
    
    print(f"\n✨ 処理完了: {success_count}/{len(image_files)} 成功")

if __name__ == "__main__":
    main()