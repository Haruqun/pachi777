#!/usr/bin/env python3
"""
site7のパチンコ台画像から各要素の正確なピクセル座標を計測する
"""

import cv2
import numpy as np
import os
from pathlib import Path

def analyze_image_elements(image_path):
    """画像から各要素の座標を検出"""
    print(f"\n=== {Path(image_path).name} の分析 ===")
    
    # 画像読み込み
    img = cv2.imread(image_path)
    if img is None:
        print(f"画像を読み込めませんでした: {image_path}")
        return
    
    height, width = img.shape[:2]
    print(f"画像サイズ: {width}x{height}")
    
    # HSV変換
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # グレースケール変換
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. 台番号の白い領域を検出
    # 左上の白い領域を探す
    white_lower = np.array([0, 0, 200])
    white_upper = np.array([180, 30, 255])
    white_mask = cv2.inRange(hsv, white_lower, white_upper)
    
    # 台番号エリア（画像の左上部分）
    unit_area = white_mask[250:350, 0:150]
    contours, _ = cv2.findContours(unit_area, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        unit_coords = (x, y+250, x+w, y+250+h)
        print(f"台番号領域: {unit_coords}")
    
    # 2. 黒い背景領域の検出（メインデータ表示部分）
    # 黒い領域を検出
    black_lower = np.array([0, 0, 0])
    black_upper = np.array([180, 255, 50])
    black_mask = cv2.inRange(hsv, black_lower, black_upper)
    
    # 大きな黒い矩形領域を探す
    kernel = np.ones((5,5), np.uint8)
    black_mask_closed = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(black_mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # 最大の黒い領域を見つける
        largest_black = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_black)
        main_black_area = (x, y, x+w, y+h)
        print(f"メイン黒背景領域: {main_black_area}")
        
        # この領域内で要素を探す
        roi = img[y:y+h, x:x+w]
        roi_hsv = hsv[y:y+h, x:x+w]
        
        # 3. 赤い大きな数字（大当り回数）の検出
        red_lower1 = np.array([0, 100, 100])
        red_upper1 = np.array([10, 255, 255])
        red_lower2 = np.array([170, 100, 100])
        red_upper2 = np.array([180, 255, 255])
        
        red_mask1 = cv2.inRange(roi_hsv, red_lower1, red_upper1)
        red_mask2 = cv2.inRange(roi_hsv, red_lower2, red_upper2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        
        # 大きな赤い数字を見つける（上部1/3の領域）
        red_top_area = red_mask[0:h//3, 0:w//2]
        contours, _ = cv2.findContours(red_top_area, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # 面積でソートして大きいものを取得
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            all_red_x = []
            all_red_y = []
            
            for cnt in contours[:5]:  # 上位5つのコンターを見る
                cnt_x, cnt_y, cnt_w, cnt_h = cv2.boundingRect(cnt)
                if cnt_h > 50:  # 高さが50px以上のものを対象
                    all_red_x.extend([cnt_x, cnt_x + cnt_w])
                    all_red_y.extend([cnt_y, cnt_y + cnt_h])
            
            if all_red_x:
                red_number_coords = (min(all_red_x) + x, min(all_red_y) + y, 
                                   max(all_red_x) + x, max(all_red_y) + y)
                print(f"赤い大当り回数: {red_number_coords}")
        
        # 4. 青い大きな数字（初当り回数）の検出
        blue_lower = np.array([100, 100, 100])
        blue_upper = np.array([130, 255, 255])
        blue_mask = cv2.inRange(roi_hsv, blue_lower, blue_upper)
        
        # 大きな青い数字を見つける（上部1/3の領域、右側）
        blue_top_area = blue_mask[0:h//3, w//2:]
        contours, _ = cv2.findContours(blue_top_area, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            all_blue_x = []
            all_blue_y = []
            
            for cnt in contours[:5]:
                cnt_x, cnt_y, cnt_w, cnt_h = cv2.boundingRect(cnt)
                if cnt_h > 50:
                    all_blue_x.extend([cnt_x + w//2, cnt_x + w//2 + cnt_w])
                    all_blue_y.extend([cnt_y, cnt_y + cnt_h])
            
            if all_blue_x:
                blue_number_coords = (min(all_blue_x) + x, min(all_blue_y) + y,
                                    max(all_blue_x) + x, max(all_blue_y) + y)
                print(f"青い初当り回数: {blue_number_coords}")
        
        # 5. その他のテキスト要素の検出
        # 白いテキストを検出
        white_text_lower = np.array([0, 0, 180])
        white_text_upper = np.array([180, 30, 255])
        white_text_mask = cv2.inRange(roi_hsv, white_text_lower, white_text_upper)
        
        # 各行のテキスト領域を推定
        # 累計スタート（右上）
        total_start_area = (x + w//2, y + 20, x + w - 20, y + 100)
        print(f"累計スタート領域（推定）: {total_start_area}")
        
        # スタート数（中央）
        start_count_area = (x + w//3, y + h//3, x + 2*w//3, y + h//2)
        print(f"スタート数領域（推定）: {start_count_area}")
        
        # 最高出玉（右）
        max_balls_area = (x + 2*w//3, y + h//3, x + w - 20, y + h//2)
        print(f"最高出玉領域（推定）: {max_balls_area}")
        
        # 下部のデータテーブル領域
        table_area = (x + 20, y + h//2, x + w - 20, y + h - 50)
        print(f"データテーブル領域（推定）: {table_area}")
        
        # 6. 更新日時の検出
        update_time_area = (x + w//4, y + 5, x + 3*w//4, y + 25)
        print(f"更新日時領域（推定）: {update_time_area}")
    
    # 7. グラフ領域の検出
    # 下部のグラフエリア（黒い背景の下）
    if contours:
        graph_start_y = main_black_area[3] + 10
        graph_area = (50, graph_start_y, width - 50, height - 200)
        print(f"グラフ領域（推定）: {graph_area}")
    
    return

def main():
    """メイン処理"""
    test_images_dir = "/Users/haruqun/Work/pachi777/test_images"
    
    # 対象画像
    images = ["IMG_2074.PNG", "IMG_2075.PNG", "IMG_2076.PNG", "IMG_2077.PNG"]
    
    for image_name in images:
        image_path = os.path.join(test_images_dir, image_name)
        if os.path.exists(image_path):
            analyze_image_elements(image_path)
        else:
            print(f"画像が見つかりません: {image_path}")

if __name__ == "__main__":
    main()