#!/usr/bin/env python3
"""
パチンコグラフ解析システム - シンプル版
画像アップロード機能のみ
"""

import streamlit as st
from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import io

# ページ設定
st.set_page_config(
    page_title="パチンコグラフ解析 - シンプル版",
    page_icon="🎰",
    layout="wide"
)

# カスタムCSS
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    .upload-section {
        background-color: #f0f2f6;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .image-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1rem;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# タイトル
st.title("🎰 パチンコグラフ解析システム")
st.markdown("### シンプル版 - 画像アップロード")

# 説明文
st.markdown("""
このシステムは、パチンコの収支グラフを解析するためのツールです。
グラフ画像をアップロードすると、自動的に最適な範囲で切り抜きを行います。
""")

# セパレーター
st.markdown("---")

# メインコンテナ
main_container = st.container()

with main_container:
    # アップロードセクション
    st.markdown("### 📤 画像をアップロード")
    
    # ファイルアップローダー
    uploaded_file = st.file_uploader(
        "グラフ画像を選択してください",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=False,
        help="グラフ画像をアップロードしてください（JPG, PNG形式）"
    )
    
    if uploaded_file:
        st.success(f"✅ 画像がアップロードされました: {uploaded_file.name}")
        
        # グリッドライン調整UI
        with st.expander("⚙️ グリッドライン位置調整", expanded=False):
            st.markdown("各グリッドラインの位置を微調整できます（ピクセル単位）")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**プラス側**")
                adjust_30k = st.number_input("+30000ライン調整", -5, 5, 0, 1, key="adj_30k")
                adjust_20k = st.number_input("+20000ライン調整", -5, 5, 0, 1, key="adj_20k")
                adjust_10k = st.number_input("+10000ライン調整", -5, 5, 0, 1, key="adj_10k")
            
            with col2:
                st.markdown("**マイナス側**")
                adjust_0 = st.number_input("0ライン調整", -5, 5, 0, 1, key="adj_0")
                adjust_minus_10k = st.number_input("-10000ライン調整", -5, 5, 0, 1, key="adj_minus_10k")
                adjust_minus_20k = st.number_input("-20000ライン調整", -5, 5, 1, 1, key="adj_minus_20k")  # デフォルト1
                adjust_minus_30k = st.number_input("-30000ライン調整", -5, 5, 0, 1, key="adj_minus_30k")
        
        # 切り抜き処理
        st.markdown("### ✂️ 切り抜き結果")
        
        # 画像処理
        with st.spinner('画像を処理中...'):")
            
            # 画像を読み込み
            image = Image.open(uploaded_file)
            img_array = np.array(image)
            height, width = img_array.shape[:2]
            
            # Pattern3: Zero Line Based の自動検出
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
            
            # グリッドライン描画
            # +30000ライン（最上部）
            y_30k = 0 + st.session_state.get('adj_30k', 0)
            cv2.line(cropped_img, (0, y_30k), (cropped_img.shape[1], y_30k), (128, 128, 128), 2)
            cv2.putText(cropped_img, '+30000', (10, max(20, y_30k + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 2)
            
            # +20000ライン
            y_20k = int(zero_line_in_crop - (20000 / scale)) + st.session_state.get('adj_20k', 0)
            if 0 < y_20k < crop_height:
                cv2.line(cropped_img, (0, y_20k), (cropped_img.shape[1], y_20k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '+20000', (10, y_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # +10000ライン
            y_10k = int(zero_line_in_crop - (10000 / scale)) + st.session_state.get('adj_10k', 0)
            if 0 < y_10k < crop_height:
                cv2.line(cropped_img, (0, y_10k), (cropped_img.shape[1], y_10k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '+10000', (10, y_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # 0ライン
            y_0 = int(zero_line_in_crop) + st.session_state.get('adj_0', 0)
            if 0 < y_0 < crop_height:
                cv2.line(cropped_img, (0, y_0), (cropped_img.shape[1], y_0), (255, 0, 0), 2)
                cv2.putText(cropped_img, '0', (10, y_0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            # -10000ライン
            y_minus_10k = int(zero_line_in_crop + (10000 / scale)) + st.session_state.get('adj_minus_10k', 0)
            if 0 < y_minus_10k < crop_height:
                cv2.line(cropped_img, (0, y_minus_10k), (cropped_img.shape[1], y_minus_10k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '-10000', (10, y_minus_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # -20000ライン
            y_minus_20k = int(zero_line_in_crop + (20000 / scale)) + st.session_state.get('adj_minus_20k', 1)  # デフォルト1px下
            if 0 < y_minus_20k < crop_height:
                cv2.line(cropped_img, (0, y_minus_20k), (cropped_img.shape[1], y_minus_20k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '-20000', (10, y_minus_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # -30000ライン（最下部）
            y_minus_30k = crop_height - 1 + st.session_state.get('adj_minus_30k', 0)
            y_minus_30k = min(max(0, y_minus_30k), crop_height - 1)  # 画像範囲内に制限
            cv2.line(cropped_img, (0, y_minus_30k), (cropped_img.shape[1], y_minus_30k), (128, 128, 128), 2)
            cv2.putText(cropped_img, '-30000', (10, max(10, y_minus_30k - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 2)
            
        # 画像を横幅いっぱいで表示
        st.image(cropped_img, use_column_width=True)
        
        # 画像情報とダウンロード
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.info(f"📐 サイズ: {cropped_img.shape[1]}×{cropped_img.shape[0]}px")
        
        with col2:
            # グリッドライン表示/非表示トグル
            show_grid = st.checkbox("グリッドラインを表示", value=True, key="show_grid")
            if not show_grid:
                # グリッドラインなしの画像を再生成
                cropped_img_no_grid = img_array[int(top):int(bottom), int(left):int(right)].copy()
                st.rerun()
        
        with col3:
            # ダウンロードボタン
            cropped_pil = Image.fromarray(cropped_img)
            buf = io.BytesIO()
            cropped_pil.save(buf, format='PNG')
            byte_im = buf.getvalue()
            
            st.download_button(
                label="⬇️ ダウンロード",
                data=byte_im,
                file_name=f"cropped_{uploaded_file.name}",
                mime="image/png"
            )
        
    else:
        # アップロード前の表示
        st.info("👆 上のボタンから画像をアップロードしてください")
        
        # 使い方
        with st.expander("💡 使い方"):
            st.markdown("""
            1. **「Browse files」ボタン**をクリック
            2. **グラフ画像を選択**
            3. **自動的に切り抜きが実行されます**
            
            対応フォーマット:
            - JPG/JPEG
            - PNG
            
            切り抜き設定:
            - 0ラインを自動検出
            - 0ラインから上246px、下247px
            - 左右125pxの余白を除外
            """)

# フッター
st.markdown("---")
footer_col1, footer_col2 = st.columns([2, 1])

with footer_col1:
    st.markdown("パチンコグラフ解析システム v2.0")
    
with footer_col2:
    st.markdown(
        f"<div style='text-align: right'>更新日: {datetime.now().strftime('%Y/%m/%d')}</div>",
        unsafe_allow_html=True
    )