"""画像処理関連の共通関数"""
import cv2
import numpy as np
from PIL import Image


def detect_orange_bar(img_array):
    """オレンジバーの下端位置を検出
    
    Args:
        img_array: numpy配列の画像
        
    Returns:
        int: オレンジバーの下端Y座標
    """
    height, width = img_array.shape[:2]
    
    # HSV変換
    hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
    orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
    
    orange_bottom = 0
    
    # 上半分をスキャンしてオレンジバーを探す
    for y in range(height//2):
        if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
            orange_bottom = y
    
    # オレンジバーの下端を精密に検出
    if orange_bottom > 0:
        for y in range(orange_bottom, min(orange_bottom + 100, height)):
            if np.sum(orange_mask[y, :]) < width * 0.1 * 255:
                orange_bottom = y
                break
    else:
        orange_bottom = 150  # デフォルト値
        
    return orange_bottom


def detect_zero_line(gray_img, orange_bottom, search_start_offset, search_end_offset):
    """ゼロラインを検出
    
    Args:
        gray_img: グレースケール画像
        orange_bottom: オレンジバーの下端Y座標
        search_start_offset: 検索開始オフセット
        search_end_offset: 検索終了オフセット
        
    Returns:
        int: ゼロラインのY座標
    """
    height, width = gray_img.shape
    search_start = orange_bottom + search_start_offset
    search_end = min(height - 100, orange_bottom + search_end_offset)
    
    best_score = 0
    zero_line_y = (search_start + search_end) // 2
    
    for y in range(search_start, search_end):
        row = gray_img[y, 100:width-100]
        darkness = 1.0 - (np.mean(row) / 255.0)
        uniformity = 1.0 - (np.std(row) / 128.0)
        score = darkness * 0.5 + uniformity * 0.5
        
        if score > best_score:
            best_score = score
            zero_line_y = y
            
    return zero_line_y


def crop_graph_area(img_array, zero_line_y, crop_settings):
    """グラフ領域を切り出し
    
    Args:
        img_array: 元画像
        zero_line_y: ゼロラインのY座標
        crop_settings: 切り出し設定（crop_top, crop_bottom, left_margin, right_margin）
        
    Returns:
        tuple: (切り出し画像, top, bottom, left, right)
    """
    height, width = img_array.shape[:2]
    
    # 切り出し範囲を計算
    top = max(0, zero_line_y - crop_settings['crop_top'])
    bottom = min(height, zero_line_y + crop_settings['crop_bottom'])
    left = crop_settings['left_margin']
    right = width - crop_settings['right_margin']
    
    # 範囲チェック
    if left >= right or top >= bottom:
        raise ValueError("無効な切り出し範囲")
    
    cropped = img_array[int(top):int(bottom), int(left):int(right)].copy()
    
    return cropped, top, bottom, left, right