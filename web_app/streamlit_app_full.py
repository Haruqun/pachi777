#!/usr/bin/env python3
"""
AI Graph Analysis Report - Professional Edition
高精度データ抽出・解析システム
"""

import streamlit as st
from datetime import datetime
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
from web_analyzer import WebCompatibleAnalyzer
import platform
import pytesseract
import re
import json
import pandas as pd
import time
import hashlib
import secrets
import sqlite3

# ページ設定
st.set_page_config(
    page_title="AI Graph Analysis Report",
    page_icon="🎰",
    layout="wide"
)

# グローバル変数でパスワードを管理（アプリ再起動まで有効）
if 'GLOBAL_USER_PASSWORD' not in st.session_state:
    # アプリ全体で共有されるグローバル変数を初期化
    if not hasattr(st, '_global_passwords'):
        st._global_passwords = {
            'user': '059',
            'admin': 'admin777'
        }
    st.session_state.GLOBAL_USER_PASSWORD = st._global_passwords['user']
    st.session_state.GLOBAL_ADMIN_PASSWORD = st._global_passwords['admin']

def extract_machine_number_from_orange_bar(image):
    """オレンジバー付近から台番号を抽出"""
    try:
        height, width = image.shape[:2]
        
        # HSV色空間に変換してオレンジバーを検出
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        # オレンジ色の範囲を定義（site7のオレンジバー用）
        orange_lower = np.array([10, 100, 100])
        orange_upper = np.array([25, 255, 255])
        
        # オレンジ色のマスクを作成
        orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
        
        # オレンジバーがある行を検出（上部300ピクセル内）
        orange_bar_y = -1
        for y in range(min(300, height)):
            # この行のオレンジピクセルの割合を計算
            orange_ratio = np.sum(orange_mask[y, :]) / (width * 255)
            if orange_ratio > 0.7:  # 70%以上がオレンジ色
                orange_bar_y = y
                break
        
        if orange_bar_y == -1:
            # オレンジバーが見つからない場合は従来の方法
            # 上部150ピクセルを切り出し
            top_region = image[0:min(150, height//8), :]
        else:
            # オレンジバーが見つかった場合、その領域を切り出し
            # オレンジバーの高さを検出
            bar_height = 0
            for y in range(orange_bar_y, min(orange_bar_y + 100, height)):
                orange_ratio = np.sum(orange_mask[y, :]) / (width * 255)
                if orange_ratio > 0.7:
                    bar_height += 1
                else:
                    break
            
            # オレンジバー領域を切り出し
            top_region = image[orange_bar_y:orange_bar_y + bar_height, :]
            
            # オレンジバー内の白文字を抽出するため、RGB値で白色を検出
            # 白文字のマスクを作成（RGB全てが200以上）
            white_mask = cv2.inRange(top_region, np.array([200, 200, 200]), np.array([255, 255, 255]))
            
            # 白文字部分を黒背景に白文字として抽出
            result = np.zeros_like(white_mask)
            result[white_mask > 0] = 255
            
            # OCRで台番号を読み取り
            try:
                # 横長の画像なのでPSM 7（単一テキスト行）を使用
                text = pytesseract.image_to_string(result, lang='jpn', config='--psm 7')
                
                # 台番号パターンを探す（「2308番台」のような形式）
                match = re.search(r'(\d{1,4})\s*番台', text)
                if match:
                    return f"{match.group(1)}番台"
                
                # 数字だけ探す
                numbers = re.findall(r'\d{4}', text)
                if numbers:
                    # 4桁の数字を台番号として扱う
                    return f"{numbers[0]}番台"
            except:
                pass
        
        # 従来の方法も試す
        # グレースケール変換
        gray_top = cv2.cvtColor(top_region, cv2.COLOR_RGB2GRAY)
        
        # 複数の二値化方法を試す
        results = []
        
        # 白文字を抽出（背景が暗い場合）
        _, binary1 = cv2.threshold(gray_top, 180, 255, cv2.THRESH_BINARY)
        
        # 黒文字を抽出（背景が明るい場合）
        _, binary2 = cv2.threshold(gray_top, 80, 255, cv2.THRESH_BINARY_INV)
        
        # 適応的二値化
        binary3 = cv2.adaptiveThreshold(gray_top, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)
        
        # 各二値化画像でOCRを実行
        for binary in [binary1, binary2, binary3]:
            try:
                # 複数のOCR設定を試す
                for config in [r'--oem 3 --psm 8', r'--oem 3 --psm 7', r'--oem 3 --psm 11', r'--oem 3 --psm 6']:
                    text = pytesseract.image_to_string(binary, lang='jpn', config=config)
                    # 台番号のパターンを探す
                    # 「1番」「1番台」「台1」「No.1」など
                    patterns = [
                        r'(\d{1,4})\s*番(?:台)?',
                        r'台\s*(\d{1,4})',
                        r'No\.\s*(\d{1,4})',
                        r'№\s*(\d{1,4})',
                        r'^(\d{1,4})$'
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, text, re.MULTILINE)
                        for match in matches:
                            if match.isdigit():
                                num_val = int(match)
                                if 1 <= num_val <= 9999:
                                    results.append(match)
            except:
                continue
        
        # 方法2: オレンジバーを探してその中から台番号を探す
        # HSV色空間に変換
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        # オレンジ色の範囲（HSV）- より広い範囲に調整
        orange_lower = np.array([5, 50, 50])
        orange_upper = np.array([35, 255, 255])
        
        # オレンジ色のマスクを作成
        orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
        
        # オレンジバーのY座標を検出
        orange_y_coords = []
        
        # 画像の上部1/3を検索（オレンジバーは通常上部にある）
        for y in range(height // 3):
            if np.sum(orange_mask[y, :]) > width * 0.2 * 255:  # 閾値を下げる
                orange_y_coords.append(y)
        
        if orange_y_coords:
            # オレンジバーの範囲を特定
            orange_top = min(orange_y_coords)
            orange_bottom = max(orange_y_coords)
            
            # オレンジバー内の画像を切り出し（バー内のみ）
            orange_region = image[orange_top:orange_bottom + 1, :]
        
        # 複数の前処理方法を試す
        results = []
        
        # 方法1: グレースケール + 適応的二値化
        gray_region = cv2.cvtColor(orange_region, cv2.COLOR_RGB2GRAY)
        binary1 = cv2.adaptiveThreshold(gray_region, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)
        
        # 方法2: 白色の抽出（RGB）
        lower_white = np.array([200, 200, 200])
        upper_white = np.array([255, 255, 255])
        white_mask = cv2.inRange(orange_region, lower_white, upper_white)
        
        # 方法3: 固定閾値での二値化
        _, binary3 = cv2.threshold(gray_region, 180, 255, cv2.THRESH_BINARY)
        
        # 各方法でOCRを実行
        configs = [
            r'--oem 3 --psm 8',   # 単一行
            r'--oem 3 --psm 7',   # 単一テキスト行
            r'--oem 3 --psm 13',  # 生のライン
        ]
        
        for binary in [binary1, white_mask, binary3]:
            for config in configs:
                try:
                    text = pytesseract.image_to_string(binary, lang='jpn', config=config)
                    # 数字を探す
                    numbers = re.findall(r'\d+', text)
                    for num in numbers:
                        if 1 <= len(num) <= 4 and num.isdigit():
                            # 妥当な台番号の範囲（1-9999）
                            num_val = int(num)
                            if 1 <= num_val <= 9999:
                                results.append(num)
                except:
                    continue
        
        # 最も頻出する番号を選択
        if results:
            from collections import Counter
            most_common = Counter(results).most_common(1)
            if most_common:
                return f"{most_common[0][0]}番台"
        
        return None
        
    except Exception as e:
        return None

def enhance_image_for_ocr(image):
    """OCR精度向上のための画像前処理"""
    # PILイメージに変換
    if isinstance(image, np.ndarray):
        pil_image = Image.fromarray(image)
    else:
        pil_image = image
    
    # 画像を2倍に拡大（OCR精度向上）
    width, height = pil_image.size
    pil_image = pil_image.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
    
    # コントラスト強調
    enhancer = ImageEnhance.Contrast(pil_image)
    pil_image = enhancer.enhance(1.5)
    
    # シャープネス強調
    enhancer = ImageEnhance.Sharpness(pil_image)
    pil_image = enhancer.enhance(2.0)
    
    # numpy配列に戻す
    enhanced = np.array(pil_image)
    
    # グレースケールに変換
    if len(enhanced.shape) == 3:
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_RGB2GRAY)
    
    # ノイズ除去（メディアンフィルタ）
    enhanced = cv2.medianBlur(enhanced, 3)
    
    # uint8型を確実にする
    enhanced = enhanced.astype(np.uint8)
    
    return enhanced

def extract_site7_data(image):
    """site7の画像からOCRでデータを抽出"""
    try:
        # 処理時間計測用
        ocr_timings = {} if st.session_state.get('show_ocr_debug', False) else None
        start_time = time.time()
        
        # オレンジバーから台番号を抽出（デフォルトでスキップ）
        machine_number = None
        if len(image.shape) == 3 and st.session_state.get('extract_machine_from_orange', False):  # 明示的に有効化した場合のみ
            if ocr_timings is not None:
                orange_start = time.time()
            machine_number = extract_machine_number_from_orange_bar(image)
            if ocr_timings is not None:
                ocr_timings['オレンジバー処理'] = f"{time.time() - orange_start:.2f}秒"
        
        # 画像の高さと幅を取得
        height, width = image.shape[:2] if len(image.shape) >= 2 else (0, 0)
        
        # 抽出したいデータのパターン定義
        data = {
            'machine_number': machine_number,  # オレンジバーから抽出した台番号
            'total_start': None,
            'jackpot_count': None,
            'first_hit_count': None,
            'current_start': None,
            'jackpot_probability': None,
            'max_payout': None,
            # パチスロ用追加フィールド
            'total_games': None,  # 累計ゲーム数
            'bb_count': None,  # BB回数
            'bb_probability': None,  # BB確率
            'rb_count': None,  # RB回数
            'rb_probability': None,  # RB確率
            'art_count': None,  # ART回数
            'composite_probability': None,  # 合成確率
            'ocr_text': "",  # OCRテキストも保存
            'orange_bar_detected': machine_number is not None,  # デバッグ用
            'enhanced_image': None,  # デバッグ用
            'ocr_timings': ocr_timings  # 処理時間情報
        }
        
        # 画像前処理
        if ocr_timings is not None:
            enhance_start = time.time()
        enhanced_image = enhance_image_for_ocr(image)
        if ocr_timings is not None:
            ocr_timings['画像前処理'] = f"{time.time() - enhance_start:.2f}秒"
        
        # OCR実行
        if ocr_timings is not None:
            ocr_start = time.time()
        text = pytesseract.image_to_string(enhanced_image, lang='jpn')
        if ocr_timings is not None:
            ocr_timings['OCR実行'] = f"{time.time() - ocr_start:.2f}秒"
        
        data['ocr_text'] = text  # シンプルに全体OCRテキストのみ保存
        
        if st.session_state.get('show_ocr_debug', False):
            data['enhanced_image'] = enhanced_image
        
        # 台番号がオレンジバーから取得できなかった場合、全体テキストから探す
        if not data['machine_number']:
            machine_patterns = [
                r'【(\d{1,4})番台】',  # 【123番台】形式
                r'(\d{1,4})\s*番台',   # 123番台 形式
                r'(\d{1,4})番\s*台',   # 123番 台 形式（スペースあり）
                r'台番号\s*[:：]?\s*(\d{1,4})',  # 台番号：123 形式
                r'(\d{1,4})台',        # 123台 形式
                r'No\.\s*(\d{1,4})',   # No.123 形式
                r'№\s*(\d{1,4})',     # №123 形式
                r'^(\d{1,4})$',        # 行頭の数字のみ
            ]
        
            for pattern in machine_patterns:
                machine_match = re.search(pattern, text)
                if machine_match:
                    data['machine_number'] = f"{machine_match.group(1)}番台"
                    break
        
        # 見つからない場合は行ごとに探す
        if not data['machine_number']:
            lines = text.split('\n')
            for line in lines:
                if '番台' in line:
                    # 番台を含む行全体を保存
                    cleaned_line = line.strip()
                    if cleaned_line and len(cleaned_line) < 20:  # 短い行のみ（ノイズ除外）
                        data['machine_number'] = cleaned_line
                        break
        
        
        # 数値データの抽出（全体テキストから）
        # OCR結果の後処理（よくある誤認識の補正）
        # 0とO、1とl、8とBなどの置換
        text_corrected = text
        text_corrected = re.sub(r'[Oo０〇](?=\d|\s|$)', '0', text_corrected)  # OやOを0に
        text_corrected = re.sub(r'(?<=\d)[lI](?=\d)', '1', text_corrected)  # lやIを1に
        text_corrected = re.sub(r'(?<=\d)B(?=\d)', '8', text_corrected)  # Bを8に
        
        # 累計スタート
        start_patterns = [
            r'累計スタート\s*(\d{3,4})',
            r'(\d{3,4})\s*スタート',
            r'累計\s*(\d{3,4})',
            r'START\s*(\d{3,4})',
        ]
        for pattern in start_patterns:
            start_match = re.search(pattern, text_corrected)
            if start_match:
                data['total_start'] = start_match.group(1)
                break
        
        # 大当り回数
        jackpot_patterns = [
            r'大当り回数\s*(\d+)\s*回',
            r'(\d+)\s*回\s*大当り',
            r'大当り回数\s*(\d+)',
            r'大当り\s*(\d+)\s*回',
            r'BONUS\s*(\d+)',
        ]
        for pattern in jackpot_patterns:
            jackpot_match = re.search(pattern, text_corrected)
            if jackpot_match:
                data['jackpot_count'] = jackpot_match.group(1)
                break
        
        # 初当り回数
        first_hit_match = re.search(r'初当り回数\s*(\d+)', text)
        if not first_hit_match:
            first_hit_match = re.search(r'(\d+)\s*回.*初当り', text)
        if first_hit_match:
            data['first_hit_count'] = first_hit_match.group(1)
        
        # 現在のスタート
        current_start_match = re.search(r'スタート\s*(\d{2,3})(?!\d)', text)
        if current_start_match:
            data['current_start'] = current_start_match.group(1)
        
        # 大当り確率
        prob_patterns = [
            r'大当り確率\s*1[7/](\d{2,3})',  # "17161"のような誤認識にも対応
            r'大当り確率\s*1/(\d{2,3})',
            r'1/(\d{2,4})',
        ]
        for pattern in prob_patterns:
            prob_match = re.search(pattern, text_corrected)
            if prob_match:
                probability = prob_match.group(1)
                # "7161"のような場合は先頭の"7"を除去して"161"にする
                if len(probability) == 4 and probability.startswith('7'):
                    probability = probability[1:]
                data['jackpot_probability'] = f"1/{probability}"
                break
        
        # 最高出玉
        max_payout_patterns = [
            r'最高出玉\s*(\d{3,5})',
            r'(\d{3,5})\s*最高',
            r'出玉\s*(\d{3,5})'
            # 最後の手段のパターンを削除（誤検出を防ぐため）
        ]
        
        for pattern in max_payout_patterns:
            max_payout_match = re.search(pattern, text)
            if max_payout_match:
                value = int(max_payout_match.group(1))
                # 妥当な範囲の値かチェック（100-99999）
                if 100 <= value <= 99999:
                    data['max_payout'] = str(value)
                    break
        
        # パチスロ用データの抽出（game_typeがパチスロの場合のみ）
        if st.session_state.get('game_type', 'パチンコ') == 'パチスロ':
            # 累計ゲーム数
            game_patterns = [
                r'累計ゲーム\s*(\d{3,5})回',
                r'累計ゲーム\s*(\d{3,5})',
                r'(\d{3,5})\s*ゲーム',
                r'総ゲーム数\s*(\d{3,5})'
            ]
            for pattern in game_patterns:
                game_match = re.search(pattern, text_corrected)
                if game_match:
                    data['total_games'] = game_match.group(1)
                    break
            
            # BB回数とBB確率
            bb_count_patterns = [
                r'BB回数\s*(\d+)回',
                r'BB\s*(\d+)回',
                r'BB回数\s*(\d+)',
                r'ビッグ\s*(\d+)回'
            ]
            for pattern in bb_count_patterns:
                bb_match = re.search(pattern, text_corrected)
                if bb_match:
                    data['bb_count'] = bb_match.group(1)
                    break
            
            bb_prob_patterns = [
                r'BB確率\s*1[/7](\d{2,4})',
                r'BB確率\s*1/(\d{2,4})',
                r'BB\s*1[/7](\d{2,4})'
            ]
            for pattern in bb_prob_patterns:
                bb_prob_match = re.search(pattern, text_corrected)
                if bb_prob_match:
                    prob = bb_prob_match.group(1)
                    if len(prob) == 4 and prob.startswith('7'):
                        prob = prob[1:]
                    data['bb_probability'] = f"1/{prob}"
                    break
            
            # RB回数とRB確率
            rb_count_patterns = [
                r'RB回数\s*(\d+)回',
                r'RB\s*(\d+)回',
                r'RB回数\s*(\d+)',
                r'レギュラー\s*(\d+)回'
            ]
            for pattern in rb_count_patterns:
                rb_match = re.search(pattern, text_corrected)
                if rb_match:
                    data['rb_count'] = rb_match.group(1)
                    break
            
            rb_prob_patterns = [
                r'RB確率\s*1[/7](\d{2,4})',
                r'RB確率\s*1/(\d{2,4})',
                r'RB\s*1[/7](\d{2,4})'
            ]
            for pattern in rb_prob_patterns:
                rb_prob_match = re.search(pattern, text_corrected)
                if rb_prob_match:
                    prob = rb_prob_match.group(1)
                    if len(prob) == 4 and prob.startswith('7'):
                        prob = prob[1:]
                    data['rb_probability'] = f"1/{prob}"
                    break
            
            # ART回数
            art_patterns = [
                r'ART回数\s*(\d+)回',
                r'ART\s*(\d+)回',
                r'AT回数\s*(\d+)回',
                r'AT\s*(\d+)回',
                r'ART回数\s*(\d+)'
            ]
            for pattern in art_patterns:
                art_match = re.search(pattern, text_corrected)
                if art_match:
                    data['art_count'] = art_match.group(1)
                    break
            
            # 合成確率
            composite_patterns = [
                r'合成確率\s*1[/7](\d{2,4})',
                r'合成確率\s*1/(\d{2,4})',
                r'合成\s*1[/7](\d{2,4})'
            ]
            for pattern in composite_patterns:
                comp_match = re.search(pattern, text_corrected)
                if comp_match:
                    prob = comp_match.group(1)
                    if len(prob) == 4 and prob.startswith('7'):
                        prob = prob[1:]
                    data['composite_probability'] = f"1/{prob}"
                    break
        
        # 合計処理時間を記録
        if ocr_timings is not None:
            ocr_timings['合計処理時間'] = f"{time.time() - start_time:.2f}秒"
        
        return data
    except Exception as e:
        st.warning(f"OCRエラー: {str(e)}")
        return None

# ヘルパー関数
def get_unit():
    """現在の遊技種別に応じた単位を返す"""
    return "玉" if st.session_state.get('game_type', 'パチンコ') == 'パチンコ' else "枚"

def get_unit_per_1000yen():
    """現在の遊技種別に応じた1000円あたりの単位数を返す"""
    return 250 if st.session_state.get('game_type', 'パチンコ') == 'パチンコ' else 50

def get_graph_limit():
    """現在の遊技種別に応じたグラフの上下限を返す"""
    return 30000 if st.session_state.get('game_type', 'パチンコ') == 'パチンコ' else 5000


# デフォルト値
default_settings = {
    'search_start_offset': 50,
    'search_end_offset': 500,
    'crop_top': 246,
    'crop_bottom': 280,
    'left_margin': 120,
    'right_margin': 120,
    # グリッドライン調整値
    'grid_30k_offset': 1,       # +30000ライン（最上部）
    'grid_minus_30k_offset': -34, # -30000ライン（最下部）
    'exchange_rate': 3.57145    # 交換レート（円/玉）デフォルトは28玉交換
}

# セッションステートの初期化（エキスパンダーより前に行う）
if 'settings' not in st.session_state:
    st.session_state.settings = default_settings.copy()

if 'saved_presets' not in st.session_state:
    st.session_state.saved_presets = {}
    # デフォルトプリセットを読み込み（存在する場合）
    try:
        import os
        default_preset_path = os.path.join(os.path.dirname(__file__), '..', 'default_presets.json')
        if os.path.exists(default_preset_path):
            with open(default_preset_path, 'r', encoding='utf-8') as f:
                default_data = json.load(f)
                if 'presets' in default_data:
                    st.session_state.saved_presets.update(default_data['presets'])
    except Exception:
        pass
    # データベースから読み込みフラグを設定
    st.session_state.force_reload_presets = True

if 'show_adjustment' not in st.session_state:
    st.session_state.show_adjustment = False

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'current_preset_name' not in st.session_state:
    st.session_state.current_preset_name = 'デフォルト'

if 'uploaded_file_names' not in st.session_state:
    st.session_state.uploaded_file_names = []

# CSV表示項目の設定を初期化
if 'csv_columns' not in st.session_state:
    # デフォルト表示項目
    st.session_state.csv_columns = [
        '台番号',
        '現在値',
        '初当たり球数',
        '初当たり回転数',
        '総獲得球数',
        '回転率①',
        '回転率②',
        '通常回転数'
    ]

# 遊技種別の初期化
if 'game_type' not in st.session_state:
    st.session_state.game_type = 'パチンコ'  # デフォルトはパチンコ


# URLパラメータによる認証バイパスを削除（セキュリティ向上のため）

# パスワード認証
if not st.session_state.authenticated:
    # モダンなログイン画面のスタイル
    st.markdown("""
    <style>
    /* メインコンテナを中央配置 */
    .main > div {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* ログインカード */
    .login-card {
        background: transparent;
        padding: 48px;
        max-width: 400px;
        margin: 0 auto;
        text-align: center;
    }
    
    /* タイトル */
    .login-title {
        font-size: 28px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 8px;
        line-height: 1.2;
    }
    
    /* サブタイトル */
    .login-subtitle {
        font-size: 16px;
        color: #cccccc;
        margin-bottom: 32px;
        line-height: 1.5;
    }
    
    /* フォームスタイル */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        padding: 12px 16px;
        font-size: 16px;
        transition: border-color 0.3s;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        outline: none;
    }
    
    /* ボタンスタイル */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 600;
        transition: transform 0.2s, box-shadow 0.2s;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* エラーメッセージ */
    .stAlert {
        border-radius: 8px;
        margin-top: 16px;
    }
    
    /* フッター */
    .login-footer {
        margin-top: 48px;
        padding-top: 24px;
        border-top: 1px solid #444;
        color: #aaa;
        font-size: 14px;
        line-height: 1.8;
        text-align: center;
    }
    
    .login-footer a {
        color: #8899ff;
        text-decoration: none;
    }
    
    .login-footer a:hover {
        text-decoration: underline;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # スペーサー
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # ログインカード
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="login-card">
            <h1 class="login-title">AI Graph Analysis Report</h1>
            <p class="login-subtitle">Professional Edition - 認証が必要です</p>
        </div>
        """, unsafe_allow_html=True)
        
        # スペース
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ログイン処理を関数化
        def handle_login():
            # グローバルパスワードを取得
            user_password = st._global_passwords['user']
            admin_password = st._global_passwords['admin']
            
            # パスワードチェック
            if st.session_state.password_input == user_password:
                st.session_state.authenticated = True
                st.session_state.is_admin = False
                st.session_state.login_success = True
            elif st.session_state.password_input == admin_password:
                st.session_state.authenticated = True
                st.session_state.is_admin = True
                st.session_state.login_success = True
            else:
                st.session_state.login_error = True
        
        # パスワード入力（Enterキーでログイン可能）
        # ラベルを上に表示
        st.markdown('<p style="margin-bottom: 5px; color: #ffffff;">パスワード</p>', unsafe_allow_html=True)
        password = st.text_input(
            label="password_field",  # 内部用のラベル
            type="password",
            placeholder="パスワードを入力してください",
            label_visibility="collapsed",  # hiddenではなくcollapsedを使用
            key="password_input",
            on_change=handle_login
        )
        
        
        # ログインボタン
        if st.button("ログイン", type="primary", use_container_width=True):
            handle_login()
        
        # ログイン成功時の処理
        if st.session_state.get('login_success', False):
            st.success("✅ ログインしました")
            st.session_state.login_success = False
            time.sleep(0.3)
            st.rerun()
        
        # ログインエラー時の処理
        if st.session_state.get('login_error', False):
            st.error("❌ パスワードが違います")
            st.session_state.login_error = False
        
        # フッター
        st.markdown(f"""
        <div class="login-footer">
            AI Graph Analysis Report v2.4<br>
            更新日: {datetime.now().strftime('%Y/%m/%d')}<br>
            Produced by <a href="https://pp-town.com/" target="_blank">PPタウン</a><br>
            Created by <a href="https://fivenine-design.com" target="_blank">fivenine-design.com</a>
        </div>
        """, unsafe_allow_html=True)
    
    # 認証されていない場合はここで処理を終了
    st.stop()

# SQLiteデータベースの設定
import os

# データベースファイルのパスを設定
# Streamlit Cloudでは書き込み可能な一時ディレクトリを使用
if os.environ.get('STREAMLIT_SHARING_MODE'):
    # Streamlit Cloud環境
    db_path = '/tmp/presets.db'
else:
    # ローカル環境
    db_dir = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir)
        except:
            db_dir = os.path.dirname(__file__)
    db_path = os.path.join(db_dir, 'presets.db')

# データベース接続とテーブル作成
def init_database():
    """データベースを初期化"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # プリセットテーブルを作成
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS presets (
            name TEXT PRIMARY KEY,
            settings TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# データベースを初期化
init_database()

# プリセットを読み込み
def load_presets_from_db():
    """データベースからプリセットを読み込み"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name, settings FROM presets')
        rows = cursor.fetchall()
        conn.close()
        
        presets = {}
        for name, settings_json in rows:
            presets[name] = json.loads(settings_json)
        
        return presets
    except Exception as e:
        st.warning(f"プリセット読み込みエラー: {str(e)}")
        return {}

# セッションステートにプリセットを読み込み
# リロード時も常に最新のプリセットを読み込む
if 'saved_presets' not in st.session_state or st.session_state.get('force_reload_presets', False):
    st.session_state.saved_presets = load_presets_from_db()
    st.session_state.force_reload_presets = False

# プリセットを保存
def save_preset_to_db(name, settings):
    """プリセットをデータベースに保存"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        settings_json = json.dumps(settings)
        
        # UPSERT操作（存在する場合は更新、なければ挿入）
        cursor.execute('''
            INSERT OR REPLACE INTO presets (name, settings, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (name, settings_json))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"プリセットの保存に失敗しました: {str(e)}")
        return False

# プリセットを削除
def delete_preset_from_db(name):
    """プリセットをデータベースから削除"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM presets WHERE name = ?', (name,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"プリセットの削除に失敗しました: {str(e)}")
        return False

# 本番解析セクション
st.markdown("---")
st.markdown("## 🎰 AI Graph Analysis Report")
st.caption("""高精度データ抽出・解析システム - Professional Edition

本システムは、パチンコ・パチスロ台のグラフ画像をAI技術で自動解析する専門ツールです。
OCR技術による台番号・回転数の自動読み取り、画像処理によるグラフデータの精密抽出、
独自アルゴリズムによる統計解析を実現。複数画像の一括処理にも対応し、
解析結果はCSV形式でダウンロード可能。プリセット機能により、
異なる端末や表示形式にも柔軟に対応できる高精度な解析システムです。""")

# 遊技種別選択
st.markdown("### 🎯 遊技種別を選択")
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    game_type = st.radio(
        "遊技種別",
        ["パチンコ", "パチスロ"],
        index=0 if st.session_state.game_type == "パチンコ" else 1,
        key="game_type_selector",
        horizontal=True
    )
    if game_type != st.session_state.game_type:
        st.session_state.game_type = game_type
        # 遊技種別に応じてデフォルト値を変更
        if game_type == "パチンコ":
            st.session_state.settings['exchange_rate'] = 3.57145  # 28玉交換
        else:
            st.session_state.settings['exchange_rate'] = 17.86  # 5.6枚交換
        st.rerun()

with col2:
    # 単位表示
    unit = "玉" if st.session_state.game_type == "パチンコ" else "枚"
    st.info(f"🎲 単位: {unit}")

with col3:
    # 交換レート表示
    rate = st.session_state.settings.get('exchange_rate', 3.57145 if st.session_state.game_type == "パチンコ" else 17.86)
    st.info(f"💱 交換レート: {rate:.2f}円/{unit}")

# 使い方ガイド
show_analysis_help = st.checkbox("📖 解析の使い方を表示", value=False, key="show_analysis_help")
if show_analysis_help:
    st.info("""
    **🎯 解析の流れ**
    
    1️⃣ **画像をアップロード**
    - site7のグラフ画像を選択
    - 複数枚まとめて処理可能
    
    2️⃣ **プリセットを選択**
    - 調整設定で保存したプリセットを選択
    - 初回はデフォルトでOK
    
    3️⃣ **解析開始**
    - 解析ボタンをクリック
    - 自動的に全データを抽出
    
    💡 **ポイント**
    - 端末に合わせたプリセットを使用すると精度が向上します
    - 解析結果はCSVダウンロード可能です
    """)

# STEP 1: ファイルアップロード
st.markdown("### 📤 STEP 1: 解析したいグラフ画像をアップロード")
st.caption("site7のグラフ画像を選択してください（複数可）")

uploaded_files = st.file_uploader(
    "画像を選択",
    type=['jpg', 'jpeg', 'png'],
    accept_multiple_files=True,
    help="複数の画像を一度にアップロードできます（JPG, PNG形式）",
    key="graph_uploader"
)

if uploaded_files:
    # 重複チェック
    seen_names = {}
    unique_files = []
    duplicate_names = []
    
    for file in uploaded_files:
        if file.name not in seen_names:
            seen_names[file.name] = 1
            unique_files.append(file)
        else:
            seen_names[file.name] += 1
            if seen_names[file.name] == 2:  # 初めての重複
                duplicate_names.append(file.name)
    
    # アップロード結果を表示
    duplicate_count = sum(count - 1 for count in seen_names.values() if count > 1)
    if duplicate_count > 0:
        st.success(f"✅ {len(unique_files)}枚の画像がアップロードされました")
        with st.expander(f"ℹ️ {duplicate_count}枚の重複ファイルをスキップしました", expanded=False):
            for name in duplicate_names:
                count = seen_names[name]
                st.caption(f"• {name} ({count}回アップロード、1枚のみ使用)")
    else:
        st.success(f"✅ {len(unique_files)}枚の画像がアップロードされました")
    
    # 以降はunique_filesを使用
    uploaded_files = unique_files
    
    # ファイル名をセッションステートに保存
    st.session_state.uploaded_file_names = [f.name for f in uploaded_files]
    
    # STEP 2: プリセット選択
    st.markdown("### 📋 STEP 2: 解析設定を選択")
    st.caption("保存されたプリセットを選択するか、デフォルト設定を使用します")
    
    # デバッグ情報（一時的）
    if st.checkbox("🐛 デバッグ情報を表示", value=False):
        st.write(f"saved_presets の内容: {st.session_state.saved_presets}")
        st.write(f"データベースパス: {db_path}")
        import os
        st.write(f"データベースファイル存在: {os.path.exists(db_path)}")
        
        # データベースから直接読み込み
        try:
            fresh_presets = load_presets_from_db()
            st.write(f"データベースから直接読み込んだプリセット: {list(fresh_presets.keys())}")
        except Exception as e:
            st.write(f"データベース読み込みエラー: {str(e)}")
    
    # プリセット一覧
    preset_names = ["デフォルト"] + list(st.session_state.saved_presets.keys())
    
    # プリセットボタンを横に並べる（調整セクションと同じスタイル）
    if len(preset_names) <= 4:
        preset_cols = st.columns(len(preset_names))
        for i, preset_name in enumerate(preset_names):
            with preset_cols[i]:
                button_type = "primary" if preset_name == st.session_state.get('current_preset_name', 'デフォルト') else "secondary"
                if st.button(f"📥 {preset_name}", use_container_width=True, key=f"analysis_preset_{preset_name}", type=button_type):
                    if preset_name == "デフォルト":
                        st.session_state.settings = default_settings.copy()
                    else:
                        st.session_state.settings = st.session_state.saved_presets[preset_name].copy()
                        # プリセットに遊技種別情報がある場合は適用
                        if 'game_type' in st.session_state.settings:
                            st.session_state.game_type = st.session_state.settings['game_type']
                    
                    # 現在のプリセット名を保存
                    st.session_state.current_preset_name = preset_name
                    
                    st.success(f"✅ '{preset_name}' の設定を適用しました")
                    time.sleep(0.5)
                    st.rerun()
    else:
        # 5個以上の場合は複数行に分ける
        num_rows = (len(preset_names) + 3) // 4  # 4列で何行必要か
        for row in range(num_rows):
            cols = st.columns(4)
            for col in range(4):
                idx = row * 4 + col
                if idx < len(preset_names):
                    preset_name = preset_names[idx]
                    with cols[col]:
                        button_type = "primary" if preset_name == st.session_state.get('current_preset_name', 'デフォルト') else "secondary"
                        if st.button(f"📥 {preset_name}", use_container_width=True, key=f"analysis_preset_{preset_name}", type=button_type):
                            if preset_name == "デフォルト":
                                st.session_state.settings = default_settings.copy()
                            else:
                                st.session_state.settings = st.session_state.saved_presets[preset_name].copy()
                                # プリセットに遊技種別情報がある場合は適用
                                if 'game_type' in st.session_state.settings:
                                    st.session_state.game_type = st.session_state.settings['game_type']
                            
                            # 現在のプリセット名を保存
                            st.session_state.current_preset_name = preset_name
                            
                            st.success(f"✅ '{preset_name}' の設定を適用しました")
                            time.sleep(0.5)
                            st.rerun()
    
    # 調整設定の案内テキスト
    st.info("⚙️ 詳細な調整設定は、ページ下部の「画像解析の調整設定」セクションにあります。")
    
    # STEP 3: 解析オプションと開始
    st.markdown("### 🚀 STEP 3: 解析オプションと開始")
    
    # 解析オプション
    col_opt1, col_opt2 = st.columns([1, 1])
    with col_opt1:
        skip_ocr = st.checkbox(
            "⚡ OCRをスキップ（高速モード）", 
            value=False,
            help="台番号や累計スタートなどのテキスト情報を読み取らず、グラフ解析のみ実行します。処理が高速になります。"
        )
    with col_opt2:
        show_ocr_debug = st.checkbox(
            "🔍 OCRデバッグ情報を表示", 
            value=False,
            help="OCRで読み取ったテキストを確認できます。台番号が認識されない場合のトラブルシューティングに使用してください。"
        )
    
    
    # 交換レート設定
    unit = get_unit()
    default_rate = 3.57145 if st.session_state.game_type == "パチンコ" else 17.86
    help_text = "1玉あたりの交換レート（円）。28玉交換の場合は3.57145円/玉" if st.session_state.game_type == "パチンコ" else "1枚あたりの交換レート（円）。5.6枚交換の場合は17.86円/枚"
    
    exchange_rate = st.number_input(
        f"💱 交換レート（円/{unit}）",
        min_value=0.1,
        max_value=20.0,
        value=st.session_state.settings.get('exchange_rate', default_rate),
        step=0.01,
        format="%.5f",
        help=help_text
    )
    st.session_state.settings['exchange_rate'] = exchange_rate
    
    st.caption("設定を確認したら、解析ボタンをクリックしてください")
    
    if st.button("🚀 解析を開始", type="primary", use_container_width=True):
        st.session_state.start_analysis = True
        st.session_state.skip_ocr = skip_ocr
        st.session_state.show_ocr_debug = show_ocr_debug
        # データエディタのセッションステートをリセット
        if 'edited_df' in st.session_state:
            del st.session_state.edited_df
        st.rerun()
    
    # プログレスバー（解析中のみ表示）
    if st.session_state.get('start_analysis', False) and uploaded_files:
        progress_bar = st.progress(0)
        status_text = st.empty()
        detail_text = st.empty()
        
        # プログレスバーをセッションステートに保存
        st.session_state.progress_bar = progress_bar
        st.session_state.status_text = status_text
        st.session_state.detail_text = detail_text
        
        st.markdown("---")

# ファイルがアップロードされたことがある場合、解析ボタンを常に表示
elif st.session_state.uploaded_file_names:
    st.info(f"💾 保存されたファイル: {', '.join(st.session_state.uploaded_file_names)}")
    st.warning("⚠️ 設定を変更した後は、画像を再度アップロードしてください")
    
    # クリアボタン
    if st.button("🗑️ ファイル情報をクリア", use_container_width=True):
        st.session_state.uploaded_file_names = []
        st.rerun()

# 解析を実行
if uploaded_files and st.session_state.get('start_analysis', False):
    # 解析結果セクション
    st.markdown("### 🎯 解析結果")
    
    # 現在使用中のプリセットを表示
    current_preset_name = st.session_state.get('current_preset_name', 'デフォルト')
    
    st.info(f"📋 使用プリセット: **{current_preset_name}**")
    
    # 現在の設定値を表示
    with st.expander("🔧 使用中の設定値", expanded=False):
        current_settings = st.session_state.get('settings', default_settings)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**切り抜き設定**")
            st.text(f"上方向: {current_settings.get('crop_top', 246)}px")
            st.text(f"下方向: {current_settings.get('crop_bottom', 247)}px")
            st.text(f"左余白: {current_settings.get('left_margin', 125)}px")
            st.text(f"右余白: {current_settings.get('right_margin', 125)}px")
        
        with col2:
            st.markdown("**検索範囲**")
            st.text(f"開始位置: +{current_settings.get('search_start_offset', 50)}px")
            st.text(f"終了位置: +{current_settings.get('search_end_offset', 500)}px")
        
        with col3:
            st.markdown("**グリッドライン調整**")
            st.text(f"+30k: {current_settings.get('grid_30k_offset', 0):+d}px")
            st.text(f"-30k: {current_settings.get('grid_minus_30k_offset', 0):+d}px")
    
    # セッションステートからプログレスバーを取得（既に上部で作成済み）
    progress_bar = st.session_state.get('progress_bar')
    status_text = st.session_state.get('status_text')
    detail_text = st.session_state.get('detail_text')
    
    # プログレスバーが存在しない場合（通常はない）
    if not progress_bar:
        st.error("プログレスバーの初期化エラー")
        st.stop()
    
    # 初期メッセージを表示
    status_text.text('🚀 解析を開始します...')
    time.sleep(0.5)  # 少し待機してメッセージを見やすくする
    
    # 解析結果を格納
    analysis_results = []
    
    # 各画像を処理
    for idx, uploaded_file in enumerate(uploaded_files):
        # 進捗更新（開始時）
        progress_start = idx / len(uploaded_files)
        progress_bar.progress(progress_start)
        status_text.text(f'処理中... ({idx + 1}/{len(uploaded_files)})')
        detail_text.text(f'📷 {uploaded_file.name} の画像を読み込み中...')
        time.sleep(0.1)  # 視覚的フィードバックのため少し徇機
        
        # 画像を読み込み
        image = Image.open(uploaded_file)
        img_array = np.array(image)
        height, width = img_array.shape[:2]
        
        # OCRでデータ抽出を試みる（スキップ設定を確認）
        if not st.session_state.get('skip_ocr', False):
            detail_text.text(f'🔍 {uploaded_file.name} のOCR解析を実行中...')
            ocr_start_time = time.time()
            ocr_data = extract_site7_data(img_array)
            ocr_end_time = time.time()
            
            # OCR処理時間の詳細表示（デバッグモードの場合）
            if ocr_data and ocr_data.get('ocr_timings'):
                timing_details = " | ".join([f"{k}: {v}" for k, v in ocr_data['ocr_timings'].items()])
                detail_text.text(f'✅ OCR完了 ({timing_details})')
            else:
                detail_text.text(f'✅ OCR完了 ({ocr_end_time - ocr_start_time:.1f}秒)')
        else:
            detail_text.text(f'⚡ {uploaded_file.name} のOCR解析をスキップ（高速モード）')
            ocr_data = None
        
        # Pattern3: Zero Line Based の自動検出
        detail_text.text(f'📐 {uploaded_file.name} のグラフ領域を検出中...')
        time.sleep(0.1)  # 視覚的フィードバック
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
        orange_bottom = 0
        
        # オレンジバーの検出
        for y in range(height//2):
            if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
                orange_bottom = y
        
        # オレンジバーの下端を正確に見つける
        if orange_bottom > 0:
            for y in range(orange_bottom, min(orange_bottom + 100, height)):
                if np.sum(orange_mask[y, :]) < width * 0.1 * 255:
                    orange_bottom = y
                    break
        else:
            orange_bottom = 150
        
        # ゼロライン検出
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 設定値を使用（セッションステートから取得）
        settings = st.session_state.get('settings', default_settings)
        
        # 検索範囲（設定値を使用）
        search_start = orange_bottom + settings['search_start_offset']
        search_end = min(height - 100, orange_bottom + settings['search_end_offset'])
        
        # 切り抜きサイズ（±30000）
        crop_top_offset = settings['crop_top']
        crop_bottom_offset = settings['crop_bottom']
        
        best_score = 0
        zero_line_y = (search_start + search_end) // 2
        
        for y in range(search_start, search_end):
            row = gray[y, 100:width-100]
            darkness = 1.0 - (np.mean(row) / 255.0)
            uniformity = 1.0 - (np.std(row) / 128.0)
            score = darkness * 0.5 + uniformity * 0.5
            
            if score > best_score:
                best_score = score
                zero_line_y = y
        
        # 切り抜き範囲を設定（最終調整値）
        top = max(0, zero_line_y - crop_top_offset)  # 0ラインから上
        bottom = min(height, zero_line_y + crop_bottom_offset)  # 0ラインから下
        left = settings['left_margin']  # 左右の余白
        right = width - settings['right_margin']  # 左右の余白
        
        # 切り抜き実行
        cropped_img = img_array[int(top):int(bottom), int(left):int(right)].copy()
        
        # グリッドラインを追加
        # 切り抜き画像の高さは493px（246+247）
        # 最上部が+30000、最下部が-30000なので、60000の範囲を493pxで表現
        # 1pxあたり約121.7玉
        crop_height = cropped_img.shape[0]
        zero_line_in_crop = zero_line_y - top  # 切り抜き画像内での0ライン位置
        
        # スケール計算（調整されたグリッドラインに基づく）
        # 注意：この変数はグリッドライン描画にのみ使用され、実際の解析には使用されない
        scale = 30000 / 246  # グリッドライン描画用のデフォルト値
        
        # グラフの上下限値を取得
        graph_limit = get_graph_limit()
        
        # グリッドライン描画（設定値を使用）
        # +上限ライン（最上部）
        y_30k = 0 + settings.get('grid_30k_offset', 0)  # 最上部基準
        if 0 <= y_30k < crop_height:
            cv2.line(cropped_img, (0, y_30k), (cropped_img.shape[1], y_30k), (128, 128, 128), 2)
            cv2.putText(cropped_img, f'+{graph_limit}', (10, max(20, y_30k + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)
        
        # -下限ライン（最下部）
        y_minus_30k = crop_height - 1 + settings.get('grid_minus_30k_offset', 0)
        y_minus_30k = min(max(0, y_minus_30k), crop_height - 1)  # 画像範囲内に制限
        cv2.line(cropped_img, (0, y_minus_30k), (cropped_img.shape[1], y_minus_30k), (128, 128, 128), 2)
        cv2.putText(cropped_img, f'-{graph_limit}', (10, max(10, y_minus_30k - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)

        
        # ゼロラインから上下限ラインまでの距離を計算
        distance_to_plus_30k = zero_line_in_crop - y_30k
        distance_to_minus_30k = y_minus_30k - zero_line_in_crop
        
        # 0ライン
        y_0 = int(zero_line_in_crop)  # 調整なし
        if 0 < y_0 < crop_height:
            cv2.line(cropped_img, (0, y_0), (cropped_img.shape[1], y_0), (255, 0, 0), 2)
            cv2.putText(cropped_img, '0', (10, y_0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)
        
        # 元画像にもグリッドラインを追加
        img_with_grid = img_array.copy()
        
        # 元画像での座標に変換（切り抜き前の座標系）
        # +上限ライン（元画像座標）
        y_30k_orig = int(top + y_30k)
        if 0 <= y_30k_orig < height:
            cv2.line(img_with_grid, (0, y_30k_orig), (width, y_30k_orig), (128, 128, 128), 2)
            cv2.putText(img_with_grid, f'+{graph_limit}', (10, max(20, y_30k_orig + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
        
        # -下限ライン（元画像座標）
        y_minus_30k_orig = int(top + y_minus_30k)
        if 0 <= y_minus_30k_orig < height:
            cv2.line(img_with_grid, (0, y_minus_30k_orig), (width, y_minus_30k_orig), (128, 128, 128), 2)
            cv2.putText(img_with_grid, f'-{graph_limit}', (10, max(10, y_minus_30k_orig - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
        
        # 0ライン（元画像座標）
        if 0 <= zero_line_y < height:
            cv2.line(img_with_grid, (0, zero_line_y), (width, zero_line_y), (255, 0, 0), 2)
            cv2.putText(img_with_grid, '0', (10, zero_line_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        
        # 切り抜き範囲を示す枠線を追加（オプション）
        cv2.rectangle(img_with_grid, (int(left), int(top)), (int(right), int(bottom)), (0, 255, 0), 2)

        # 解析を自動実行
        detail_text.text(f'📊 {uploaded_file.name} のグラフデータを解析中...')
        
        # アナライザーを初期化
        analyzer = WebCompatibleAnalyzer()
        
        # グリッドラインなしの画像を使用
        analysis_img = img_array[int(top):int(bottom), int(left):int(right)].copy()
        
        # 0ラインの位置を設定
        analyzer.zero_y = zero_line_in_crop
        # 調整されたグリッドライン位置に基づいてスケールを計算
        crop_height = analysis_img.shape[0]
        
        # 調整された±30,000ライン位置
        y_30k_adjusted = 0 + settings.get('grid_30k_offset', 0)
        y_minus_30k_adjusted = crop_height - 1 + settings.get('grid_minus_30k_offset', 0)
        
        # ゼロラインから調整された±30,000ラインまでの距離
        distance_to_plus_30k_adjusted = zero_line_in_crop - y_30k_adjusted
        distance_to_minus_30k_adjusted = y_minus_30k_adjusted - zero_line_in_crop
        
        # グラフの上下限値を取得
        graph_limit = get_graph_limit()
        
        # 通常の線形スケール計算
        if distance_to_plus_30k_adjusted > 0 and distance_to_minus_30k_adjusted > 0:
            # 上下の平均距離を使用
            avg_distance_adjusted = (distance_to_plus_30k_adjusted + distance_to_minus_30k_adjusted) / 2
            analyzer.scale = graph_limit / avg_distance_adjusted
        else:
            # フォールバック（調整前の値を使用）
            distance_to_top = zero_line_in_crop
            distance_to_bottom = crop_height - zero_line_in_crop
            avg_distance = (distance_to_top + distance_to_bottom) / 2
            analyzer.scale = graph_limit / avg_distance
        
        # グラフデータを抽出
        graph_data_points, dominant_color, _, graph_info = analyzer.extract_graph_data(analysis_img)
        
        # デバッグ情報を無効化（必要に応じて有効化可能）
        # if uploaded_file.name in ["IMG_0165.PNG", "IMG_0174.PNG", "IMG_0177.PNG"]:
        #     st.write(f"🔍 デバッグ情報 - {uploaded_file.name}")
        #     st.write(f"- ゼロライン位置（切り抜き内）: {zero_line_in_crop}px")
        #     st.write(f"- 切り抜き画像の高さ: {crop_height}px")
        #     st.write(f"- 調整された+30000ライン位置: {y_30k_adjusted}px (オフセット: {settings.get('grid_30k_offset', 0)})")
        #     st.write(f"- 調整された-30000ライン位置: {y_minus_30k_adjusted}px (オフセット: {settings.get('grid_minus_30k_offset', 0)})")
        #     st.write(f"- ゼロから+30000までの距離: {distance_to_plus_30k_adjusted}px")
        #     st.write(f"- ゼロから-30000までの距離: {distance_to_minus_30k_adjusted}px")
        #     st.write(f"- スケール: {analyzer.scale:.2f} 玉/ピクセル")
        #     st.write(f"- 検出された色: {dominant_color}")
        #     st.write(f"- データポイント数: {len(graph_data_points) if graph_data_points else 0}")
        #     if graph_data_points:
        #         sample_points = graph_data_points[::100][:10]  # 10点をサンプル表示
        #         st.write("- サンプルデータ (x, 値):")
        #         for x, val in sample_points:
        #             y_pixel = zero_line_in_crop - (val / analyzer.scale)
        #             st.write(f"  X={int(x)}, 値={int(val)}玉, Y座標={int(y_pixel)}px")

        if graph_data_points:
            # データポイントから値のみを抽出
            graph_values = [value for x, value in graph_data_points]
            # 補正前の値を保存
            graph_values_original = graph_values.copy()

            # 統計情報を計算
            max_val_original = max(graph_values)
            min_val_original = min(graph_values)
            current_val_original = graph_values[-1] if graph_values else 0
            
            # インデックスを保存
            max_idx = graph_values.index(max_val_original)
            min_idx = graph_values.index(min_val_original)
            
            # 補正係数の計算
            correction_factor = settings.get('correction_factor', 1.0)
            
            # 補正を適用
            if correction_factor != 1.0:
                max_val = max_val_original * correction_factor
                min_val = min_val_original * correction_factor
                current_val = current_val_original * correction_factor
                # グラフ値も更新（初当たり検出用）
                graph_values = [v * correction_factor for v in graph_values]
            else:
                max_val = max_val_original
                min_val = min_val_original
                current_val = current_val_original

            # グラフの上下限値でクリップ
            graph_limit = get_graph_limit()
            
            # 最大値が上限を超える場合は上限にクリップ
            if max_val > graph_limit:
                max_val = graph_limit
            
            # 最小値が下限を下回る場合は下限にクリップ
            if min_val < -graph_limit:
                min_val = -graph_limit

            # MAXがマイナスの場合は0を表示
            if max_val < 0:
                max_val = 0

            # 初当たり値を探す（production版と同じロジック）
            first_hit_val = 0
            first_hit_x = None
            min_payout = 100 if st.session_state.get('game_type', 'パチンコ') == 'パチンコ' else 20  # 最低払い出し単位数
            
            # 初当たり検出デバッグ情報
            first_hit_debug_info = {
                'detected_position': None,
                'detected_value': None,
                'detection_method': None,
                'candidates': []
            }

            # 方法1: 閾値以上の急激な増加を検出
            for i in range(1, min(len(graph_values)-2, 150)):  # 最大150点まで探索
                current_increase = graph_values[i+1] - graph_values[i]

                # 閾値以上の増加を検出
                if current_increase > min_payout:
                    # 候補として記録
                    if graph_values[i] < 0:
                        first_hit_debug_info['candidates'].append({
                            'position': i,
                            'value': graph_values[i],
                            'increase': current_increase,
                            'next_point': graph_values[i+1] if i+1 < len(graph_values) else None,
                            'reason': f'{current_increase:.0f}玉の上昇検出'
                        })
                    # 次の点も上昇または維持していることを確認（ノイズ除外）
                    noise_threshold = 50 if st.session_state.game_type == 'パチンコ' else 10
                    if graph_values[i+2] >= graph_values[i+1] - noise_threshold:
                        # 初当たりは必ずマイナス値から
                        if graph_values[i] < 0:
                            # 補正なしで純粋な検出位置を使用
                            first_hit_val = graph_values[i]
                            first_hit_x = i
                            first_hit_debug_info['detection_method'] = '方法1: 急激な増加検出'
                            first_hit_debug_info['candidates'].append({
                                'position': i,
                                'value': graph_values[i],
                                'increase': current_increase,
                                'reason': f'{current_increase:.0f}玉の急上昇'
                            })
                            break

            # 方法2: 減少傾向からの急上昇を検出
            if first_hit_x is None:
                window_size = 5
                for i in range(window_size, len(graph_values)-1):
                    # 過去の傾向を計算
                    past_window = graph_values[max(0, i-window_size):i]
                    if len(past_window) >= 2:
                        avg_slope = (past_window[-1] - past_window[0]) / len(past_window)

                        # 現在の変化
                        current_change = graph_values[i+1] - graph_values[i]

                        # 減少傾向からの急上昇
                        if avg_slope <= 0 and current_change > min_payout:
                            noise_threshold = 50 if st.session_state.game_type == 'パチンコ' else 10
                            if i + 2 < len(graph_values) and graph_values[i+2] > graph_values[i+1] - noise_threshold:
                                # 初当たりは必ずマイナス値
                                if graph_values[i] < 0:
                                    # 補正なしで純粋な検出位置を使用
                                    first_hit_val = graph_values[i]
                                    first_hit_x = i
                                    first_hit_debug_info['detection_method'] = '方法2: 減少傾向からの急上昇'
                                    first_hit_debug_info['candidates'].append({
                                        'position': i,
                                        'value': graph_values[i],
                                        'slope': avg_slope,
                                        'increase': current_change,
                                        'reason': f'傾き{avg_slope:.1f}から{current_change:.0f}玉上昇'
                                    })
                                    break

            # 初当たり値がプラスの場合は0を表示
            if first_hit_val > 0:
                first_hit_val = 0
            
            # デバッグ情報に最終結果を設定
            first_hit_debug_info['detected_position'] = first_hit_x
            first_hit_debug_info['detected_value'] = first_hit_val if first_hit_x is not None else None
            
            # スケール情報を追加（1pxあたりの回転数と玉数）
            if 'analyzer' in locals() and hasattr(analyzer, 'scale'):
                first_hit_debug_info['scale_info'] = {
                    'balls_per_pixel': analyzer.scale,
                    'spins_per_pixel': None  # 後で計算
                }
            else:
                first_hit_debug_info['scale_info'] = {
                    'balls_per_pixel': None,
                    'spins_per_pixel': None
                }
            
            # 初当たりまでの使用球数を計算
            first_hit_used_balls = 0
            if first_hit_x is not None and first_hit_val < 0:
                # 初当たりまでの最低値（最も球を使った時点）を探す
                min_val_before_first = 0
                # 初当たり位置を少し広げて探索（検出誤差を考慮）
                search_end = min(first_hit_x + 5, len(graph_values) - 1)
                for i in range(search_end + 1):
                    if graph_values[i] < min_val_before_first:
                        min_val_before_first = graph_values[i]
                # 使用球数は最低値の絶対値
                first_hit_used_balls = abs(min_val_before_first)

            # 総獲得球数の計算（大当り時の増加分の合計）
            # 補正後の値（graph_values）を使用
            total_jackpot_balls = 0
            jackpot_count = 0  # 大当り回数をカウント
            jackpot_details = []  # 各大当りの詳細情報
            # 遊技種別に応じた閾値
            increase_threshold = 100 if st.session_state.game_type == 'パチンコ' else 20  # パチスロは20枚以上
            
            i = 0
            while i < len(graph_values) - 1:
                # 急激な増加を検出
                increase = graph_values[i+1] - graph_values[i]
                if increase >= increase_threshold:
                    # 大当りの開始点
                    start_val = graph_values[i]
                    start_idx = i
                    # 大当りの終了点を探す（最大値まで継続）
                    j = i + 1
                    max_val_in_jackpot = graph_values[j]
                    
                    while j < len(graph_values) - 1:
                        if graph_values[j+1] > max_val_in_jackpot:
                            max_val_in_jackpot = graph_values[j+1]
                            j += 1
                        elif graph_values[j+1] < graph_values[j] - (50 if st.session_state.game_type == 'パチンコ' else 10):  # 下降で大当り終了（パチスロは10枚）
                            break
                        else:
                            j += 1
                    
                    # この大当りでの獲得球数（開始点から最大値まで）
                    jackpot_balls = max_val_in_jackpot - start_val
                    if jackpot_balls > 0:
                        total_jackpot_balls += jackpot_balls
                        jackpot_count += 1
                        jackpot_details.append({
                            'number': jackpot_count,
                            'start_idx': start_idx,
                            'end_idx': j,
                            'balls': jackpot_balls,
                            'start_val': start_val,
                            'peak_val': max_val_in_jackpot
                        })
                    
                    # 次の検出開始点を更新
                    i = j
                else:
                    i += 1
            
            # 平均獲得球数を計算
            avg_jackpot_balls = total_jackpot_balls / jackpot_count if jackpot_count > 0 else 0

            # オーバーレイ画像を作成
            overlay_img = cropped_img.copy()

            # 検出されたグラフラインを描画
            prev_x = None
            prev_y = None

            # 緑色で統一（見やすさ重視）
            draw_color = (0, 255, 0)  # 緑色固定

            # グラフポイントを描画
            for x, value in graph_data_points:
                # Y座標を計算（線形スケール）
                y = int(zero_line_in_crop - (value / analyzer.scale))

                # 画像範囲内かチェック
                if y is not None and 0 <= y < overlay_img.shape[0] and 0 <= x < overlay_img.shape[1]:
                    # 点を描画（より見やすくするため）
                    cv2.circle(overlay_img, (int(x), y), 2, draw_color, -1)

                    # 線で接続
                    if prev_x is not None and prev_y is not None:
                        cv2.line(overlay_img, (int(prev_x), int(prev_y)), (int(x), y), draw_color, 2)

                    prev_x = x
                    prev_y = y

            # 最高値、最低値、初当たりの位置を見つける
            # インデックスは既に上で取得済み

            # Y座標計算用の関数（線形スケール）
            def calculate_y_from_value(val):
                return int(zero_line_in_crop - (val / analyzer.scale))
            
            # 横線を描画（最低値、最高値、現在値、初当たり値）
            # 最高値ライン（端から端まで）
            max_y = calculate_y_from_value(max_val)
            if 0 <= max_y < overlay_img.shape[0]:
                # 端から端まで線を引く
                cv2.line(overlay_img, (0, max_y), (overlay_img.shape[1], max_y), (0, 255, 255), 2)
                # 最高値の点に大きめの円を描画
                max_x = graph_data_points[max_idx][0]
                cv2.circle(overlay_img, (int(max_x), max_y), 8, (0, 255, 255), -1)
                cv2.circle(overlay_img, (int(max_x), max_y), 10, (0, 200, 200), 2)
                # 背景付きテキスト（白背景、濃い黄色文字）右端に表示
                text = f'MAX: {int(max_val):,}'
                text_width = 140
                text_y = max_y if max_y > 20 else max_y + 20  # 上端で見切れないように調整
                cv2.rectangle(overlay_img, (overlay_img.shape[1] - text_width - 15, text_y - 15), 
                             (overlay_img.shape[1] - 10, text_y + 5), (255, 255, 255), -1)
                cv2.putText(overlay_img, text, (overlay_img.shape[1] - text_width - 10, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 150), 1, cv2.LINE_AA)

            # 最低値ライン（端から端まで）
            min_y = calculate_y_from_value(min_val)
            if 0 <= min_y < overlay_img.shape[0]:
                # 端から端まで線を引く
                cv2.line(overlay_img, (0, min_y), (overlay_img.shape[1], min_y), (255, 0, 255), 2)
                # 最低値の点に大きめの円を描画
                min_x = graph_data_points[min_idx][0]
                cv2.circle(overlay_img, (int(min_x), min_y), 8, (255, 0, 255), -1)
                cv2.circle(overlay_img, (int(min_x), min_y), 10, (200, 0, 200), 2)
                # 背景付きテキスト（白背景、濃いマゼンタ文字）右端に表示
                text = f'MIN: {int(min_val):,}'
                text_width = 140
                text_y = min_y if (min_y > 20 and min_y < overlay_img.shape[0] - 20) else (20 if min_y <= 20 else overlay_img.shape[0] - 20)
                cv2.rectangle(overlay_img, (overlay_img.shape[1] - text_width - 15, text_y - 15), 
                             (overlay_img.shape[1] - 10, text_y + 5), (255, 255, 255), -1)
                cv2.putText(overlay_img, text, (overlay_img.shape[1] - text_width - 10, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 0, 150), 1, cv2.LINE_AA)

            # 現在値ライン（端から端まで）
            current_y = calculate_y_from_value(current_val)
            if 0 <= current_y < overlay_img.shape[0]:
                cv2.line(overlay_img, (0, current_y), (overlay_img.shape[1], current_y), (255, 255, 0), 2)
                # 現在値の点に大きめの円を描画（グラフ上）
                if len(graph_data_points) > 0:
                    current_x = graph_data_points[-1][0]  # 最後のデータポイントのX座標
                    cv2.circle(overlay_img, (int(current_x), current_y), 8, (255, 255, 0), -1)
                    cv2.circle(overlay_img, (int(current_x), current_y), 10, (200, 200, 0), 2)
                # 背景付きテキスト（白背景、濃いシアン文字）右端に表示
                text = f'CURRENT: {int(current_val):,}'
                text_width = 160
                text_y = current_y - 10 if current_y > 30 else current_y + 15
                cv2.rectangle(overlay_img, (overlay_img.shape[1] - text_width - 15, text_y - 15), 
                             (overlay_img.shape[1] - 10, text_y + 5), (255, 255, 255), -1)
                cv2.putText(overlay_img, text, (overlay_img.shape[1] - text_width - 10, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 0), 1, cv2.LINE_AA)

            # 初当たり値ライン（端から端まで）
            if first_hit_x is not None and first_hit_val != 0:  # 初当たりがある場合
                first_hit_y = calculate_y_from_value(first_hit_val)
                if 0 <= first_hit_y < overlay_img.shape[0]:
                    # 端から端まで線を引く
                    cv2.line(overlay_img, (0, first_hit_y), (overlay_img.shape[1], first_hit_y), (155, 48, 255), 2)
                    # 初当たりの点に大きめの円を描画
                    first_hit_graph_x = graph_data_points[first_hit_x][0]
                    cv2.circle(overlay_img, (int(first_hit_graph_x), first_hit_y), 8, (155, 48, 255), -1)
                    cv2.circle(overlay_img, (int(first_hit_graph_x), first_hit_y), 10, (120, 30, 200), 2)
                    # 背景付きテキスト（白背景、紫文字）右端に表示
                    text = f'FIRST HIT: {int(first_hit_val):,}'
                    text_width = 150
                    text_y = first_hit_y if (first_hit_y > 20 and first_hit_y < overlay_img.shape[0] - 20) else (20 if first_hit_y <= 20 else overlay_img.shape[0] - 20)
                    cv2.rectangle(overlay_img, (overlay_img.shape[1] - text_width - 15, text_y - 15), 
                                 (overlay_img.shape[1] - 10, text_y + 5), (255, 255, 255), -1)
                    cv2.putText(overlay_img, text, (overlay_img.shape[1] - text_width - 10, text_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 0, 150), 1, cv2.LINE_AA)
            
            # グラフの開始点と現在地のマーカーを追加（ゼロライン上）
            if graph_info and len(graph_data_points) > 0:
                # ゼロラインのY座標
                zero_y = zero_line_in_crop
                
                # 開始点（緑の点）- ゼロライン上
                if graph_info.get('start_x') is not None:
                    start_x = graph_info['start_x']
                    cv2.circle(overlay_img, (int(start_x), zero_y), 10, (0, 255, 0), -1)
                    cv2.circle(overlay_img, (int(start_x), zero_y), 12, (0, 200, 0), 2)
                    # ラベル
                    cv2.putText(overlay_img, 'START', (int(start_x) - 20, zero_y - 15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 0), 1, cv2.LINE_AA)
                

            # 結果を保存
            # 回転率計算（OCRデータがある場合のみ）
            rotation_metrics = None
            if ocr_data and ocr_data.get('total_start') and not st.session_state.get('skip_ocr', False):
                # グラフの実効幅（左右マージンを除外）
                graph_width = right - left
                # analyze_values形式のデータを作成
                analysis_data = {
                    'max_value': int(max_val),
                    'max_index': max_idx,
                    'min_value': int(min_val),
                    'min_index': min_idx,
                    'first_hit_index': first_hit_x if first_hit_x is not None else -1,
                    'first_hit_value': int(first_hit_val) if first_hit_x is not None else 0,
                    'final_value': int(current_val)
                }
                rotation_metrics = analyzer.calculate_rotation_metrics(
                    graph_data_points, 
                    analysis_data, 
                    ocr_data['total_start'],
                    graph_width,
                    graph_info,
                    ocr_data,  # OCRデータを追加
                    st.session_state.get('game_type', 'パチンコ')  # 遊技種別を追加
                )
                # スケール情報を更新
                if rotation_metrics and 'spins_per_pixel' in rotation_metrics:
                    first_hit_debug_info['scale_info']['spins_per_pixel'] = rotation_metrics['spins_per_pixel']
                # グラフ情報も追加
                first_hit_debug_info['graph_info'] = {
                    'graph_width': graph_width,
                    'total_spins': int(ocr_data['total_start']) if ocr_data.get('total_start') else None,
                    'graph_start_x': graph_info.get('start_x') if graph_info else None,
                    'graph_end_x': graph_info.get('end_x') if graph_info else None
                }
            
            analysis_results.append({
                'name': uploaded_file.name,
                'original_image': img_with_grid,  # グリッド付き元画像を保存
                'cropped_image': cropped_img,  # 切り抜き画像
                'overlay_image': overlay_img,  # オーバーレイ画像
                'success': True,
                'max_val': int(max_val),
                'min_val': int(min_val),
                'current_val': int(current_val),
                'first_hit_val': int(first_hit_val) if first_hit_x is not None else None,
                'first_hit_used_balls': int(first_hit_used_balls),  # 初当たりまでの使用球数
                'total_jackpot_balls': int(total_jackpot_balls),  # 総獲得球数を追加
                'jackpot_count': jackpot_count,  # 大当り回数（グラフから検出）
                'avg_jackpot_balls': int(avg_jackpot_balls),  # 平均獲得球数
                'jackpot_details': jackpot_details,  # 各大当りの詳細
                'dominant_color': dominant_color,
                'ocr_data': ocr_data,  # OCRデータを追加
                'ocr_text': ocr_data.get('ocr_text') if ocr_data else None,  # OCRテキストを追加
                'correction_factor': correction_factor,  # 補正係数を追加
                'rotation_metrics': rotation_metrics,  # 回転率データを追加
                'first_hit_debug': first_hit_debug_info  # 初当たり検出デバッグ情報を追加
            })
        else:
            # 解析失敗時
            analysis_results.append({
                'name': uploaded_file.name,
                'original_image': img_with_grid,  # グリッド付き元画像を保存
                'cropped_image': cropped_img,
                'overlay_image': cropped_img,  # 解析失敗時は切り抜き画像を使用
                'success': False,
                'ocr_data': ocr_data  # OCRデータを追加
            })
        
        # 各画像の処理完了時に進捗を更新
        progress_end = (idx + 1) / len(uploaded_files)
        progress_bar.progress(progress_end)
    
    # プログレスバーを完了
    progress_bar.progress(1.0)
    status_text.text('✅ 全ての画像の処理が完了しました！')
    detail_text.empty()
    time.sleep(1.0)  # 完了メッセージを表示する時間
    
    # 結果を保存
    st.session_state.analysis_results = analysis_results
    
    # Reset analysis state
    st.session_state.start_analysis = False
    st.rerun()

    # 使い方
    with st.expander("💡 使い方"):
        st.markdown("""
            1. **「Browse files」ボタン**をクリック
            2. **グラフ画像を選択**（複数選択可）
            3. **自動的に切り抜きと解析が実行されます**
            
            対応フォーマット:
            - JPG/JPEG
            - PNG
            """)

# 機能紹介
st.markdown("---")
st.markdown("### 🚀 主な機能")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("#### 📈 AIグラフ解析")
    st.markdown("AIがグラフを自動認識し、正確なデータを抽出")
with col2:
    st.markdown("#### ✂️ 自動切り抜き")
    st.markdown("グラフ領域を自動検出して最適化")
with col3:
    st.markdown("#### 💡 統計分析")
    st.markdown("最高値、最低値、初当たり等を瞬時に計算")

# 操作マニュアル
st.markdown("---")
st.markdown("### 📖 操作マニュアル")
with st.expander("使い方と注意事項を確認する"):
    st.markdown("""
    #### 🎯 本ツールについて
    このツールは **[site7](https://m.site777.jp/)のグラフデータ専用** の解析ツールです。  
    それ以外のサイトのグラフには対応していません。
    
    #### 📋 使い方
    1. **画像をアップロード**
       - 「Browse files」ボタンをクリック
       - site7のグラフ画像を選択（複数選択可）
       - 対応形式：JPG/JPEG、PNG
    
    2. **自動解析**
       - アップロード後、自動的に解析が開始されます
       - グラフの0ラインを検出し、適切な範囲で切り抜きます
       - グラフデータを抽出し、統計情報を計算します
    
    3. **結果の確認**
       - 解析結果は2列で表示されます（モバイルでは1列）
       - 各結果には以下が含まれます：
         - 解析済みグラフ画像（緑色のライン）
         - 統計情報（最高値、最低値、現在値、初当たり）
         - 元画像（折りたたみ可能）
    
    #### ⚠️ 注意事項
    - **site7専用**：他のサイトのグラフは正しく解析できません
    - **画像品質**：鮮明な画像ほど精度が向上します
    - **グラフ全体**：グラフの上下が切れていない画像を使用してください
    - **初当たり検出**：マイナス値からの100玉以上の急上昇を検出します
    
    #### 🔧 技術仕様
    - 0ライン基準：上246px、下280px（±30,000玉相当）
    - スケール：約120玉/ピクセル
    - 左右余白：120px除外
    
    #### 🆕 回転率計算機能
    - **回転率①**：初当たりまでの1000円あたり回転数
    - **回転率②**：通常時全体の1000円あたり回転数
    - OCRで読み取った累計スタートを使用して精密計算
    - 初当たりが検出されない場合は回転率①は表示されません
    """)

# 解析結果を表示
if 'analysis_results' in st.session_state and st.session_state.analysis_results:
    analysis_results = st.session_state.analysis_results
    
    # 結果をグリッド表示
    st.markdown("### 📊 解析結果一覧")

    # 解析結果を3列で表示（行ごとに処理）
    for row_idx in range(0, len(analysis_results), 3):
        cols = st.columns(3)
        
        # 各行の3つの結果を処理
        for col_idx in range(3):
            idx = row_idx + col_idx
            if idx < len(analysis_results):
                result = analysis_results[idx]
                
                with cols[col_idx]:
                    # 台番号を表示、なければファイル名を表示
                    if result.get('ocr_data') and result['ocr_data'].get('machine_number'):
                        display_name = result['ocr_data']['machine_number']
                    else:
                        # OCRで台番号が取得できなかった場合はファイル名をそのまま表示
                        display_name = result['name']
                    st.markdown(f"#### {idx + 1}. {display_name}")

                    # 解析結果画像
                    st.image(result['overlay_image'], use_column_width=True)

                    # 元画像を折りたたみ可能に
                    with st.expander("📷 元画像を表示"):
                        st.image(result['original_image'], use_column_width=True)

                    # 成功時は統計情報を表示（解析結果の下に縦に並べる）
                    if result['success']:
                        # 統計情報をカード風に表示
                        st.markdown("""
                <style>
                .stat-card {
                    background-color: #f0f2f6;
                    padding: 15px;
                    border-radius: 10px;
                    margin-top: 10px;
                }
                .stat-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 5px 0;
                    border-bottom: 1px solid #e0e0e0;
                }
                .stat-item:last-child {
                    border-bottom: none;
                }
                .stat-label {
                    color: #666;
                    font-weight: 500;
                }
                .stat-value {
                    font-weight: bold;
                    color: #333;
                }
                .stat-value.positive {
                    color: #28a745;
                }
                .stat-value.negative {
                    color: #dc3545;
                }
                .stat-value.zero {
                    color: #6c757d;
                }
                </style>
                """, unsafe_allow_html=True)

                    # 値に応じて色分けするためのクラスを決定
                    def get_value_class(val):
                        if val > 0:
                            return "positive"
                        elif val < 0:
                            return "negative"
                        else:
                            return "zero"

                    unit = get_unit()
                    first_hit_text = f"{result['first_hit_val']:,}{unit}" if result['first_hit_val'] is not None else "なし"
                    first_hit_class = get_value_class(result['first_hit_val']) if result['first_hit_val'] is not None else ""

                    # 補正係数の表示を準備（非表示にする）
                    correction_info = ""
                    
                    # 回転率データの準備（パチンコのみ）
                    rotation_html = ""
                    rotation_detail = ""
                    if result.get('rotation_metrics') and st.session_state.game_type == 'パチンコ':
                        metrics = result['rotation_metrics']
                        if metrics.get('rotation_rate_1', 0) >= 0:
                            if metrics['rotation_rate_1'] > 0:
                                # 異常値チェック（現実的な範囲: 10-35回/千円）
                                warning = " ⚠️" if metrics['rotation_rate_1'] < 10 or metrics['rotation_rate_1'] > 35 else ""
                                rotation_html += f'<div class="stat-item"><span class="stat-label">📊 回転率①</span><span class="stat-value positive">{metrics["rotation_rate_1"]:.1f}回/千円{warning}</span></div>'
                            else:
                                rotation_html += f'<div class="stat-item"><span class="stat-label">📊 回転率①</span><span class="stat-value">-</span></div>'
                            # デバッグ情報（初当たりまで）
                            rotation_detail += f'<div style="font-size: 0.8em; color: #666; margin-left: 20px;">→ 初当たりまで: {metrics["first_hit_spins"]}回転 ÷ {metrics["first_hit_balls"]}{unit}使用</div>'
                            
                        # 回転率②は常に表示（0の場合も含む）
                        if metrics.get('rotation_rate_2', 0) >= 0:
                            if metrics['rotation_rate_2'] > 0:
                                # 異常値チェック（現実的な範囲: 10-30回/千円）
                                warning = " ⚠️" if metrics['rotation_rate_2'] < 10 or metrics['rotation_rate_2'] > 30 else ""
                                rotation_html += f'<div class="stat-item"><span class="stat-label">📊 回転率②</span><span class="stat-value positive">{metrics["rotation_rate_2"]:.1f}回/千円{warning}</span></div>'
                            else:
                                rotation_html += f'<div class="stat-item"><span class="stat-label">📊 回転率②</span><span class="stat-value">-</span></div>'
                            # デバッグ情報（通常時）
                            rotation_detail += f'<div style="font-size: 0.8em; color: #666; margin-left: 20px;">→ 通常時: {metrics["normal_decline_spins"]}回転 ÷ {metrics["normal_decline_balls"]}{unit}使用</div>'
                    
                    # 初当たり関連のHTMLを条件分岐で生成
                    first_hit_html = ""
                    if st.session_state.game_type == 'パチンコ':
                        first_hit_spins = (result.get('rotation_metrics') or {}).get('first_hit_spins', 0) if result.get('first_hit_val') is not None else 0
                        first_hit_html = f'<div class="stat-item"><span class="stat-label">🎰 初当たり{unit}数</span><span class="stat-value {first_hit_class}">{first_hit_text}</span></div>'
                        first_hit_html += f'<div class="stat-item"><span class="stat-label">🎲 初当たり回転数</span><span class="stat-value">{first_hit_spins}回</span></div>'
                    
                    # 大当り回数の計算
                    if st.session_state.game_type == 'パチンコ':
                        jackpot_count = (result.get('ocr_data') or {}).get('first_hit_count') or result.get('jackpot_count') or 0
                        jackpot_label = "初当たり回数"
                    else:
                        ocr_data = result.get('ocr_data') or {}
                        bb_count = int(ocr_data.get('bb_count') or 0)
                        rb_count = int(ocr_data.get('rb_count') or 0)
                        jackpot_count = bb_count + rb_count if (bb_count or rb_count) else result.get('jackpot_count') or 0
                        jackpot_label = "大当り回数"
                    
                    # HTMLコンテンツを組み立て
                    html_content = f"""
                    <div class="stat-card">
                        <div class="stat-item">
                            <span class="stat-label">🎯 現在値</span>
                            <span class="stat-value {get_value_class(result['current_val'])}">{result['current_val']:,}{unit}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">📈 最高値</span>
                            <span class="stat-value {get_value_class(result['max_val'])}">{result['max_val']:,}{unit}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">📉 最低値</span>
                            <span class="stat-value {get_value_class(result['min_val'])}">{result['min_val']:,}{unit}</span>
                        </div>
                        """
                    
                    # パチンコの場合のみ初当たり情報を追加
                    if st.session_state.game_type == 'パチンコ':
                        html_content += first_hit_html
                    
                    # 残りの統計情報を追加
                    html_content += f'<div class="stat-item"><span class="stat-label">🎯 {jackpot_label}</span><span class="stat-value positive">{jackpot_count}回</span></div>'
                    html_content += f'<div class="stat-item"><span class="stat-label">💰 総獲得{unit}数</span><span class="stat-value positive">{result.get("total_jackpot_balls", 0):,}{unit}</span></div>'
                    
                    # 回転率データを追加
                    if rotation_html:
                        html_content += rotation_html
                    if rotation_detail:
                        html_content += rotation_detail
                    if correction_info:
                        html_content += correction_info
                    
                    # stat-cardを閉じる
                    html_content += '</div>'
                    
                    st.markdown(html_content, unsafe_allow_html=True)

                    # OCRデータがある場合は表示（すべてNoneでも構造は表示）
                    if result.get('ocr_data') is not None:
                        ocr = result['ocr_data']
                        st.markdown("""
                        <style>
                        .ocr-card {
                            background-color: #e8f4f8;
                            padding: 15px;
                            border-radius: 10px;
                            margin-top: 10px;
                            border: 1px solid #bee5eb;
                        }
                        .ocr-title {
                            color: #17a2b8;
                            font-weight: bold;
                            margin-bottom: 10px;
                        }
                        .ocr-item {
                            display: flex;
                            justify-content: space-between;
                            padding: 5px 0;
                            border-bottom: 1px solid #d1ecf1;
                        }
                        .ocr-item:last-child {
                            border-bottom: none;
                        }
                        .ocr-label {
                            color: #0c5460;
                            font-weight: 500;
                        }
                        .ocr-value {
                            font-weight: bold;
                            color: #0c5460;
                        }
                        </style>
                        """, unsafe_allow_html=True)

                        ocr_html = '<div class="ocr-card"><div class="ocr-title">📱 site7データ</div>'

                        # 台番号（デバッグ情報付き）
                        if ocr.get('machine_number'):
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">🔢 台番号</span><span class="ocr-value">{ocr["machine_number"]}</span></div>'
                        else:
                            # 台番号が取得できない場合
                            ocr_html += '<div class="ocr-item"><span class="ocr-label">🔢 台番号</span><span class="ocr-value" style="color: #999;">未検出</span></div>'

                        # 遊技データ
                        if ocr.get('total_start'):
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">🎲 累計スタート</span><span class="ocr-value">{ocr["total_start"]}</span></div>'
                        if ocr.get('jackpot_count'):
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">🎊 大当り回数</span><span class="ocr-value">{ocr["jackpot_count"]}回</span></div>'
                        if ocr.get('first_hit_count'):
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">🎯 初当り回数</span><span class="ocr-value">{ocr["first_hit_count"]}回</span></div>'
                        if ocr.get('current_start'):
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">📊 スタート</span><span class="ocr-value">{ocr["current_start"]}</span></div>'
                        if ocr.get('jackpot_probability'):
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">📈 大当り確率</span><span class="ocr-value">{ocr["jackpot_probability"]}</span></div>'
                        if ocr.get('max_payout'):
                            unit_label = "玉" if st.session_state.game_type == 'パチンコ' else "枚"
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">💰 最高出{unit_label}</span><span class="ocr-value">{ocr["max_payout"]}{unit_label}</span></div>'
                        
                        # パチスロ特有のデータ表示
                        if st.session_state.game_type == 'パチスロ':
                            if ocr.get('total_games'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">🎮 累計ゲーム</span><span class="ocr-value">{ocr["total_games"]}回</span></div>'
                            if ocr.get('bb_count'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">🅱️ BB回数</span><span class="ocr-value">{ocr["bb_count"]}回</span></div>'
                            if ocr.get('bb_probability'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">📊 BB確率</span><span class="ocr-value">{ocr["bb_probability"]}</span></div>'
                            if ocr.get('rb_count'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">🆁 RB回数</span><span class="ocr-value">{ocr["rb_count"]}回</span></div>'
                            if ocr.get('rb_probability'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">📊 RB確率</span><span class="ocr-value">{ocr["rb_probability"]}</span></div>'
                            if ocr.get('art_count'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">🎯 ART回数</span><span class="ocr-value">{ocr["art_count"]}回</span></div>'
                            if ocr.get('composite_probability'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">📈 合成確率</span><span class="ocr-value">{ocr["composite_probability"]}</span></div>'

                        # すべてのOCRデータがNoneの場合
                        basic_fields = [ocr.get('machine_number'), ocr.get('total_start'), ocr.get('jackpot_count'), 
                                       ocr.get('first_hit_count'), ocr.get('current_start'), ocr.get('jackpot_probability'), 
                                       ocr.get('max_payout')]
                        slot_fields = [ocr.get('total_games'), ocr.get('bb_count'), ocr.get('bb_probability'),
                                      ocr.get('rb_count'), ocr.get('rb_probability'), ocr.get('art_count'),
                                      ocr.get('composite_probability')] if st.session_state.game_type == 'パチスロ' else []
                        if not any(basic_fields + slot_fields):
                            ocr_html += '<div class="ocr-item"><span style="color: #856404;">⚠️ OCRデータを取得できませんでした</span></div>'

                        ocr_html += '</div>'
                        st.markdown(ocr_html, unsafe_allow_html=True)
                        
                        # OCRデバッグ情報を表示
                        if st.session_state.get('show_ocr_debug', False) and result.get('ocr_data'):
                            with st.expander("🔍 OCRデバッグ情報"):
                                # OCRテキスト結果
                                if result['ocr_data'].get('ocr_text'):
                                    st.markdown("#### OCRで読み取ったテキスト")
                                    st.text_area("OCR結果", result['ocr_data']['ocr_text'], height=200, disabled=True)
                                
                                # 抽出されたデータ
                                st.markdown("#### 抽出されたデータ")
                                ocr_debug_data = {
                                    '台番号': result['ocr_data'].get('machine_number', '未検出'),
                                    '累計スタート': result['ocr_data'].get('total_start', '未検出'),
                                    '大当り回数': result['ocr_data'].get('jackpot_count', '未検出'),
                                    '初当り回数': result['ocr_data'].get('first_hit_count', '未検出'),
                                    '現在スタート': result['ocr_data'].get('current_start', '未検出'),
                                    '大当り確率': result['ocr_data'].get('jackpot_probability', '未検出'),
                                    '最高出玉': result['ocr_data'].get('max_payout', '未検出')
                                }
                                for key, value in ocr_debug_data.items():
                                    st.write(f"- **{key}**: {value}")
                                
                                # 処理時間情報を表示
                                if result['ocr_data'].get('ocr_timings'):
                                    st.markdown("#### ⏱️ 処理時間")
                                    timing_data = result['ocr_data']['ocr_timings']
                                    for key, value in timing_data.items():
                                        st.write(f"- **{key}**: {value}")
                        
                        # 初当たり検出デバッグ情報を表示
                        if result.get('first_hit_debug'):
                            with st.expander("🔍 初当たり検出デバッグ情報"):
                                debug_info = result['first_hit_debug']
                                
                                # site7データと同じスタイル
                                st.markdown("""
                                <style>
                                .debug-card {
                                    background-color: #e8f4f8;
                                    padding: 15px;
                                    border-radius: 10px;
                                    margin-top: 10px;
                                    border: 1px solid #bee5eb;
                                }
                                .debug-title {
                                    color: #17a2b8;
                                    font-weight: bold;
                                    margin-bottom: 10px;
                                }
                                .debug-item {
                                    display: flex;
                                    justify-content: space-between;
                                    padding: 5px 0;
                                    border-bottom: 1px solid #d1ecf1;
                                }
                                .debug-item:last-child {
                                    border-bottom: none;
                                }
                                .debug-label {
                                    color: #0c5460;
                                    font-weight: 500;
                                }
                                .debug-value {
                                    font-weight: bold;
                                    color: #0c5460;
                                }
                                </style>
                                """, unsafe_allow_html=True)
                                
                                # 検出結果
                                debug_html = '<div class="debug-card"><div class="debug-title">🎯 検出結果</div>'
                                
                                if debug_info['detected_position'] is not None:
                                    debug_html += f'<div class="debug-item"><span class="debug-label">📍 検出位置</span><span class="debug-value">{debug_info["detected_position"]}点目</span></div>'
                                    debug_html += f'<div class="debug-item"><span class="debug-label">💰 検出値</span><span class="debug-value">{debug_info["detected_value"]:,.0f}玉</span></div>'
                                else:
                                    debug_html += '<div class="debug-item"><span class="debug-label">📍 検出位置</span><span class="debug-value" style="color: #999;">未検出</span></div>'
                                    debug_html += '<div class="debug-item"><span class="debug-label">💰 検出値</span><span class="debug-value" style="color: #999;">-</span></div>'
                                
                                debug_html += f'<div class="debug-item"><span class="debug-label">🔍 検出方法</span><span class="debug-value">{debug_info["detection_method"] or "なし"}</span></div>'
                                debug_html += f'<div class="debug-item"><span class="debug-label">📋 候補数</span><span class="debug-value">{len(debug_info["candidates"])}件</span></div>'
                                debug_html += '</div>'
                                
                                st.markdown(debug_html, unsafe_allow_html=True)
                                
                                # スケール情報を表示
                                if 'scale_info' in debug_info:
                                    scale_html = '<div class="debug-card"><div class="debug-title">📏 スケール情報（1pxあたりの数値）</div>'
                                    
                                    balls_per_px = debug_info['scale_info'].get('balls_per_pixel')
                                    spins_per_px = debug_info['scale_info'].get('spins_per_pixel')
                                    
                                    if balls_per_px:
                                        scale_html += f'<div class="debug-item"><span class="debug-label">🎱 玉数/px</span><span class="debug-value">{balls_per_px:.4f}玉</span></div>'
                                    else:
                                        scale_html += '<div class="debug-item"><span class="debug-label">🎱 玉数/px</span><span class="debug-value" style="color: #999;">未計算</span></div>'
                                    
                                    if spins_per_px:
                                        scale_html += f'<div class="debug-item"><span class="debug-label">🎯 回転数/px</span><span class="debug-value">{spins_per_px:.4f}回</span></div>'
                                    else:
                                        scale_html += '<div class="debug-item"><span class="debug-label">🎯 回転数/px</span><span class="debug-value" style="color: #999;">未計算</span></div>'
                                    
                                    scale_html += '</div>'
                                    st.markdown(scale_html, unsafe_allow_html=True)
                                    
                                    # グラフ情報も表示
                                    if 'graph_info' in debug_info:
                                        graph_info = debug_info['graph_info']
                                        graph_html = '<div class="debug-card"><div class="debug-title">📊 グラフ情報</div>'
                                        
                                        graph_html += f'<div class="debug-item"><span class="debug-label">📐 グラフ幅</span><span class="debug-value">{graph_info.get("graph_width", 0)}px</span></div>'
                                        graph_html += f'<div class="debug-item"><span class="debug-label">🎰 総回転数</span><span class="debug-value">{graph_info.get("total_spins", 0):,}回</span></div>'
                                        graph_html += f'<div class="debug-item"><span class="debug-label">▶️ 開始X座標</span><span class="debug-value">{graph_info.get("graph_start_x", 0)}px</span></div>'
                                        graph_html += f'<div class="debug-item"><span class="debug-label">⏸️ 終了X座標</span><span class="debug-value">{graph_info.get("graph_end_x", 0)}px</span></div>'
                                        
                                        graph_html += '</div>'
                                        st.markdown(graph_html, unsafe_allow_html=True)
                                
                                if debug_info['candidates']:
                                    candidates_html = '<div class="debug-card"><div class="debug-title">🔍 検出候補一覧</div>'
                                    
                                    for idx, candidate in enumerate(debug_info['candidates']):
                                        candidates_html += f'<div style="margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #d1ecf1;"><div style="font-weight: bold; color: #17a2b8; margin-bottom: 5px;">候補{idx+1}</div>'
                                        candidates_html += f'<div class="debug-item"><span class="debug-label">📍 位置</span><span class="debug-value">{candidate["position"]}点目</span></div>'
                                        candidates_html += f'<div class="debug-item"><span class="debug-label">💰 検出値</span><span class="debug-value">{candidate["value"]:,.0f}玉</span></div>'
                                        candidates_html += f'<div class="debug-item"><span class="debug-label">📈 上昇量</span><span class="debug-value">{candidate.get("increase", 0):,.0f}玉</span></div>'
                                        if 'slope' in candidate:
                                            candidates_html += f'<div class="debug-item"><span class="debug-label">📊 傾き</span><span class="debug-value">{candidate["slope"]:.1f}</span></div>'
                                        candidates_html += f'<div class="debug-item"><span class="debug-label">💡 検出理由</span><span class="debug-value">{candidate["reason"]}</span></div>'
                                        candidates_html += '</div>'
                                    
                                    candidates_html += '</div>'
                                    st.markdown(candidates_html, unsafe_allow_html=True)

                    else:
                        st.warning("⚠️ グラフデータを検出できませんでした")

                    # 区切り線（各列内で）
                    if idx < len(analysis_results) - 3:
                        st.markdown("---")

    # サマリー情報
    st.markdown("### 📋 解析サマリー")

    success_count = sum(1 for r in analysis_results if r['success'])
    st.info(f"📈 総画像数: {len(analysis_results)}枚 | ✅ 成功: {success_count}枚 | ⚠️ 失敗: {len(analysis_results) - success_count}枚")


    # 結果を表形式で表示
    st.markdown("### 📊 解析結果（表形式）")

    # 統計情報を計算して表示
    if analysis_results:
        success_results = [r for r in analysis_results if r.get('success')]
        if success_results:
            # 統計情報の計算
            total_balance = sum(r['current_val'] for r in success_results)
            exchange_rate = st.session_state.settings.get('exchange_rate', 3.57145)
            total_balance_yen = int(total_balance * exchange_rate)
            avg_balance = total_balance / len(success_results)
            avg_balance_yen = int(avg_balance * exchange_rate)
            max_result = max(success_results, key=lambda x: x['current_val'])
            min_result = min(success_results, key=lambda x: x['current_val'])
            
            # 1日の総獲得球数を計算
            total_day_jackpot_balls = sum(r.get('total_jackpot_balls', 0) for r in success_results)
            
            # パチスロの場合はBB+RBの合計、パチンコは従来通り
            if st.session_state.game_type == 'パチスロ':
                total_day_jackpot_count = sum(
                    int((r.get('ocr_data') or {}).get('bb_count') or 0) + 
                    int((r.get('ocr_data') or {}).get('rb_count') or 0)
                    if (r.get('ocr_data') or {}).get('bb_count') or (r.get('ocr_data') or {}).get('rb_count')
                    else r.get('jackpot_count', 0)
                    for r in success_results
                )
            else:
                total_day_jackpot_count = sum(r.get('jackpot_count', 0) for r in success_results)
            
            avg_day_jackpot_balls = total_day_jackpot_balls / total_day_jackpot_count if total_day_jackpot_count > 0 else 0
            
            # 総投資球数を計算（各台の最低値の絶対値の合計）
            total_investment = sum(abs(min(r['min_val'], 0)) for r in success_results)
            
            # 実質収支 = 総獲得球数 - 総投資球数
            net_balance = total_day_jackpot_balls - total_investment
            net_balance_yen = int(net_balance * exchange_rate)

            # 統計情報を2列で表示（見やすさ重視）
            st.markdown("#### 📊 収支サマリー")
            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "🎯 現在の合計収支",
                    f"{total_balance_yen:+,}円",
                    f"{total_balance:+,}{get_unit()}",
                    delta_color="normal"
                )

            with col2:
                st.metric(
                    "📊 台平均収支",
                    f"{avg_balance_yen:+,.0f}円",
                    f"{avg_balance:+,.0f}{get_unit()}",
                    delta_color="normal"
                )
            
            # 大当り情報を別セクションに
            st.markdown("#### 🎰 大当り分析")
            col5, col6, col7 = st.columns(3)
            
            with col5:
                st.metric(
                    "総大当り回数",
                    f"{total_day_jackpot_count}回",
                    f"{len(success_results)}台合計"
                )
            
            with col6:
                unit = get_unit()
                label = "総獲得球数" if st.session_state.game_type == "パチンコ" else "総獲得枚数"
                st.metric(
                    label,
                    f"{total_day_jackpot_balls:,}{unit}",
                    f"平均{avg_day_jackpot_balls:,.0f}{unit}/回"
                )
            
            with col7:
                st.metric(
                    "獲得金額換算",
                    f"{int(total_day_jackpot_balls * exchange_rate):,}円",
                    f"@{exchange_rate:.3f}円/{get_unit()}"
                )

        # データフレームを作成
        df_data = []
        for result in analysis_results:
            if result['success']:
                # 台番号の決定（OCRスキップ時はファイル名を使用）
                if st.session_state.get('skip_ocr', False):
                    machine_number = result['name']
                else:
                    machine_number = result.get('ocr_data', {}).get('machine_number', result['name'])
                
                row = {
                    '画像名': result['name'],  # 画像名を追加
                    '台番号': machine_number,
                    '最高値': result['max_val'],
                    '最低値': result['min_val'],
                    '現在値': result['current_val'],
                    '初当たり球数': result['first_hit_val'] if result['first_hit_val'] is not None else None,
                    '初当たり回転数': (result.get('rotation_metrics') or {}).get('first_hit_spins', 0) if result.get('first_hit_val') is not None else 0,
                    '収支（円）': int(result['current_val'] * st.session_state.settings.get('exchange_rate', 3.57145)),
                    '総獲得球数': result.get('total_jackpot_balls', 0),
                    '大当り回数（グラフ）': result.get('jackpot_count', 0),  # 列名を変更
                    '色': result['dominant_color']
                }
                
                # 回転率データを追加（利用可能な場合）
                if result.get('rotation_metrics'):
                    metrics = result['rotation_metrics']
                    if metrics['rotation_rate_1'] > 0:
                        # 異常値に絵文字を追加（現実的な範囲: 10-35回/千円）
                        rate1_str = f"{metrics['rotation_rate_1']:.1f}"
                        if metrics['rotation_rate_1'] < 10 or metrics['rotation_rate_1'] > 35:
                            rate1_str += " ⚠️"  # 異常値警告
                        row['回転率①'] = rate1_str
                    else:
                        row['回転率①'] = '-'
                    
                    if metrics['rotation_rate_2'] > 0:
                        # 異常値に絵文字を追加（現実的な範囲: 10-30回/千円）
                        rate2_str = f"{metrics['rotation_rate_2']:.1f}"
                        if metrics['rotation_rate_2'] < 10 or metrics['rotation_rate_2'] > 30:
                            rate2_str += " ⚠️"  # 異常値警告
                        row['回転率②'] = rate2_str
                    else:
                        row['回転率②'] = '-'
                        
                    # 詳細データ
                    row['初当り使用玉'] = metrics['first_hit_balls'] if metrics['first_hit_balls'] > 0 else '-'
                    
                    # 通常回転数を追加
                    if 'normal_decline_spins' in metrics:
                        row['通常回転数'] = metrics['normal_decline_spins'] if metrics['normal_decline_spins'] > 0 else 0
                    else:
                        row['通常回転数'] = 0
                # OCRデータを追加（OCRスキップモードでない場合のみ）
                if not st.session_state.get('skip_ocr', False) and result.get('ocr_data'):
                    ocr = result['ocr_data']
                    row.update({
                        '累計スタート': ocr.get('total_start', ''),
                        '大当り回数（OCR）': ocr.get('jackpot_count', ''),  # 列名を変更
                        '初当り回数': ocr.get('first_hit_count', ''),
                        '現在スタート': ocr.get('current_start', ''),
                        '大当り確率': ocr.get('jackpot_probability', ''),
                        '最高出玉': ocr.get('max_payout', '')
                    })
                    # パチスロ用データを追加
                    if st.session_state.game_type == 'パチスロ':
                        row.update({
                            '累計ゲーム': ocr.get('total_games', ''),
                            'BB回数': ocr.get('bb_count', ''),
                            'BB確率': ocr.get('bb_probability', ''),
                            'RB回数': ocr.get('rb_count', ''),
                            'RB確率': ocr.get('rb_probability', ''),
                            'ART回数': ocr.get('art_count', ''),
                            '合成確率': ocr.get('composite_probability', ''),
                            'BB+RB回数': int(ocr.get('bb_count') or 0) + int(ocr.get('rb_count') or 0) if (ocr.get('bb_count') or ocr.get('rb_count')) else ''
                        })
                df_data.append(row)
            else:
                # 解析失敗時も台番号の決定方法を統一
                if st.session_state.get('skip_ocr', False):
                    machine_number = result['name']
                else:
                    machine_number = result.get('ocr_data', {}).get('machine_number', result['name'])
                    
                df_data.append({
                    '画像名': result['name'],  # 画像名を追加
                    '台番号': machine_number,
                    '最高値': '解析失敗',
                    '最低値': '-',
                    '現在値': '-',
                    '初当たり球数': None,
                    '収支（円）': '-',
                    '色': '-'
                })

        if df_data:
            # 全データを含むDataFrameを作成
            df_full = pd.DataFrame(df_data)
            
            # 選択された列のみを抽出
            # csv_columnsに存在する列のみを選択
            selected_cols = [col for col in st.session_state.csv_columns if col in df_full.columns]
            df = df_full[selected_cols].copy()
            
            # データエディタで編集可能にする
            st.markdown("#### 📝 データ編集")
            st.info("""
            💡 表内のセルをクリックして直接編集できます。
            
            **自動計算される項目：**
            - 現在値を変更 → 収支（円）が自動更新
            - 初当たり球数・回転数を変更 → 回転率①が自動更新
            - 編集後は下のボタンでダウンロードしてください。
            """)
            
            # セッションステートにデータフレームを保存（初回のみ）
            if 'edited_df' not in st.session_state:
                st.session_state.edited_df = df.copy()
            
            edited_df = st.data_editor(
                st.session_state.edited_df,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",  # 行の追加・削除を許可
                key="data_editor",
                column_config={
                    "台番号": st.column_config.TextColumn(
                        "台番号",
                        help="台番号を入力",
                        required=True
                    ),
                    "最高値": st.column_config.NumberColumn(
                        "最高値",
                        help="最高値（玉数）",
                        format="%d玉"
                    ),
                    "最低値": st.column_config.NumberColumn(
                        "最低値", 
                        help="最低値（玉数）",
                        format="%d玉"
                    ),
                    "現在値": st.column_config.NumberColumn(
                        "現在値",
                        help="現在値（玉数）", 
                        format="%d玉"
                    ),
                    "初当たり球数": st.column_config.NumberColumn(
                        "初当たり球数",
                        help="初当たり時の玉数",
                        format="%d玉"
                    ),
                    "初当たり回転数": st.column_config.NumberColumn(
                        "初当たり回転数",
                        help="初当たりまでの回転数",
                        format="%d回"
                    ),
                    "収支（円）": st.column_config.NumberColumn(
                        "収支（円）",
                        help="現在値×4円",
                        format="¥%d"
                    ),
                    "総獲得球数": st.column_config.NumberColumn(
                        "総獲得球数",
                        help="大当りで獲得した総球数",
                        format="%d玉"
                    ),
                    "大当り回数": st.column_config.NumberColumn(
                        "大当り回数",
                        help="大当りの回数",
                        format="%d回"
                    ),
                    "回転率①": st.column_config.TextColumn(
                        "回転率①",
                        help="初当たりまでの回転率"
                    ),
                    "回転率②": st.column_config.TextColumn(
                        "回転率②",
                        help="通常時全体の回転率"
                    ),
                    "通常回転数": st.column_config.NumberColumn(
                        "通常回転数",
                        help="大当たり中を除いた通常時の総回転数",
                        format="%d回"
                    )
                }
            )
            
            # データが編集された場合、自動計算を実行
            if edited_df is not None and not edited_df.equals(st.session_state.edited_df):
                # 現在の交換レートを取得
                exchange_rate = st.session_state.settings.get('exchange_rate', 3.57145)
                
                # 各行について自動計算
                for idx in range(len(edited_df)):
                    # 収支（円）を現在値から自動計算
                    if pd.notna(edited_df.at[idx, '現在値']):
                        edited_df.at[idx, '収支（円）'] = int(edited_df.at[idx, '現在値'] * exchange_rate)
                    
                    # 回転率①を自動計算
                    if pd.notna(edited_df.at[idx, '初当たり回転数']) and pd.notna(edited_df.at[idx, '初当たり球数']):
                        spins = edited_df.at[idx, '初当たり回転数']
                        balls = abs(edited_df.at[idx, '初当たり球数'])  # 絶対値を使用
                        if balls > 0:
                            rate1 = round((spins / balls) * 250, 1)
                            edited_df.at[idx, '回転率①'] = f"{rate1:.1f}"
                        else:
                            edited_df.at[idx, '回転率①'] = '-'
                
                # セッションステートを更新
                st.session_state.edited_df = edited_df.copy()
                # 画面を再描画
                st.rerun()

            # 編集されたデータでCSVダウンロードボタン
            col1, col2 = st.columns([1, 4])
            with col1:
                csv = edited_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 編集済みCSVダウンロード",
                    data=csv,
                    file_name=f'pachinko_analysis_edited_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                    mime='text/csv',
                    type="primary"
                )
            
            # 回転率の詳細情報を表示
            with st.expander("📊 回転率計算の詳細"):
                st.markdown("""
                ### 回転率の計算方法
                
                **回転率①（初当たりまで）**
                - 初当たりまでの回転数 ÷ (使用玉数 ÷ 250)
                - 初当たりまでの1000円あたりの回転数
                - 朝一から初当たりを引くまでの釘の状態を反映
                
                **回転率②（通常時全体）**
                - 通常時の総回転数 ÷ (総消費玉数 ÷ 250)
                - 累計スタート数から大当たり中の回転数を除いて計算
                - 全体を通しての釘の状態を反映
                
                ※ 1000円 = 250玉として計算
                ※ 回転率②は最低値（最大投資額）を基準に計算
                """)
            
            # データ出力フォーム（簡易版）
            st.markdown("---")
            st.markdown("### 📝 データ出力")
            st.caption("pachikeisan.x0.com用のフォーマットで一括出力します")
            
            # 一括データ出力（常に表示）
            # 今日の日付を取得
            today = datetime.now().strftime("%-m/%-d")  # 例: 7/7
            
            # データ収集用のリスト
            output_lines = [today]  # 日付を最初に追加
            
            # 各解析結果に対してデータを収集（自動処理）
            for idx, row in edited_df.iterrows():
                # 台番号を取得
                machine_number = str(row.get('台番号', ''))
                if machine_number == '' or machine_number == row.get('画像名', '') or machine_number == 'None' or machine_number == '未検出':
                    # 画像名から拡張子を除去して台番号とする
                    image_name = row.get('画像名', f'台{idx + 1}')
                    machine_number = image_name.rsplit('.', 1)[0]
                
                # 初当たり回転数
                first_hit_spins = int(row.get('初当たり回転数', 0))
                
                # 初当たり玉数（絶対値）
                first_hit_balls_value = row.get('初当たり球数', 0)
                if first_hit_balls_value is None or first_hit_balls_value == 'なし':
                    first_hit_balls = 0
                else:
                    try:
                        first_hit_balls = abs(int(first_hit_balls_value))
                    except (ValueError, TypeError):
                        first_hit_balls = 0
                
                # 回転率①
                rotation_rate_1 = row.get('回転率①', '-')
                if rotation_rate_1 != '-':
                    if isinstance(rotation_rate_1, str):
                        rotation_rate_1 = rotation_rate_1.replace('回/千円', '').replace(' ⚠️', '')
                    else:
                        rotation_rate_1 = str(rotation_rate_1)
                else:
                    rotation_rate_1 = '0'
                
                # 通常回転数（rotation_metricsから取得）
                normal_spins = 0
                if st.session_state.analysis_results:
                    for result in st.session_state.analysis_results:
                        if result['name'] == row.get('画像名'):
                            if result.get('rotation_metrics'):
                                normal_spins = result['rotation_metrics'].get('normal_decline_spins', 0)
                            break
                
                # 総獲得球数
                total_win = int(row.get('総獲得球数', 0))
                
                # 現在値
                current_value = int(row.get('現在値', 0))
                
                # 回転率②
                rotation_rate_2 = row.get('回転率②', '-')
                if rotation_rate_2 != '-':
                    if isinstance(rotation_rate_2, str):
                        rotation_rate_2 = rotation_rate_2.replace('回/千円', '').replace(' ⚠️', '')
                    else:
                        rotation_rate_2 = str(rotation_rate_2)
                else:
                    rotation_rate_2 = '0'
                
                # 1行目: (初) 台番#初当たり回転数#初当たり玉数(回転率①)
                line1 = f"(初){machine_number}#{first_hit_spins}#{first_hit_balls}({rotation_rate_1})"
                output_lines.append(line1)
                
                # 2行目: (全) 台番#通常回転数#獲得数#現在値(回転率②)
                line2 = f"(全){machine_number}#{normal_spins}#{total_win}#{current_value}({rotation_rate_2})"
                output_lines.append(line2)
            
            # 全データ出力
            all_data = "\n".join(output_lines)
            st.text_area("コピー用データ", value=all_data, height=300)
            
            # 出力フォーマット説明
            st.info("""
            📌 **出力フォーマット**
            - 1行目: 日付
            - 以降、1台につき2行で出力
            - (初)台番#初当たり回転数#初当たり玉数(回転率①)
            - (全)台番#通常回転数#獲得数#現在値(回転率②)
            """)
            
            # 調整設定の案内
            st.markdown("---")
            st.info("""
            💡 **出力結果が期待と異なる場合は？**
            
            端末や画面サイズによってグラフの表示が異なるため、調整設定が必要な場合があります。
            ページ下部の「⚙️ 画像解析の調整設定」から、お使いの端末に合わせた設定を保存してください。
            """)

# CSV表示項目の設定セクション
with st.expander("📊 CSV表示項目の設定", expanded=False):
    st.markdown("##### CSVデータテーブルに表示する項目を選択")
    st.caption("チェックを外した項目は表示されません。表が横に長くなりすぎる場合は不要な項目を非表示にできます。")
    
    # 全項目リスト（単位を動的に変更）
    unit = get_unit()
    all_columns = [
        '画像名', '台番号', '最高値', '最低値', '現在値',
        f'初当たり{unit}数', '初当たり回転数', '収支（円）',
        f'総獲得{unit}数', '大当り回数（グラフ）', '色', '回転率①', '回転率②',
        '通常回転数', f'初当り使用{unit}',
        '累計スタート', '大当り回数（OCR）', '初当り回数',
        '現在スタート', '大当り確率', f'最高出{unit}'
    ]
    
    # パチスロ用の追加カラム
    if st.session_state.game_type == 'パチスロ':
        all_columns.extend([
            '累計ゲーム', 'BB回数', 'BB確率', 'RB回数', 'RB確率',
            'ART回数', '合成確率', 'BB+RB回数'
        ])
    
    # デフォルト表示項目
    default_columns = [
        '台番号', '現在値', f'初当たり{unit}数', '初当たり回転数',
        f'総獲得{unit}数', '回転率①', '回転率②', '通常回転数'
    ]
    
    # 初期化時にデフォルト値を設定
    if 'csv_columns' not in st.session_state or len(st.session_state.csv_columns) == 0:
        st.session_state.csv_columns = default_columns.copy()
    
    # 項目を3列で表示
    col_count = 3
    cols = st.columns(col_count)
    
    # 選択された項目を一時的に保存
    selected_columns = []
    
    for i, column in enumerate(all_columns):
        col_idx = i % col_count
        with cols[col_idx]:
            # デフォルトでチェックされているかどうか
            is_checked = column in st.session_state.csv_columns
            # インデックスを含むユニークなキーを生成
            if st.checkbox(column, value=is_checked, key=f"csv_col_{i}_{column}"):
                selected_columns.append(column)
    
    # ボタンで操作
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    
    with btn_col1:
        if st.button("デフォルトに戻す", use_container_width=True):
            st.session_state.csv_columns = default_columns.copy()
            st.success("デフォルト設定に戻しました")
            st.rerun()
    
    with btn_col2:
        if st.button("全て選択", use_container_width=True):
            st.session_state.csv_columns = all_columns.copy()
            st.success("全項目を選択しました")
            st.rerun()
    
    with btn_col3:
        if st.button("選択を適用", type="primary", use_container_width=True):
            st.session_state.csv_columns = selected_columns
            st.success(f"{len(selected_columns)}個の項目を選択しました")
            st.rerun()

# 調整機能（コラプス）
# アンカー用のHTMLを追加
st.markdown('<div id="adjustment-settings"></div>', unsafe_allow_html=True)

# スクロール処理
if st.session_state.get('scroll_to_adjustment', False):
    st.markdown("""
    <script>
    // ページ読み込み後にスクロール
    window.addEventListener('load', function() {
        setTimeout(function() {
            var element = document.getElementById('adjustment-settings');
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 500);
    });
    </script>
    """, unsafe_allow_html=True)
    st.session_state.scroll_to_adjustment = False

with st.expander("⚙️ 画像解析の調整設定", expanded=st.session_state.show_adjustment):
    st.markdown("##### 端末ごとの調整設定")
    st.caption("※ お使いの端末で撮影した画像に合わせて調整してください")
    
    # 初心者向けの使い方説明
    show_help = st.checkbox("📖 調整機能の使い方を表示", value=False, key="show_adjustment_help")
    if show_help:
        st.info("""
        **🎯 調整機能とは？**  
        site7のグラフは端末（iPhone/Android）や画面サイズによって表示が異なります。
        この機能で**お使いの端末に最適な設定**を保存できます。
        
        **📝 使い方（3ステップ）**
        
        1️⃣ **テスト画像を準備**
        - 実際の最大値がわかるグラフ画像を用意
        - 例：パチンコ「最大値が+15,000玉」、パチスロ「最大値が+2,500枚」とわかっている画像
        
        2️⃣ **自動調整を実行**
        - 画像をアップロード → 実際の最大値を入力
        - 「🔧 推奨値を自動適用」ボタンをクリック
        - 必要に応じて手動で微調整
        
        3️⃣ **設定を保存**
        - プリセット名を入力（例：iPhone15用）
        - 「💾 保存」ボタンをクリック
        
        💡 **ポイント**
        - 複数枚の画像で調整するとより正確になります
        - 一度設定すれば、次回から選ぶだけでOK
        - 端末を変えたら新しいプリセットを作成
        """)
        st.divider()
    
    # STEP 1: テスト画像のアップロード
    st.markdown("### 📸 STEP 1: テスト用画像をアップロード")
    st.caption("実際の最大値がわかるグラフ画像を用意してください")
    
    # サンプル画像の表示
    show_sample = st.checkbox("📷 調整例を表示", value=False, key="show_adjustment_sample")
    if show_sample:
        st.info("""
        **調整用画像の例**
        
        ✅ **良い例**
        - 実際の最大値が確認できる画像
        - 例：店舗の実機でパチンコ「最大+15,000玉」、パチスロ「最大+2,500枚」と確認した画像
        - グラフが明確に写っている画像
        
        ❌ **悪い例**
        - 最大値が不明な画像
        - グラフが不鮮明な画像
        - 画面が暗い・ぼやけている画像
        
        💡 **ヒント**
        - 複数枚使用するとより正確になります
        - 異なる最大値の画像を混ぜてもOK
        """)
        
        # サンプル画像が存在する場合は表示
        sample_image_path = "images/sample.png"
        if os.path.exists(sample_image_path):
            st.markdown("**📸 調整画面の見本**")
            st.image(sample_image_path, caption="各エリアの説明付きサンプル", use_column_width=True)
            st.caption("このような画像で、実際の最大値（この例では+2290玉）を入力して調整します")
    
    test_images = st.file_uploader(
        "画像を選択",
        type=['jpg', 'jpeg', 'png'],
        help="調整用の画像を複数アップロードできます。複数枚の場合は統計的に処理されます",
        key="test_images",
        accept_multiple_files=True
    )
    
    # 単一画像の場合の互換性のため
    test_image = test_images[0] if test_images else None
    
    # 画像がアップロードされた場合のみプリセット選択を表示
    if test_image:
        st.divider()
        
        # STEP 2: プリセット選択セクション
        st.markdown("### 📋 STEP 2: 設定の読み込み（任意）")
        st.caption("保存済みの設定がある場合は選択してください")
        
        # 保存されたプリセット一覧
        preset_names = ["デフォルト"] + list(st.session_state.saved_presets.keys())
        
        # プリセットボタンを横に並べる
        if len(preset_names) <= 4:
            preset_cols = st.columns(len(preset_names))
            # プリセットが4個以下の場合
            for i, preset_name in enumerate(preset_names):
                with preset_cols[i]:
                    button_type = "primary" if preset_name == st.session_state.get('current_preset_name', 'デフォルト') else "secondary"
                    if st.button(f"📥 {preset_name}", use_container_width=True, key=f"load_preset_{preset_name}", type=button_type):
                        if preset_name == "デフォルト":
                            st.session_state.settings = default_settings.copy()
                        else:
                            st.session_state.settings = st.session_state.saved_presets[preset_name].copy()
                            # プリセットに遊技種別情報がある場合は適用
                            if 'game_type' in st.session_state.settings:
                                st.session_state.game_type = st.session_state.settings['game_type']
                        
                        # 現在のプリセット名を保存（編集モードで使用）
                        st.session_state.current_preset_name = preset_name
                        st.session_state.editing_preset_name = preset_name
                        
                        st.success(f"✅ '{preset_name}' の設定を読み込みました")
                        time.sleep(0.5)
                        st.rerun()
        else:
            # 5個以上の場合は複数行に分ける
            num_rows = (len(preset_names) + 3) // 4  # 4列で何行必要か
            for row in range(num_rows):
                cols = st.columns(4)
                for col in range(4):
                    idx = row * 4 + col
                    if idx < len(preset_names):
                        preset_name = preset_names[idx]
                        with cols[col]:
                            button_type = "primary" if preset_name == st.session_state.get('current_preset_name', 'デフォルト') else "secondary"
                            if st.button(f"📥 {preset_name}", use_container_width=True, key=f"load_preset_{preset_name}", type=button_type):
                                if preset_name == "デフォルト":
                                    st.session_state.settings = default_settings.copy()
                                else:
                                    st.session_state.settings = st.session_state.saved_presets[preset_name].copy()
                                    # プリセットに遊技種別情報がある場合は適用
                                    if 'game_type' in st.session_state.settings:
                                        st.session_state.game_type = st.session_state.settings['game_type']
                                
                                # 現在のプリセット名を保存（編雈モードで使用）
                                st.session_state.current_preset_name = preset_name
                                st.session_state.editing_preset_name = preset_name
                                
                                st.success(f"✅ '{preset_name}' の設定を読み込みました")
                                time.sleep(0.5)
                                st.rerun()
        
        st.divider()
    
    
    # 設定値の初期化
    if test_image:
        # 画像を読み込み
        img_array = np.array(Image.open(test_image).convert('RGB'))
        height, width = img_array.shape[:2]
        
        # オレンジバーを検出
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
        orange_bottom = 0
        
        for y in range(height//2):
            if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
                orange_bottom = y
        
        if orange_bottom > 0:
            for y in range(orange_bottom, min(orange_bottom + 100, height)):
                if np.sum(orange_mask[y, :]) < width * 0.1 * 255:
                    orange_bottom = y
                    break
        else:
            orange_bottom = 150
        
        # グレースケール変換
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        st.info(f"画像サイズ: {width}x{height}px")
        
        # レイアウト用のメインカラム（画像を読み込んだ後）
        main_col1, main_col2 = st.columns([3, 2])
    
    # 画像がアップロードされている場合のみレイアウトを適用
    if test_image:
        with main_col2:
            # STEP 3: 設定用の入力フィールド
            st.markdown("### 🔍 STEP 3: 詳細設定（通常はデフォルトでOK）")
            st.caption("必要に応じて微調整できます")
            
            st.markdown("#### ゼロライン検索設定")
            col1, col2 = st.columns(2)
    
            with col1:
                search_start_offset = st.number_input(
                    "検索開始位置（オレンジバーから）",
                    min_value=0, max_value=800, value=st.session_state.settings['search_start_offset'],
                    step=10, help="オレンジバーから何ピクセル下から検索を開始するか"
                )
            
            with col2:
                search_end_offset = st.number_input(
                    "検索終了位置（オレンジバーから）",
                    min_value=100, max_value=1200, value=st.session_state.settings['search_end_offset'],
                    step=50, help="オレンジバーから何ピクセル下まで検索するか"
                )
            
            st.markdown("#### ✂️ 切り抜きサイズの設定")
            col3, col4 = st.columns(2)
    
            with col3:
                crop_top = st.number_input(
                    "上方向の切り抜きサイズ",
                    min_value=100, max_value=500, value=st.session_state.settings['crop_top'],
                    step=1, help="ゼロラインから上方向に何ピクセル切り抜くか"
                )
                crop_bottom = st.number_input(
                    "下方向の切り抜きサイズ",
                    min_value=100, max_value=500, value=st.session_state.settings['crop_bottom'],
                    step=1, help="ゼロラインから下方向に何ピクセル切り抜くか"
                )
            
            with col4:
                left_margin = st.number_input(
                    "左側の余白",
                    min_value=0, max_value=300, value=st.session_state.settings['left_margin'],
                    step=25, help="左側から何ピクセル除外するか"
                )
                right_margin = st.number_input(
                    "右側の余白",
                    min_value=0, max_value=300, value=st.session_state.settings['right_margin'],
                    step=25, help="右側から何ピクセル除外するか"
                )
            
            # グリッドライン調整
            st.markdown("#### 📏 グリッドライン調整")
            
            # グリッドライン手動調整
            st.markdown("#### ⚙️ 手動調整")
            # 遊技種別に応じた上下限値を取得
            graph_limit = get_graph_limit()
            st.caption(f"±{graph_limit:,}ラインの位置を微調整できます（単位：ピクセル）")
            
            grid_col1, grid_col2 = st.columns(2)
            
            with grid_col1:
                grid_30k_offset = st.number_input(
                    f"+{graph_limit:,}ライン調整",
                    min_value=-1000, max_value=1000, value=st.session_state.settings.get('grid_30k_offset', 0),
                    step=1, help=f"上端の+{graph_limit:,}ラインの位置調整"
                )
            
            with grid_col2:
                grid_minus_30k_offset = st.number_input(
                    f"-{graph_limit:,}ライン調整",
                    min_value=-1000, max_value=1000, value=st.session_state.settings.get('grid_minus_30k_offset', 0),
                    step=1, help=f"下端の-{graph_limit:,}ラインの位置調整"
                )
            
            # 中間ライン用のダミー変数を設定（他のコードで参照されるため）
            
            # STEP 4: 最大値アライメント機能を統合
            if test_images:
                st.markdown("### 🎯 STEP 4: 実際の最大値を入力して自動調整")
                st.caption(f"アップロードされた{len(test_images)}枚の画像から最適な設定を自動計算します")
                
                # 複数画像の解析結果を保存
                all_detections = []
                all_max_positions = []
                
                # 現在の設定を取得（入力フィールドの値を使用）
                current_settings_align = {
                    'search_start_offset': search_start_offset,
                    'search_end_offset': search_end_offset,
                    'crop_top': crop_top,
                    'crop_bottom': crop_bottom,
                    'left_margin': left_margin,
                    'right_margin': right_margin,
                    'grid_30k_offset': grid_30k_offset,
                    'grid_minus_30k_offset': grid_minus_30k_offset
                }
                
                # 各画像を解析
                for img_idx, test_img in enumerate(test_images):
                    # 画像を読み込み
                    img_array_tmp = np.array(Image.open(test_img).convert('RGB'))
                    height_tmp, width_tmp = img_array_tmp.shape[:2]
                    
                    # オレンジバーを検出
                    hsv_tmp = cv2.cvtColor(img_array_tmp, cv2.COLOR_RGB2HSV)
                    orange_mask_tmp = cv2.inRange(hsv_tmp, np.array([10, 100, 100]), np.array([30, 255, 255]))
                    orange_bottom_tmp = 0
                    
                    for y in range(height_tmp//2):
                        if np.sum(orange_mask_tmp[y, :]) > width_tmp * 0.3 * 255:
                            orange_bottom_tmp = y
                    
                    if orange_bottom_tmp > 0:
                        for y in range(orange_bottom_tmp, min(orange_bottom_tmp + 100, height_tmp)):
                            if np.sum(orange_mask_tmp[y, :]) < width_tmp * 0.1 * 255:
                                orange_bottom_tmp = y
                                break
                    else:
                        orange_bottom_tmp = 150
                    
                    # グレースケール変換
                    gray_tmp = cv2.cvtColor(img_array_tmp, cv2.COLOR_RGB2GRAY)
                    
                    # 現在の画像で解析を実行
                    analyzer_align = WebCompatibleAnalyzer()
                    
                    # ゼロライン検出（最大値アライメント用）
                    align_search_start = orange_bottom_tmp + search_start_offset
                    align_search_end = min(height_tmp - 100, orange_bottom_tmp + search_end_offset)
                    
                    # ゼロライン検出
                    align_best_score = 0
                    align_zero_line_y = (align_search_start + align_search_end) // 2
                    
                    for y in range(align_search_start, align_search_end):
                        row = gray_tmp[y, 100:width_tmp-100]
                        darkness = 1.0 - (np.mean(row) / 255.0)
                        uniformity = 1.0 - (np.std(row) / 128.0)
                        score = darkness * 0.5 + uniformity * 0.5
                        
                        if score > align_best_score:
                            align_best_score = score
                            align_zero_line_y = y
                    
                    # 切り抜き
                    align_top = max(0, align_zero_line_y - crop_top)
                    align_bottom = min(height_tmp, align_zero_line_y + crop_bottom)
                    align_left = left_margin
                    align_right = width_tmp - right_margin
                    
                    # グリッドライン調整値も適用（現在の入力値を使用）
                    align_zero_in_crop = align_zero_line_y - align_top
                    align_distance_to_plus_30k = align_zero_in_crop - grid_30k_offset
                    align_distance_to_minus_30k = (align_bottom - align_top - 1 + grid_minus_30k_offset) - align_zero_in_crop
                    
                    # カスタム設定で解析
                    analyzer_align.zero_y = align_zero_in_crop
                    graph_limit = get_graph_limit()
                    analyzer_align.scale = graph_limit / align_distance_to_plus_30k if align_distance_to_plus_30k > 0 else 122
                    
                    # 切り抜き画像で解析
                    cropped_for_align = img_array_tmp[int(align_top):int(align_bottom), int(align_left):int(align_right)]
                    # BGRに変換（OpenCVの標準形式）
                    cropped_bgr_align = cv2.cvtColor(cropped_for_align, cv2.COLOR_RGB2BGR)
                    
                    # 解析実行（画像データを直接渡す）
                    data_points_align, color_align, detected_zero_align, graph_info_align = analyzer_align.extract_graph_data(cropped_bgr_align)
                    
                    if data_points_align:
                        analysis_align = analyzer_align.analyze_values(data_points_align, st.session_state.game_type)
                        detected_max_align = analysis_align['max_value']
                        
                        # 最大値の位置を取得
                        max_index = analysis_align['max_index']
                        if max_index < len(data_points_align):
                            max_x, max_y_value = data_points_align[max_index]
                            # 画像座標系での最大値のY座標
                            max_y_pixel = int(align_zero_in_crop - (max_y_value / analyzer_align.scale))
                            
                            all_detections.append({
                                'detected_max': detected_max_align,
                                'max_y_pixel': max_y_pixel,
                                'zero_in_crop': align_zero_in_crop,
                                'crop_height': cropped_for_align.shape[0],
                                'image_name': test_img.name
                            })
                            
                            all_max_positions.append({
                                'x': int(max_x),
                                'y': max_y_pixel,
                                'value': max_y_value
                            })
                
                if all_detections:
                    # 統計情報を計算
                    detected_maxes = [d['detected_max'] for d in all_detections]
                    avg_detected_max = int(np.mean(detected_maxes))
                    median_detected_max = int(np.median(detected_maxes))
                    
                    # 検出結果を表示
                    st.markdown("##### 📊 検出結果と実際の値の入力")
                    
                    # 各画像に対して個別に実際の値を入力
                    visual_max_values = []
                    
                    if len(all_detections) > 1:
                        # 統計情報を表示
                        unit = get_unit()
                        detection_cols = st.columns(3)
                        with detection_cols[0]:
                            st.metric("検出平均値", f"{avg_detected_max:,}{unit}")
                        with detection_cols[1]:
                            st.metric("検出中央値", f"{median_detected_max:,}{unit}")
                        with detection_cols[2]:
                            st.metric("検出画像数", f"{len(all_detections)}/{len(test_images)}枚")
                        
                        st.markdown("---")
                        st.markdown("##### 🎯 各画像の実際の最大値を入力")
                        st.caption("各画像を確認して、実際の最大値を入力してください")
                        
                        # 各画像に対して入力フィールドを作成
                        cols_per_row = 2
                        for i, detection in enumerate(all_detections):
                            if i % cols_per_row == 0:
                                cols = st.columns(cols_per_row)
                            
                            with cols[i % cols_per_row]:
                                st.markdown(f"**{detection['image_name']}**")
                                unit = get_unit()
                                st.caption(f"検出値: {detection['detected_max']:,}{unit}")
                                
                                # プレビューボタン
                                if st.button(f"🔍 画像を確認", key=f"preview_btn_{i}"):
                                    st.session_state['preview_image_index'] = i
                                    # 検出情報も保存
                                    st.session_state['preview_detection_info'] = detection
                                
                                # セッションステートから値を取得（なければデフォルト値を使用）
                                # ウィジェットのキーとは別のキーを使用
                                default_val = st.session_state.get(f"saved_visual_max_{i}", detection['detected_max'])
                                visual_max = st.number_input(
                                    "実際の最大値",
                                    min_value=0,
                                    max_value=50000,
                                    value=default_val,
                                    step=100,
                                    help=f"{detection['image_name']}の実際の最高値",
                                    key=f"visual_max_{i}",
                                    label_visibility="visible"
                                )
                                # 値が変更されたら保存
                                if visual_max != default_val:
                                    st.session_state[f"saved_visual_max_{i}"] = visual_max
                                visual_max_values.append(visual_max)
                    else:
                        # 単一画像の場合
                        detection = all_detections[0]
                        unit = get_unit()
                        st.info(f"🔍 検出値: **{detection['detected_max']:,}{unit}**")
                        
                        # セッションステートから値を取得（なければデフォルト値を使用）
                        default_val = st.session_state.get("saved_visual_max_single", detection['detected_max'])
                        visual_max = st.number_input(
                            "実際の最大値を入力",
                            min_value=0,
                            max_value=50000,
                            value=default_val,
                            step=100,
                            help="グラフ画像を見て確認した最高値",
                            key="visual_max_single",
                            label_visibility="visible"
                        )
                        # 値が変更されたら保存
                        if visual_max != default_val:
                            st.session_state["saved_visual_max_single"] = visual_max
                        visual_max_values.append(visual_max)
                    
                    if any(v > 0 for v in visual_max_values):
                        # 各画像での補正率を計算
                        corrections = []
                        for i, (detection, visual_max) in enumerate(zip(all_detections, visual_max_values)):
                            if detection['detected_max'] > 0 and visual_max > 0:
                                correction_factor = visual_max / detection['detected_max']
                                actual_distance = detection['zero_in_crop'] - detection['max_y_pixel']
                                if actual_distance > 0:
                                    new_scale = visual_max / actual_distance
                                    
                                    # 新しい上限ラインの位置を計算
                                    graph_limit = get_graph_limit()
                                    new_30k_distance = graph_limit / new_scale
                                    current_30k_distance = detection['zero_in_crop'] - current_settings_align['grid_30k_offset']
                                    adjustment_30k = int(current_30k_distance - new_30k_distance)
                                    
                                    # 新しい下限ラインの位置を計算
                                    new_minus_30k_distance = graph_limit / new_scale
                                    current_minus_30k_distance = (detection['crop_height'] - 1 + current_settings_align['grid_minus_30k_offset']) - detection['zero_in_crop']
                                    adjustment_minus_30k = int(new_minus_30k_distance - current_minus_30k_distance)
                                    
                                    corrections.append({
                                        'adjustment_30k': adjustment_30k,
                                        'adjustment_minus_30k': adjustment_minus_30k,
                                        'correction_factor': correction_factor
                                    })
                        
                        if corrections:
                            # 平均調整値を計算
                            avg_adjustment_30k = int(np.mean([c['adjustment_30k'] for c in corrections]))
                            avg_adjustment_minus_30k = int(np.mean([c['adjustment_minus_30k'] for c in corrections]))
                            avg_correction_factor = np.mean([c['correction_factor'] for c in corrections])
                            
                            # セッションステートに保存
                            st.session_state.avg_correction_factor = avg_correction_factor
                            
                            if abs(avg_correction_factor - 1.0) > 0.001:
                                # 推奨調整値を表示
                                # st.info(f"平均補正率: **{avg_correction_factor:.2f}x** （{len(corrections)}枚の画像から計算）")  # 補正率表示を非表示化
                                
                                col_adj1, col_adj2 = st.columns(2)
                                graph_limit = get_graph_limit()
                                with col_adj1:
                                    st.info(f"**+{graph_limit:,}ライン:** {grid_30k_offset}px → {grid_30k_offset + avg_adjustment_30k}px (調整: {avg_adjustment_30k:+d}px)")
                                with col_adj2:
                                    st.info(f"**-{graph_limit:,}ライン:** {grid_minus_30k_offset}px → {grid_minus_30k_offset + avg_adjustment_minus_30k}px (調整: {avg_adjustment_minus_30k:+d}px)")
                                
                                # 自動適用ボタン
                                if st.button("🔧 推奨値を自動適用", type="secondary", key="apply_max_alignment"):
                                    # セッションステートに新しい値を設定（現在の入力値に調整を加える）
                                    st.session_state.settings['grid_30k_offset'] = grid_30k_offset + avg_adjustment_30k
                                    st.session_state.settings['grid_minus_30k_offset'] = grid_minus_30k_offset + avg_adjustment_minus_30k
                                    
                                    # 最初の画像の最大値位置を保存（非線形スケール用）
                                    if all_max_positions:
                                        st.session_state['max_value_position'] = all_max_positions[0]
                                    
                                    st.success("✅ 推奨値を適用しました！画面が更新されます...")
                                    time.sleep(1)
                                    st.rerun()
                            else:
                                st.success("✅ 検出値と実際の値が一致しています")
                else:
                    st.warning("グラフデータを検出できませんでした")
            
    
    
    if test_images:
        st.markdown("### 🖼️ リアルタイムプレビュー")
        
        # プレビューする画像を決定（ボタンで選択されたもの、または最初の画像）
        if 'preview_image_index' in st.session_state and st.session_state['preview_image_index'] < len(test_images):
            selected_image_idx = st.session_state['preview_image_index']
            selected_image = test_images[selected_image_idx]
            if len(test_images) > 1:
                st.info(f"📸 表示中: **{selected_image.name}**")
        else:
            selected_image = test_image
            selected_image_idx = 0
        
        # 選択された画像を読み込み
        img_array_preview = np.array(Image.open(selected_image).convert('RGB'))
        height_preview, width_preview = img_array_preview.shape[:2]
        
        # オレンジバーを検出（選択された画像用）
        hsv_preview = cv2.cvtColor(img_array_preview, cv2.COLOR_RGB2HSV)
        orange_mask_preview = cv2.inRange(hsv_preview, np.array([10, 100, 100]), np.array([30, 255, 255]))
        orange_bottom_preview = 0
        
        for y in range(height_preview//2):
            if np.sum(orange_mask_preview[y, :]) > width_preview * 0.3 * 255:
                orange_bottom_preview = y
        
        if orange_bottom_preview > 0:
            for y in range(orange_bottom_preview, min(orange_bottom_preview + 100, height_preview)):
                if np.sum(orange_mask_preview[y, :]) < width_preview * 0.1 * 255:
                    orange_bottom_preview = y
                    break
        else:
            orange_bottom_preview = 150
        
        # グレースケール変換
        gray_preview = cv2.cvtColor(img_array_preview, cv2.COLOR_RGB2GRAY)
        
        # 現在の設定で切り抜き処理を実行
        search_start = orange_bottom_preview + search_start_offset
        search_end = min(height_preview - 100, orange_bottom_preview + search_end_offset)
        
        # ゼロライン検出
        best_score = 0
        zero_line_y = (search_start + search_end) // 2
        
        for y in range(search_start, search_end):
            row = gray_preview[y, 100:width_preview-100]
            darkness = 1.0 - (np.mean(row) / 255.0)
            uniformity = 1.0 - (np.std(row) / 128.0)
            score = darkness * 0.5 + uniformity * 0.5
            
            if score > best_score:
                best_score = score
                zero_line_y = y
        
        # 切り抜き
        top = max(0, zero_line_y - crop_top)
        bottom = min(height_preview, zero_line_y + crop_bottom)
        left = left_margin
        right = width_preview - right_margin
        
        # オーバーレイ画像を作成
        overlay_img = img_array_preview.copy()
        
        # 検索範囲を可視化（濃い緑の枠線）
        cv2.rectangle(overlay_img, (100, search_start), (width_preview-100, search_end), (0, 255, 0), 3)
        # 半透明の緑で塗りつぶし
        overlay = overlay_img.copy()
        cv2.rectangle(overlay, (100, search_start), (width_preview-100, search_end), (0, 255, 0), -1)
        overlay_img = cv2.addWeighted(overlay_img, 0.8, overlay, 0.2, 0)
        
        # 検索範囲の説明テキストを右上に追加
        text = 'Zero Line Search Area'
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        cv2.putText(overlay_img, text, (width_preview - text_size[0] - 110, search_start + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)
        
        text2 = f'({search_start_offset} ~ {search_end_offset}px)'
        text_size2 = cv2.getTextSize(text2, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.putText(overlay_img, text2, (width_preview - text_size2[0] - 110, search_start + 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)
        
        # 検出したゼロラインを描画（赤）
        cv2.line(overlay_img, (0, zero_line_y), (width_preview, zero_line_y), (255, 0, 0), 3)
        cv2.putText(overlay_img, f'Zero Line (score: {best_score:.3f})', (10, zero_line_y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # 切り抜き範囲を描画（濃い青）
        cv2.rectangle(overlay_img, (left, int(top)), (right, int(bottom)), (0, 0, 255), 4)
        
        # 切り抜き範囲の説明テキストを右上に追加
        text3 = 'Crop Area'
        text_size3 = cv2.getTextSize(text3, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        cv2.putText(overlay_img, text3, (right - text_size3[0] - 5, int(top) + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 200), 2)
        
        text4 = f'(Top: {crop_top}px, Bottom: {crop_bottom}px)'
        text_size4 = cv2.getTextSize(text4, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.putText(overlay_img, text4, (right - text_size4[0] - 5, int(top) + 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 200), 2)
        
        # オレンジバーの位置を表示（濃いオレンジ）
        cv2.line(overlay_img, (0, orange_bottom_preview), (width_preview, orange_bottom_preview), (255, 140, 0), 3)
        cv2.putText(overlay_img, 'Orange Bar', (10, orange_bottom_preview + 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 140, 0), 2)
        
        # ゼロラインから±30000ラインまでの距離を計算（切り抜き内での計算）
        zero_in_crop = zero_line_y - top
        distance_to_plus_30k = zero_in_crop - grid_30k_offset
        distance_to_minus_30k = (bottom - top - 1 + grid_minus_30k_offset) - zero_in_crop
        
        # グリッドラインを元画像にも追加
        # +30000ライン（元画像座標）
        y_30k_orig = int(top + grid_30k_offset)
        if 0 <= y_30k_orig < height_preview:
            cv2.line(overlay_img, (0, y_30k_orig), (width_preview, y_30k_orig), (128, 128, 128), 2)
            cv2.putText(overlay_img, '+30000', (10, max(20, y_30k_orig + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
        
        # -30000ライン（元画像座標）
        y_minus_30k_orig = int(bottom - 1 + grid_minus_30k_offset)
        if 0 <= y_minus_30k_orig < height_preview:
            cv2.line(overlay_img, (0, y_minus_30k_orig), (width_preview, y_minus_30k_orig), (128, 128, 128), 2)
            cv2.putText(overlay_img, '-30000', (10, max(10, y_minus_30k_orig - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
        
        
        # プレビューを左カラムに表示（縦に配置）
        with main_col1:
            # 元画像（調整範囲を表示）
            st.markdown("#### 元画像（調整範囲を表示）")
            st.image(overlay_img, use_column_width=True)
            
            # 切り抜き結果（元画像の下に配置）
            st.markdown("#### 切り抜き結果")
            cropped_preview_original = img_array_preview[int(top):int(bottom), int(left):int(right)].copy()
            cropped_preview = cropped_preview_original.copy()  # 表示用のコピーを作成
            
            # グリッドラインを追加（表示用画像にのみ）
            zero_in_crop = zero_line_y - top
            cv2.line(cropped_preview, (0, int(zero_in_crop)), (cropped_preview.shape[1], int(zero_in_crop)), (255, 0, 0), 2)
            
            # グリッドラインを追加（調整値付き）
            # +30000ライン（最上部付近）
            y_30k = 0 + grid_30k_offset  # 最上部を基準に調整
            if 0 <= y_30k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_30k), (cropped_preview.shape[1], y_30k), (0, 150, 0), 3)
                cv2.putText(cropped_preview, '+30000', (10, max(20, y_30k + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 0), 2)
            
            # -30000ライン
            y_minus_30k = cropped_preview.shape[0] - 1 + grid_minus_30k_offset  # 最下部基準
            if 0 <= y_minus_30k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_minus_30k), (cropped_preview.shape[1], y_minus_30k), (150, 0, 0), 3)
                cv2.putText(cropped_preview, '-30000', (10, max(10, y_minus_30k - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 0, 0), 2)
            
            
            # 選択された画像の実際の最大値を表示
            if 'preview_image_index' in st.session_state:
                preview_idx = st.session_state.get('preview_image_index', 0)
                
                # プレビュー用の解析を実行して最大値を検出
                analyzer_preview = WebCompatibleAnalyzer()
                analyzer_preview.zero_y = zero_in_crop
                
                # 調整されたグリッドライン位置に基づいてスケールを計算
                y_30k_adjusted = 0 + grid_30k_offset
                y_minus_30k_adjusted = cropped_preview.shape[0] - 1 + grid_minus_30k_offset
                
                # 線形スケールのみ使用
                distance_to_plus_30k_adjusted = zero_in_crop - y_30k_adjusted
                distance_to_minus_30k_adjusted = y_minus_30k_adjusted - zero_in_crop
                
                if distance_to_plus_30k_adjusted > 0 and distance_to_minus_30k_adjusted > 0:
                    avg_distance_adjusted = (distance_to_plus_30k_adjusted + distance_to_minus_30k_adjusted) / 2
                    analyzer_preview.scale = 30000 / avg_distance_adjusted
                else:
                    analyzer_preview.scale = 122  # デフォルト


                # BGRに変換（グリッドラインなしの元画像を使用）
                cropped_bgr_preview = cv2.cvtColor(cropped_preview_original, cv2.COLOR_RGB2BGR)
                
                # グラフデータを抽出
                data_points_preview, color_preview, _, graph_info_preview = analyzer_preview.extract_graph_data(cropped_bgr_preview)
                
                if data_points_preview:
                    # 最大値を検出
                    values_preview = [value for x, value in data_points_preview]
                    max_val_detected = max(values_preview)
                    max_idx = values_preview.index(max_val_detected)
                    max_x, _ = data_points_preview[max_idx]
                    
                    # 入力された実際の最大値を取得
                    actual_max_value = None
                    if f'visual_max_{preview_idx}' in st.session_state:
                        actual_max_value = st.session_state[f'visual_max_{preview_idx}']
                    
                    # 実際の値が入力されている場合はそれを使用、そうでなければ検出値を使用
                    display_max_value = actual_max_value if actual_max_value is not None else max_val_detected
                    
                    # グラフ上の実際の最大値のY座標（線形スケール）
                    max_y_in_crop = int(zero_in_crop - (max_val_detected / analyzer_preview.scale))
                    
                    # 表示する値は実際の値があればそれを使用
                    if actual_max_value and max_val_detected > 0:
                        correction_factor = actual_max_value / max_val_detected
                        display_value = actual_max_value
                    else:
                        correction_factor = 1.0
                        display_value = max_val_detected
                    
                    if 0 <= max_y_in_crop < cropped_preview.shape[0]:
                        # 赤い水平線を描画（グラフの最高点の高さ）
                        cv2.line(cropped_preview, (0, max_y_in_crop), (cropped_preview.shape[1], max_y_in_crop), (0, 0, 255), 3)
                        # 最大値の点に円を描画（グラフ上の実際の位置）
                        cv2.circle(cropped_preview, (int(max_x), max_y_in_crop), 8, (0, 0, 255), -1)
                        cv2.circle(cropped_preview, (int(max_x), max_y_in_crop), 10, (0, 0, 200), 2)
                        # ラベルを追加（表示する値は実際の値）
                        label_text = f"MAX: {int(display_value):,}"
                        cv2.putText(cropped_preview, label_text, (cropped_preview.shape[1] - 180, max_y_in_crop - 5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    # 補正情報を表示
                    if actual_max_value and abs(correction_factor - 1.0) > 0.01:
                        unit = get_unit()
                        info_text = f"🔍 検出値: {int(max_val_detected):,}{unit} → 実際の値: {int(actual_max_value):,}{unit}"
                        st.info(info_text)
            
            st.image(cropped_preview, use_column_width=True)
            
            # 情報表示
            st.caption(f"🔍 検出情報: オレンジバー位置 Y={orange_bottom}, ゼロライン Y={zero_line_y}, 検索範囲 Y={search_start}〜{search_end}")
            st.caption(f"✂️ 切り抜き範囲: 上{crop_top}px, 下{crop_bottom}px, 左{left_margin}px, 右{right_margin}px")
        
    # 設定の保存とプリセット削除を同じ配置で表示（順序を入れ替え）
    
    # 設定の保存セクション（全体で共通、保存ボタンだけ別）  
    # test_imageがある場合は変数を利用、ない場合はセッションステート利用
    if test_image:
        # test_imageがある場合、入力値から直接設定を作成
        def save_settings():
            settings = {
                'search_start_offset': search_start_offset,
                'search_end_offset': search_end_offset,
                'crop_top': crop_top,
                'crop_bottom': crop_bottom,
                'left_margin': left_margin,
                'right_margin': right_margin,
                'grid_30k_offset': grid_30k_offset,
                'grid_minus_30k_offset': grid_minus_30k_offset,
                'game_type': st.session_state.game_type  # 遊技種別を追加
            }
            return settings
    else:
        # test_imageがない場合、セッションステートから取得
        def save_settings():
            settings = st.session_state.settings.copy()
            settings['game_type'] = st.session_state.game_type  # 遊技種別を追加
            return settings
    
    # STEP 5: 設定の保存の見出しを適切な場所に配置（画像がある場合のみ表示）
    if test_image:
        with main_col2:
            st.markdown("### 💾 STEP 5: 設定の保存")
            st.caption("調整が完了したら、端末名をつけて保存してください")
    
    # 設定の保存の内容（test_imageの有無で配置を変更）
    def render_save_settings():
        # 既存のプリセットを編集する場合
        if st.session_state.saved_presets:
            edit_mode = st.checkbox("既存のプリセットを編集", key="edit_preset_mode")
            
            if edit_mode:
                # 編集するプリセットを選択
                selected_preset = st.selectbox(
                    "編集するプリセットを選択",
                    ["新規作成"] + list(st.session_state.saved_presets.keys()),
                    key="edit_preset_select"
                )
                
                if selected_preset != "新規作成":
                    # 選択されたプリセット名を入力フィールドに設定
                    preset_name = st.text_input(
                        "プリセット名",
                        value=selected_preset,
                        help="プリセット名を変更することもできます"
                    )
                else:
                    # 編集中のプリセット名がある場合はそれを使用
                    default_name = st.session_state.get('editing_preset_name', '')
                    if default_name == 'デフォルト':
                        default_name = ''
                    preset_name = st.text_input(
                        "プリセット名",
                        value=default_name,
                        placeholder="例: iPhone15用、S__シリーズ用",
                        help="保存する設定の名前を入力してください"
                    )
            else:
                # 新規作成モード（編集中のプリセット名がある場合はそれを使用）
                default_name = st.session_state.get('editing_preset_name', '')
                if default_name == 'デフォルト':
                    default_name = ''
                preset_name = st.text_input(
                    "プリセット名",
                    value=default_name,
                    placeholder="例: iPhone15用、S__シリーズ用",
                    help="保存する設定の名前を入力してください"
                )
        else:
            # プリセットがない場合は新規作成のみ（編集中のプリセット名がある場合はそれを使用）
            default_name = st.session_state.get('editing_preset_name', '')
            if default_name == 'デフォルト':
                default_name = ''
            preset_name = st.text_input(
                "プリセット名",
                value=default_name,
                placeholder="例: iPhone15用、S__シリーズ用",
                help="保存する設定の名前を入力してください"
            )
        
        # ボタン用のカラムレイアウト
        save_col1, save_col2 = st.columns([1, 1])
        
        with save_col1:
            # 編集モードかどうかでボタンのラベルを変更
            save_button_label = "💾 プリセットを更新" if (st.session_state.saved_presets and 
                                                         'edit_preset_mode' in st.session_state and 
                                                         st.session_state.edit_preset_mode and 
                                                         'edit_preset_select' in st.session_state and
                                                         st.session_state.edit_preset_select != "新規作成") else "💾 プリセットを保存"
            
            if st.button(save_button_label, type="primary", use_container_width=True):
                if preset_name:
                    # 現在の設定を取得
                    settings = save_settings()
                    
                    # 補正係数があれば追加
                    if 'avg_correction_factor' in st.session_state:
                        settings['correction_factor'] = st.session_state.avg_correction_factor
                    
                    # プリセットに保存
                    st.session_state.saved_presets[preset_name] = settings.copy()
                    # 現在の設定も更新
                    st.session_state.settings = settings
                    
                    # データベースに保存
                    if save_preset_to_db(preset_name, settings):
                        # データベースから再読み込みして確実に反映
                        st.session_state.saved_presets = load_presets_from_db()
                        
                        # 編集モードかどうかでメッセージを変更
                        if (st.session_state.saved_presets and 
                            'edit_preset_mode' in st.session_state and 
                            st.session_state.edit_preset_mode and 
                            'edit_preset_select' in st.session_state and
                            st.session_state.edit_preset_select != "新規作成"):
                            st.success(f"✅ プリセット '{preset_name}' を更新しました")
                        else:
                            st.success(f"✅ プリセット '{preset_name}' を保存しました")
                        st.rerun()
                else:
                    st.error("プリセット名を入力してください")
        
        with save_col2:
            if st.button("🔄 デフォルトに戻す", use_container_width=True):
                st.session_state.settings = default_settings.copy()
                st.rerun()
    
    # 設定の保存を描画（画像がある場合のみ）
    if test_image:
        with main_col2:
            render_save_settings()
    
    # プリセット削除セクション（設定の保存の直後に配置）
    if test_image:
        with main_col2:
            # プリセット削除
            if st.session_state.saved_presets:
                st.markdown("### 🗑️ プリセットの削除")
                
                # 現在編集中のプリセットをデフォルトにする
                default_delete_preset = None
                if ('edit_preset_mode' in st.session_state and 
                    st.session_state.edit_preset_mode and 
                    'edit_preset_select' in st.session_state and
                    st.session_state.edit_preset_select != "新規作成"):
                    default_delete_preset = st.session_state.edit_preset_select
                
                # デフォルト値を見つける
                preset_list = list(st.session_state.saved_presets.keys())
                default_index = 0
                if default_delete_preset and default_delete_preset in preset_list:
                    default_index = preset_list.index(default_delete_preset)
                
                # プリセット選択（全幅）
                preset_to_delete = st.selectbox(
                    "削除するプリセット",
                    preset_list,
                    index=default_index,
                    key="delete_preset"
                )
                
                # 削除ボタン
                if st.button("🗑️ 削除", type="secondary", use_container_width=True):
                    if preset_to_delete:
                        del st.session_state.saved_presets[preset_to_delete]
                        
                        # データベースから削除
                        if delete_preset_from_db(preset_to_delete):
                            st.success(f"✅ プリセット '{preset_to_delete}' を削除しました")
                            st.rerun()

# フッター
st.markdown("---")

# プリセットのエクスポート/インポート機能
with st.expander("📤 プリセットのエクスポート/インポート"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📤 エクスポート")
        if st.session_state.saved_presets:
            # プリセットデータをJSON形式で表示
            preset_data = {
                "presets": st.session_state.saved_presets,
                "version": "2.1",
                "exported_at": datetime.now().isoformat()
            }
            preset_json = json.dumps(preset_data, ensure_ascii=False, indent=2)
            st.text_area("プリセットデータ（コピーして保存）", preset_json, height=200)
            
            # ダウンロードボタン
            st.download_button(
                label="📥 JSONファイルとしてダウンロード",
                data=preset_json,
                file_name=f"presets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        else:
            st.info("保存されたプリセットがありません")
    
    with col2:
        st.markdown("#### 📥 インポート")
        import_data = st.text_area("プリセットデータを貼り付け", height=200, placeholder="エクスポートしたJSONデータを貼り付けてください")
        
        if st.button("📥 インポート実行"):
            if import_data:
                try:
                    imported = json.loads(import_data)
                    if "presets" in imported:
                        # 既存のプリセットに追加
                        for name, preset in imported["presets"].items():
                            st.session_state.saved_presets[name] = preset
                            # データベースにも保存
                            save_preset_to_db(name, preset)
                        st.success(f"✅ {len(imported['presets'])}個のプリセットをインポートしました")
                        st.rerun()
                    else:
                        st.error("無効なプリセットデータです")
                except json.JSONDecodeError:
                    st.error("JSONの形式が正しくありません")
                except Exception as e:
                    st.error(f"インポートエラー: {str(e)}")
            else:
                st.warning("インポートするデータを入力してください")

# フッターをカラムで配置
footer_col1, footer_col2, footer_col3 = st.columns([2, 1, 1])

with footer_col1:
    st.markdown(f"""
    🎰 パチンコグラフ解析システム v2.5.0  
    更新日: {datetime.now().strftime('%Y/%m/%d')}  
    Produced by [PPタウン](https://pp-town.com/)  
    Created by [fivenine-design.com](https://fivenine-design.com)
    """)

with footer_col2:
    # 管理者の場合はパスワード変更ボタンを表示
    if st.session_state.get('is_admin', False):
        if st.button("🔐 パスワード管理", key="password_management_button"):
            st.session_state.show_password_management = True

with footer_col3:
    if st.button("🚪 ログアウト", key="logout_button"):
        st.session_state.authenticated = False
        st.session_state.is_admin = False
        # URLパラメータをクリア
        st.query_params.clear()
        time.sleep(0.3)
        st.rerun()

# パスワード管理モーダル（管理者のみ）
if st.session_state.get('show_password_management', False) and st.session_state.get('is_admin', False):
    with st.container():
        st.markdown("---")
        st.markdown("### 🔐 パスワード管理")
        
        # 現在のパスワードを表示
        st.info(f"""
        **現在のパスワード:**
        - 一般ユーザー: {st._global_passwords['user']}
        - 管理者: {st._global_passwords['admin']}
        """)
        
        # パスワード変更フォーム
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 一般ユーザーパスワード")
            new_user_password = st.text_input(
                "新しいパスワード",
                type="password",
                key="new_user_password",
                placeholder="新しいパスワードを入力"
            )
            if st.button("一般パスワードを変更", key="change_user_password"):
                if new_user_password:
                    st._global_passwords['user'] = new_user_password
                    st.success("✅ 一般ユーザーパスワードを変更しました（アプリ再起動まで有効）")
                else:
                    st.error("パスワードを入力してください")
        
        with col2:
            st.markdown("#### 管理者パスワード")
            new_admin_password = st.text_input(
                "新しいパスワード",
                type="password",
                key="new_admin_password",
                placeholder="新しいパスワードを入力"
            )
            if st.button("管理者パスワードを変更", key="change_admin_password"):
                if new_admin_password:
                    st._global_passwords['admin'] = new_admin_password
                    st.success("✅ 管理者パスワードを変更しました（アプリ再起動まで有効）")
                else:
                    st.error("パスワードを入力してください")
        
        # 閉じるボタン
        if st.button("閉じる", key="close_password_management"):
            st.session_state.show_password_management = False
            st.rerun()