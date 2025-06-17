#!/usr/bin/env python3
"""
最適化グラフ切り取りツール
- グラフ描画領域を正確に特定
- Y軸の-30,000〜+30,000の範囲を含む
- 0ラインを基準に上下対称に切り取り
- X軸の左右マージンを適切に設定
"""

import os
import numpy as np
from PIL import Image
import cv2
from typing import Tuple, Optional, Dict

class OptimalGraphCropper:
    """最適化グラフ切り取りシステム"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        if self.debug_mode:
            print(f"[{level}] {message}")
    
    def detect_zero_line_robust(self, img_array: np.ndarray) -> Optional[int]:
        """0ラインを確実に検出"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 中央付近で最も濃い水平線を探す
        center_y = height // 2
        search_range = height // 4  # 中央から上下25%の範囲
        
        max_darkness = 0
        zero_line_y = None
        
        for y in range(center_y - search_range, center_y + search_range):
            # 水平方向のエッジ強度を計算
            if y > 0 and y < height - 1:
                edge_strength = np.abs(gray[y-1, :].astype(float) - gray[y+1, :].astype(float))
                darkness = np.mean(edge_strength)
                
                if darkness > max_darkness:
                    max_darkness = darkness
                    zero_line_y = y
        
        return zero_line_y
    
    def find_y_axis_labels(self, img_array: np.ndarray) -> Tuple[Optional[int], Optional[int]]:
        """Y軸のラベル（30,000と-30,000）の位置を検出"""
        height, width = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 左側の領域でテキストを探す（Y軸ラベルがある領域）
        left_region = gray[:, :width//4]
        
        # エッジ検出でテキスト領域を特定
        edges = cv2.Canny(left_region, 50, 150)
        
        # 上部と下部でテキストが集中している領域を探す
        top_text_y = None
        bottom_text_y = None
        
        # 上部1/3で探す
        for y in range(height//6, height//3):
            if np.sum(edges[y, :]) > 50:  # エッジが多い行
                top_text_y = y
                break
        
        # 下部1/3で探す
        for y in range(2*height//3, 5*height//6):
            if np.sum(edges[y, :]) > 50:
                bottom_text_y = y
                break
        
        return top_text_y, bottom_text_y
    
    def find_optimal_boundaries(self, img_array: np.ndarray) -> Tuple[int, int, int, int]:
        """最適なグラフ境界を計算"""
        height, width = img_array.shape[:2]
        
        # 1. 0ラインを検出
        zero_line_y = self.detect_zero_line_robust(img_array)
        if zero_line_y is None:
            self.log("0ライン検出失敗、画像中央を使用", "WARNING")
            zero_line_y = height // 2
        else:
            self.log(f"0ライン検出: Y={zero_line_y}", "SUCCESS")
        
        # 2. Y軸ラベルの位置から上下境界を推定
        top_label_y, bottom_label_y = self.find_y_axis_labels(img_array)
        
        if top_label_y and bottom_label_y:
            # ラベル位置から少し内側をグラフ境界とする
            graph_top = top_label_y + 20
            graph_bottom = bottom_label_y - 20
        else:
            # フォールバック: 0ラインから上下対称に
            graph_height = int(height * 0.6)  # グラフの高さ（全体の60%程度）
            graph_top = zero_line_y - graph_height // 2
            graph_bottom = zero_line_y + graph_height // 2
        
        # 3. 左右境界の設定
        # Y軸ラベル（BACK/NEXT）を除外
        graph_left = int(width * 0.12)   # 左側12%をマージン
        graph_right = int(width * 0.88)  # 右側12%をマージン
        
        # 4. グラフ背景色の検証
        # グラフ領域内の背景色をチェック
        roi = img_array[graph_top:graph_bottom, graph_left:graph_right]
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        
        # 背景色（薄いベージュ/グレー）の割合を確認
        bg_mask = (gray_roi > 200) & (gray_roi < 250)
        bg_ratio = np.sum(bg_mask) / (bg_mask.shape[0] * bg_mask.shape[1])
        
        self.log(f"背景色の割合: {bg_ratio*100:.1f}%", "DEBUG")
        
        # 境界の微調整
        # 上部のオレンジヘッダーを確実に除外
        if graph_top < 100:
            graph_top = 100
        
        # 下部のボタンを除外
        if graph_bottom > height - 100:
            graph_bottom = height - 100
        
        return (graph_left, graph_top, graph_right, graph_bottom)
    
    def crop_optimal_graph(self, image_path: str, output_path: str = None) -> Tuple[bool, Optional[str], Dict]:
        """最適化されたグラフ切り取りを実行"""
        try:
            self.log(f"処理開始: {os.path.basename(image_path)}")
            
            # 画像読み込み
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # 最適な境界を計算
            left, top, right, bottom = self.find_optimal_boundaries(img_array)
            
            # 切り取り実行
            cropped_img = img.crop((left, top, right, bottom))
            
            # 出力パス生成
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"{base_name}_optimal.png"
            
            # 保存
            cropped_img.save(output_path, "PNG", optimize=True)
            
            # 詳細情報
            details = {
                "original_size": img.size,
                "cropped_size": (right - left, bottom - top),
                "boundaries": (left, top, right, bottom),
                "success": True
            }
            
            self.log(f"切り取り成功: {details['cropped_size'][0]}×{details['cropped_size'][1]}")
            
            return True, output_path, details
            
        except Exception as e:
            self.log(f"エラー: {str(e)}", "ERROR")
            return False, None, {"error": str(e)}

def main():
    """バッチ処理"""
    print("🎯 最適化グラフ切り取りツール")
    
    # 入出力フォルダ設定
    input_folder = "graphs/cropped_perfect"
    output_folder = "graphs/optimal"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 画像ファイルを取得
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith('.png')]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    cropper = OptimalGraphCropper(debug_mode=False)
    
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