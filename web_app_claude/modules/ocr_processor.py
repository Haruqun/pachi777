"""OCR処理関連の関数"""
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import pytesseract
import re
import streamlit as st
import time


def preprocess_detail_image(image):
    """出玉詳細画像の前処理（黒枠検出 + overlay.png + 50%切り抜き）"""
    from modules.graph_analyzer import detect_and_draw_black_frames
    
    # PIL ImageをPIL Imageのまま処理
    if hasattr(image, 'mode'):  # PIL Image の場合
        # detect_and_draw_black_frames関数を呼び出し
        # overlay_mask=True: overlay.pngを重ねる
        # crop_upper_half=True: 上半分（50%）を切り抜く
        processed_image, debug_info = detect_and_draw_black_frames(
            image, 
            overlay_mask=True, 
            crop_upper_half=True
        )
        return processed_image
    else:
        # NumPy配列の場合はPIL Imageに変換してから処理
        pil_image = Image.fromarray(image)
        processed_image, debug_info = detect_and_draw_black_frames(
            pil_image, 
            overlay_mask=True, 
            crop_upper_half=True
        )
        return processed_image


def enhance_image_for_ocr(image):
    """OCR用に画像を強調処理"""
    # Pillowで画像を強調
    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    # コントラスト強調
    enhancer = ImageEnhance.Contrast(pil_image)
    pil_image = enhancer.enhance(2.0)
    
    # シャープネス強調
    enhancer = ImageEnhance.Sharpness(pil_image)
    pil_image = enhancer.enhance(2.0)
    
    # 明度調整
    enhancer = ImageEnhance.Brightness(pil_image)
    pil_image = enhancer.enhance(1.2)
    
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)


def extract_site7_data(image):
    """site7の画像からOCRでデータを抽出"""
    ocr_timings = {} if st.session_state.get('show_ocr_debug', False) else None
    
    # タイマースタート
    ocr_start_time = time.time() if ocr_timings is not None else None
    
    # 画像の前処理
    adjusted = enhance_image_for_ocr(image)
    
    # OCR実行
    try:
        text = pytesseract.image_to_string(adjusted, lang='jpn', config='--psm 6')
        
        if ocr_timings is not None:
            ocr_timings['total_ocr_time'] = time.time() - ocr_start_time
    except Exception:
        text = ""
    
    # パターンマッチングで各データを抽出
    patterns = {
        'total_start': r'(\d{3,5})\s*スタート',
        'jackpot_count': r'(\d+)\s*回\s*大当り',
        'jackpot_probability': r'1/(\d{2,4})',
        'total_investment': r'累計投資\s*[:：]?\s*[\-−]?\s*(\d+)',
        'total_payout': r'累計払出\s*[:：]?\s*[\+＋]?\s*(\d+)',
        'balance': r'収支\s*[:：]?\s*([+-−＋]?\s*\d+)',
        'payout_per_1k': r'(\d{2,3}\.\d)\s*[玉枚]/千円',
        'current_start': r'現在\s*[:：]?\s*(\d+)',
        'highest_hits': r'最高連\s*[:：]?\s*(\d+)\s*連'
    }
    
    extracted_data = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip()
            # 符号を含む数値の処理
            if key in ['total_investment', 'total_payout', 'balance']:
                value = value.replace('−', '-').replace('＋', '+').replace(' ', '')
            extracted_data[key] = value
    
    # 機種名の抽出（最初の「P」で始まる行）
    machine_match = re.search(r'(P[^\n]+)', text)
    if machine_match:
        extracted_data['machine_name'] = machine_match.group(1).strip()
    
    # 台番号の抽出（オレンジバー付近）
    machine_number = extract_machine_number_from_orange_bar(image)
    if machine_number:
        extracted_data['machine_number'] = machine_number
    
    # OCRのデバッグ情報
    if st.session_state.get('show_ocr_debug', False):
        extracted_data['ocr_raw_text'] = text
        extracted_data['ocr_timings'] = ocr_timings
    
    return extracted_data


def extract_machine_number_from_orange_bar(image):
    """オレンジバー付近から台番号を抽出"""
    try:
        # HSV変換
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # オレンジ色の範囲（調整済み）
        orange_lower = np.array([8, 150, 150])
        orange_upper = np.array([25, 255, 255])
        
        # オレンジマスク
        orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
        
        # オレンジ領域を探す
        height = image.shape[0]
        orange_y_start = None
        orange_y_end = None
        
        # 上から順にスキャン
        for y in range(height):
            if np.sum(orange_mask[y, :]) > image.shape[1] * 0.3 * 255:
                if orange_y_start is None:
                    orange_y_start = y
                orange_y_end = y
            elif orange_y_start is not None:
                break
        
        if orange_y_start is None:
            return None
        
        # オレンジ領域の高さの中心
        orange_center = (orange_y_start + orange_y_end) // 2
        
        # 台番号領域を切り出し（左端から）
        number_region = image[orange_center-15:orange_center+15, 10:200]
        
        if number_region.size == 0:
            return None
        
        # 白色で塗りつぶされた領域をマスク
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        white_mask = cv2.inRange(cv2.cvtColor(number_region, cv2.COLOR_BGR2HSV), 
                                lower_white, upper_white)
        
        # 白色領域を黒で塗りつぶし
        number_region_cleaned = number_region.copy()
        number_region_cleaned[white_mask > 0] = [255, 255, 255]
        
        # 前処理
        enhanced = enhance_image_for_ocr(number_region_cleaned)
        
        # OCR実行（数字のみ）
        config = '--psm 7 -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(enhanced, config=config)
        
        # 数字を抽出
        numbers = re.findall(r'\d+', text)
        if numbers:
            return numbers[0]
        
        return None
        
    except Exception:
        return None