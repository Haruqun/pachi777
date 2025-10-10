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
        # まず400px幅にリサイズ（元の実装と同じ）
        image = resize_to_default_width(image)
        
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
        # まず400px幅にリサイズ（元の実装と同じ）
        pil_image = resize_to_default_width(pil_image)
        
        processed_image, debug_info = detect_and_draw_black_frames(
            pil_image, 
            overlay_mask=True, 
            crop_upper_half=True
        )
        return processed_image


def resize_to_default_width(image, target_width=400):
    """画像を指定幅にリサイズ（アスペクト比保持）
    
    Args:
        image: PIL Image
        target_width: 目標の横幅（デフォルト400px）
    
    Returns:
        リサイズされたPIL Image
    """
    width, height = image.size
    if width != target_width:
        aspect_ratio = height / width
        new_height = int(target_width * aspect_ratio)
        return image.resize((target_width, new_height), Image.Resampling.LANCZOS)
    return image


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
    
    # デバッグモードの場合、前回のオレンジバーOCRデバッグ情報をクリア
    if st.session_state.get('show_ocr_debug', False):
        st.session_state.orange_bar_ocr_debug = {}
    
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
    
    # 台番号の抽出（複数の方法を試行）
    machine_number = None
    
    # 方法1: OCRテキストから複数のパターンを検索
    # パターン1: 「〇〇番台」
    machine_pattern = re.search(r'(\d{3,4})番台', text)
    if machine_pattern:
        machine_number = machine_pattern.group(1)
        if st.session_state.get('show_ocr_debug', False):
            extracted_data['machine_number_source'] = 'OCR_pattern_番台'
    
    # パターン2: 「〇〇番」（番台なし）
    if not machine_number:
        machine_pattern = re.search(r'(\d{3,4})番(?!台)', text)
        if machine_pattern:
            machine_number = machine_pattern.group(1)
            if st.session_state.get('show_ocr_debug', False):
                extracted_data['machine_number_source'] = 'OCR_pattern_番'
    
    # パターン3: 「台番〇〇」
    if not machine_number:
        machine_pattern = re.search(r'台番\s*[:：]?\s*(\d{3,4})', text)
        if machine_pattern:
            machine_number = machine_pattern.group(1)
            if st.session_state.get('show_ocr_debug', False):
                extracted_data['machine_number_source'] = 'OCR_pattern_台番'
    
    # 方法2: オレンジバー付近から抽出（フォールバック）
    if not machine_number:
        machine_number = extract_machine_number_from_orange_bar(image)
        if machine_number and st.session_state.get('show_ocr_debug', False):
            extracted_data['machine_number_source'] = 'orange_bar'
    
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
        
        # デバッグ用に切り出し領域の情報を保存
        if st.session_state.get('show_ocr_debug', False):
            if 'orange_bar_ocr_debug' not in st.session_state:
                st.session_state.orange_bar_ocr_debug = {}
            st.session_state.orange_bar_ocr_debug['crop_region'] = {
                'y_start': orange_center - 15,
                'y_end': orange_center + 15,
                'x_start': 10,
                'x_end': 200,
                'orange_center': orange_center
            }
        
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
        
        # デバッグ情報を保存
        if st.session_state.get('show_ocr_debug', False):
            if 'orange_bar_ocr_debug' not in st.session_state:
                st.session_state.orange_bar_ocr_debug = {}
            st.session_state.orange_bar_ocr_debug = {
                'raw_text': text,
                'orange_found': orange_y_start is not None,
                'orange_y_range': (orange_y_start, orange_y_end) if orange_y_start else None,
                'number_region_shape': number_region.shape if number_region.size > 0 else None
            }
        
        # 数字を抽出
        numbers = re.findall(r'\d+', text)
        if numbers:
            return numbers[0]
        
        return None
        
    except Exception as e:
        if st.session_state.get('show_ocr_debug', False):
            st.session_state.orange_bar_ocr_debug = {
                'error': str(e)
            }
        return None