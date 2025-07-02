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
import time

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


# デフォルト値
default_settings = {
    'search_start_offset': 50,
    'search_end_offset': 400,
    'crop_top': 246,
    'crop_bottom': 247,
    'left_margin': 125,
    'right_margin': 125,
    # グリッドライン調整値
    'grid_30k_offset': 0,       # +30000ライン（最上部）
    'grid_20k_offset': 0,       # +20000ライン  
    'grid_10k_offset': 0,       # +10000ライン
    'grid_minus_10k_offset': 0, # -10000ライン
    'grid_minus_20k_offset': 0, # -20000ライン
    'grid_minus_30k_offset': 0  # -30000ライン（最下部）
}

# セッションステートの初期化（エキスパンダーより前に行う）
if 'settings' not in st.session_state:
    st.session_state.settings = default_settings.copy()

if 'saved_presets' not in st.session_state:
    st.session_state.saved_presets = {}

if 'show_adjustment' not in st.session_state:
    st.session_state.show_adjustment = False

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'current_preset_name' not in st.session_state:
    st.session_state.current_preset_name = 'デフォルト'

# Cookieからのログイン状態確認は一時的に無効化

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
            <h1 class="login-title">パチンコグラフ解析</h1>
            <p class="login-subtitle">認証が必要です</p>
        </div>
        """, unsafe_allow_html=True)
        
        # スペース
        st.markdown("<br>", unsafe_allow_html=True)
        
        # パスワード入力
        password = st.text_input(
            "パスワード",
            type="password",
            placeholder="パスワードを入力",
            label_visibility="collapsed",
            key="password_input"
        )
        
        # ログインボタン
        if st.button("ログイン", type="primary", use_container_width=True):
            if password == "059":
                st.session_state.authenticated = True
                # Cookie設定は一時的に無効化
                st.success("✅ ログインしました")
                st.rerun()
            else:
                st.error("❌ パスワードが違います")
        
        # フッター
        st.markdown(f"""
        <div class="login-footer">
            パチンコグラフ解析システム v2.0<br>
            更新日: {datetime.now().strftime('%Y/%m/%d')}<br>
            Produced by <a href="https://pp-town.com/" target="_blank">PPタウン</a><br>
            Created by <a href="https://fivenine-design.com" target="_blank">fivenine-design.com</a>
        </div>
        """, unsafe_allow_html=True)
    
    # 認証されていない場合はここで処理を終了
    st.stop()

# プリセットをファイルから読み込み
try:
    import pickle
    import os
    preset_file = os.path.join(os.path.expanduser('~'), '.pachi777_presets.pkl')
    if os.path.exists(preset_file):
        with open(preset_file, 'rb') as f:
            saved_data = pickle.load(f)
            if 'presets' in saved_data:
                st.session_state.saved_presets = saved_data['presets']
            # 'current'設定の読み込みを削除（デフォルト値を保持するため）
            # if 'current' in saved_data:
            #     st.session_state.settings = saved_data['current']
except Exception as e:
    # 読み込みエラーは無視
    pass

# 調整機能（コラプス）
with st.expander("⚙️ 画像解析の調整設定", expanded=st.session_state.show_adjustment):
    st.markdown("##### 端末ごとの調整設定")
    st.caption("※ お使いの端末で撮影した画像に合わせて調整してください")
    
    # プリセット選択セクション
    st.markdown("### 📋 プリセット選択")
    
    # 保存されたプリセット一覧
    preset_names = ["デフォルト"] + list(st.session_state.saved_presets.keys())
    
    col_preset1, col_preset2 = st.columns([3, 1])
    
    with col_preset1:
        selected_preset_adjustment = st.selectbox(
            "設定プリセットを選択",
            preset_names,
            help="保存された設定を選択して適用します",
            key="adjustment_preset_select"
        )
    
    with col_preset2:
        # プリセット適用ボタン
        if st.button("📥 適用", use_container_width=True, key="apply_preset_adjustment"):
            if selected_preset_adjustment == "デフォルト":
                st.session_state.settings = default_settings.copy()
            else:
                st.session_state.settings = st.session_state.saved_presets[selected_preset_adjustment].copy()
            
            # 現在のプリセット名を保存
            st.session_state.current_preset_name = selected_preset_adjustment
            
            st.success(f"✅ '{selected_preset_adjustment}' を適用しました")
            st.rerun()
    
    st.divider()
    
    # テスト画像のアップロード（全幅で表示）
    test_image = st.file_uploader(
        "🖼️ テスト用画像をアップロード",
        type=['jpg', 'jpeg', 'png'],
        help="調整用の画像を1枚アップロードしてください",
        key="test_image"
    )
    
    # LocalStorageとの連携用JavaScript
    st.markdown("""
    <script>
    // LocalStorageから全設定を読み込む
    function loadAllSettings() {
        const allSettings = localStorage.getItem('pachi777_all_settings');
        if (allSettings) {
            return JSON.parse(allSettings);
        }
        return null;
    }
    
    // ページ読み込み時に設定を復元
    window.addEventListener('load', function() {
        const savedData = loadAllSettings();
        if (savedData) {
            // Streamlitのセッションステートを更新するためのメッセージ
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                key: 'load_saved_settings',
                value: savedData
            }, '*');
        }
    });
    </script>
    """, unsafe_allow_html=True)
    
    # 編集モードで選択されたプリセットの設定値を読み込む
    if ('edit_preset_mode' in st.session_state and 
        st.session_state.edit_preset_mode and 
        'edit_preset_select' in st.session_state and
        st.session_state.edit_preset_select != "新規作成" and
        st.session_state.edit_preset_select in st.session_state.saved_presets):
        # 選択されたプリセットの設定値を読み込む
        selected_preset_name = st.session_state.edit_preset_select
        if 'last_edited_preset' not in st.session_state or st.session_state.last_edited_preset != selected_preset_name:
            # 新しいプリセットが選択された場合のみ設定を更新
            st.session_state.settings = st.session_state.saved_presets[selected_preset_name].copy()
            st.session_state.last_edited_preset = selected_preset_name
            st.rerun()
    elif 'edit_preset_mode' in st.session_state and not st.session_state.edit_preset_mode:
        # 編集モードが解除された場合、状態をリセット
        if 'last_edited_preset' in st.session_state:
            del st.session_state.last_edited_preset
    
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
            # 設定用の入力フィールド
            st.markdown("### 🔍 ゼロライン検索設定")
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
            
            st.markdown("### ✂️ 切り抜きサイズの設定")
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
            st.markdown("### 📏 グリッドライン微調整")
            st.caption("※ 各グリッドラインを個別に調整できます")
            
            grid_col1, grid_col2, grid_col3 = st.columns(3)
            
            with grid_col1:
                grid_30k_offset = st.number_input(
                    "+30,000ライン調整",
                    min_value=-1000, max_value=1000, value=st.session_state.settings.get('grid_30k_offset', 0),
                    step=1, help="上端の+30,000ラインの位置調整"
                )
                grid_20k_offset = st.number_input(
                    "+20,000ライン調整",
                    min_value=-1000, max_value=1000, value=st.session_state.settings.get('grid_20k_offset', 0),
                    step=1, help="+20,000ラインの位置調整"
                )
            
            with grid_col2:
                grid_10k_offset = st.number_input(
                    "+10,000ライン調整",
                    min_value=-1000, max_value=1000, value=st.session_state.settings.get('grid_10k_offset', 0),
                    step=1, help="+10,000ラインの位置調整"
                )
                grid_minus_10k_offset = st.number_input(
                    "-10,000ライン調整",
                    min_value=-1000, max_value=1000, value=st.session_state.settings.get('grid_minus_10k_offset', 0),
                    step=1, help="-10,000ラインの位置調整"
                )
            
            with grid_col3:
                grid_minus_20k_offset = st.number_input(
                    "-20,000ライン調整",
                    min_value=-1000, max_value=1000, value=st.session_state.settings.get('grid_minus_20k_offset', 0),
                    step=1, help="-20,000ラインの位置調整"
                )
                grid_minus_30k_offset = st.number_input(
                    "-30,000ライン調整",
                    min_value=-1000, max_value=1000, value=st.session_state.settings.get('grid_minus_30k_offset', 0),
                    step=1, help="下端の-30,000ラインの位置調整"
                )
    
    # リアルタイムプレビュー
    if test_image:
        st.markdown("### 🖼️ リアルタイムプレビュー")
        
        
        # 現在の設定で切り抜き処理を実行
        search_start = orange_bottom + search_start_offset
        search_end = min(height - 100, orange_bottom + search_end_offset)
        
        # ゼロライン検出
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
        
        # 切り抜き
        top = max(0, zero_line_y - crop_top)
        bottom = min(height, zero_line_y + crop_bottom)
        left = left_margin
        right = width - right_margin
        
        # オーバーレイ画像を作成
        overlay_img = img_array.copy()
        
        # 検索範囲を可視化（濃い緑の枠線）
        cv2.rectangle(overlay_img, (100, search_start), (width-100, search_end), (0, 255, 0), 3)
        # 半透明の緑で塗りつぶし
        overlay = overlay_img.copy()
        cv2.rectangle(overlay, (100, search_start), (width-100, search_end), (0, 255, 0), -1)
        overlay_img = cv2.addWeighted(overlay_img, 0.8, overlay, 0.2, 0)
        
        # 検出したゼロラインを描画（赤）
        cv2.line(overlay_img, (0, zero_line_y), (width, zero_line_y), (255, 0, 0), 3)
        cv2.putText(overlay_img, f'Zero Line (score: {best_score:.3f})', (10, zero_line_y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # 切り抜き範囲を描画（濃い青）
        cv2.rectangle(overlay_img, (left, int(top)), (right, int(bottom)), (0, 0, 255), 4)
        
        # オレンジバーの位置を表示（濃いオレンジ）
        cv2.line(overlay_img, (0, orange_bottom), (width, orange_bottom), (255, 140, 0), 3)
        cv2.putText(overlay_img, 'Orange Bar', (10, orange_bottom + 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 140, 0), 2)
        
        # グリッドラインを元画像にも追加
        # +30000ライン（元画像座標）
        y_30k_orig = int(top + grid_30k_offset)
        if 0 <= y_30k_orig < height:
            cv2.line(overlay_img, (0, y_30k_orig), (width, y_30k_orig), (128, 128, 128), 2)
            cv2.putText(overlay_img, '+30000', (10, max(20, y_30k_orig + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
        
        # -30000ライン（元画像座標）
        y_minus_30k_orig = int(bottom - 1 + grid_minus_30k_offset)
        if 0 <= y_minus_30k_orig < height:
            cv2.line(overlay_img, (0, y_minus_30k_orig), (width, y_minus_30k_orig), (128, 128, 128), 2)
            cv2.putText(overlay_img, '-30000', (10, max(10, y_minus_30k_orig - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
        
        # ゼロラインから±30000ラインまでの距離を計算（切り抜き内での計算）
        zero_in_crop = zero_line_y - top
        distance_to_plus_30k = zero_in_crop - grid_30k_offset
        distance_to_minus_30k = (bottom - top - 1 + grid_minus_30k_offset) - zero_in_crop
        
        # +20000ライン（元画像座標）
        y_20k_orig = int(zero_line_y - (distance_to_plus_30k * 2 / 3) + grid_20k_offset)
        if 0 <= y_20k_orig < height:
            cv2.line(overlay_img, (0, y_20k_orig), (width, y_20k_orig), (128, 128, 128), 1)
            cv2.putText(overlay_img, '+20000', (10, y_20k_orig - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (64, 64, 64), 1)
        
        # +10000ライン（元画像座標）
        y_10k_orig = int(zero_line_y - (distance_to_plus_30k * 1 / 3) + grid_10k_offset)
        if 0 <= y_10k_orig < height:
            cv2.line(overlay_img, (0, y_10k_orig), (width, y_10k_orig), (128, 128, 128), 1)
            cv2.putText(overlay_img, '+10000', (10, y_10k_orig - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (64, 64, 64), 1)
        
        # -10000ライン（元画像座標）
        y_minus_10k_orig = int(zero_line_y + (distance_to_minus_30k * 1 / 3) + grid_minus_10k_offset)
        if 0 <= y_minus_10k_orig < height:
            cv2.line(overlay_img, (0, y_minus_10k_orig), (width, y_minus_10k_orig), (128, 128, 128), 1)
            cv2.putText(overlay_img, '-10000', (10, y_minus_10k_orig - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (64, 64, 64), 1)
        
        # -20000ライン（元画像座標）
        y_minus_20k_orig = int(zero_line_y + (distance_to_minus_30k * 2 / 3) + grid_minus_20k_offset)
        if 0 <= y_minus_20k_orig < height:
            cv2.line(overlay_img, (0, y_minus_20k_orig), (width, y_minus_20k_orig), (128, 128, 128), 1)
            cv2.putText(overlay_img, '-20000', (10, y_minus_20k_orig - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (64, 64, 64), 1)
        
        # プレビューを左カラムに表示（縦に配置）
        with main_col1:
            st.markdown("### 🖼️ リアルタイムプレビュー")
            
            # 元画像（調整範囲を表示）
            st.markdown("#### 元画像（調整範囲を表示）")
            st.image(overlay_img, use_column_width=True)
            
            # 切り抜き結果（元画像の下に配置）
            st.markdown("#### 切り抜き結果")
            cropped_preview = img_array[int(top):int(bottom), int(left):int(right)].copy()
            
            # グリッドラインを追加
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
            
            # ゼロラインから±30000ラインまでの距離を計算
            distance_to_plus_30k = zero_in_crop - y_30k
            distance_to_minus_30k = y_minus_30k - zero_in_crop
            
            # +20000ライン（+30000の2/3の位置 + 微調整）
            y_20k = int(zero_in_crop - (distance_to_plus_30k * 2 / 3)) + grid_20k_offset
            if 0 < y_20k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_20k), (cropped_preview.shape[1], y_20k), (100, 100, 100), 2)
                cv2.putText(cropped_preview, '+20000', (10, y_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 2)
            
            # +10000ライン（+30000の1/3の位置 + 微調整）
            y_10k = int(zero_in_crop - (distance_to_plus_30k * 1 / 3)) + grid_10k_offset
            if 0 < y_10k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_10k), (cropped_preview.shape[1], y_10k), (100, 100, 100), 2)
                cv2.putText(cropped_preview, '+10000', (10, y_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 2)
            
            # -10000ライン（-30000の1/3の位置 + 微調整）
            y_minus_10k = int(zero_in_crop + (distance_to_minus_30k * 1 / 3)) + grid_minus_10k_offset
            if 0 < y_minus_10k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_minus_10k), (cropped_preview.shape[1], y_minus_10k), (100, 100, 100), 2)
                cv2.putText(cropped_preview, '-10000', (10, y_minus_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 2)
            
            # -20000ライン（-30000の2/3の位置 + 微調整）
            y_minus_20k = int(zero_in_crop + (distance_to_minus_30k * 2 / 3)) + grid_minus_20k_offset
            if 0 < y_minus_20k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_minus_20k), (cropped_preview.shape[1], y_minus_20k), (100, 100, 100), 2)
                cv2.putText(cropped_preview, '-20000', (10, y_minus_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 2)
            
            st.image(cropped_preview, use_column_width=True)
            
            # 情報表示
            st.caption(f"🔍 検出情報: オレンジバー位置 Y={orange_bottom}, ゼロライン Y={zero_line_y}, 検索範囲 Y={search_start}〜{search_end}")
            st.caption(f"✂️ 切り抜き範囲: 上{crop_top}px, 下{crop_bottom}px, 左{left_margin}px, 右{right_margin}px")
        
    # テスト機能：最大値アライメント
    if test_image:
        st.markdown("### 🧪 テスト機能: 最大値アライメント")
        st.info("この機能は実験的なものです。読み取ったグラフの最高値と画像上の最高値を一致させることで精度向上を試みます。")
        st.caption("💡 ヒント: 実際の最大値を入力すると、自動的にグリッドラインの調整値を計算し、ワンクリックで適用できます。")
        
        # 最大値アライメント設定
        # テスト解析を実行
        analyzer = WebCompatibleAnalyzer()
        
        # 現在の設定で解析実行
        current_settings = {
            'search_start_offset': search_start_offset,
            'search_end_offset': search_end_offset,
            'crop_top': crop_top,
            'crop_bottom': crop_bottom,
            'left_margin': left_margin,
            'right_margin': right_margin,
            'grid_30k_offset': grid_30k_offset,
            'grid_20k_offset': grid_20k_offset,
            'grid_10k_offset': grid_10k_offset,
            'grid_minus_10k_offset': grid_minus_10k_offset,
            'grid_minus_20k_offset': grid_minus_20k_offset,
            'grid_minus_30k_offset': grid_minus_30k_offset
        }
        
        # カスタム設定で解析
        analyzer.zero_y = zero_in_crop
        analyzer.scale = 30000 / distance_to_plus_30k if distance_to_plus_30k > 0 else 122
        
        # 切り抜き画像で解析
        cropped_for_analysis = img_array[int(top):int(bottom), int(left):int(right)]
        # BGRに変換（OpenCVの標準形式）
        cropped_bgr = cv2.cvtColor(cropped_for_analysis, cv2.COLOR_RGB2BGR)
        
        # 解析実行（画像データを直接渡す）
        data_points, color, detected_zero = analyzer.extract_graph_data(cropped_bgr)
        
        if data_points:
            analysis = analyzer.analyze_values(data_points)
            detected_max = analysis['max_value']
            
            # 最大値の位置にマーカーを追加した画像を作成
            marked_image = cropped_for_analysis.copy()
            max_index = analysis['max_index']
            if max_index < len(data_points):
                max_x, max_y_value = data_points[max_index]
                max_y_pixel = int(zero_in_crop - (max_y_value / analyzer.scale))
                # 最大値の位置に赤い横線を引く
                cv2.line(marked_image, (0, max_y_pixel), (marked_image.shape[1], max_y_pixel), (255, 0, 0), 2)
                # 最大値のラベルを追加
                cv2.putText(marked_image, f'MAX: {detected_max:,}', (10, max_y_pixel - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("検出された最大値", f"{detected_max:,}玉")
                st.image(marked_image, caption="最大値の位置（赤線）", use_column_width=True)
            
            with col2:
                    visual_max = st.number_input(
                        "画像上の実際の最大値",
                        min_value=0,
                        max_value=50000,
                        value=detected_max,
                        step=100,
                        help="グラフ画像を見て、実際の最高値を入力してください"
                    )
                
            if visual_max > 0 and detected_max > 0:
                correction_factor = visual_max / detected_max
                st.metric("補正係数", f"{correction_factor:.3f}")
                
                if abs(correction_factor - 1.0) > 0.01:
                    st.warning(f"検出値と実際の値に{abs(1-correction_factor)*100:.1f}%の差があります。")
                    
                    # 補正後のスケール計算
                    corrected_scale = analyzer.scale * correction_factor
                    st.info(f"推奨スケール: {corrected_scale:.1f} 玉/ピクセル (現在: {analyzer.scale:.1f})")
                    
                    # 最大値の位置を取得
                    max_index = analysis['max_index']
                    if max_index < len(data_points):
                        max_x, max_y_value = data_points[max_index]
                        # 画像座標系での最大値のY座標（0が上、heightが下）
                        max_y_pixel = int(zero_in_crop - (max_y_value / analyzer.scale))
                        
                        # 実際の最大値に基づいて新しいスケールを計算
                        # max_y_pixelから0ラインまでの距離がvisual_max玉に相当
                        actual_distance = zero_in_crop - max_y_pixel
                        if actual_distance > 0:
                            new_scale = visual_max / actual_distance
                            
                            # 新しい+30000ラインの位置を計算
                            new_30k_distance = 30000 / new_scale
                            current_30k_distance = zero_in_crop - grid_30k_offset
                            adjustment_30k = int(current_30k_distance - new_30k_distance)
                            
                            # 新しい-30000ラインの位置を計算
                            new_minus_30k_distance = 30000 / new_scale
                            current_minus_30k_distance = (cropped_for_analysis.shape[0] - 1 + grid_minus_30k_offset) - zero_in_crop
                            adjustment_minus_30k = int(new_minus_30k_distance - current_minus_30k_distance)
                            
                            st.write("### 🎯 自動調整の推奨値")
                            st.write("最大値の位置に基づいて、以下の調整を推奨します：")
                            
                            col_adj1, col_adj2 = st.columns(2)
                            with col_adj1:
                                st.write(f"**+30,000ライン調整:** `{adjustment_30k:+d}` px")
                                st.write(f"**+20,000ライン調整:** `{int(adjustment_30k * 2/3):+d}` px")
                                st.write(f"**+10,000ライン調整:** `{int(adjustment_30k * 1/3):+d}` px")
                            
                            with col_adj2:
                                st.write(f"**-10,000ライン調整:** `{int(adjustment_minus_30k * 1/3):+d}` px")
                                st.write(f"**-20,000ライン調整:** `{int(adjustment_minus_30k * 2/3):+d}` px")
                                st.write(f"**-30,000ライン調整:** `{adjustment_minus_30k:+d}` px")
                            
                            # 自動適用ボタン
                            if st.button("🔧 推奨値を自動適用", type="secondary"):
                                # セッションステートに新しい値を設定
                                st.session_state.settings['grid_30k_offset'] = grid_30k_offset + adjustment_30k
                                st.session_state.settings['grid_20k_offset'] = grid_20k_offset + int(adjustment_30k * 2/3)
                                st.session_state.settings['grid_10k_offset'] = grid_10k_offset + int(adjustment_30k * 1/3)
                                st.session_state.settings['grid_minus_10k_offset'] = grid_minus_10k_offset + int(adjustment_minus_30k * 1/3)
                                st.session_state.settings['grid_minus_20k_offset'] = grid_minus_20k_offset + int(adjustment_minus_30k * 2/3)
                                st.session_state.settings['grid_minus_30k_offset'] = grid_minus_30k_offset + adjustment_minus_30k
                                
                                st.success("✅ 推奨値を適用しました！画面が更新されます...")
                                time.sleep(1)
                                st.rerun()
                else:
                    st.success("✅ 検出値と実際の値がほぼ一致しています！")
        else:
            st.warning("グラフデータを検出できませんでした。")
    
    # 設定の保存
    st.markdown("### 💾 設定の保存")
    
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
                preset_name = st.text_input(
                    "プリセット名",
                    placeholder="例: iPhone15用、S__シリーズ用",
                    help="保存する設定の名前を入力してください"
                )
        else:
            # 新規作成モード
            preset_name = st.text_input(
                "プリセット名",
                placeholder="例: iPhone15用、S__シリーズ用",
                help="保存する設定の名前を入力してください"
            )
    else:
        # プリセットがない場合は新規作成のみ
        preset_name = st.text_input(
            "プリセット名",
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
                # セッションステートから現在の値を取得
                if test_image:
                    # test_imageがある場合は入力フィールドから直接取得
                    settings = {
                        'search_start_offset': search_start_offset,
                        'search_end_offset': search_end_offset,
                        'crop_top': crop_top,
                        'crop_bottom': crop_bottom,
                        'left_margin': left_margin,
                        'right_margin': right_margin,
                        'grid_30k_offset': grid_30k_offset,
                        'grid_20k_offset': grid_20k_offset,
                        'grid_10k_offset': grid_10k_offset,
                        'grid_minus_10k_offset': grid_minus_10k_offset,
                        'grid_minus_20k_offset': grid_minus_20k_offset,
                        'grid_minus_30k_offset': grid_minus_30k_offset
                    }
                else:
                    # test_imageがない場合はセッションステートから取得
                    settings = st.session_state.settings.copy()
                
                # プリセットに保存
                st.session_state.saved_presets[preset_name] = settings.copy()
                # 現在の設定も更新
                st.session_state.settings = settings
                
                # ファイルに保存
                try:
                    import pickle
                    import os
                    preset_file = os.path.join(os.path.expanduser('~'), '.pachi777_presets.pkl')
                    all_presets = {
                        'presets': st.session_state.saved_presets
                    }
                    with open(preset_file, 'wb') as f:
                        pickle.dump(all_presets, f)
                except:
                    pass
                
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
    
    # プリセット削除（test_imageがある場合は右カラム、ない場合は全幅）
    if st.session_state.saved_presets:
        if test_image:
            with main_col2:
                st.markdown("### 🗑️ プリセットの削除")
                
                # プリセット選択（全幅）
                preset_to_delete = st.selectbox(
                    "削除するプリセット",
                    list(st.session_state.saved_presets.keys()),
                    key="delete_preset"
                )
                
                # 削除ボタン
                if st.button("🗑️ 削除", type="secondary", use_container_width=True):
                        if preset_to_delete:
                            del st.session_state.saved_presets[preset_to_delete]
                            
                            # ファイルを更新
                            try:
                                import pickle
                                import os
                                preset_file = os.path.join(os.path.expanduser('~'), '.pachi777_presets.pkl')
                                all_presets = {
                                    'presets': st.session_state.saved_presets
                                }
                                with open(preset_file, 'wb') as f:
                                    pickle.dump(all_presets, f)
                            except:
                                pass
                            
                            st.success(f"✅ プリセット '{preset_to_delete}' を削除しました")
                            st.rerun()
        else:
            st.markdown("### 🗑️ プリセットの削除")
            
            # プリセット選択（全幅）
            preset_to_delete = st.selectbox(
                "削除するプリセット",
                list(st.session_state.saved_presets.keys()),
                key="delete_preset"
            )
            
            # 削除ボタン
            if st.button("🗑️ 削除", type="secondary", use_container_width=True):
                    if preset_to_delete:
                        del st.session_state.saved_presets[preset_to_delete]
                        
                        # ファイルを更新
                        try:
                            import pickle
                            import os
                            preset_file = os.path.join(os.path.expanduser('~'), '.pachi777_presets.pkl')
                            all_presets = {
                                'presets': st.session_state.saved_presets
                            }
                            with open(preset_file, 'wb') as f:
                                pickle.dump(all_presets, f)
                        except:
                            pass
                        
                        st.success(f"✅ プリセット '{preset_to_delete}' を削除しました")
                        st.rerun()


# ファイルアップローダー（一番最初に表示）
uploaded_files = st.file_uploader(
    "📤 グラフ画像をアップロード",
    type=['jpg', 'jpeg', 'png'],
    accept_multiple_files=True,
    help="複数の画像を一度にアップロードできます（JPG, PNG形式）"
)

if uploaded_files:
    st.success(f"✅ {len(uploaded_files)}枚の画像がアップロードされました")
    
    # プリセット選択セクション（画像アップロード後に表示）
    st.markdown("### 📋 解析設定")
    
    # プリセット選択（上段）
    preset_names = ["デフォルト"] + list(st.session_state.saved_presets.keys())
    selected_preset = st.selectbox(
        "設定プリセットを選択",
        preset_names,
        help="保存された設定を選択して適用します",
        key="analysis_preset_select"
    )
    
    # ボタン（下段）
    button_col1, button_col2, button_col3 = st.columns([1, 1, 1])
    
    with button_col1:
        # プリセット適用ボタン
        if st.button("📥 適用", use_container_width=True, key="apply_preset_analysis"):
            if selected_preset == "デフォルト":
                st.session_state.settings = default_settings.copy()
            else:
                st.session_state.settings = st.session_state.saved_presets[selected_preset].copy()
            
            # 現在のプリセット名を保存
            st.session_state.current_preset_name = selected_preset
            
            # デバッグ情報を表示
            with st.expander("🔍 適用された設定値", expanded=False):
                st.code(f"検索開始: {st.session_state.settings.get('search_start_offset', 50)}")
                st.code(f"検索終了: {st.session_state.settings.get('search_end_offset', 400)}")
                st.code(f"上切り抜き: {st.session_state.settings.get('crop_top', 246)}")
                st.code(f"下切り抜き: {st.session_state.settings.get('crop_bottom', 247)}")
                st.code(f"+30kライン調整: {st.session_state.settings.get('grid_30k_offset', 0)}")
                st.code(f"-30kライン調整: {st.session_state.settings.get('grid_minus_30k_offset', 0)}")
            
            st.success(f"✅ '{selected_preset}' を適用しました")
            st.rerun()
    
    with button_col2:
        # 設定を調整ボタン
        if st.button("⚙️ 設定を調整", use_container_width=True):
            st.session_state.show_adjustment = True
            st.rerun()
    
    with button_col3:
        pass  # 空のカラムでバランスを取る
    
    # 解析開始ボタン
    if st.button("🚀 解析を開始", type="primary", use_container_width=True):
        st.session_state.start_analysis = True
        st.rerun()
    
    # 解析を実行
    if 'start_analysis' in st.session_state and st.session_state.start_analysis:
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
                st.text(f"終了位置: +{current_settings.get('search_end_offset', 400)}px")
            
            with col3:
                st.markdown("**グリッドライン調整**")
                st.text(f"+30k: {current_settings.get('grid_30k_offset', 0):+d}px")
                st.text(f"+20k: {current_settings.get('grid_20k_offset', 0):+d}px")
                st.text(f"+10k: {current_settings.get('grid_10k_offset', 0):+d}px")
                st.text(f"-10k: {current_settings.get('grid_minus_10k_offset', 0):+d}px")
                st.text(f"-20k: {current_settings.get('grid_minus_20k_offset', 0):+d}px")
                st.text(f"-30k: {current_settings.get('grid_minus_30k_offset', 0):+d}px")
    
        # プログレスバー
        progress_bar = st.progress(0)
        status_text = st.empty()
        detail_text = st.empty()
        
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
            time.sleep(0.1)  # 視覚的フィードバックのため少し待機

            # 画像を読み込み
            image = Image.open(uploaded_file)
            img_array = np.array(image)
            height, width = img_array.shape[:2]

            # OCRでデータ抽出を試みる
            detail_text.text(f'🔍 {uploaded_file.name} のOCR解析を実行中...')
            time.sleep(0.1)  # 視覚的フィードバック
            ocr_data = extract_site7_data(img_array)

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
            settings = st.session_state.get('settings', {
                'search_start_offset': 50,
                'search_end_offset': 400,
                'crop_top': 246,
                'crop_bottom': 247,
                'left_margin': 125,
                'right_margin': 125,
                'grid_30k_offset': 0,
                'grid_20k_offset': 0,
                'grid_10k_offset': 0,
                'grid_minus_10k_offset': 0,
                'grid_minus_20k_offset': 0,
                'grid_minus_30k_offset': 0
            })

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

            # スケール計算（上下246,247pxで±30000）
            scale = 30000 / 246  # 約121.95玉/px

            # グリッドライン描画（設定値を使用）
            # +30000ライン（最上部）
            y_30k = 0 + settings.get('grid_30k_offset', 0)  # 最上部基準
            if 0 <= y_30k < crop_height:
                cv2.line(cropped_img, (0, y_30k), (cropped_img.shape[1], y_30k), (128, 128, 128), 2)
                cv2.putText(cropped_img, '+30000', (10, max(20, y_30k + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)

            # -30000ライン（最下部）
            y_minus_30k = crop_height - 1 + settings.get('grid_minus_30k_offset', 0)
            y_minus_30k = min(max(0, y_minus_30k), crop_height - 1)  # 画像範囲内に制限
            cv2.line(cropped_img, (0, y_minus_30k), (cropped_img.shape[1], y_minus_30k), (128, 128, 128), 2)
            cv2.putText(cropped_img, '-30000', (10, max(10, y_minus_30k - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)

            # ゼロラインから±30000ラインまでの距離を計算
            distance_to_plus_30k = zero_line_in_crop - y_30k
            distance_to_minus_30k = y_minus_30k - zero_line_in_crop

            # +20000ライン（+30000の2/3の位置 + 微調整）
            y_20k = int(zero_line_in_crop - (distance_to_plus_30k * 2 / 3)) + settings.get('grid_20k_offset', 0)
            if 0 < y_20k < crop_height:
                cv2.line(cropped_img, (0, y_20k), (cropped_img.shape[1], y_20k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '+20000', (10, y_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)

            # +10000ライン（+30000の1/3の位置 + 微調整）
            y_10k = int(zero_line_in_crop - (distance_to_plus_30k * 1 / 3)) + settings.get('grid_10k_offset', 0)
            if 0 < y_10k < crop_height:
                cv2.line(cropped_img, (0, y_10k), (cropped_img.shape[1], y_10k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '+10000', (10, y_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)

            # 0ライン
            y_0 = int(zero_line_in_crop)  # 調整なし
            if 0 < y_0 < crop_height:
                cv2.line(cropped_img, (0, y_0), (cropped_img.shape[1], y_0), (255, 0, 0), 2)
                cv2.putText(cropped_img, '0', (10, y_0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)

            # -10000ライン（-30000の1/3の位置 + 微調整）
            y_minus_10k = int(zero_line_in_crop + (distance_to_minus_30k * 1 / 3)) + settings.get('grid_minus_10k_offset', 0)
            if 0 < y_minus_10k < crop_height:
                cv2.line(cropped_img, (0, y_minus_10k), (cropped_img.shape[1], y_minus_10k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '-10000', (10, y_minus_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)

            # -20000ライン（-30000の2/3の位置 + 微調整）
            y_minus_20k = int(zero_line_in_crop + (distance_to_minus_30k * 2 / 3)) + settings.get('grid_minus_20k_offset', 0)
            if 0 < y_minus_20k < crop_height:
                cv2.line(cropped_img, (0, y_minus_20k), (cropped_img.shape[1], y_minus_20k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '-20000', (10, y_minus_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # 元画像にもグリッドラインを追加
            img_with_grid = img_array.copy()
            
            # 元画像での座標に変換（切り抜き前の座標系）
            # +30000ライン（元画像座標）
            y_30k_orig = int(top + y_30k)
            if 0 <= y_30k_orig < height:
                cv2.line(img_with_grid, (0, y_30k_orig), (width, y_30k_orig), (128, 128, 128), 2)
                cv2.putText(img_with_grid, '+30000', (10, max(20, y_30k_orig + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
            
            # -30000ライン（元画像座標）
            y_minus_30k_orig = int(top + y_minus_30k)
            if 0 <= y_minus_30k_orig < height:
                cv2.line(img_with_grid, (0, y_minus_30k_orig), (width, y_minus_30k_orig), (128, 128, 128), 2)
                cv2.putText(img_with_grid, '-30000', (10, max(10, y_minus_30k_orig - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
            
            # +20000ライン（元画像座標）
            y_20k_orig = int(top + y_20k)
            if 0 <= y_20k_orig < height:
                cv2.line(img_with_grid, (0, y_20k_orig), (width, y_20k_orig), (128, 128, 128), 1)
                cv2.putText(img_with_grid, '+20000', (10, y_20k_orig - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (64, 64, 64), 1)
            
            # +10000ライン（元画像座標）
            y_10k_orig = int(top + y_10k)
            if 0 <= y_10k_orig < height:
                cv2.line(img_with_grid, (0, y_10k_orig), (width, y_10k_orig), (128, 128, 128), 1)
                cv2.putText(img_with_grid, '+10000', (10, y_10k_orig - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (64, 64, 64), 1)
            
            # 0ライン（元画像座標）
            if 0 <= zero_line_y < height:
                cv2.line(img_with_grid, (0, zero_line_y), (width, zero_line_y), (255, 0, 0), 2)
                cv2.putText(img_with_grid, '0', (10, zero_line_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            
            # -10000ライン（元画像座標）
            y_minus_10k_orig = int(top + y_minus_10k)
            if 0 <= y_minus_10k_orig < height:
                cv2.line(img_with_grid, (0, y_minus_10k_orig), (width, y_minus_10k_orig), (128, 128, 128), 1)
                cv2.putText(img_with_grid, '-10000', (10, y_minus_10k_orig - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (64, 64, 64), 1)
            
            # -20000ライン（元画像座標）
            y_minus_20k_orig = int(top + y_minus_20k)
            if 0 <= y_minus_20k_orig < height:
                cv2.line(img_with_grid, (0, y_minus_20k_orig), (width, y_minus_20k_orig), (128, 128, 128), 1)
                cv2.putText(img_with_grid, '-20000', (10, y_minus_20k_orig - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (64, 64, 64), 1)
            
            # 切り抜き範囲を示す枠線を追加（オプション）
            cv2.rectangle(img_with_grid, (int(left), int(top)), (int(right), int(bottom)), (0, 255, 0), 2)

            # 解析を自動実行
            detail_text.text(f'📊 {uploaded_file.name} のグラフデータを解析中...')
            with st.spinner(f"グラフを解析中... ({idx + 1}/{len(uploaded_files)})"):
                # アナライザーを初期化
                analyzer = WebCompatibleAnalyzer()

                # グリッドラインなしの画像を使用
                analysis_img = img_array[int(top):int(bottom), int(left):int(right)].copy()

                # 0ラインの位置を設定
                analyzer.zero_y = zero_line_in_crop
                # 実際の切り抜きサイズに基づいてスケールを計算
                # 切り抜き高さの半分が30,000玉に相当
                crop_height = analysis_img.shape[0]
                # ゼロラインから上端までと下端までの距離の平均を使用
                distance_to_top = zero_line_in_crop
                distance_to_bottom = crop_height - zero_line_in_crop
                avg_distance = (distance_to_top + distance_to_bottom) / 2
                analyzer.scale = 30000 / avg_distance  # 動的スケール設定

                # グラフデータを抽出
                graph_data_points, dominant_color, _ = analyzer.extract_graph_data(analysis_img)
                
                # デバッグ情報を追加
                if uploaded_file.name == "IMG_0165.PNG":
                    st.write(f"🔍 デバッグ情報 - {uploaded_file.name}")
                    st.write(f"- ゼロライン位置（切り抜き内）: {zero_line_in_crop}px")
                    st.write(f"- 切り抜き画像の高さ: {crop_height}px")
                    st.write(f"- スケール: {analyzer.scale:.2f} 玉/ピクセル")
                    st.write(f"- 検出された色: {dominant_color}")
                    st.write(f"- データポイント数: {len(graph_data_points) if graph_data_points else 0}")
                    if graph_data_points:
                        sample_points = graph_data_points[::100][:10]  # 10点をサンプル表示
                        st.write("- サンプルデータ (x, 値):")
                        for x, val in sample_points:
                            y_pixel = zero_line_in_crop - (val / analyzer.scale)
                            st.write(f"  X={int(x)}, 値={int(val)}玉, Y座標={int(y_pixel)}px")

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
                        'original_image': img_with_grid,  # グリッド付き元画像を保存
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
                    
                    # 各画像の処理完了時に進捗を更新
                    progress_end = (idx + 1) / len(uploaded_files)
                    progress_bar.progress(progress_end)
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
        
        # Reset analysis state
        st.session_state.start_analysis = False

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

# フッターをカラムで配置
footer_col1, footer_col2, footer_col3 = st.columns([2, 1, 1])

with footer_col1:
    st.markdown(f"""
    🎰 パチンコグラフ解析システム v2.0  
    更新日: {datetime.now().strftime('%Y/%m/%d')}  
    Produced by [PPタウン](https://pp-town.com/)  
    Created by [fivenine-design.com](https://fivenine-design.com)
    """)

with footer_col3:
    if st.button("🚪 ログアウト", key="logout_button"):
        # Cookie削除は一時的に無効化
        st.session_state.authenticated = False
        st.rerun()