#!/usr/bin/env python3
"""
高精度グラフ基準線検出ツール
- ピクセル単位で正確な線検出
- ±30,000の線を確実に特定
- 複数の検証手法を組み合わせ
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
from typing import Tuple, Optional, Dict, List
import matplotlib.pyplot as plt

class PreciseLineDetector:
    """高精度グラフ基準線検出システム"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{level}] {message}")
    
    def analyze_line_profile(self, img_array: np.ndarray, y: int) -> Dict:
        """特定のY座標の線のプロファイルを分析"""
        height, width = img_array.shape[:2]
        if y < 0 or y >= height:
            return {"is_line": False}
        
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 線上のピクセル値
        line_values = gray[y, :]
        
        # 線の特徴を計算
        mean_val = np.mean(line_values)
        std_val = np.std(line_values)
        min_val = np.min(line_values)
        max_val = np.max(line_values)
        
        # エッジ強度（上下との差分）
        edge_strength = 0
        if 0 < y < height - 1:
            above_diff = np.mean(np.abs(gray[y-1, :].astype(float) - line_values.astype(float)))
            below_diff = np.mean(np.abs(gray[y+1, :].astype(float) - line_values.astype(float)))
            edge_strength = (above_diff + below_diff) / 2
        
        # 線かどうかの判定
        is_line = (
            std_val < 30 and  # 一様性（標準偏差が小さい）
            edge_strength > 5 and  # エッジ強度
            mean_val < 200  # ある程度暗い
        )
        
        return {
            "is_line": is_line,
            "mean": mean_val,
            "std": std_val,
            "edge_strength": edge_strength,
            "darkness": 255 - mean_val
        }
    
    def find_grid_lines_precise(self, img_array: np.ndarray) -> List[int]:
        """高精度でグリッド線を検出"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Cannyエッジ検出（パラメータ調整）
        edges = cv2.Canny(gray, 50, 150)
        
        # 水平方向の投影（エッジの合計）
        horizontal_projection = np.sum(edges, axis=1)
        
        # しきい値（画面幅の40%以上のエッジがある行）
        threshold = width * 0.4
        
        # 候補線を検出
        candidate_lines = []
        for y in range(height):
            if horizontal_projection[y] > threshold:
                # 線のプロファイルを詳細分析
                profile = self.analyze_line_profile(img_array, y)
                if profile["is_line"]:
                    candidate_lines.append((y, profile))
        
        # 近接した線をグループ化
        if not candidate_lines:
            return []
        
        grouped_lines = []
        current_group = [candidate_lines[0]]
        
        for i in range(1, len(candidate_lines)):
            if candidate_lines[i][0] - candidate_lines[i-1][0] <= 2:
                current_group.append(candidate_lines[i])
            else:
                # グループ内で最も強いエッジを持つ線を選択
                best_line = max(current_group, key=lambda x: x[1]["edge_strength"])
                grouped_lines.append(best_line[0])
                current_group = [candidate_lines[i]]
        
        # 最後のグループを処理
        best_line = max(current_group, key=lambda x: x[1]["edge_strength"])
        grouped_lines.append(best_line[0])
        
        return grouped_lines
    
    def detect_zero_line_precise(self, img_array: np.ndarray, grid_lines: List[int]) -> Optional[int]:
        """0ラインを高精度で検出"""
        height = img_array.shape[0]
        center_y = height // 2
        
        # 中央に最も近い線を候補とする
        candidates = []
        for line_y in grid_lines:
            distance_from_center = abs(line_y - center_y)
            if distance_from_center < height * 0.2:  # 中央から20%以内
                profile = self.analyze_line_profile(img_array, line_y)
                candidates.append({
                    "y": line_y,
                    "distance": distance_from_center,
                    "darkness": profile["darkness"],
                    "edge_strength": profile["edge_strength"]
                })
        
        if not candidates:
            return None
        
        # スコアリング（中央に近く、暗く、エッジが強い）
        for candidate in candidates:
            distance_score = 1 - (candidate["distance"] / (height * 0.2))
            darkness_score = candidate["darkness"] / 255
            edge_score = min(candidate["edge_strength"] / 20, 1)
            
            candidate["score"] = (
                distance_score * 0.5 +  # 中央重視
                darkness_score * 0.3 +
                edge_score * 0.2
            )
        
        # 最高スコアの線を選択
        best_candidate = max(candidates, key=lambda x: x["score"])
        return best_candidate["y"]
    
    def detect_boundary_lines_precise(self, img_array: np.ndarray, grid_lines: List[int], zero_line: int) -> Tuple[Optional[int], Optional[int]]:
        """±30,000ラインを高精度で検出"""
        height = img_array.shape[0]
        
        if not zero_line or len(grid_lines) < 3:
            return None, None
        
        # グリッド線の間隔を分析
        intervals = []
        for i in range(1, len(grid_lines)):
            intervals.append(grid_lines[i] - grid_lines[i-1])
        
        if intervals:
            # 最頻値の間隔を基準とする
            median_interval = np.median(intervals)
            self.log(f"グリッド線の標準間隔: {median_interval:.1f}px", "DEBUG")
        
        # 0ラインより上の線を探す（+30,000）
        top_candidates = [y for y in grid_lines if y < zero_line - 20]
        
        # 0ラインより下の線を探す（-30,000）
        bottom_candidates = [y for y in grid_lines if y > zero_line + 20]
        
        # 最も外側の線を選択（ただし画像端に近すぎない）
        top_line = None
        if top_candidates:
            # 上端から10%以上離れている線
            valid_top = [y for y in top_candidates if y > height * 0.05]
            if valid_top:
                top_line = min(valid_top)
        
        bottom_line = None
        if bottom_candidates:
            # 下端から10%以上離れている線
            valid_bottom = [y for y in bottom_candidates if y < height * 0.95]
            if valid_bottom:
                bottom_line = max(valid_bottom)
        
        # 対称性チェック
        if top_line and bottom_line and zero_line:
            top_distance = zero_line - top_line
            bottom_distance = bottom_line - zero_line
            symmetry_ratio = min(top_distance, bottom_distance) / max(top_distance, bottom_distance)
            
            self.log(f"上部距離: {top_distance}px, 下部距離: {bottom_distance}px", "DEBUG")
            self.log(f"対称性: {symmetry_ratio:.2f}", "DEBUG")
            
            # 対称性が低い場合は警告
            if symmetry_ratio < 0.8:
                self.log("警告: 上下の線の対称性が低い", "WARNING")
        
        return top_line, bottom_line
    
    def analyze_graph_lines_precise(self, image_path: str) -> Dict:
        """グラフの基準線を高精度で分析"""
        self.log(f"高精度分析開始: {os.path.basename(image_path)}")
        
        # 画像読み込み
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # グリッド線を高精度で検出
        grid_lines = self.find_grid_lines_precise(img_array)
        self.log(f"検出されたグリッド線: {len(grid_lines)}本", "INFO")
        
        if len(grid_lines) < 3:
            self.log("グリッド線が不足しています", "ERROR")
            return {
                "image_size": img.size,
                "grid_lines": grid_lines,
                "zero_line": None,
                "top_line": None,
                "bottom_line": None
            }
        
        # 0ラインを検出
        zero_line = self.detect_zero_line_precise(img_array, grid_lines)
        
        # ±30,000ラインを検出
        top_line, bottom_line = self.detect_boundary_lines_precise(img_array, grid_lines, zero_line)
        
        # 結果をログ出力
        if zero_line:
            self.log(f"0ライン: Y={zero_line}px", "SUCCESS")
        else:
            self.log("0ライン検出失敗", "ERROR")
        
        if top_line and bottom_line:
            self.log(f"+30,000ライン: Y={top_line}px", "SUCCESS")
            self.log(f"-30,000ライン: Y={bottom_line}px", "SUCCESS")
            
            # ピクセル/値の比率を計算
            pixel_range = bottom_line - top_line
            value_range = 60000  # -30,000 to +30,000
            pixels_per_value = pixel_range / value_range
            self.log(f"スケール: {pixels_per_value:.4f} px/unit", "INFO")
        else:
            self.log("境界線検出失敗", "ERROR")
        
        return {
            "image_size": img.size,
            "grid_lines": grid_lines,
            "zero_line": zero_line,
            "top_line": top_line,
            "bottom_line": bottom_line
        }
    
    def create_detailed_overlay(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str]]:
        """詳細なオーバーレイを作成"""
        try:
            # 分析実行
            results = self.analyze_graph_lines_precise(image_path)
            
            # 画像読み込み
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            
            width, height = img.size
            
            # すべてのグリッド線を薄く描画
            for y in results["grid_lines"]:
                draw.line([(0, y), (width, y)], fill=(200, 200, 200), width=1)
            
            # 0ラインを描画（赤色、太線）
            if results["zero_line"]:
                y = results["zero_line"]
                draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=3)
                draw.text((10, y-20), f"0 (Y={y})", fill=(255, 0, 0))
            
            # +30,000ラインを描画（青色、太線）
            if results["top_line"]:
                y = results["top_line"]
                draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=3)
                draw.text((10, y-20), f"+30,000 (Y={y})", fill=(0, 0, 255))
            
            # -30,000ラインを描画（青色、太線）
            if results["bottom_line"]:
                y = results["bottom_line"]
                draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=3)
                draw.text((10, y+5), f"-30,000 (Y={y})", fill=(0, 0, 255))
            
            # 検出情報を画像に追記
            info_y = 20
            if results["zero_line"] and results["top_line"] and results["bottom_line"]:
                pixel_range = results["bottom_line"] - results["top_line"]
                draw.text((width-200, info_y), f"Range: {pixel_range}px", fill=(0, 0, 0))
                info_y += 20
                
                # 対称性チェック
                top_dist = results["zero_line"] - results["top_line"]
                bottom_dist = results["bottom_line"] - results["zero_line"]
                draw.text((width-200, info_y), f"Top: {top_dist}px", fill=(0, 0, 0))
                info_y += 20
                draw.text((width-200, info_y), f"Bottom: {bottom_dist}px", fill=(0, 0, 0))
            
            # 出力パス生成
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"{base_name}_precise_overlay.png"
            
            # 保存
            img.save(output_path, "PNG")
            
            self.log(f"詳細オーバーレイ画像を保存: {output_path}", "SUCCESS")
            
            return True, output_path
            
        except Exception as e:
            self.log(f"エラー: {str(e)}", "ERROR")
            return False, None

def main():
    """メイン処理"""
    print("🎯 高精度グラフ基準線検出ツール")
    print("📊 ピクセル単位で正確な線検出を行います")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal_v2"
    output_folder = "graphs/precise_line_detection"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 画像ファイルを取得（最初の3枚でテスト）
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith('.png')][:3]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    detector = PreciseLineDetector(debug_mode=True)
    
    # 各画像を処理
    for i, file in enumerate(image_files, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(image_files)}] 処理中: {file}")
        
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, 
                                   f"{os.path.splitext(file)[0]}_precise_overlay.png")
        
        success, _ = detector.create_detailed_overlay(input_path, output_path)
        
        if success:
            print(f"✅ 成功")
        else:
            print(f"❌ 失敗")

if __name__ == "__main__":
    main()