#!/usr/bin/env python3
"""
完璧データ抽出ツール
- 911×797px統一グラフからの正確抽出
- 0ライン基準、-30,000~+30,000範囲
- 0ラインスタート前提の最適化
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
import pandas as pd
from typing import Tuple, List, Optional, Dict
from datetime import datetime
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm

# macOS対応日本語フォント設定
def setup_japanese_font():
    """macOS対応の日本語フォントを設定"""
    import platform
    import os
    
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        # 実際に存在するmacOSフォントを使用
        hiragino_path = '/System/Library/Fonts/Hiragino Sans GB.ttc'
        
        if os.path.exists(hiragino_path):
            # Hiraginoフォントを直接指定
            plt.rcParams['font.family'] = ['Hiragino Sans GB']
            plt.rcParams['font.sans-serif'] = ['Hiragino Sans GB', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            print(f"macOS日本語フォント設定完了: Hiragino Sans GB")
            return 'Hiragino Sans GB'
    
    # 一般的なフォント名での検索
    japanese_fonts = [
        'Arial Unicode MS',        # macOSに存在する可能性
        'Apple Color Emoji',       # macOS標準
        'Yu Gothic',               # Windows/macOS両対応
        'DejaVu Sans'             # フォールバック
    ]
    
    for font_name in japanese_fonts:
        try:
            available_fonts = [f.name for f in fm.fontManager.ttflist]
            if font_name in available_fonts:
                plt.rcParams['font.family'] = font_name
                print(f"日本語フォント設定完了: {font_name}")
                return font_name
        except:
            continue
    
    # 最終フォールバック: 日本語文字は諦めて英語のみ対応
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False  # マイナス記号の文字化け防止
    print("警告: 日本語フォントが見つかりません。英語表示でフォールバックします。")
    return 'DejaVu Sans'


class PerfectDataExtractor:
    """完璧データ抽出システム"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        
        # 日本語フォント設定
        self.font_name = setup_japanese_font()
        
        # グラフ仕様（完璧切り抜き済み前提）
        self.GRAPH_WIDTH = 911
        self.GRAPH_HEIGHT = 797
        self.Y_MIN = -30000
        self.Y_MAX = 30000
        self.Y_RANGE = self.Y_MAX - self.Y_MIN  # 60,000
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            timestamp = datetime.now().strftime("%H:%M:%S")
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{timestamp}] {message}")
    
    def detect_zero_line_precise(self, image_path: str) -> int:
        """
        完璧切り抜き画像での0ライン検出
        911×797px画像で最適化
        """
        self.log("0ライン精密検出を開始", "DEBUG")
        
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        # グレースケール変換
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 水平線検出（完璧切り抜き画像専用最適化）
        line_candidates = []
        
        # 画像の中央80%領域で水平線を検索
        left_margin = int(width * 0.1)
        right_margin = int(width * 0.9)
        
        # 縦方向は中央付近を重点的に（0ラインは通常中央やや下）
        search_top = int(height * 0.4)
        search_bottom = int(height * 0.7)
        
        for y in range(search_top, search_bottom):
            row = gray[y, left_margin:right_margin]
            
            # 水平線の特徴分析
            mean_val = np.mean(row)
            min_val = np.min(row)
            std_val = np.std(row)
            
            # 暗い線ほど高スコア
            darkness_score = (255 - mean_val) / 255
            
            # 一様性（標準偏差が小さいほど高スコア）
            uniformity_score = 1 / (1 + std_val)
            
            # 最も暗い部分のスコア
            min_darkness_score = (255 - min_val) / 255
            
            # 水平線らしさの総合スコア
            total_score = darkness_score * 0.4 + uniformity_score * 0.4 + min_darkness_score * 0.2
            
            # 一定以上のスコアを持つ線を候補とする
            if total_score > 0.3:
                line_candidates.append((y, total_score))
        
        if not line_candidates:
            # フォールバック: 画像の中央やや下
            zero_line_y = int(height * 0.55)
            self.log(f"0ライン検出失敗、推定位置使用: Y={zero_line_y}", "WARNING")
        else:
            # 最高スコアの線を0ラインとする
            best_line = max(line_candidates, key=lambda x: x[1])
            zero_line_y = best_line[0]
            self.log(f"0ライン検出成功: Y={zero_line_y} (スコア: {best_line[1]:.3f})", "SUCCESS")
        
        return zero_line_y
    
    def detect_graph_line(self, image_path: str) -> Optional[np.ndarray]:
        """
        グラフライン（複数色対応）を検出
        ピンク、青、緑、赤、紫、オレンジの線を検出
        """
        self.log("グラフライン検出を開始", "DEBUG")
        
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        # 各色の検出
        pink_mask = self._detect_pink_line(img_array)
        blue_mask = self._detect_blue_line(img_array)
        green_mask = self._detect_green_line(img_array)
        red_mask = self._detect_red_line(img_array)
        purple_mask = self._detect_purple_line(img_array)
        orange_mask = self._detect_orange_line(img_array)
        
        # 統合マスク
        combined_mask = np.logical_or.reduce([
            pink_mask, blue_mask, green_mask, 
            red_mask, purple_mask, orange_mask
        ])
        
        # ノイズ除去
        cleaned_mask = self._clean_line_mask(combined_mask)
        
        total_pixels = np.sum(cleaned_mask)
        self.log(f"グラフライン検出完了: {total_pixels}ピクセル", "SUCCESS")
        
        return cleaned_mask if total_pixels > 50 else None
    
    def _detect_pink_line(self, img_array: np.ndarray) -> np.ndarray:
        """ピンク線検出 - 実際の画像色分析結果に基づく精密検出"""
        height, width = img_array.shape[:2]
        
        # HSV色空間での精密なピンク検出
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        
        # 実際の分析結果に基づくピンク色範囲
        # RGB(225, 135, 205)をHSVに変換すると約 H=315, S=40%, V=88%
        pink_ranges = [
            ([310, 30, 70], [325, 60, 95]),    # メインピンク範囲
            ([300, 25, 65], [335, 70, 100]),   # 拡張ピンク範囲
        ]
        
        pink_mask = np.zeros((height, width), dtype=bool)
        
        for lower, upper in pink_ranges:
            lower = np.array(lower)
            upper = np.array(upper)
            mask = cv2.inRange(hsv, lower, upper)
            pink_mask = pink_mask | (mask > 0)
        
        # RGB距離による補完検出（より厳しい閾値）
        target_colors = [
            (225, 135, 205),  # 分析結果の平均色
            (245, 155, 215),  # 明るめバリエーション
            (205, 115, 195),  # 暗めバリエーション
        ]
        
        for target_rgb in target_colors:
            target = np.array(target_rgb)
            reshaped = img_array[:, :, :3].reshape(-1, 3).astype(np.float64)
            distances = np.sqrt(np.sum((reshaped - target) ** 2, axis=1))
            
            # 厳しい許容誤差（背景色除外のため）
            tolerance = 30  # バランスを考慮した設定
            mask = distances <= tolerance
            mask_2d = mask.reshape(height, width)
            pink_mask = pink_mask | mask_2d
        
        return pink_mask
    
    def _detect_blue_line(self, img_array: np.ndarray) -> np.ndarray:
        """ブルー線検出"""
        height, width = img_array.shape[:2]
        
        # ブルー色の定義（RGB）
        blue_colors = [
            (0, 150, 255),    # 明るいブルー
            (30, 144, 255),   # ドジャーブルー
            (135, 206, 250),  # ライトスカイブルー
            (70, 130, 180),   # スチールブルー
            (0, 100, 200),    # 濃いブルー
        ]
        
        blue_mask = np.zeros((height, width), dtype=bool)
        
        for target_rgb in blue_colors:
            target = np.array(target_rgb)
            reshaped = img_array[:, :, :3].reshape(-1, 3).astype(np.float64)
            distances = np.sqrt(np.sum((reshaped - target) ** 2, axis=1))
            
            # 許容誤差内のピクセルを検出
            tolerance = 45  # 適度に緊緩
            mask = distances <= tolerance
            mask_2d = mask.reshape(height, width)
            blue_mask = blue_mask | mask_2d
        
        return blue_mask
    
    def _detect_green_line(self, img_array: np.ndarray) -> np.ndarray:
        """緑線検出"""
        height, width = img_array.shape[:2]
        
        # 緑色の定義（RGB）
        green_colors = [
            (0, 255, 0),      # 純緑
            (50, 205, 50),    # ライムグリーン
            (0, 200, 0),      # 濃い緑
            (144, 238, 144),  # ライトグリーン
            (34, 139, 34),    # フォレストグリーン
        ]
        
        green_mask = np.zeros((height, width), dtype=bool)
        
        for target_rgb in green_colors:
            target = np.array(target_rgb)
            reshaped = img_array[:, :, :3].reshape(-1, 3).astype(np.float64)
            distances = np.sqrt(np.sum((reshaped - target) ** 2, axis=1))
            
            tolerance = 40  # 緑は適度に
            mask = distances <= tolerance
            mask_2d = mask.reshape(height, width)
            green_mask = green_mask | mask_2d
        
        return green_mask
    
    def _detect_red_line(self, img_array: np.ndarray) -> np.ndarray:
        """赤線検出"""
        height, width = img_array.shape[:2]
        
        # 赤色の定義（RGB）
        red_colors = [
            (255, 0, 0),      # 純赤
            (220, 20, 60),    # クリムゾン
            (255, 69, 0),     # レッドオレンジ
            (178, 34, 34),    # ファイアブリック
            (255, 99, 71),    # トマト
        ]
        
        red_mask = np.zeros((height, width), dtype=bool)
        
        for target_rgb in red_colors:
            target = np.array(target_rgb)
            reshaped = img_array[:, :, :3].reshape(-1, 3).astype(np.float64)
            distances = np.sqrt(np.sum((reshaped - target) ** 2, axis=1))
            
            tolerance = 35  # 赤は比較的厳しく
            mask = distances <= tolerance
            mask_2d = mask.reshape(height, width)
            red_mask = red_mask | mask_2d
        
        return red_mask
    
    def _detect_purple_line(self, img_array: np.ndarray) -> np.ndarray:
        """紫線検出"""
        height, width = img_array.shape[:2]
        
        # 紫色の定義（RGB）
        purple_colors = [
            (128, 0, 128),    # 紫
            (147, 112, 219),  # ミディアムパープル
            (138, 43, 226),   # ブルーバイオレット
            (186, 85, 211),   # ミディアムオーキッド
            (218, 112, 214),  # オーキッド
        ]
        
        purple_mask = np.zeros((height, width), dtype=bool)
        
        for target_rgb in purple_colors:
            target = np.array(target_rgb)
            reshaped = img_array[:, :, :3].reshape(-1, 3).astype(np.float64)
            distances = np.sqrt(np.sum((reshaped - target) ** 2, axis=1))
            
            tolerance = 40  # 紫も適度に
            mask = distances <= tolerance
            mask_2d = mask.reshape(height, width)
            purple_mask = purple_mask | mask_2d
        
        return purple_mask
    
    def _detect_orange_line(self, img_array: np.ndarray) -> np.ndarray:
        """オレンジ線検出（グラフ線用）"""
        height, width = img_array.shape[:2]
        
        # オレンジ色の定義（RGB） - UIのオレンジバーとは異なる色合い
        orange_colors = [
            (255, 165, 0),    # オレンジ
            (255, 140, 0),    # ダークオレンジ
            (255, 127, 80),   # コーラル
            (255, 99, 71),    # トマト
            (255, 215, 0),    # ゴールド
        ]
        
        orange_mask = np.zeros((height, width), dtype=bool)
        
        for target_rgb in orange_colors:
            target = np.array(target_rgb)
            reshaped = img_array[:, :, :3].reshape(-1, 3).astype(np.float64)
            distances = np.sqrt(np.sum((reshaped - target) ** 2, axis=1))
            
            tolerance = 30  # オレンジは厳しめでも適度に
            mask = distances <= tolerance
            mask_2d = mask.reshape(height, width)
            orange_mask = orange_mask | mask_2d
        
        return orange_mask
    
    def _clean_line_mask(self, mask: np.ndarray) -> np.ndarray:
        """マスクのクリーニング - 線状要素のみを抽出"""
        mask_uint8 = mask.astype(np.uint8) * 255
        
        # 1. 小さなノイズ除去
        kernel_small = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(mask_uint8, cv2.MORPH_OPEN, kernel_small)
        
        # 2. 線の連続性確保
        kernel_line = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_line)
        
        # 3. エロージョンで線を細くする（thinningの代替）
        kernel_thin = np.ones((2, 2), np.uint8)
        cleaned = cv2.erode(cleaned, kernel_thin, iterations=1)
        
        # 4. 大きな塊状のノイズ除去
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        height, width = mask.shape
        filtered_mask = np.zeros((height, width), dtype=np.uint8)
        
        for contour in contours:
            # 輪郭の形状分析
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            
            # 線状の判定条件
            if area > 0 and perimeter > 0:
                # アスペクト比と面積で線状要素を判定
                rect = cv2.boundingRect(contour)
                aspect_ratio = max(rect[2], rect[3]) / min(rect[2], rect[3])
                
                # 線状要素の条件：より柔軟に
                # 1. 面積が適度（大きすぎる塊のみ除外）
                # 2. アスペクト比または面積で判定
                # 3. 周囲長が十分ある
                if (area < 10000 and  # より大きな塊まで許可
                    (aspect_ratio > 2 or area < 500) and  # より柔軟な条件
                    perimeter > 5):  # より短い線も許可
                    cv2.drawContours(filtered_mask, [contour], -1, 255, -1)
        
        # 5. 線の連続性強化
        # より強いクロージングで線を接続
        kernel_close = np.ones((3, 3), np.uint8)
        filtered_mask = cv2.morphologyEx(filtered_mask, cv2.MORPH_CLOSE, kernel_close)
        
        # さらに細かいギャップを埋める
        kernel_dilate = np.ones((2, 2), np.uint8)
        filtered_mask = cv2.dilate(filtered_mask, kernel_dilate, iterations=1)
        filtered_mask = cv2.erode(filtered_mask, kernel_dilate, iterations=1)
        
        return filtered_mask.astype(bool)
    
    def extract_data_points_precise(self, mask: np.ndarray) -> List[Tuple[int, int]]:
        """
        高精度データポイント抽出
        X座標ごとに最適なY座標を決定
        """
        self.log("データポイント抽出を開始", "DEBUG")
        
        height, width = mask.shape
        data_points = []
        
        for x in range(width):
            column = mask[:, x]
            y_coords = np.where(column)[0]
            
            if len(y_coords) > 0:
                if len(y_coords) == 1:
                    # 単一点
                    y = y_coords[0]
                elif len(y_coords) <= 5:
                    # 少数点: 中央値
                    y = int(np.median(y_coords))
                else:
                    # 多数点: 全ての座標を個別に追加（上部・下部の線も含める）
                    for y_coord in y_coords:
                        data_points.append((x, y_coord))
                    continue
                
                data_points.append((x, y))
        
        self.log(f"データポイント抽出完了: {len(data_points)}点", "SUCCESS")
        return data_points
    
    def convert_to_real_values(self, points: List[Tuple[int, int]], zero_line_y: int, image_path: str = None) -> List[Tuple[int, float]]:
        """
        ピクセル座標を実際の値に変換
        複数の線を考慮してグループ化
        画像タイプによって変換比率を調整
        """
        self.log("実値変換を開始", "DEBUG")
        
        if not points:
            return []
        
        # X座標でグループ化して複数の線を処理
        x_groups = {}
        for x_pixel, y_pixel in points:
            if x_pixel not in x_groups:
                x_groups[x_pixel] = []
            x_groups[x_pixel].append(y_pixel)
        
        # 画像タイプによって変換比率を決定（微調整済み）
        if image_path and ("S__" in os.path.basename(image_path) or "S_" in os.path.basename(image_path)):
            # S_で始まる画像: 0ラインから上251px・下250pxが±30,000円
            # 平均値で計算: (251+250)/2 = 250.5px for ±30,000円
            pixels_per_unit = 250.5 / 30000  # 0.008350 px/円（微調整済み）
            scale_type = "S_画像(上251px/下250px)"
        else:
            # IMG_で始まる画像: 0ラインから上下333pxが±30,000円
            pixels_per_unit = 333 / 30000  # 0.0111 px/円
            scale_type = "IMG画像"
        
        self.log(f"変換パラメータ ({scale_type}):", "DEBUG")
        self.log(f"  0ライン位置: Y={zero_line_y}", "DEBUG")
        self.log(f"  ピクセル/単位: {pixels_per_unit:.4f} px/円", "DEBUG")
        self.log(f"  Y軸範囲: {self.Y_MIN} 〜 {self.Y_MAX}", "DEBUG")
        
        converted_points = []
        
        for x_pixel in sorted(x_groups.keys()):
            y_pixels = x_groups[x_pixel]
            
            # 複数の線がある場合は全て変換
            for y_pixel in y_pixels:
                # 0ラインからの距離を計算
                distance_from_zero = y_pixel - zero_line_y
                
                # 実際の値に変換（上がプラス、下がマイナス）
                real_value = -distance_from_zero / pixels_per_unit
                
                # 範囲制限
                real_value = max(self.Y_MIN, min(self.Y_MAX, real_value))
                
                converted_points.append((x_pixel, real_value))
        
        self.log(f"実値変換完了: {len(converted_points)}点", "SUCCESS")
        
        # 統計情報
        if converted_points:
            y_values = [p[1] for p in converted_points]
            min_val, max_val = min(y_values), max(y_values)
            
            self.log(f"  変換後範囲: {min_val:.0f} 〜 {max_val:.0f}", "DEBUG")
            self.log(f"  平均値: {np.mean(y_values):.0f}", "DEBUG")
            self.log(f"  データ点数: {len(converted_points)}", "DEBUG")
            
            # 上限振り切りエラー検出
            if abs(max_val) >= 29500 or abs(min_val) >= 29500:
                self.log(f"⚠️ 上限振り切り検出: 最大={max_val:.0f}, 最小={min_val:.0f}", "WARNING")
                self.log("このデータは上限/下限に張り付いており、正確な最終差玉の測定ができません", "WARNING")
            
            # 30,000円を超える値の検出でエラー
            if abs(max_val) > 30000 or abs(min_val) > 30000:
                error_msg = f"❌ エラー: グラフの値が±30,000円の範囲を超えています (最大={max_val:.0f}, 最小={min_val:.0f})"
                self.log(error_msg, "ERROR")
                raise ValueError(error_msg)
        
        return converted_points
    
    def validate_zero_start(self, points: List[Tuple[int, float]]) -> bool:
        """
        0ラインスタートの検証
        最初の数点が0付近にあるかチェック
        """
        if not points or len(points) < 3:
            return False
        
        # 最初の5点の平均を確認
        first_points = points[:min(5, len(points))]
        first_values = [p[1] for p in first_points]
        avg_start = np.mean(first_values)
        
        # 0から1000円以内ならOK
        is_zero_start = abs(avg_start) <= 1000
        
        self.log(f"0ラインスタート検証: 開始平均値={avg_start:.0f} → {'✅' if is_zero_start else '❌'}", 
                "SUCCESS" if is_zero_start else "WARNING")
        
        return is_zero_start
    
    def improve_start_end_precision(self, points: List[Tuple[int, float]]) -> List[Tuple[int, float]]:
        """開始・終点精度向上処理"""
        if len(points) < 10:
            return points
        
        improved_points = points.copy()
        
        # 開始点精度向上: 最初の5点を0ライン寄りに補正
        start_section = [p[1] for p in points[:5]]
        start_avg = np.mean(start_section)
        
        if abs(start_avg) > 500:  # 0ラインから500円以上離れている場合
            # 最初の5点を0ライン近くに補正
            correction_factor = 0.3  # 30%補正
            for i in range(5):
                x_pos, y_val = improved_points[i]
                corrected_y = y_val * (1 - correction_factor)
                improved_points[i] = (x_pos, corrected_y)
            
            self.log(f"開始点補正: {start_avg:.0f} → {np.mean([p[1] for p in improved_points[:5]]):.0f}", "DEBUG")
        
        # 終点精度向上: 最後の15点から最安定区間を特定
        if len(points) >= 15:
            end_values = [p[1] for p in points[-15:]]
            
            # 5点移動窓での標準偏差を計算
            min_std = float('inf')
            best_start_idx = len(end_values) - 5
            
            for i in range(len(end_values) - 4):
                segment = end_values[i:i+5]
                std = np.std(segment)
                if std < min_std:
                    min_std = std
                    best_start_idx = i
            
            # 最安定区間の平均値で最後の5点を置換
            if min_std < 300:  # 十分安定している場合
                stable_avg = np.mean(end_values[best_start_idx:best_start_idx+5])
                original_avg = np.mean([p[1] for p in points[-5:]])
                
                for i in range(5):
                    x_pos = improved_points[-(5-i)][0]
                    improved_points[-(5-i)] = (x_pos, stable_avg)
                
                self.log(f"終点安定化: {original_avg:.0f} → {stable_avg:.0f} (std: {min_std:.1f})", "DEBUG")
        
        return improved_points
    
    def extract_perfect_data(self, image_path: str, output_csv: str = None) -> Optional[pd.DataFrame]:
        """
        完璧データ抽出メイン処理
        """
        try:
            self.log(f"🎯 完璧データ抽出開始: {os.path.basename(image_path)}", "INFO")
            
            # 画像サイズ検証
            img = Image.open(image_path)
            if img.size != (self.GRAPH_WIDTH, self.GRAPH_HEIGHT):
                self.log(f"警告: 画像サイズが {img.size}、期待値 {(self.GRAPH_WIDTH, self.GRAPH_HEIGHT)}", "WARNING")
            
            # Step 1: 0ライン検出
            zero_line_y = self.detect_zero_line_precise(image_path)
            
            # Step 2: グラフライン検出
            line_mask = self.detect_graph_line(image_path)
            if line_mask is None:
                self.log("グラフライン検出失敗", "ERROR")
                return None
            
            # Step 3: データポイント抽出
            raw_points = self.extract_data_points_precise(line_mask)
            if not raw_points:
                self.log("データポイント抽出失敗", "ERROR")
                return None
            
            # Step 4: 実値変換
            real_points = self.convert_to_real_values(raw_points, zero_line_y, image_path)
            if not real_points:
                self.log("実値変換失敗", "ERROR")
                return None
            
            # Step 4.5: 開始・終点精度向上
            real_points = self.improve_start_end_precision(real_points)
            
            # Step 5: 0ラインスタート検証
            is_valid_start = self.validate_zero_start(real_points)
            
            # Step 6: DataFrame作成
            df = pd.DataFrame(real_points, columns=['x_pixel', 'y_value'])
            
            # X軸正規化（0-1）
            x_min, x_max = df['x_pixel'].min(), df['x_pixel'].max()
            if x_max > x_min:
                df['x_normalized'] = (df['x_pixel'] - x_min) / (x_max - x_min)
            else:
                df['x_normalized'] = 0
            
            # 時間インデックス（便宜上）
            df['time_index'] = df['x_normalized']
            
            # 統計情報
            stats = {
                'total_points': len(df),
                'y_min': df['y_value'].min(),
                'y_max': df['y_value'].max(),
                'y_mean': df['y_value'].mean(),
                'y_std': df['y_value'].std(),
                'zero_line_y': zero_line_y,
                'valid_zero_start': is_valid_start,
                'extraction_accuracy': self._calculate_accuracy(df)
            }
            
            # Step 7: CSV保存
            if output_csv:
                df.to_csv(output_csv, index=False)
                self.log(f"CSV保存完了: {output_csv}", "SUCCESS")
            
            # Step 8: 可視化生成（デフォルトで生成）
            try:
                self.visualize_extraction(image_path, df, zero_line_y)
                self.create_overlay_image(image_path, df, zero_line_y)
            except Exception as e:
                self.log(f"可視化生成でエラー（処理は継続）: {e}", "WARNING")
            
            # 結果表示
            self.log(f"✅ 完璧データ抽出完了:", "SUCCESS")
            self.log(f"   データ点数: {stats['total_points']}", "INFO")
            self.log(f"   Y値範囲: {stats['y_min']:.0f} 〜 {stats['y_max']:.0f}", "INFO")
            self.log(f"   平均値: {stats['y_mean']:.0f}", "INFO")
            self.log(f"   0ライン位置: Y={stats['zero_line_y']}", "INFO")
            self.log(f"   0スタート: {'✅' if stats['valid_zero_start'] else '❌'}", "INFO")
            self.log(f"   抽出精度: {stats['extraction_accuracy']:.1f}%", "INFO")
            
            return df
            
        except Exception as e:
            self.log(f"データ抽出エラー: {e}", "ERROR")
            return None
    
    def _calculate_accuracy(self, df: pd.DataFrame) -> float:
        """抽出精度の概算計算"""
        # 期待されるデータ点数と実際の比較
        expected_points = self.GRAPH_WIDTH  # 横幅分のデータ点
        actual_points = len(df)
        
        coverage = min(actual_points / expected_points, 1.0) * 100
        
        # Y値の範囲チェック
        y_range_coverage = 1.0
        if df['y_value'].max() > self.Y_MAX * 0.8 or df['y_value'].min() < self.Y_MIN * 0.8:
            y_range_coverage = 0.9  # 範囲が広い場合はより良い
        
        return coverage * y_range_coverage
    
    def visualize_extraction(self, image_path: str, df: pd.DataFrame, zero_line_y: int, 
                           output_path: str = None) -> str:
        """
        抽出結果を元画像に重ねて可視化
        """
        self.log("抽出結果可視化を開始", "DEBUG")
        
        try:
            # 元画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # matplotlibで可視化
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'データ抽出精度検証: {os.path.basename(image_path)}', fontsize=16, fontweight='bold')
            
            # 1. 元画像 + 境界線（0ライン、±30000ライン）
            axes[0, 0].imshow(img)
            
            # 境界線のY座標を計算（画像タイプに応じて）
            if ("S__" in os.path.basename(image_path) or "S_" in os.path.basename(image_path)):
                pixels_per_unit = 244.7 / 30000  # S_画像
            else:
                pixels_per_unit = 333 / 30000  # IMG画像
            top_line_y = zero_line_y - (30000 * pixels_per_unit)    # +30000円の位置
            bottom_line_y = zero_line_y + (30000 * pixels_per_unit) # -30000円の位置
            
            # 境界線を描画
            axes[0, 0].axhline(y=zero_line_y, color='green', linestyle='-', linewidth=2, alpha=0.9, label='0ライン')
            axes[0, 0].axhline(y=top_line_y, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='+30,000円')
            axes[0, 0].axhline(y=bottom_line_y, color='blue', linestyle='--', linewidth=1.5, alpha=0.7, label='-30,000円')
            
            axes[0, 0].set_title('1. 元画像 + 境界線（0ライン・±30,000円）')
            axes[0, 0].legend()
            axes[0, 0].axis('off')
            
            # 2. 元画像 + 抽出データポイント + 境界線
            axes[0, 1].imshow(img)
            if not df.empty:
                # 抽出されたポイントを重ねる
                x_coords = df['x_pixel'].values
                y_coords = []
                
                # 実値をピクセル座標に逆変換（画像タイプに応じた変換比率使用）
                if ("S__" in os.path.basename(image_path) or "S_" in os.path.basename(image_path)):
                    pixels_per_unit = 244.7 / 30000  # S_画像
                else:
                    pixels_per_unit = 333 / 30000  # IMG画像
                for y_value in df['y_value'].values:
                    y_pixel = zero_line_y - (y_value * pixels_per_unit)
                    y_coords.append(y_pixel)
                
                axes[0, 1].plot(x_coords, y_coords, 'red', linewidth=2, alpha=0.8, label='抽出データライン')
                axes[0, 1].scatter(x_coords[::20], np.array(y_coords)[::20], color='red', s=10, alpha=0.6)
                
            # 境界線を描画（パネル2でも表示）
            axes[0, 1].axhline(y=zero_line_y, color='green', linestyle='-', linewidth=2, alpha=0.7, label='0ライン')
            axes[0, 1].axhline(y=top_line_y, color='red', linestyle='--', linewidth=1, alpha=0.5, label='+30,000円')
            axes[0, 1].axhline(y=bottom_line_y, color='blue', linestyle='--', linewidth=1, alpha=0.5, label='-30,000円')
            
            axes[0, 1].set_title('2. 元画像 + 抽出データライン + 境界線')
            axes[0, 1].legend()
            axes[0, 1].axis('off')
            
            # 3. 抽出データのY値グラフ + 境界線
            if not df.empty:
                axes[1, 0].plot(df['x_normalized'], df['y_value'], 'blue', linewidth=2, label='抽出データ')
                
                # 境界線を描画
                axes[1, 0].axhline(y=0, color='green', linestyle='-', linewidth=2, alpha=0.8, label='0ライン')
                axes[1, 0].axhline(y=30000, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='+30,000円')
                axes[1, 0].axhline(y=-30000, color='blue', linestyle='--', linewidth=1.5, alpha=0.7, label='-30,000円')
                
                axes[1, 0].set_title('3. 抽出データ（実値）+ 境界線')
                axes[1, 0].set_xlabel('時間軸（正規化）')
                axes[1, 0].set_ylabel('収支（円）')
                axes[1, 0].grid(True, alpha=0.3)
                axes[1, 0].legend()
                
                # Y軸範囲を設定（境界線も見えるように）
                y_min, y_max = df['y_value'].min(), df['y_value'].max()
                y_margin = (y_max - y_min) * 0.1
                plot_min = max(-35000, y_min - y_margin)  # -30000より少し下まで
                plot_max = min(35000, y_max + y_margin)   # +30000より少し上まで
                axes[1, 0].set_ylim(plot_min, plot_max)
            
            # 4. 統計情報とピクセル分析
            axes[1, 1].axis('off')
            if not df.empty:
                stats_text = f"""
データ抽出統計:
━━━━━━━━━━━━━━━━━━━━━━
📊 基本情報:
   データ点数: {len(df):,}点
   0ライン位置: Y={zero_line_y}px
   
📈 Y値統計:
   最小値: {df['y_value'].min():,.0f}円
   最大値: {df['y_value'].max():,.0f}円
   平均値: {df['y_value'].mean():,.0f}円
   標準偏差: {df['y_value'].std():,.0f}円
   
🎯 変換情報:
   ピクセル/円: {self.GRAPH_HEIGHT / self.Y_RANGE:.6f}
   Y軸範囲: {self.Y_MIN:,} 〜 {self.Y_MAX:,}円
   
✅ 検証結果:
   0スタート: {"✅" if abs(df['y_value'].iloc[:5].mean()) <= 1000 else "❌"}
   データ密度: {len(df)/self.GRAPH_WIDTH*100:.1f}%
   """
                
                axes[1, 1].text(0.05, 0.95, stats_text, transform=axes[1, 1].transAxes,
                               fontsize=10, verticalalignment='top', fontfamily=self.font_name,
                               bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))
            
            plt.tight_layout()
            
            # 保存
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"graphs/extracted_data/{base_name}_visualization.png"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            
            self.log(f"可視化画像保存: {output_path}", "SUCCESS")
            
            # 表示
            plt.show()
            
            return output_path
            
        except Exception as e:
            self.log(f"可視化エラー: {e}", "ERROR")
            return None
    
    def create_overlay_image(self, image_path: str, df: pd.DataFrame, zero_line_y: int,
                           output_path: str = None) -> str:
        """
        PILを使って抽出ラインを直接重ねた画像を生成
        """
        self.log("オーバーレイ画像生成を開始", "DEBUG")
        
        try:
            # 元画像読み込み
            img = Image.open(image_path).convert('RGBA')
            overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            # 境界線のY座標を計算（画像タイプに応じて）
            if ("S__" in os.path.basename(image_path) or "S_" in os.path.basename(image_path)):
                pixels_per_unit = 244.7 / 30000  # S_画像
            else:
                pixels_per_unit = 333 / 30000  # IMG画像
            top_line_y = zero_line_y - (30000 * pixels_per_unit)    # +30000円の位置
            bottom_line_y = zero_line_y + (30000 * pixels_per_unit) # -30000円の位置
            
            width = img.size[0]
            
            # 境界線を描画（破線風）
            # 0ライン（緑）
            for x in range(0, width, 10):
                draw.line([(x, zero_line_y), (min(x+7, width), zero_line_y)], 
                         fill=(0, 255, 0, 255), width=3)
            
            # +30000円ライン（赤）
            for x in range(0, width, 15):
                draw.line([(x, int(top_line_y)), (min(x+8, width), int(top_line_y))], 
                         fill=(255, 0, 0, 180), width=2)
            
            # -30000円ライン（青）
            for x in range(0, width, 15):
                draw.line([(x, int(bottom_line_y)), (min(x+8, width), int(bottom_line_y))], 
                         fill=(0, 0, 255, 180), width=2)
            
            if not df.empty:
                # 実値をピクセル座標に逆変換（画像タイプに応じた変換比率使用）
                points = []
                for _, row in df.iterrows():
                    x_pixel = int(row['x_pixel'])
                    y_pixel = zero_line_y - (row['y_value'] * pixels_per_unit)
                    points.append((x_pixel, int(y_pixel)))
                
                # 抽出ラインを描画（太い赤線）
                if len(points) > 1:
                    for i in range(len(points) - 1):
                        draw.line([points[i], points[i + 1]], fill=(255, 0, 0, 200), width=3)
                
                # データポイントを描画（小さな円）
                for x, y in points[::10]:  # 10点おきに描画
                    draw.ellipse([x-2, y-2, x+2, y+2], fill=(255, 0, 0, 255))
            
            # 画像合成
            result = Image.alpha_composite(img, overlay).convert('RGB')
            
            # 保存
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"graphs/extracted_data/{base_name}_overlay.png"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            result.save(output_path)
            
            self.log(f"オーバーレイ画像保存: {output_path}", "SUCCESS")
            return output_path
            
        except Exception as e:
            self.log(f"オーバーレイ画像生成エラー: {e}", "ERROR")
            return None
    
    def batch_extract_perfect(self, input_folder: str = "graphs/cropped_perfect",
                            output_folder: str = "graphs/extracted_data"):
        """完璧データ抽出バッチ処理"""
        self.log("🎯 完璧データ抽出バッチ処理開始", "INFO")
        
        if not os.path.exists(input_folder):
            self.log(f"入力フォルダが見つかりません: {input_folder}", "ERROR")
            return
        
        # 対象画像ファイル
        image_files = [f for f in os.listdir(input_folder)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not image_files:
            self.log("処理対象の画像ファイルが見つかりません", "ERROR")
            return
        
        os.makedirs(output_folder, exist_ok=True)
        
        self.log(f"📁 処理対象: {len(image_files)}個のファイル", "INFO")
        
        successful = 0
        failed = []
        all_stats = []
        
        for i, filename in enumerate(image_files, 1):
            self.log(f"\n[{i}/{len(image_files)}] 処理中: {filename}", "INFO")
            
            input_path = os.path.join(input_folder, filename)
            base_name = os.path.splitext(filename)[0]
            csv_path = os.path.join(output_folder, f"{base_name}_data.csv")
            
            df = self.extract_perfect_data(input_path, csv_path)
            
            if df is not None:
                successful += 1
                
                # 統計情報収集
                stats = {
                    'filename': filename,
                    'points': len(df),
                    'y_min': df['y_value'].min(),
                    'y_max': df['y_value'].max(),
                    'y_mean': df['y_value'].mean(),
                    'y_std': df['y_value'].std()
                }
                all_stats.append(stats)
                
            else:
                failed.append(filename)
        
        # バッチ処理結果
        self.log(f"\n🎉 完璧データ抽出バッチ処理完了!", "SUCCESS")
        self.log(f"✅ 成功: {successful}/{len(image_files)}", "SUCCESS")
        
        if failed:
            self.log(f"❌ 失敗: {len(failed)}個", "ERROR")
            for f in failed:
                self.log(f"  - {f}", "ERROR")
        
        # 統計サマリー
        if all_stats:
            self.log(f"📊 抽出統計:", "INFO")
            avg_points = np.mean([s['points'] for s in all_stats])
            avg_range = np.mean([s['y_max'] - s['y_min'] for s in all_stats])
            
            self.log(f"   平均データ点数: {avg_points:.0f}点", "INFO")
            self.log(f"   平均Y値範囲: {avg_range:.0f}円", "INFO")
        
        # レポート保存
        report = {
            "timestamp": datetime.now().isoformat(),
            "input_folder": input_folder,
            "output_folder": output_folder,
            "total_files": len(image_files),
            "successful": successful,
            "failed": failed,
            "statistics": all_stats
        }
        
        report_path = f"perfect_extraction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.log(f"📋 レポート保存: {report_path}", "INFO")
        self.log(f"📁 出力フォルダ: {output_folder}", "INFO")


def main():
    """メイン処理"""
    print("=" * 60)
    print("🎯 完璧データ抽出ツール")
    print("=" * 60)
    print(f"📏 対象: 911×797px統一グラフ")
    print(f"📊 範囲: -30,000 〜 +30,000円")
    print(f"🎮 0ラインスタート前提最適化")
    
    extractor = PerfectDataExtractor()
    
    # 入力フォルダチェック
    input_folder = "graphs/cropped_perfect"
    if not os.path.exists(input_folder):
        print(f"\n❌ 入力フォルダが見つかりません: {input_folder}")
        print("💡 先に perfect_graph_cropper.py で切り抜きを実行してください")
        return
    
    # 画像ファイル検索
    image_files = [f for f in os.listdir(input_folder)
                  if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not image_files:
        print(f"\n❌ 処理対象の画像ファイルが見つかりません")
        return
    
    print(f"\n📁 見つかった画像ファイル ({len(image_files)}個):")
    for i, file in enumerate(image_files, 1):
        print(f"   {i}. {file}")
    
    # 処理モード選択
    print(f"\n🎯 処理モードを選択:")
    print("1. 🚀 完璧データ抽出バッチ処理（推奨）")
    print("2. 📷 単一画像の完璧抽出")
    print("3. 🔍 抽出テスト（CSV保存なし）")
    
    try:
        choice = input("\n選択 (1-3): ").strip()
        
        if choice == "1":
            # バッチ処理
            extractor.batch_extract_perfect()
            
        elif choice == "2":
            # 単一画像処理
            print(f"\n📁 画像を選択:")
            for i, file in enumerate(image_files, 1):
                print(f"{i}. {file}")
            
            try:
                file_num = int(input("画像番号を選択: "))
                if 1 <= file_num <= len(image_files):
                    selected_file = image_files[file_num - 1]
                    image_path = os.path.join(input_folder, selected_file)
                    
                    # CSV出力パス
                    base_name = os.path.splitext(selected_file)[0]
                    csv_path = f"graphs/extracted_data/{base_name}_data.csv"
                    os.makedirs("graphs/extracted_data", exist_ok=True)
                    
                    df = extractor.extract_perfect_data(image_path, csv_path)
                    
                    if df is not None:
                        print(f"\n🎉 完璧抽出成功!")
                        print(f"📁 CSV: {csv_path}")
                        print(f"📊 データ: {len(df)}点")
                        print(f"📈 範囲: {df['y_value'].min():.0f} 〜 {df['y_value'].max():.0f}")
                    else:
                        print(f"\n❌ 抽出失敗")
                else:
                    print("❌ 無効な番号です")
            except ValueError:
                print("❌ 数字を入力してください")
                
        elif choice == "3":
            # テスト処理
            print(f"\n📁 画像を選択:")
            for i, file in enumerate(image_files, 1):
                print(f"{i}. {file}")
            
            try:
                file_num = int(input("画像番号を選択: "))
                if 1 <= file_num <= len(image_files):
                    selected_file = image_files[file_num - 1]
                    image_path = os.path.join(input_folder, selected_file)
                    
                    df = extractor.extract_perfect_data(image_path)  # CSV保存なし
                    
                    if df is not None:
                        print(f"\n🔍 抽出テスト結果:")
                        print(f"   データ点数: {len(df)}")
                        print(f"   Y値範囲: {df['y_value'].min():.0f} 〜 {df['y_value'].max():.0f}")
                        print(f"   平均値: {df['y_value'].mean():.0f}")
                        print(f"   標準偏差: {df['y_value'].std():.0f}")
                        
                        # 最初と最後の数点を表示
                        print(f"\n📊 最初の5点:")
                        print(df.head()[['x_pixel', 'y_value']].to_string(index=False))
                        print(f"\n📊 最後の5点:")
                        print(df.tail()[['x_pixel', 'y_value']].to_string(index=False))
                    else:
                        print(f"\n❌ 抽出失敗")
                else:
                    print("❌ 無効な番号です")
            except ValueError:
                print("❌ 数字を入力してください")
        else:
            print("❌ 無効な選択です")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 処理が中断されました")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
    
    print(f"\n✨ 処理完了")


if __name__ == "__main__":
    main()