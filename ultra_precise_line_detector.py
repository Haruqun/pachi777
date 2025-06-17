#!/usr/bin/env python3
"""
超高精度グラフ基準線検出ツール
- 薄いグリッド線も確実に検出
- 点線パターンを認識
- 等間隔性を利用
"""

import os
import numpy as np
from PIL import Image, ImageDraw
import cv2
from typing import Tuple, Optional, Dict, List
from scipy.signal import find_peaks
import matplotlib.pyplot as plt

class UltraPreciseLineDetector:
    """超高精度グラフ基準線検出システム"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            symbols = {"INFO": "📋", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
            print(f"{symbols.get(level, '📋')} [{level}] {message}")
    
    def enhance_grid_lines(self, img_array: np.ndarray) -> np.ndarray:
        """グリッド線を強調"""
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # ガウシアンフィルタでノイズ除去
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # アダプティブ閾値処理でグリッド線を強調
        adaptive = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY_INV, 11, 2)
        
        # モルフォロジー処理で水平線を強調
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        morphed = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel)
        
        return morphed
    
    def detect_dotted_lines(self, img_array: np.ndarray) -> List[int]:
        """点線パターンを検出"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        detected_lines = []
        
        # 各Y座標で点線パターンをチェック
        for y in range(height):
            row = gray[y, :]
            
            # 行の変化を計算
            diff = np.abs(np.diff(row.astype(float)))
            
            # 周期的な変化（点線）を検出
            if np.mean(diff) > 0.5 and np.std(diff) > 1:
                # FFTで周期性を確認
                fft = np.fft.fft(diff)
                power = np.abs(fft[:len(fft)//2])
                
                # 高周波成分が存在する場合は点線の可能性
                high_freq_power = np.sum(power[10:50])
                if high_freq_power > np.sum(power) * 0.1:
                    detected_lines.append(y)
        
        # 近接した線をマージ
        if detected_lines:
            merged = []
            current_group = [detected_lines[0]]
            
            for i in range(1, len(detected_lines)):
                if detected_lines[i] - detected_lines[i-1] <= 2:
                    current_group.append(detected_lines[i])
                else:
                    merged.append(int(np.mean(current_group)))
                    current_group = [detected_lines[i]]
            merged.append(int(np.mean(current_group)))
            
            return merged
        
        return []
    
    def find_regular_grid_lines(self, img_array: np.ndarray) -> List[int]:
        """等間隔のグリッド線を検出"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 各行の平均輝度を計算
        row_means = np.mean(gray, axis=1)
        
        # 輝度の変化を計算
        row_diff = np.abs(np.diff(row_means))
        
        # ピークを検出（局所的な変化点）
        peaks, properties = find_peaks(row_diff, height=np.std(row_diff)*0.5, distance=10)
        
        if len(peaks) < 3:
            return []
        
        # 間隔を分析
        intervals = np.diff(peaks)
        median_interval = np.median(intervals)
        
        # 等間隔の線を選択
        regular_lines = []
        for i, peak in enumerate(peaks):
            if i == 0:
                regular_lines.append(peak)
            else:
                expected_pos = regular_lines[-1] + median_interval
                if abs(peak - expected_pos) < median_interval * 0.3:  # 30%の誤差を許容
                    regular_lines.append(peak)
        
        return regular_lines
    
    def detect_major_lines(self, img_array: np.ndarray) -> Dict[str, Optional[int]]:
        """主要な3本の線（+30,000、0、-30,000）を検出"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 強調画像を作成
        enhanced = self.enhance_grid_lines(img_array)
        
        # 水平投影
        horizontal_projection = np.sum(enhanced, axis=1)
        
        # しきい値を動的に設定
        threshold = np.mean(horizontal_projection) + np.std(horizontal_projection)
        
        # 候補線を検出
        candidate_lines = []
        for y in range(height):
            if horizontal_projection[y] > threshold:
                candidate_lines.append(y)
        
        # 連続した線をグループ化
        if not candidate_lines:
            # 別の手法を試す
            candidate_lines = self.find_regular_grid_lines(img_array)
        
        if len(candidate_lines) < 3:
            self.log("候補線が不足", "WARNING")
            return {"top": None, "zero": None, "bottom": None}
        
        # グループ化
        grouped_lines = []
        current_group = [candidate_lines[0]]
        
        for i in range(1, len(candidate_lines)):
            if candidate_lines[i] - candidate_lines[i-1] <= 5:
                current_group.append(candidate_lines[i])
            else:
                grouped_lines.append(int(np.mean(current_group)))
                current_group = [candidate_lines[i]]
        grouped_lines.append(int(np.mean(current_group)))
        
        # 最低3本の線が必要
        if len(grouped_lines) < 3:
            return {"top": None, "zero": None, "bottom": None}
        
        # 画像の構造から推定
        # 上部10-30%に+30,000ライン
        # 中央付近に0ライン
        # 下部70-90%に-30,000ライン
        
        top_candidates = [y for y in grouped_lines if y < height * 0.3]
        middle_candidates = [y for y in grouped_lines if height * 0.4 < y < height * 0.6]
        bottom_candidates = [y for y in grouped_lines if y > height * 0.7]
        
        # 各領域から最適な線を選択
        top_line = min(top_candidates) if top_candidates else grouped_lines[0]
        bottom_line = max(bottom_candidates) if bottom_candidates else grouped_lines[-1]
        
        # 0ラインは中央に最も近い線、または上下の中点
        if middle_candidates:
            center_y = height // 2
            zero_line = min(middle_candidates, key=lambda y: abs(y - center_y))
        else:
            # 上下の線から等間隔で推定
            zero_line = (top_line + bottom_line) // 2
        
        return {
            "top": top_line,
            "zero": zero_line,
            "bottom": bottom_line
        }
    
    def create_precise_overlay(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str]]:
        """高精度オーバーレイを作成"""
        try:
            self.log(f"処理開始: {os.path.basename(image_path)}")
            
            # 画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # 主要線を検出
            lines = self.detect_major_lines(img_array)
            
            # 結果をログ出力
            if lines["top"] is not None:
                self.log(f"+30,000ライン: Y={lines['top']}px", "SUCCESS")
            if lines["zero"] is not None:
                self.log(f"0ライン: Y={lines['zero']}px", "SUCCESS")
            if lines["bottom"] is not None:
                self.log(f"-30,000ライン: Y={lines['bottom']}px", "SUCCESS")
            
            # オーバーレイ描画
            draw = ImageDraw.Draw(img)
            width, height = img.size
            
            # +30,000ライン（青色）
            if lines["top"] is not None:
                y = lines["top"]
                draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=2)
                draw.text((10, y-20), f"+30,000 (Y={y})", fill=(0, 0, 255))
            
            # 0ライン（赤色）
            if lines["zero"] is not None:
                y = lines["zero"]
                draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=3)
                draw.text((10, y-20), f"0 (Y={y})", fill=(255, 0, 0))
            
            # -30,000ライン（青色）
            if lines["bottom"] is not None:
                y = lines["bottom"]
                draw.line([(0, y), (width, y)], fill=(0, 0, 255), width=2)
                draw.text((10, y+5), f"-30,000 (Y={y})", fill=(0, 0, 255))
            
            # 精度情報を追加
            if all(lines[k] is not None for k in ["top", "zero", "bottom"]):
                # 対称性チェック
                top_dist = lines["zero"] - lines["top"]
                bottom_dist = lines["bottom"] - lines["zero"]
                total_range = lines["bottom"] - lines["top"]
                
                info_text = f"Range: {total_range}px"
                draw.text((width-150, 20), info_text, fill=(0, 0, 0))
                
                symmetry = min(top_dist, bottom_dist) / max(top_dist, bottom_dist)
                sym_text = f"Symmetry: {symmetry:.2f}"
                draw.text((width-150, 40), sym_text, fill=(0, 0, 0))
            
            # 出力パス生成
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"{base_name}_ultra_precise.png"
            
            # 保存
            img.save(output_path, "PNG")
            
            self.log(f"オーバーレイ画像を保存: {output_path}", "SUCCESS")
            
            return True, output_path
            
        except Exception as e:
            self.log(f"エラー: {str(e)}", "ERROR")
            return False, None

def main():
    """メイン処理"""
    print("🎯 超高精度グラフ基準線検出ツール")
    print("📊 薄いグリッド線も確実に検出します")
    
    # 入出力フォルダ設定
    input_folder = "graphs/optimal_v2"
    output_folder = "graphs/ultra_precise_detection"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # すべての画像を処理
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith('.png')]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    detector = UltraPreciseLineDetector(debug_mode=True)
    
    success_count = 0
    
    # 各画像を処理
    for i, file in enumerate(image_files, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(image_files)}] 処理中: {file}")
        
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, 
                                   f"{os.path.splitext(file)[0]}_ultra_precise.png")
        
        success, _ = detector.create_precise_overlay(input_path, output_path)
        
        if success:
            success_count += 1
    
    print(f"\n✨ 処理完了: {success_count}/{len(image_files)} 成功")

if __name__ == "__main__":
    main()