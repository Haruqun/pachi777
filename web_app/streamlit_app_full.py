#!/usr/bin/env python3
"""
パチンコグラフ解析システム - シンプル版
画像アップロード機能のみ
"""

import streamlit as st
from datetime import datetime
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
from web_analyzer import WebCompatibleAnalyzer
import platform
import pytesseract
import re
import json
import pandas as pd

# ページ設定
st.set_page_config(
    page_title="パチンコグラフ解析",
    page_icon="🎰",
    layout="wide"
)

def extract_site7_data(image):
    """site7の画像からOCRでデータを抽出"""
    try:
        # 画像をグレースケールに変換
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # OCRの前処理
        # コントラストを上げる
        alpha = 1.5  # コントラスト制御
        beta = 0     # 明度制御
        adjusted = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)
        
        # 全体のOCR実行（日本語対応）
        text = pytesseract.image_to_string(adjusted, lang='jpn')
        
        # 抽出したいデータのパターン定義
        data = {
            'machine_number': None,
            'total_start': None,
            'jackpot_count': None,
            'first_hit_count': None,
            'current_start': None,
            'jackpot_probability': None,
            'max_payout': None
        }
        
        # 台番号の抽出
        lines = text.split('\n')
        for line in lines:
            if '番台' in line and '【' in line:
                data['machine_number'] = line.strip()
        
        # 数値データの抽出
        # 累計スタート
        start_match = re.search(r'(\d{3,4})\s*スタート', text)
        if start_match:
            data['total_start'] = start_match.group(1)
        
        # 大当り回数
        jackpot_match = re.search(r'(\d+)\s*回\s*大当り', text)
        if not jackpot_match:
            jackpot_match = re.search(r'大当り回数\s*(\d+)', text)
        if jackpot_match:
            data['jackpot_count'] = jackpot_match.group(1)
        
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
        prob_match = re.search(r'1/(\d{2,4})', text)
        if prob_match:
            data['jackpot_probability'] = f"1/{prob_match.group(1)}"
        
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
        
        
        return data
    except Exception as e:
        st.warning(f"OCRエラー: {str(e)}")
        return None


# ファイルアップローダー（一番最初に表示）
uploaded_files = st.file_uploader(
    "📤 グラフ画像をアップロード",
    type=['jpg', 'jpeg', 'png'],
    accept_multiple_files=True,
    help="複数の画像を一度にアップロードできます（JPG, PNG形式）"
)

if uploaded_files:
    st.success(f"✅ {len(uploaded_files)}枚の画像がアップロードされました")
    
    # 解析結果セクション
    st.markdown("### 🎯 解析結果")
    
    # プログレスバー
    progress_bar = st.progress(0)
    status_text = st.empty()
    detail_text = st.empty()
    
    # 解析結果を格納
    analysis_results = []
    
    # 各画像を処理
    for idx, uploaded_file in enumerate(uploaded_files):
        # 進捗更新
        progress = (idx + 1) / len(uploaded_files)
        progress_bar.progress(progress)
        status_text.text(f'処理中... ({idx + 1}/{len(uploaded_files)})')
        detail_text.text(f'📷 {uploaded_file.name} の画像を読み込み中...')
        
        # 画像を読み込み
        image = Image.open(uploaded_file)
        img_array = np.array(image)
        height, width = img_array.shape[:2]
        
        # OCRでデータ抽出を試みる
        detail_text.text(f'🔍 {uploaded_file.name} のOCR解析を実行中...')
        ocr_data = extract_site7_data(img_array)
        
        # Pattern3: Zero Line Based の自動検出
        detail_text.text(f'📐 {uploaded_file.name} のグラフ領域を検出中...')
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
        search_start = orange_bottom + 50
        search_end = min(height - 100, orange_bottom + 400)
        
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
        top = max(0, zero_line_y - 246)  # 0ラインから上246px
        bottom = min(height, zero_line_y + 247)  # 0ラインから下247px
        left = 125  # 左右の余白125px
        right = width - 125  # 左右の余白125px
        
        # 切り抜き実行
        cropped_img = img_array[int(top):int(bottom), int(left):int(right)].copy()
        
        # グリッドラインを追加
        # 切り抜き画像の高さは493px（246+247）
        # 最上部が+30000、最下部が-30000なので、60000の範囲を493pxで表現
        # 1pxあたり約121.7玉
        crop_height = cropped_img.shape[0]
        zero_line_in_crop = zero_line_y - top  # 切り抜き画像内での0ライン位置
        
        # スケール計算（上下246,247pxで±30000）
        scale = 30000 / 246  # 約121.95玉/px
        
        # グリッドライン描画（固定値）
        # +30000ライン（最上部）
        y_30k = -1  # 固定調整値
        cv2.line(cropped_img, (0, y_30k), (cropped_img.shape[1], y_30k), (128, 128, 128), 2)
        cv2.putText(cropped_img, '+30000', (10, max(20, y_30k + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)
        
        # +20000ライン
        y_20k = int(zero_line_in_crop - (20000 / scale)) - 2  # 固定調整値
        if 0 < y_20k < crop_height:
            cv2.line(cropped_img, (0, y_20k), (cropped_img.shape[1], y_20k), (128, 128, 128), 1)
            cv2.putText(cropped_img, '+20000', (10, y_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
        
        # +10000ライン
        y_10k = int(zero_line_in_crop - (10000 / scale)) - 1  # 固定調整値
        if 0 < y_10k < crop_height:
            cv2.line(cropped_img, (0, y_10k), (cropped_img.shape[1], y_10k), (128, 128, 128), 1)
            cv2.putText(cropped_img, '+10000', (10, y_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
        
        # 0ライン
        y_0 = int(zero_line_in_crop)  # 調整なし
        if 0 < y_0 < crop_height:
            cv2.line(cropped_img, (0, y_0), (cropped_img.shape[1], y_0), (255, 0, 0), 2)
            cv2.putText(cropped_img, '0', (10, y_0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)
        
        # -10000ライン
        y_minus_10k = int(zero_line_in_crop + (10000 / scale)) + 1  # 固定調整値
        if 0 < y_minus_10k < crop_height:
            cv2.line(cropped_img, (0, y_minus_10k), (cropped_img.shape[1], y_minus_10k), (128, 128, 128), 1)
            cv2.putText(cropped_img, '-10000', (10, y_minus_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
        
        # -20000ライン
        y_minus_20k = int(zero_line_in_crop + (20000 / scale)) + 1  # 固定調整値
        if 0 < y_minus_20k < crop_height:
            cv2.line(cropped_img, (0, y_minus_20k), (cropped_img.shape[1], y_minus_20k), (128, 128, 128), 1)
            cv2.putText(cropped_img, '-20000', (10, y_minus_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
        
        # -30000ライン（最下部）
        y_minus_30k = crop_height - 1 + 2  # 固定調整値
        y_minus_30k = min(max(0, y_minus_30k), crop_height - 1)  # 画像範囲内に制限
        cv2.line(cropped_img, (0, y_minus_30k), (cropped_img.shape[1], y_minus_30k), (128, 128, 128), 2)
        cv2.putText(cropped_img, '-30000', (10, max(10, y_minus_30k - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)
        
        # 解析を自動実行
        detail_text.text(f'📊 {uploaded_file.name} のグラフデータを解析中...')
        with st.spinner(f"グラフを解析中... ({idx + 1}/{len(uploaded_files)})"):
            # アナライザーを初期化
            analyzer = WebCompatibleAnalyzer()
            
            # グリッドラインなしの画像を使用
            analysis_img = img_array[int(top):int(bottom), int(left):int(right)].copy()
            
            # 0ラインの位置を設定
            analyzer.zero_y = zero_line_in_crop
            analyzer.scale = 30000 / 246  # スケール設定
            
            # グラフデータを抽出
            graph_data_points, dominant_color, _ = analyzer.extract_graph_data(analysis_img)
            
            if graph_data_points:
                # データポイントから値のみを抽出
                graph_values = [value for x, value in graph_data_points]
                
                # 統計情報を計算
                max_val = max(graph_values)
                min_val = min(graph_values)
                current_val = graph_values[-1] if graph_values else 0
                
                # MAXがマイナスの場合は0を表示
                if max_val < 0:
                    max_val = 0
                
                # 初当たり値を探す（production版と同じロジック）
                first_hit_val = 0
                first_hit_x = None
                min_payout = 100  # 最低払い出し玉数
                
                # 方法1: 100玉以上の急激な増加を検出
                for i in range(1, min(len(graph_values)-2, 150)):  # 最大150点まで探索
                    current_increase = graph_values[i+1] - graph_values[i]
                    
                    # 100玉以上の増加を検出
                    if current_increase > min_payout:
                        # 次の点も上昇または維持していることを確認（ノイズ除外）
                        if graph_values[i+2] >= graph_values[i+1] - 50:
                            # 初当たりは必ずマイナス値から
                            if graph_values[i] < 0:
                                first_hit_val = graph_values[i]
                                first_hit_x = i
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
                                if i + 2 < len(graph_values) and graph_values[i+2] > graph_values[i+1] - 50:
                                    # 初当たりは必ずマイナス値
                                    if graph_values[i] < 0:
                                        first_hit_val = graph_values[i]
                                        first_hit_x = i
                                        break
                
                # 初当たり値がプラスの場合は0を表示
                if first_hit_val > 0:
                    first_hit_val = 0
                
                # オーバーレイ画像を作成
                overlay_img = cropped_img.copy()
                    
                # 検出されたグラフラインを描画
                prev_x = None
                prev_y = None
                
                # 緑色で統一（見やすさ重視）
                draw_color = (0, 255, 0)  # 緑色固定
                
                # グラフポイントを描画
                for x, value in graph_data_points:
                    # Y座標を計算（0ラインからの相対位置）
                    y = int(zero_line_in_crop - (value / analyzer.scale))
                    
                    # 画像範囲内かチェック
                    if 0 <= y < overlay_img.shape[0] and 0 <= x < overlay_img.shape[1]:
                        # 点を描画（より見やすくするため）
                        cv2.circle(overlay_img, (int(x), y), 2, draw_color, -1)
                        
                        # 線で接続
                        if prev_x is not None and prev_y is not None:
                            cv2.line(overlay_img, (int(prev_x), int(prev_y)), (int(x), y), draw_color, 2)
                        
                        prev_x = x
                        prev_y = y
                
                # 最高値、最低値、初当たりの位置を見つける
                # MAXが0に修正された場合は、元の最高値のインデックスを保持
                if max_val == 0 and max(graph_values) < 0:
                    max_idx = graph_values.index(max(graph_values))
                else:
                    max_idx = graph_values.index(max_val)
                min_idx = graph_values.index(min_val)
                
                # 横線を描画（最低値、最高値、現在値、初当たり値）
                # 最高値ライン（端から端まで）
                max_y = int(zero_line_in_crop - (max_val / analyzer.scale))
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
                min_y = int(zero_line_in_crop - (min_val / analyzer.scale))
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
                current_y = int(zero_line_in_crop - (current_val / analyzer.scale))
                if 0 <= current_y < overlay_img.shape[0]:
                    cv2.line(overlay_img, (0, current_y), (overlay_img.shape[1], current_y), (255, 255, 0), 2)
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
                    first_hit_y = int(zero_line_in_crop - (first_hit_val / analyzer.scale))
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
                
                # 結果を保存
                analysis_results.append({
                    'name': uploaded_file.name,
                    'original_image': img_array,  # 元画像を保存
                    'cropped_image': cropped_img,  # 切り抜き画像
                    'overlay_image': overlay_img,  # オーバーレイ画像
                    'success': True,
                    'max_val': int(max_val),
                    'min_val': int(min_val),
                    'current_val': int(current_val),
                    'first_hit_val': int(first_hit_val) if first_hit_x is not None else None,
                    'dominant_color': dominant_color,
                    'ocr_data': ocr_data  # OCRデータを追加
                })
            else:
                # 解析失敗時
                analysis_results.append({
                    'name': uploaded_file.name,
                    'original_image': img_array,  # 元画像を保存
                    'cropped_image': cropped_img,
                    'overlay_image': cropped_img,  # 解析失敗時は切り抜き画像を使用
                    'success': False,
                    'ocr_data': ocr_data  # OCRデータを追加
                })
    
    # プログレスバーを完了
    progress_bar.progress(1.0)
    status_text.text('✅ 全ての画像の処理が完了しました！')
    detail_text.empty()
    
    # 結果をグリッド表示
    st.markdown("### 📊 解析結果一覧")
    
    # 解析結果を2列で表示
    cols = st.columns(2)
    
    for idx, result in enumerate(analysis_results):
        with cols[idx % 2]:
            # 台番号を優先表示、なければファイル名
            if result.get('ocr_data') and result['ocr_data'].get('machine_number'):
                display_name = result['ocr_data']['machine_number']
            else:
                display_name = result['name']
            st.markdown(f"#### {idx + 1}. {display_name}")
            
            # 解析結果画像
            st.image(result['overlay_image'], use_column_width=True)
            
            # 元画像を折りたたみ可能に
            with st.expander("📷 元画像を表示"):
                st.image(result['original_image'], use_column_width=True)
            
            # テスト切り抜き機能（開発用）
            with st.expander("🧪 切り抜きテスト（開発用）"):
                st.caption("※ これは開発用のテスト機能です。通常の解析には影響しません。")
                
                # 現状の仕様
                st.markdown("#### 現状の仕様（メイン処理）")
                try:
                    # 現在の実装と同じロジック
                    test_hsv = cv2.cvtColor(result['original_image'], cv2.COLOR_RGB2HSV)
                    test_orange_mask = cv2.inRange(test_hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
                    test_height, test_width = result['original_image'].shape[:2]
                    test_gray = cv2.cvtColor(result['original_image'], cv2.COLOR_RGB2GRAY)
                    
                    # オレンジバーの検出
                    current_orange_bottom = 0
                    for y in range(test_height//2):
                        if np.sum(test_orange_mask[y, :]) > test_width * 0.3 * 255:
                            current_orange_bottom = y
                    
                    # オレンジバーの下端を正確に見つける
                    if current_orange_bottom > 0:
                        for y in range(current_orange_bottom, min(current_orange_bottom + 100, test_height)):
                            if np.sum(test_orange_mask[y, :]) < test_width * 0.1 * 255:
                                current_orange_bottom = y
                                break
                    else:
                        current_orange_bottom = 150
                    
                    # ゼロライン検出
                    search_start_current = current_orange_bottom + 50
                    search_end_current = min(test_height - 100, current_orange_bottom + 400)
                    
                    best_score_current = 0
                    zero_line_current = (search_start_current + search_end_current) // 2
                    
                    for y in range(search_start_current, search_end_current):
                        row = test_gray[y, 100:test_width-100]
                        darkness = 1.0 - (np.mean(row) / 255.0)
                        uniformity = 1.0 - (np.std(row) / 128.0)
                        score = darkness * 0.5 + uniformity * 0.5
                        
                        if score > best_score_current:
                            best_score_current = score
                            zero_line_current = y
                    
                    # 切り抜き
                    top_current = max(0, zero_line_current - 246)
                    bottom_current = min(test_height, zero_line_current + 247)
                    left_current = 125
                    right_current = test_width - 125
                    
                    cropped_current = result['original_image'][int(top_current):int(bottom_current), int(left_current):int(right_current)].copy()
                    
                    # グリッドライン追加
                    zero_in_crop_current = zero_line_current - top_current
                    cv2.line(cropped_current, (0, int(zero_in_crop_current)), (cropped_current.shape[1], int(zero_in_crop_current)), (0, 0, 255), 2)
                    cv2.putText(cropped_current, 'Zero (Current)', (10, int(zero_in_crop_current) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    
                    st.image(cropped_current, caption="現状の仕様による切り抜き", use_column_width=True)
                    st.info(f"オレンジバー: Y={current_orange_bottom}, ゼロライン: Y={zero_line_current}, スコア: {best_score_current:.3f}")
                    
                except Exception as e:
                    st.error(f"現状の仕様でエラーが発生: {str(e)}")
                
                # A案: グラフエリア中央方式
                st.markdown("#### A案: グラフエリア中央方式")
                try:
                    # グラフエリアの検出
                    test_gray = cv2.cvtColor(result['original_image'], cv2.COLOR_RGB2GRAY)
                    test_height, test_width = result['original_image'].shape[:2]
                    
                    # オレンジバーの位置は既に検出済みなので、そこから探す
                    # ※ オレンジバーの位置を再検出
                    test_hsv = cv2.cvtColor(result['original_image'], cv2.COLOR_RGB2HSV)
                    test_orange_mask = cv2.inRange(test_hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
                    test_orange_bottom = 0
                    
                    for y in range(test_height//2):
                        if np.sum(test_orange_mask[y, :]) > test_width * 0.3 * 255:
                            test_orange_bottom = y
                    
                    if test_orange_bottom > 0:
                        for y in range(test_orange_bottom, min(test_orange_bottom + 100, test_height)):
                            if np.sum(test_orange_mask[y, :]) < test_width * 0.1 * 255:
                                test_orange_bottom = y
                                break
                    
                    # グラフエリアの上端（オレンジバーの下）
                    graph_top_a = test_orange_bottom + 20
                    
                    # グラフエリアの下端を見つける（統計情報の上）
                    graph_bottom_a = test_height - 300  # デフォルト値
                    for y in range(test_height - 300, test_orange_bottom, -1):
                        row = test_gray[y, test_width//4:test_width*3//4]
                        # 背景が急に暗くなる部分を探す（統計情報エリア）
                        if np.mean(row) < 150:
                            graph_bottom_a = y
                            break
                    
                    # グラフエリアの中央をゼロラインとする
                    zero_line_a = graph_top_a + (graph_bottom_a - graph_top_a) // 2
                    
                    # 切り抜き
                    top_a = max(0, zero_line_a - 246)
                    bottom_a = min(test_height, zero_line_a + 247)
                    left_a = 125
                    right_a = test_width - 125
                    
                    cropped_a = result['original_image'][int(top_a):int(bottom_a), int(left_a):int(right_a)].copy()
                    
                    # グリッドライン追加（簡易版）
                    zero_in_crop_a = zero_line_a - top_a
                    cv2.line(cropped_a, (0, int(zero_in_crop_a)), (cropped_a.shape[1], int(zero_in_crop_a)), (255, 0, 0), 2)
                    cv2.putText(cropped_a, 'Zero (A)', (10, int(zero_in_crop_a) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    
                    st.image(cropped_a, caption="A案による切り抜き", use_column_width=True)
                    st.info(f"グラフエリア: top={graph_top_a}, bottom={graph_bottom_a}, zero={zero_line_a}")
                    
                except Exception as e:
                    st.error(f"A案でエラーが発生: {str(e)}")
                
                # B案: 暗い水平線検出方式
                st.markdown("#### B案: 暗い水平線検出方式")
                try:
                    # より広い範囲で暗い線を探す
                    search_start_b = test_orange_bottom + 50
                    search_end_b = test_height - 200
                    
                    best_score_b = 0
                    zero_line_b = (search_start_b + search_end_b) // 2
                    scores_b = []
                    
                    # エッジ検出を使用
                    edges = cv2.Canny(test_gray, 50, 150)
                    
                    for y in range(search_start_b, search_end_b):
                        # 左右の余白を考慮
                        left_margin = test_width // 6
                        right_margin = test_width - left_margin
                        
                        # エッジの強度をチェック
                        edge_row = edges[y, left_margin:right_margin]
                        edge_strength = np.sum(edge_row > 0) / len(edge_row)
                        
                        # グレースケール値をチェック
                        gray_row = test_gray[y, left_margin:right_margin]
                        
                        # スコア計算
                        darkness = 1.0 - (np.mean(gray_row) / 255.0)
                        uniformity = 1.0 - (np.std(gray_row) / 128.0)
                        score = darkness * 0.4 + uniformity * 0.3 + edge_strength * 0.3
                        
                        scores_b.append((y, score))
                        
                        if score > best_score_b:
                            best_score_b = score
                            zero_line_b = y
                    
                    # 切り抜き
                    top_b = max(0, zero_line_b - 246)
                    bottom_b = min(test_height, zero_line_b + 247)
                    left_b = 125
                    right_b = test_width - 125
                    
                    cropped_b = result['original_image'][int(top_b):int(bottom_b), int(left_b):int(right_b)].copy()
                    
                    # グリッドライン追加（簡易版）
                    zero_in_crop_b = zero_line_b - top_b
                    cv2.line(cropped_b, (0, int(zero_in_crop_b)), (cropped_b.shape[1], int(zero_in_crop_b)), (0, 255, 0), 2)
                    cv2.putText(cropped_b, 'Zero (B)', (10, int(zero_in_crop_b) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    st.image(cropped_b, caption="B案による切り抜き", use_column_width=True)
                    st.info(f"検出スコア: {best_score_b:.3f}, ゼロライン: {zero_line_b}")
                    
                    # スコアのグラフを表示（上位10個）
                    top_scores = sorted(scores_b, key=lambda x: x[1], reverse=True)[:10]
                    st.caption("上位10個の候補位置:")
                    for i, (y, score) in enumerate(top_scores):
                        st.caption(f"{i+1}. Y={y}, スコア={score:.3f}")
                    
                except Exception as e:
                    st.error(f"B案でエラーが発生: {str(e)}")
                
                # C案: グリッド目盛りベース方式（IMG_0167.PNG対応）
                st.markdown("#### C案: グリッド目盛りベース方式")
                try:
                    # 右側のグリッド目盛りをOCRで読み取る
                    right_area = result['original_image'][:, test_width - 100:]
                    right_gray = cv2.cvtColor(right_area, cv2.COLOR_RGB2GRAY)
                    
                    # OCRで数値を検出
                    import pytesseract
                    ocr_text = pytesseract.image_to_string(right_gray, config='--psm 6 -c tessedit_char_whitelist=0123456789,.-')
                    
                    # 数値を抽出
                    import re
                    numbers = re.findall(r'-?\d+[,.]?\d*', ocr_text.replace(',', ''))
                    detected_scale = None
                    
                    if numbers:
                        # 最大値を推定（通常は30000, 50000, 80000など）
                        max_num = max([abs(float(n)) for n in numbers if n])
                        if max_num > 20000:
                            detected_scale = max_num
                    
                    # スケールに基づいてグラフエリアを推定
                    if detected_scale:
                        st.caption(f"検出されたスケール: ±{int(detected_scale):,}")
                    else:
                        detected_scale = 30000  # デフォルト
                        st.caption("スケール検出失敗、デフォルト値を使用")
                    
                    # グラフエリアをオレンジバーから推定
                    graph_top_c = test_orange_bottom + 30
                    # スケールに応じてグラフの高さを調整
                    if detected_scale >= 50000:
                        graph_height = 600  # より大きなグラフ
                    else:
                        graph_height = 493  # 標準サイズ
                    
                    # グラフの中央をゼロラインとする
                    zero_line_c = graph_top_c + graph_height // 2
                    
                    # 切り抜き
                    top_c = max(0, zero_line_c - graph_height // 2)
                    bottom_c = min(test_height, zero_line_c + graph_height // 2)
                    left_c = 125
                    right_c = test_width - 125
                    
                    cropped_c = result['original_image'][int(top_c):int(bottom_c), int(left_c):int(right_c)].copy()
                    
                    # グリッドライン追加
                    zero_in_crop_c = zero_line_c - top_c
                    cv2.line(cropped_c, (0, int(zero_in_crop_c)), (cropped_c.shape[1], int(zero_in_crop_c)), (255, 0, 255), 2)
                    cv2.putText(cropped_c, 'Zero (C)', (10, int(zero_in_crop_c) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                    
                    st.image(cropped_c, caption="C案による切り抜き", use_column_width=True)
                    st.info(f"グラフ高さ: {graph_height}px, ゼロライン: {zero_line_c}")
                    
                except Exception as e:
                    st.error(f"C案でエラーが発生: {str(e)}")
                
                # D案: 適応的検出方式（複合アプローチ）
                st.markdown("#### D案: 適応的検出方式")
                try:
                    # 複数の方法を試して最適なものを選択
                    candidates = []
                    
                    # 方法1: 現在の実装と同じ（暗い線検出）
                    search_start_d = test_orange_bottom + 50
                    search_end_d = min(test_height - 100, test_orange_bottom + 400)
                    
                    best_darkness_score = 0
                    darkness_zero = (search_start_d + search_end_d) // 2
                    
                    for y in range(search_start_d, search_end_d):
                        row = test_gray[y, 100:test_width-100]
                        darkness = 1.0 - (np.mean(row) / 255.0)
                        uniformity = 1.0 - (np.std(row) / 128.0)
                        score = darkness * 0.5 + uniformity * 0.5
                        
                        if score > best_darkness_score:
                            best_darkness_score = score
                            darkness_zero = y
                    
                    if best_darkness_score > 0.3:  # 閾値
                        candidates.append(('暗い線検出', darkness_zero, best_darkness_score))
                    
                    # 方法2: グラフ線の分布から推定
                    hsv_d = cv2.cvtColor(result['original_image'], cv2.COLOR_RGB2HSV)
                    # ピンク・紫系の色を検出
                    pink_mask = cv2.inRange(hsv_d, np.array([140, 50, 50]), np.array([170, 255, 255]))
                    purple_mask = cv2.inRange(hsv_d, np.array([270, 50, 50]), np.array([320, 255, 255]))
                    graph_mask = cv2.bitwise_or(pink_mask, purple_mask)
                    
                    # グラフ線のY座標分布を調べる
                    graph_y_coords = []
                    for y in range(search_start_d, search_end_d):
                        if np.sum(graph_mask[y, 100:test_width-100]) > 50:
                            graph_y_coords.append(y)
                    
                    if graph_y_coords:
                        # グラフの中央値をゼロラインとして推定
                        median_y = int(np.median(graph_y_coords))
                        candidates.append(('グラフ分布', median_y, 0.5))
                    
                    # 方法3: デフォルト位置（グラフエリアの推定中央）
                    default_zero = test_orange_bottom + 300
                    candidates.append(('デフォルト', default_zero, 0.1))
                    
                    # 最適な候補を選択
                    if candidates:
                        candidates.sort(key=lambda x: x[2], reverse=True)
                        best_method, zero_line_d, confidence = candidates[0]
                        
                        # 切り抜き
                        top_d = max(0, zero_line_d - 246)
                        bottom_d = min(test_height, zero_line_d + 247)
                        left_d = 125
                        right_d = test_width - 125
                        
                        cropped_d = result['original_image'][int(top_d):int(bottom_d), int(left_d):int(right_d)].copy()
                        
                        # グリッドライン追加
                        zero_in_crop_d = zero_line_d - top_d
                        cv2.line(cropped_d, (0, int(zero_in_crop_d)), (cropped_d.shape[1], int(zero_in_crop_d)), (0, 255, 255), 2)
                        cv2.putText(cropped_d, 'Zero (D)', (10, int(zero_in_crop_d) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                        
                        st.image(cropped_d, caption="D案による切り抜き", use_column_width=True)
                        st.info(f"選択された方法: {best_method}, 信頼度: {confidence:.2f}")
                        
                        # 全候補を表示
                        st.caption("検出候補:")
                        for method, y, score in candidates:
                            st.caption(f"- {method}: Y={y}, スコア={score:.3f}")
                    
                except Exception as e:
                    st.error(f"D案でエラーが発生: {str(e)}")
                
                # E案: グラフ線ベース検出方式（IMG_0164.PNG対応）
                st.markdown("#### E案: グラフ線ベース検出方式")
                try:
                    # グラフの色を検出（紫、ピンク、緑、青など）
                    hsv_e = cv2.cvtColor(result['original_image'], cv2.COLOR_RGB2HSV)
                    
                    # 複数の色範囲でグラフ線を検出
                    masks = []
                    # 紫色
                    masks.append(cv2.inRange(hsv_e, np.array([130, 30, 30]), np.array([160, 255, 255])))
                    # ピンク色
                    masks.append(cv2.inRange(hsv_e, np.array([160, 30, 30]), np.array([180, 255, 255])))
                    masks.append(cv2.inRange(hsv_e, np.array([0, 30, 30]), np.array([10, 255, 255])))
                    # 緑色
                    masks.append(cv2.inRange(hsv_e, np.array([40, 30, 30]), np.array([80, 255, 255])))
                    # 青色
                    masks.append(cv2.inRange(hsv_e, np.array([100, 30, 30]), np.array([130, 255, 255])))
                    
                    # 全てのマスクを結合
                    graph_mask_e = masks[0]
                    for mask in masks[1:]:
                        graph_mask_e = cv2.bitwise_or(graph_mask_e, mask)
                    
                    # グラフ線が存在するY座標を収集
                    graph_y_positions = []
                    search_start_e = test_orange_bottom + 50
                    search_end_e = test_height - 300
                    
                    for y in range(search_start_e, search_end_e):
                        # 中央部分のみチェック（左右の余白を除く）
                        center_region = graph_mask_e[y, test_width//4:test_width*3//4]
                        if np.sum(center_region) > 100:  # 閾値
                            graph_y_positions.append(y)
                    
                    if graph_y_positions:
                        # グラフ線の最小Y座標と最大Y座標を取得
                        min_y = min(graph_y_positions)
                        max_y = max(graph_y_positions)
                        
                        # グラフがほぼ水平な場合（変動が少ない）
                        if max_y - min_y < 50:
                            # グラフ線の平均位置をゼロラインとする
                            zero_line_e = int(np.mean(graph_y_positions))
                            detection_method = "水平グラフ検出"
                        else:
                            # グラフに変動がある場合は、グラフの重心をゼロラインとする
                            weighted_sum = 0
                            weight_total = 0
                            for y in graph_y_positions:
                                weight = np.sum(graph_mask_e[y, test_width//4:test_width*3//4])
                                weighted_sum += y * weight
                                weight_total += weight
                            zero_line_e = int(weighted_sum / weight_total) if weight_total > 0 else int(np.mean(graph_y_positions))
                            detection_method = "グラフ重心検出"
                    else:
                        # グラフ線が検出できない場合のフォールバック
                        # オレンジバーから一定の比率で推定
                        zero_line_e = test_orange_bottom + int((search_end_e - test_orange_bottom) * 0.4)
                        detection_method = "フォールバック"
                    
                    # 切り抜き
                    top_e = max(0, zero_line_e - 246)
                    bottom_e = min(test_height, zero_line_e + 247)
                    left_e = 125
                    right_e = test_width - 125
                    
                    cropped_e = result['original_image'][int(top_e):int(bottom_e), int(left_e):int(right_e)].copy()
                    
                    # グリッドライン追加
                    zero_in_crop_e = zero_line_e - top_e
                    cv2.line(cropped_e, (0, int(zero_in_crop_e)), (cropped_e.shape[1], int(zero_in_crop_e)), (255, 255, 0), 2)
                    cv2.putText(cropped_e, 'Zero (E)', (10, int(zero_in_crop_e) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    
                    # グラフ線の検出結果を可視化（デバッグ用）
                    if graph_y_positions:
                        for y in [min(graph_y_positions), max(graph_y_positions)]:
                            y_in_crop = y - top_e
                            if 0 <= y_in_crop < cropped_e.shape[0]:
                                cv2.line(cropped_e, (0, int(y_in_crop)), (50, int(y_in_crop)), (0, 255, 255), 1)
                    
                    st.image(cropped_e, caption="E案による切り抜き", use_column_width=True)
                    st.info(f"検出方法: {detection_method}, ゼロライン: {zero_line_e}")
                    if graph_y_positions:
                        st.caption(f"グラフ検出範囲: Y={min(graph_y_positions)}〜{max(graph_y_positions)} (幅: {max(graph_y_positions)-min(graph_y_positions)}px)")
                    
                except Exception as e:
                    st.error(f"E案でエラーが発生: {str(e)}")
                
                # F案: 固定位置方式（IMG_0xxx.PNG専用）
                st.markdown("#### F案: 固定位置方式")
                try:
                    # IMG_0xxx.PNGシリーズの特徴を検出
                    is_img_series = False
                    
                    # 特徴1: 画面サイズが特定の値
                    if test_height > 2400 and test_height < 2700:
                        # 特徴2: オレンジバーの位置が特定の範囲
                        if test_orange_bottom > 650 and test_orange_bottom < 750:
                            # 特徴3: 背景色がグレー系
                            bg_sample = test_gray[test_orange_bottom + 100:test_orange_bottom + 200, test_width//4:test_width*3//4]
                            bg_mean = np.mean(bg_sample)
                            if bg_mean > 200 and bg_mean < 240:
                                is_img_series = True
                    
                    if is_img_series:
                        # IMG_0xxx.PNG用の固定位置
                        # 実際の観察から、ゼロラインは約Y=1350付近にある
                        zero_line_f = test_orange_bottom + 650  # オレンジバーから650px下
                        detection_info = "IMG_0xxx.PNG検出"
                    else:
                        # 通常の画像用（現在の実装と同じ）
                        search_start_f = test_orange_bottom + 50
                        search_end_f = min(test_height - 100, test_orange_bottom + 400)
                        
                        best_score_f = 0
                        zero_line_f = (search_start_f + search_end_f) // 2
                        
                        for y in range(search_start_f, search_end_f):
                            row = test_gray[y, 100:test_width-100]
                            darkness = 1.0 - (np.mean(row) / 255.0)
                            uniformity = 1.0 - (np.std(row) / 128.0)
                            score = darkness * 0.5 + uniformity * 0.5
                            
                            if score > best_score_f:
                                best_score_f = score
                                zero_line_f = y
                        
                        detection_info = f"通常検出（スコア: {best_score_f:.3f}）"
                    
                    # 切り抜き
                    top_f = max(0, zero_line_f - 246)
                    bottom_f = min(test_height, zero_line_f + 247)
                    left_f = 125
                    right_f = test_width - 125
                    
                    cropped_f = result['original_image'][int(top_f):int(bottom_f), int(left_f):int(right_f)].copy()
                    
                    # グリッドライン追加
                    zero_in_crop_f = zero_line_f - top_f
                    cv2.line(cropped_f, (0, int(zero_in_crop_f)), (cropped_f.shape[1], int(zero_in_crop_f)), (255, 0, 255), 2)
                    cv2.putText(cropped_f, 'Zero (F)', (10, int(zero_in_crop_f) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                    
                    # 追加のグリッドライン（±10000）
                    scale_f = 122  # 固定スケール
                    for val, label in [(10000, '+10k'), (-10000, '-10k')]:
                        y_offset = int(val / scale_f)
                        y_pos = int(zero_in_crop_f - y_offset)
                        if 0 < y_pos < cropped_f.shape[0]:
                            cv2.line(cropped_f, (0, y_pos), (cropped_f.shape[1], y_pos), (200, 200, 200), 1)
                            cv2.putText(cropped_f, label, (10, y_pos - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
                    
                    st.image(cropped_f, caption="F案による切り抜き", use_column_width=True)
                    st.info(f"{detection_info}, ゼロライン: {zero_line_f}")
                    
                    if is_img_series:
                        st.caption("IMG_0xxx.PNGシリーズと判定されました")
                        st.caption(f"背景輝度: {bg_mean:.1f}, 画像高さ: {test_height}px")
                    
                except Exception as e:
                    st.error(f"F案でエラーが発生: {str(e)}")
                
                # G案: IMG_0xxx.PNG専用拡張検索方式
                st.markdown("#### G案: IMG_0xxx.PNG専用拡張検索方式")
                try:
                    # IMG_0xxx.PNGシリーズの検出
                    is_img_series_g = False
                    if test_height > 2400 and test_height < 2700:
                        if test_orange_bottom < 1000:  # オレンジバーが上部にある
                            # 背景色チェック
                            bg_sample_g = test_gray[test_orange_bottom + 100:test_orange_bottom + 200, test_width//4:test_width*3//4]
                            bg_mean_g = np.mean(bg_sample_g)
                            if bg_mean_g > 200 and bg_mean_g < 240:
                                is_img_series_g = True
                    
                    if is_img_series_g:
                        # IMG_0xxx.PNG用の拡張検索範囲
                        search_start_g = test_orange_bottom + 200  # より下から開始
                        search_end_g = min(test_height - 300, test_orange_bottom + 800)  # より広い範囲
                        detection_info_g = "IMG_0xxx.PNG検出（拡張範囲）"
                    else:
                        # 通常の検索範囲
                        search_start_g = test_orange_bottom + 50
                        search_end_g = min(test_height - 100, test_orange_bottom + 400)
                        detection_info_g = "通常検出"
                    
                    best_score_g = 0
                    zero_line_g = (search_start_g + search_end_g) // 2
                    scores_g = []
                    
                    for y in range(search_start_g, search_end_g):
                        row_g = test_gray[y, 100:test_width-100]
                        darkness_g = 1.0 - (np.mean(row_g) / 255.0)
                        uniformity_g = 1.0 - (np.std(row_g) / 128.0)
                        score_g = darkness_g * 0.5 + uniformity_g * 0.5
                        
                        scores_g.append((y, score_g))
                        
                        if score_g > best_score_g:
                            best_score_g = score_g
                            zero_line_g = y
                    
                    # 切り抜き
                    top_g = max(0, zero_line_g - 246)
                    bottom_g = min(test_height, zero_line_g + 247)
                    left_g = 125
                    right_g = test_width - 125
                    
                    cropped_g = result['original_image'][int(top_g):int(bottom_g), int(left_g):int(right_g)].copy()
                    
                    # グリッドライン追加
                    zero_in_crop_g = zero_line_g - top_g
                    cv2.line(cropped_g, (0, int(zero_in_crop_g)), (cropped_g.shape[1], int(zero_in_crop_g)), (0, 255, 128), 2)
                    cv2.putText(cropped_g, 'Zero (G)', (10, int(zero_in_crop_g) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 128), 2)
                    
                    st.image(cropped_g, caption="G案による切り抜き", use_column_width=True)
                    st.info(f"{detection_info_g}, ゼロライン: {zero_line_g}, スコア: {best_score_g:.3f}")
                    st.caption(f"検索範囲: Y={search_start_g}〜{search_end_g} (幅: {search_end_g-search_start_g}px)")
                    
                    if is_img_series_g:
                        # 上位スコアを表示
                        top_scores_g = sorted(scores_g, key=lambda x: x[1], reverse=True)[:5]
                        st.caption("上位5個の候補:")
                        for i, (y, score) in enumerate(top_scores_g):
                            st.caption(f"{i+1}. Y={y}, スコア={score:.3f}")
                    
                except Exception as e:
                    st.error(f"G案でエラーが発生: {str(e)}")
                
                # H案: G案改良版（スケール調整付き）
                st.markdown("#### H案: G案改良版（スケール調整付き）")
                try:
                    # IMG_0xxx.PNGシリーズの検出
                    is_img_series_h = False
                    if test_height > 2400 and test_height < 2700:
                        if test_orange_bottom < 1000:  # オレンジバーが上部にある
                            # 背景色チェック
                            bg_sample_h = test_gray[test_orange_bottom + 100:test_orange_bottom + 200, test_width//4:test_width*3//4]
                            bg_mean_h = np.mean(bg_sample_h)
                            if bg_mean_h > 200 and bg_mean_h < 240:
                                is_img_series_h = True
                    
                    if is_img_series_h:
                        # IMG_0xxx.PNG用の拡張検索範囲
                        search_start_h = test_orange_bottom + 200
                        search_end_h = min(test_height - 300, test_orange_bottom + 800)
                        detection_info_h = "IMG_0xxx.PNG検出（拡張範囲）"
                        # IMG_0xxx.PNG用のスケール（±50000）
                        scale_h = 50000 / 408  # 約122.5玉/px（グラフ高さ816pxで±50000）
                        crop_top_offset = 408  # 上方向の切り抜きサイズ
                        crop_bottom_offset = 408  # 下方向の切り抜きサイズ
                    else:
                        # 通常の検索範囲
                        search_start_h = test_orange_bottom + 50
                        search_end_h = min(test_height - 100, test_orange_bottom + 400)
                        detection_info_h = "通常検出"
                        # 通常のスケール（±30000）
                        scale_h = 30000 / 246  # 約122玉/px
                        crop_top_offset = 246
                        crop_bottom_offset = 247
                    
                    best_score_h = 0
                    zero_line_h = (search_start_h + search_end_h) // 2
                    
                    for y in range(search_start_h, search_end_h):
                        row_h = test_gray[y, 100:test_width-100]
                        darkness_h = 1.0 - (np.mean(row_h) / 255.0)
                        uniformity_h = 1.0 - (np.std(row_h) / 128.0)
                        score_h = darkness_h * 0.5 + uniformity_h * 0.5
                        
                        if score_h > best_score_h:
                            best_score_h = score_h
                            zero_line_h = y
                    
                    # 切り抜き（スケールに応じたサイズ）
                    top_h = max(0, zero_line_h - crop_top_offset)
                    bottom_h = min(test_height, zero_line_h + crop_bottom_offset)
                    left_h = 125
                    right_h = test_width - 125
                    
                    cropped_h = result['original_image'][int(top_h):int(bottom_h), int(left_h):int(right_h)].copy()
                    
                    # グリッドライン追加
                    zero_in_crop_h = zero_line_h - top_h
                    cv2.line(cropped_h, (0, int(zero_in_crop_h)), (cropped_h.shape[1], int(zero_in_crop_h)), (128, 255, 128), 2)
                    cv2.putText(cropped_h, 'Zero (H)', (10, int(zero_in_crop_h) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 255, 128), 2)
                    
                    # スケールに応じたグリッドライン
                    if is_img_series_h:
                        # ±50000, ±25000のライン
                        grid_values = [(50000, '+50k'), (25000, '+25k'), (-25000, '-25k'), (-50000, '-50k')]
                    else:
                        # ±30000, ±10000のライン
                        grid_values = [(30000, '+30k'), (10000, '+10k'), (-10000, '-10k'), (-30000, '-30k')]
                    
                    for val, label in grid_values:
                        y_offset = int(val / scale_h)
                        y_pos = int(zero_in_crop_h - y_offset)
                        if 0 < y_pos < cropped_h.shape[0]:
                            cv2.line(cropped_h, (0, y_pos), (cropped_h.shape[1], y_pos), (200, 200, 200), 1)
                            cv2.putText(cropped_h, label, (10, y_pos - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
                    
                    st.image(cropped_h, caption="H案による切り抜き", use_column_width=True)
                    st.info(f"{detection_info_h}, ゼロライン: {zero_line_h}, スコア: {best_score_h:.3f}")
                    st.caption(f"スケール: ±{int(scale_h * crop_top_offset):,}, 切り抜きサイズ: {int(bottom_h - top_h)}px")
                    
                except Exception as e:
                    st.error(f"H案でエラーが発生: {str(e)}")
            
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
                
                first_hit_text = f"{result['first_hit_val']:,}玉" if result['first_hit_val'] is not None else "なし"
                first_hit_class = get_value_class(result['first_hit_val']) if result['first_hit_val'] is not None else ""
                
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-item">
                        <span class="stat-label">📈 最高値</span>
                        <span class="stat-value {get_value_class(result['max_val'])}">{result['max_val']:,}玉</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">📉 最低値</span>
                        <span class="stat-value {get_value_class(result['min_val'])}">{result['min_val']:,}玉</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">🎯 現在値</span>
                        <span class="stat-value {get_value_class(result['current_val'])}">{result['current_val']:,}玉</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">🎰 初当たり</span>
                        <span class="stat-value {first_hit_class}">{first_hit_text}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # OCRデータがある場合は表示
                if result.get('ocr_data') and any(result['ocr_data'].values()):
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
                    
                    # 台番号
                    if ocr.get('machine_number'):
                        ocr_html += f'<div class="ocr-item"><span class="ocr-label">🔢 台番号</span><span class="ocr-value">{ocr["machine_number"]}</span></div>'
                    
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
                        ocr_html += f'<div class="ocr-item"><span class="ocr-label">💰 最高出玉</span><span class="ocr-value">{ocr["max_payout"]}玉</span></div>'
                    
                    ocr_html += '</div>'
                    st.markdown(ocr_html, unsafe_allow_html=True)
                
            else:
                st.warning("⚠️ グラフデータを検出できませんでした")
            
            # 区切り線（各列内で）
            if idx < len(analysis_results) - 2:
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
            total_balance_yen = total_balance * 4
            avg_balance = total_balance / len(success_results)
            avg_balance_yen = avg_balance * 4
            max_result = max(success_results, key=lambda x: x['current_val'])
            min_result = min(success_results, key=lambda x: x['current_val'])
            
            # 統計情報を3列で表示
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "合計収支",
                    f"{total_balance_yen:+,}円",
                    f"{total_balance:+,}玉"
                )
            
            with col2:
                st.metric(
                    "平均収支",
                    f"{avg_balance_yen:+,.0f}円",
                    f"{avg_balance:+,.0f}玉"
                )
            
            with col3:
                st.metric(
                    "解析台数",
                    f"{len(success_results)}台",
                    f"成功率 {len(success_results)/len(analysis_results)*100:.0f}%"
                )
    
    # データフレーム作成
    table_data = []
    for idx, result in enumerate(analysis_results):
        if result.get('success'):
            row = {
                '番号': idx + 1,
                'ファイル名': result['name'],
                '最高値': f"{result['max_val']:,}",
                '最低値': f"{result['min_val']:,}",
                '現在値': f"{result['current_val']:,}",
                '初当たり': f"{result['first_hit_val']:,}" if result['first_hit_val'] is not None else "-",
                '収支(円)': f"{result['current_val'] * 4:+,}",
            }
            
            # OCRデータがある場合は追加
            if result.get('ocr_data'):
                ocr = result['ocr_data']
                row.update({
                    '累計スタート': ocr.get('total_start', '-'),
                    '大当り回数': f"{ocr.get('jackpot_count')}回" if ocr.get('jackpot_count') else '-',
                    '初当り回数': f"{ocr.get('first_hit_count')}回" if ocr.get('first_hit_count') else '-',
                    '確率': ocr.get('jackpot_probability', '-'),
                    '最高出玉': f"{ocr.get('max_payout')}玉" if ocr.get('max_payout') else '-',
                })
            
            table_data.append(row)
    
    if table_data:
        df = pd.DataFrame(table_data)
        
        # 表示する列を選択（存在する列のみ）
        display_columns = ['番号', 'ファイル名', '累計スタート', '大当り回数', 
                          '最高値', '最低値', '現在値', '初当たり', '収支(円)']
        display_columns = [col for col in display_columns if col in df.columns]
        
        # データフレームを表示
        st.dataframe(
            df[display_columns],
            use_container_width=True,
            hide_index=True
        )
        
        # CSVダウンロード
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV ダウンロード",
            data=csv,
            file_name=f"pachi_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help="Excel等で開けるCSV形式でダウンロード"
        )
    
else:
    # アップロード前の表示
    st.info("👆 上のボタンから画像をアップロードしてください")
    
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
    - 0ライン基準：上246px、下247px（±30,000玉相当）
    - スケール：120玉/ピクセル
    - 左右余白：125px除外
    """)

# フッター
st.markdown("---")
st.markdown(f"""
🎰 パチンコグラフ解析システム v2.0  
更新日: {datetime.now().strftime('%Y/%m/%d')}  
Produced by [PPタウン](https://pp-town.com/)  
Created by [fivenine-design.com](https://fivenine-design.com)
""")