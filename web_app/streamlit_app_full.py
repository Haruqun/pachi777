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


# デフォルト値
default_settings = {
    'search_start_offset': 50,
    'search_end_offset': 400,
    'crop_top': 246,
    'crop_bottom': 247,
    'left_margin': 125,
    'right_margin': 125,
    # グリッドライン調整値
    'grid_30k_offset': -1,      # +30000ライン
    'grid_20k_offset': -2,      # +20000ライン  
    'grid_10k_offset': -1,      # +10000ライン
    'grid_minus_10k_offset': 1, # -10000ライン
    'grid_minus_20k_offset': 1, # -20000ライン
    'grid_minus_30k_offset': 2  # -30000ライン
}

# セッションステートの初期化（エキスパンダーより前に行う）
if 'settings' not in st.session_state:
    st.session_state.settings = default_settings.copy()

if 'saved_presets' not in st.session_state:
    st.session_state.saved_presets = {}

# 調整機能（コラプス）
with st.expander("⚙️ 画像解析の調整設定"):
    st.markdown("##### 端末ごとの調整設定")
    st.caption("※ お使いの端末で撮影した画像に合わせて調整してください")
    
    # プリセット管理セクション
    st.markdown("### 📁 設定プリセット")
    preset_col1, preset_col2 = st.columns([2, 1])
    
    with preset_col1:
        # 既存のプリセット選択
        preset_names = ["デフォルト"] + list(st.session_state.saved_presets.keys())
        selected_preset = st.selectbox(
            "プリセットを選択",
            preset_names,
            help="保存された設定を選択して適用します"
        )
    
    with preset_col2:
        # プリセット適用ボタン
        if st.button("📥 適用", use_container_width=True):
            if selected_preset == "デフォルト":
                st.session_state.settings = default_settings.copy()
            else:
                st.session_state.settings = st.session_state.saved_presets[selected_preset].copy()
            st.success(f"✅ '{selected_preset}' を適用しました")
            st.rerun()
    
    # テスト画像のアップロード
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
    st.caption("※ グリッドラインが正確に±30,000等の位置に来るように調整します")
    
    grid_col1, grid_col2, grid_col3 = st.columns(3)
    
    with grid_col1:
        grid_30k_offset = st.number_input(
            "+30,000ライン調整",
            min_value=-10, max_value=10, value=st.session_state.settings.get('grid_30k_offset', -1),
            step=1, help="上端の+30,000ラインの位置調整"
        )
        grid_20k_offset = st.number_input(
            "+20,000ライン調整",
            min_value=-10, max_value=10, value=st.session_state.settings.get('grid_20k_offset', -2),
            step=1, help="+20,000ラインの位置調整"
        )
    
    with grid_col2:
        grid_10k_offset = st.number_input(
            "+10,000ライン調整",
            min_value=-10, max_value=10, value=st.session_state.settings.get('grid_10k_offset', -1),
            step=1, help="+10,000ラインの位置調整"
        )
        grid_minus_10k_offset = st.number_input(
            "-10,000ライン調整",
            min_value=-10, max_value=10, value=st.session_state.settings.get('grid_minus_10k_offset', 1),
            step=1, help="-10,000ラインの位置調整"
        )
    
    with grid_col3:
        grid_minus_20k_offset = st.number_input(
            "-20,000ライン調整",
            min_value=-10, max_value=10, value=st.session_state.settings.get('grid_minus_20k_offset', 1),
            step=1, help="-20,000ラインの位置調整"
        )
        grid_minus_30k_offset = st.number_input(
            "-30,000ライン調整",
            min_value=-10, max_value=10, value=st.session_state.settings.get('grid_minus_30k_offset', 2),
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
        
        # 検索範囲を可視化（半透明の緑）
        overlay = overlay_img.copy()
        cv2.rectangle(overlay, (100, search_start), (width-100, search_end), (0, 255, 0), -1)
        overlay_img = cv2.addWeighted(overlay_img, 0.7, overlay, 0.3, 0)
        
        # 検出したゼロラインを描画（赤）
        cv2.line(overlay_img, (0, zero_line_y), (width, zero_line_y), (255, 0, 0), 3)
        cv2.putText(overlay_img, f'Zero Line (score: {best_score:.3f})', (10, zero_line_y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # 切り抜き範囲を描画（青）
        cv2.rectangle(overlay_img, (left, int(top)), (right, int(bottom)), (0, 0, 255), 3)
        
        # オレンジバーの位置を表示（オレンジ）
        cv2.line(overlay_img, (0, orange_bottom), (width, orange_bottom), (255, 165, 0), 2)
        cv2.putText(overlay_img, 'Orange Bar', (10, orange_bottom + 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 165, 0), 2)
        
        # プレビューを表示
        col_preview, col_cropped = st.columns(2)
        
        with col_preview:
            st.caption("元画像（調整範囲を表示）")
            st.image(overlay_img, use_column_width=True)
        
        with col_cropped:
            st.caption("切り抜き結果")
            cropped_preview = img_array[int(top):int(bottom), int(left):int(right)].copy()
            
            # グリッドラインを追加
            zero_in_crop = zero_line_y - top
            cv2.line(cropped_preview, (0, int(zero_in_crop)), (cropped_preview.shape[1], int(zero_in_crop)), (255, 0, 0), 2)
            
            # グリッドラインを追加（調整値付き）
            scale = 122.0
            
            # +30000ライン
            y_30k = grid_30k_offset
            if 0 <= y_30k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_30k), (cropped_preview.shape[1], y_30k), (128, 128, 128), 2)
                cv2.putText(cropped_preview, '+30000', (10, max(20, y_30k + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)
            
            # +20000ライン
            y_20k = int(zero_in_crop - (20000 / scale)) + grid_20k_offset
            if 0 < y_20k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_20k), (cropped_preview.shape[1], y_20k), (128, 128, 128), 1)
                cv2.putText(cropped_preview, '+20000', (10, y_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # +10000ライン
            y_10k = int(zero_in_crop - (10000 / scale)) + grid_10k_offset
            if 0 < y_10k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_10k), (cropped_preview.shape[1], y_10k), (128, 128, 128), 1)
                cv2.putText(cropped_preview, '+10000', (10, y_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # -10000ライン
            y_minus_10k = int(zero_in_crop + (10000 / scale)) + grid_minus_10k_offset
            if 0 < y_minus_10k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_minus_10k), (cropped_preview.shape[1], y_minus_10k), (128, 128, 128), 1)
                cv2.putText(cropped_preview, '-10000', (10, y_minus_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # -20000ライン
            y_minus_20k = int(zero_in_crop + (20000 / scale)) + grid_minus_20k_offset
            if 0 < y_minus_20k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_minus_20k), (cropped_preview.shape[1], y_minus_20k), (128, 128, 128), 1)
                cv2.putText(cropped_preview, '-20000', (10, y_minus_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # -30000ライン
            y_minus_30k = min(cropped_preview.shape[0] - 1, cropped_preview.shape[0] - 1 + grid_minus_30k_offset)
            if 0 <= y_minus_30k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_minus_30k), (cropped_preview.shape[1], y_minus_30k), (128, 128, 128), 2)
                cv2.putText(cropped_preview, '-30000', (10, max(10, y_minus_30k - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)
            
            st.image(cropped_preview, use_column_width=True)
        
        # 情報表示
        st.caption(f"🔍 検出情報: オレンジバー位置 Y={orange_bottom}, ゼロライン Y={zero_line_y}, 検索範囲 Y={search_start}〜{search_end}")
        st.caption(f"✂️ 切り抜き範囲: 上{crop_top}px, 下{crop_bottom}px, 左{left_margin}px, 右{right_margin}px")
    
    # 設定の保存
    st.markdown("### 💾 設定の保存")
    
    # プリセット名入力と保存
    save_col1, save_col2, save_col3 = st.columns([2, 1, 1])
    
    with save_col1:
        preset_name = st.text_input(
            "プリセット名",
            placeholder="例: iPhone15用、S__シリーズ用",
            help="保存する設定の名前を入力してください"
        )
    
    with save_col2:
        if st.button("💾 プリセットを保存", type="primary", use_container_width=True):
            if preset_name:
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
                
                # プリセットに保存
                st.session_state.saved_presets[preset_name] = settings.copy()
                # 現在の設定も更新
                st.session_state.settings = settings
                
                # LocalStorageにも保存
                all_presets = {
                    'current': settings,
                    'presets': st.session_state.saved_presets
                }
                
                st.markdown(f"""
                <script>
                localStorage.setItem('pachi777_all_settings', JSON.stringify({json.dumps(all_presets)}));
                alert('プリセット "{preset_name}" を保存しました');
                </script>
                """, unsafe_allow_html=True)
                
                st.success(f"✅ プリセット '{preset_name}' を保存しました")
                st.rerun()
            else:
                st.error("プリセット名を入力してください")
    
    with save_col3:
        if st.button("🔄 デフォルトに戻す"):
            st.session_state.settings = default_settings.copy()
            st.markdown("""
            <script>
            alert('デフォルト設定に戻しました');
            </script>
            """, unsafe_allow_html=True)
            st.rerun()
    
    # プリセット削除
    if st.session_state.saved_presets:
        st.markdown("### 🗑️ プリセットの削除")
        delete_col1, delete_col2 = st.columns([2, 1])
        
        with delete_col1:
            preset_to_delete = st.selectbox(
                "削除するプリセット",
                list(st.session_state.saved_presets.keys()),
                key="delete_preset"
            )
        
        with delete_col2:
            if st.button("🗑️ 削除", type="secondary", use_container_width=True):
                if preset_to_delete:
                    del st.session_state.saved_presets[preset_to_delete]
                    
                    # LocalStorageも更新
                    all_presets = {
                        'current': st.session_state.settings,
                        'presets': st.session_state.saved_presets
                    }
                    
                    st.markdown(f"""
                    <script>
                    localStorage.setItem('pachi777_all_settings', JSON.stringify({json.dumps(all_presets)}));
                    alert('プリセット "{preset_to_delete}" を削除しました');
                    </script>
                    """, unsafe_allow_html=True)
                    
                    st.success(f"✅ プリセット '{preset_to_delete}' を削除しました")
                    st.rerun()

# LocalStorageから設定を読み込むためのプレースホルダー
load_placeholder = st.empty()
with load_placeholder.container():
    # JavaScriptからの設定読み込みを待つ
    st.markdown("""
    <script>
    // LocalStorageから設定を読み込んでStreamlitに送信
    const allSettings = localStorage.getItem('pachi777_all_settings');
    if (allSettings) {
        const data = JSON.parse(allSettings);
        // Streamlitの隠しコンポーネントを通じて設定を送信
        const hiddenDiv = document.getElementById('load_settings_div');
        if (hiddenDiv) {
            hiddenDiv.textContent = allSettings;
            hiddenDiv.dispatchEvent(new Event('change'));
        }
    }
    </script>
    <div id="load_settings_div" style="display:none;"></div>
    """, unsafe_allow_html=True)
load_placeholder.empty()

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
        
        # 設定値を使用（セッションステートから取得）
        settings = st.session_state.get('settings', {
            'search_start_offset': 50,
            'search_end_offset': 400,
            'crop_top': 246,
            'crop_bottom': 247,
            'left_margin': 125,
            'right_margin': 125
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
        y_30k = settings.get('grid_30k_offset', -1)
        cv2.line(cropped_img, (0, y_30k), (cropped_img.shape[1], y_30k), (128, 128, 128), 2)
        cv2.putText(cropped_img, '+30000', (10, max(20, y_30k + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)
        
        # +20000ライン
        y_20k = int(zero_line_in_crop - (20000 / scale)) + settings.get('grid_20k_offset', -2)
        if 0 < y_20k < crop_height:
            cv2.line(cropped_img, (0, y_20k), (cropped_img.shape[1], y_20k), (128, 128, 128), 1)
            cv2.putText(cropped_img, '+20000', (10, y_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
        
        # +10000ライン
        y_10k = int(zero_line_in_crop - (10000 / scale)) + settings.get('grid_10k_offset', -1)
        if 0 < y_10k < crop_height:
            cv2.line(cropped_img, (0, y_10k), (cropped_img.shape[1], y_10k), (128, 128, 128), 1)
            cv2.putText(cropped_img, '+10000', (10, y_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
        
        # 0ライン
        y_0 = int(zero_line_in_crop)  # 調整なし
        if 0 < y_0 < crop_height:
            cv2.line(cropped_img, (0, y_0), (cropped_img.shape[1], y_0), (255, 0, 0), 2)
            cv2.putText(cropped_img, '0', (10, y_0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)
        
        # -10000ライン
        y_minus_10k = int(zero_line_in_crop + (10000 / scale)) + settings.get('grid_minus_10k_offset', 1)
        if 0 < y_minus_10k < crop_height:
            cv2.line(cropped_img, (0, y_minus_10k), (cropped_img.shape[1], y_minus_10k), (128, 128, 128), 1)
            cv2.putText(cropped_img, '-10000', (10, y_minus_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
        
        # -20000ライン
        y_minus_20k = int(zero_line_in_crop + (20000 / scale)) + settings.get('grid_minus_20k_offset', 1)
        if 0 < y_minus_20k < crop_height:
            cv2.line(cropped_img, (0, y_minus_20k), (cropped_img.shape[1], y_minus_20k), (128, 128, 128), 1)
            cv2.putText(cropped_img, '-20000', (10, y_minus_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
        
        # -30000ライン（最下部）
        y_minus_30k = crop_height - 1 + settings.get('grid_minus_30k_offset', 2)
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