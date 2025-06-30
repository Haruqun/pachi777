#!/usr/bin/env python3
"""
新しい18枚の画像を切り抜くスクリプト
最適な689×558pxサイズで切り抜き
"""

import cv2
import numpy as np
import os
import glob

def detect_orange_bar(img):
    """オレンジバーの下端を検出"""
    height, width = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # オレンジ色の範囲
    orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
    
    # オレンジバーの最下端を探す
    orange_bottom = 0
    for y in range(height//2):
        if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
            orange_bottom = y
    
    return orange_bottom

def detect_button_area(img):
    """下部のボタンエリアを検出"""
    height, width = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # ボタンエリアの検出（下部1/4エリアでオレンジまたは青の濃い色）
    bottom_quarter = height * 3 // 4
    
    for y in range(height-1, bottom_quarter, -1):
        row_hsv = hsv[y, :]
        # オレンジ系または青系の鮮やかな色を検出
        bright_pixels = np.sum((row_hsv[:, 1] > 150) & (row_hsv[:, 2] > 100))
        if bright_pixels > width * 0.4:
            return y
    
    return int(height * 0.83)  # デフォルト83%位置

def detect_graph_boundaries(img):
    """グラフの境界を検出"""
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # オレンジバー検出
    orange_bottom = detect_orange_bar(img)
    graph_top = orange_bottom + 70  # オレンジバーから70px下
    
    # ボタンエリア検出
    button_top = detect_button_area(img)
    graph_bottom = button_top - 35  # ボタンエリアから35px上
    
    # 左右の境界（各列の分散を計算）
    search_region = gray[graph_top:graph_bottom, :]
    col_variances = np.var(search_region, axis=0)
    
    # 左端：左から分散が急増する位置
    graph_left = 0
    for x in range(width//4):
        if col_variances[x] > np.median(col_variances) * 0.3:
            graph_left = x
            break
    
    # 右端：右から分散が急増する位置
    graph_right = width - 1
    for x in range(width-1, width*3//4, -1):
        if col_variances[x] > np.median(col_variances) * 0.3:
            graph_right = x
            break
    
    return graph_top, graph_bottom, graph_left, graph_right

def crop_to_optimal_size(img, top, bottom, left, right):
    """689×558pxの最適サイズに切り抜き"""
    TARGET_WIDTH = 689
    TARGET_HEIGHT = 558
    
    # 現在のサイズ
    current_height = bottom - top
    current_width = right - left
    
    # 中心を基準に目標サイズに切り抜き
    center_y = (top + bottom) // 2
    center_x = (left + right) // 2
    
    # 新しい境界を計算
    new_top = max(0, center_y - TARGET_HEIGHT // 2)
    new_bottom = min(img.shape[0], new_top + TARGET_HEIGHT)
    new_left = max(0, center_x - TARGET_WIDTH // 2)
    new_right = min(img.shape[1], new_left + TARGET_WIDTH)
    
    # 切り抜き
    cropped = img[new_top:new_bottom, new_left:new_right]
    
    # サイズが完全に一致しない場合はリサイズ
    if cropped.shape[:2] != (TARGET_HEIGHT, TARGET_WIDTH):
        cropped = cv2.resize(cropped, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_CUBIC)
    
    return cropped

def process_new_images():
    """新しい画像を処理"""
    # 新しい画像のパターン
    new_patterns = [
        "graphs/original/S__7974*.jpg",
        "graphs/original/S__7978*.jpg", 
        "graphs/original/S__8015*.jpg"
    ]
    
    new_files = []
    for pattern in new_patterns:
        new_files.extend(glob.glob(pattern))
    
    # 既に処理済みの画像を除外
    existing_cropped = glob.glob("graphs/cropped/*_optimal.png")
    existing_bases = [os.path.basename(f).replace("_optimal.png", "") for f in existing_cropped]
    
    files_to_process = []
    for f in new_files:
        base = os.path.splitext(os.path.basename(f))[0]
        if base not in existing_bases:
            files_to_process.append(f)
    
    print(f"処理対象: {len(files_to_process)}枚の新しい画像")
    
    # 出力ディレクトリ
    os.makedirs("graphs/cropped", exist_ok=True)
    
    success_count = 0
    for image_path in sorted(files_to_process):
        print(f"\n処理中: {os.path.basename(image_path)}")
        
        img = cv2.imread(image_path)
        if img is None:
            print(f"エラー: 画像を読み込めません")
            continue
        
        try:
            # 境界検出
            top, bottom, left, right = detect_graph_boundaries(img)
            print(f"  検出境界: ({left}, {top}) - ({right}, {bottom})")
            print(f"  サイズ: {right-left}×{bottom-top}")
            
            # 最適サイズに切り抜き
            cropped = crop_to_optimal_size(img, top, bottom, left, right)
            
            # 保存
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            output_path = f"graphs/cropped/{base_name}_optimal.png"
            cv2.imwrite(output_path, cropped)
            print(f"  ✅ 保存: {output_path} (689×558px)")
            
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ エラー: {e}")
    
    print(f"\n完了: {success_count}/{len(files_to_process)}枚を正常に処理")
    return success_count

if __name__ == "__main__":
    process_new_images()