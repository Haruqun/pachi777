#!/usr/bin/env python3
"""
最適化グラフ切り取りツール V2
- ±30,000の線を含むグラフ領域を切り取り
- Y軸の数値ラベルは含めない（BACK/NEXTなど）
- グリッド線を基準に正確な境界検出
"""

import os
import numpy as np
from PIL import Image
import cv2
from typing import Tuple, Optional, Dict

class OptimalGraphCropperV2:
    """最適化グラフ切り取りシステム V2"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            print(f"[{level}] {message}")
    
    def detect_horizontal_lines(self, img_array: np.ndarray) -> list:
        """水平線（グリッド線）を検出"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # エッジ検出
        edges = cv2.Canny(gray, 30, 100)
        
        # 水平線を検出
        horizontal_lines = []
        min_line_length = width * 0.5  # 画面幅の50%以上
        
        for y in range(height):
            # 水平方向のエッジをカウント
            edge_count = np.sum(edges[y, width//4:3*width//4] > 0)
            if edge_count > min_line_length:
                horizontal_lines.append(y)
        
        # 連続した線をグループ化して代表値を取る
        if not horizontal_lines:
            return []
        
        grouped_lines = []
        current_group = [horizontal_lines[0]]
        
        for i in range(1, len(horizontal_lines)):
            if horizontal_lines[i] - horizontal_lines[i-1] <= 3:
                current_group.append(horizontal_lines[i])
            else:
                grouped_lines.append(int(np.mean(current_group)))
                current_group = [horizontal_lines[i]]
        
        grouped_lines.append(int(np.mean(current_group)))
        
        return grouped_lines
    
    def find_graph_boundaries_by_lines(self, img_array: np.ndarray) -> Tuple[int, int, int, int]:
        """グリッド線を基準にグラフ境界を検出"""
        height, width = img_array.shape[:2]
        
        # 水平線を検出
        h_lines = self.detect_horizontal_lines(img_array)
        
        if len(h_lines) < 2:
            self.log("グリッド線が不足、デフォルト値を使用", "WARNING")
            # フォールバック値
            top = int(height * 0.15)
            bottom = int(height * 0.85)
        else:
            # 最上部と最下部のグリッド線を±30,000の線として扱う
            # ただし、あまりに端に近い線は除外
            valid_lines = [y for y in h_lines if height * 0.1 < y < height * 0.9]
            
            if len(valid_lines) >= 2:
                top = min(valid_lines)
                bottom = max(valid_lines)
                
                # 上下に少しマージンを追加（線が切れないように）
                top = max(0, top - 5)
                bottom = min(height - 1, bottom + 5)
            else:
                top = int(height * 0.15)
                bottom = int(height * 0.85)
        
        # 左右の境界
        # グラフ描画領域の開始と終了を検出
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 垂直エッジを検出して左右の境界を見つける
        edges_v = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        edges_v = np.abs(edges_v)
        
        # 左側の境界（Y軸の右側）
        left = 0
        for x in range(width//4):
            if np.mean(edges_v[top:bottom, x]) > 20:
                left = x + 10  # 少し右にオフセット
                break
        
        if left == 0:
            left = int(width * 0.08)  # デフォルト値
        
        # 右側の境界
        right = width
        for x in range(width-1, 3*width//4, -1):
            if np.mean(edges_v[top:bottom, x]) > 20:
                right = x - 10  # 少し左にオフセット
                break
        
        if right == width:
            right = int(width * 0.92)  # デフォルト値
        
        # 0ラインの検出（デバッグ用）
        zero_line_y = self.detect_zero_line(img_array[top:bottom, left:right])
        if zero_line_y is not None:
            zero_line_y += top
            self.log(f"0ライン検出: Y={zero_line_y} (相対位置: {(zero_line_y-top)/(bottom-top)*100:.1f}%)", "DEBUG")
        
        return (left, top, right, bottom)
    
    def detect_zero_line(self, roi: np.ndarray) -> Optional[int]:
        """ROI内で0ラインを検出"""
        height, width = roi.shape[:2]
        gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        
        # 中央付近で最も濃い線を探す
        center_y = height // 2
        search_range = height // 3
        
        max_darkness = 0
        zero_line_y = None
        
        for y in range(max(1, center_y - search_range), 
                      min(height - 1, center_y + search_range)):
            # ライン上のピクセルの暗さを評価
            line_darkness = 255 - np.mean(gray[y, :])
            
            if line_darkness > max_darkness:
                max_darkness = line_darkness
                zero_line_y = y
        
        return zero_line_y
    
    def crop_optimal_graph(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str], Dict]:
        """最適化されたグラフ切り取りを実行"""
        try:
            self.log(f"処理開始: {os.path.basename(image_path)}")
            
            # 画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # グリッド線基準で境界を検出
            left, top, right, bottom = self.find_graph_boundaries_by_lines(img_array)
            
            self.log(f"検出境界: ({left}, {top}, {right}, {bottom})")
            self.log(f"切り取りサイズ: {right-left}×{bottom-top}")
            
            # 切り取り実行
            cropped_img = img.crop((left, top, right, bottom))
            
            # 出力パス生成
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"{base_name}_optimal_v2.png"
            
            # 保存
            cropped_img.save(output_path, "PNG", optimize=True)
            
            # 詳細情報
            details = {
                "original_size": img.size,
                "cropped_size": (right - left, bottom - top),
                "boundaries": (left, top, right, bottom),
                "success": True
            }
            
            return True, output_path, details
            
        except Exception as e:
            self.log(f"エラー: {str(e)}", "ERROR")
            return False, None, {"error": str(e)}

def main():
    """バッチ処理"""
    print("🎯 最適化グラフ切り取りツール V2")
    print("📊 ±30,000の線を含むグラフ領域を切り取ります")
    
    # 入出力フォルダ設定
    input_folder = "graphs/cropped_perfect"
    output_folder = "graphs/optimal_v2"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 画像ファイルを取得
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith('.png')]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    cropper = OptimalGraphCropperV2(debug_mode=False)
    
    success_count = 0
    
    # すべての画像を処理
    for i, file in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] 処理中: {file}")
        
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, 
                                   f"{os.path.splitext(file)[0].replace('_perfect', '')}_optimal.png")
        
        success, _, details = cropper.crop_optimal_graph(input_path, output_path)
        
        if success:
            success_count += 1
            print(f"✅ 成功 - サイズ: {details['cropped_size']}")
        else:
            print(f"❌ 失敗: {details.get('error')}")
    
    print(f"\n✨ 処理完了: {success_count}/{len(image_files)} 成功")

if __name__ == "__main__":
    main()