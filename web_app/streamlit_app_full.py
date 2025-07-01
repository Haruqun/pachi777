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
現在は画像アップロード機能のみ提供しています。
""")

# セパレーター
st.markdown("---")

# メインコンテナ
main_container = st.container()

with main_container:
    # アップロードセクション
    st.markdown("### 📤 画像をアップロード")
    
    # ファイルアップローダー
    uploaded_files = st.file_uploader(
        "グラフ画像を選択してください",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        help="複数の画像を一度にアップロードできます（JPG, PNG形式）"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)}枚の画像がアップロードされました")
        
        # 切り抜き設定セクション
        st.markdown("### ✂️ 切り抜き設定")
        
        # 画像選択
        selected_idx = st.selectbox(
            "切り抜く画像を選択",
            range(len(uploaded_files)),
            format_func=lambda x: uploaded_files[x].name
        )
        
        selected_file = uploaded_files[selected_idx]
        
        # 画像を読み込み
        image = Image.open(selected_file)
        img_array = np.array(image)
        height, width = img_array.shape[:2]
        
        # 初期値を設定（浮動小数点として）
        if 'top' not in st.session_state:
            st.session_state.top = 0.0
        if 'bottom' not in st.session_state:
            st.session_state.bottom = float(height)
        if 'left' not in st.session_state:
            st.session_state.left = 0.0
        if 'right' not in st.session_state:
            st.session_state.right = float(width)
        if 'zero_line' not in st.session_state:
            st.session_state.zero_line = float(height) / 2.0
        
        # 現在の値を取得
        top = st.session_state.get('top', 0)
        bottom = st.session_state.get('bottom', height)
        left = st.session_state.get('left', 0)
        right = st.session_state.get('right', width)
        
        # 切り抜きサイズを計算
        crop_width = right - left
        crop_height = bottom - top
        
        # 2列レイアウト
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### 元画像")
            
            # 切り抜き範囲を描画した画像を作成
            display_img = img_array.copy()
            
            # 0ラインを表示（設定されている場合）
            if 'zero_line' in st.session_state:
                zero_y = int(st.session_state.zero_line)
                cv2.line(display_img, (0, zero_y), (width, zero_y), (0, 255, 0), 2)
                cv2.putText(display_img, "0 Line", (10, zero_y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 切り抜き範囲を赤い四角で表示
            if crop_width > 0 and crop_height > 0:
                # OpenCVで四角を描画（整数に変換）
                cv2.rectangle(display_img, (int(left), int(top)), (int(right), int(bottom)), (255, 0, 0), 3)
                
                # 切り抜き範囲外を半透明にする
                overlay = display_img.copy()
                # 整数に変換
                t, b, l, r = int(top), int(bottom), int(left), int(right)
                # 上部
                if t > 0:
                    overlay[0:t, :] = (overlay[0:t, :] * 0.3).astype(np.uint8)
                # 下部
                if b < height:
                    overlay[b:height, :] = (overlay[b:height, :] * 0.3).astype(np.uint8)
                # 左部
                if l > 0:
                    overlay[t:b, 0:l] = (overlay[t:b, 0:l] * 0.3).astype(np.uint8)
                # 右部
                if r < width:
                    overlay[t:b, r:width] = (overlay[t:b, r:width] * 0.3).astype(np.uint8)
                
                display_img = overlay
            
            st.image(display_img, use_column_width=True)
            st.caption(f"サイズ: {width}×{height}px")
        
        with col2:
            st.markdown("#### 切り抜き範囲設定")
            
            # プリセットボタン
            st.markdown("**プリセット**")
            preset_cols = st.columns(3)
            
            # ボタンの説明
            with st.expander("プリセットの説明", expanded=False):
                st.markdown("""
                - **自動検出**: グラフのゼロラインを検出し、上下250pxずつの範囲を選択
                - **全体**: 画像全体を選択
                - **中央部分**: 上下左右50pxの余白を除いた範囲を選択
                """)
            
            with preset_cols[0]:
                if st.button("自動検出", use_container_width=True):
                    # Pattern3: Zero Line Based の完全な実装
                    
                    # 1. オレンジバー検出
                    hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
                    orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
                    orange_bottom = 0
                    
                    # オレンジバーの最下端を検出
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
                        # デフォルト値
                        orange_bottom = 150
                    
                    # 2. ゼロライン検出（Pattern3の核心部分）
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                    search_start = orange_bottom + 50
                    search_end = min(height - 100, orange_bottom + 400)
                    
                    best_score = 0
                    zero_line_y = (search_start + search_end) // 2
                    
                    for y in range(search_start, search_end):
                        # 中央付近の行を評価（左右の余白を除く）
                        row = gray[y, 100:width-100]
                        
                        # 暗い水平線を探す
                        darkness = 1.0 - (np.mean(row) / 255.0)  # 暗さ
                        uniformity = 1.0 - (np.std(row) / 128.0)  # 均一性
                        
                        # 暗くて均一な線ほどスコアが高い
                        score = darkness * 0.5 + uniformity * 0.5
                        
                        if score > best_score:
                            best_score = score
                            zero_line_y = y
                    
                    # 3. ゼロラインから上下に拡張（Pattern3のアプローチ）
                    st.session_state.top = max(orange_bottom + 20, zero_line_y - 250)
                    st.session_state.bottom = min(height - 50, zero_line_y + 250)
                    st.session_state.left = 100
                    st.session_state.right = width - 100
                    
                    st.rerun()
            
            with preset_cols[1]:
                if st.button("全体", use_container_width=True):
                    st.session_state.top = 0
                    st.session_state.bottom = height
                    st.session_state.left = 0
                    st.session_state.right = width
                    st.rerun()
            
            with preset_cols[2]:
                if st.button("中央部分", use_container_width=True):
                    margin = 50
                    st.session_state.top = margin
                    st.session_state.bottom = height - margin
                    st.session_state.left = margin
                    st.session_state.right = width - margin
                    st.rerun()
            
            # 0ライン基準の手動調整
            st.markdown("**手動調整（0ライン基準）**")
            
            # まず0ラインを検出または手動設定
            zero_line_y = st.number_input(
                "0ライン位置 (px)", 
                0.0, 
                float(height), 
                float(st.session_state.get('zero_line', height/2)), 
                step=1.0, 
                format="%.1f",
                key="zero_line_input",
                help="グラフの0ラインの位置を指定してください"
            )
            
            # 0ライン検出ボタン
            if st.button("0ラインを自動検出", use_container_width=True):
                # Pattern3の0ライン検出ロジック
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
                
                # オレンジバー検出
                orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
                orange_bottom = 150
                for y in range(height//2):
                    if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
                        orange_bottom = y
                        break
                
                # 0ライン検出
                search_start = orange_bottom + 50
                search_end = min(height - 100, orange_bottom + 400)
                best_score = 0
                detected_zero = (search_start + search_end) // 2
                
                for y in range(search_start, search_end):
                    row = gray[y, 100:width-100]
                    darkness = 1.0 - (np.mean(row) / 255.0)
                    uniformity = 1.0 - (np.std(row) / 128.0)
                    score = darkness * 0.5 + uniformity * 0.5
                    if score > best_score:
                        best_score = score
                        detected_zero = y
                
                st.session_state.zero_line = detected_zero
                st.rerun()
            
            # 0ラインからの範囲指定
            st.markdown("**切り抜き範囲**")
            
            # 上下の範囲
            pixels_above = st.number_input(
                "0ラインから上方向 (px)", 
                0.0, 
                float(height), 
                250.0, 
                step=10.0, 
                format="%.1f",
                key="pixels_above",
                help="0ラインから上に何ピクセル含めるか"
            )
            
            pixels_below = st.number_input(
                "0ラインから下方向 (px)", 
                0.0, 
                float(height), 
                250.0, 
                step=10.0, 
                format="%.1f",
                key="pixels_below",
                help="0ラインから下に何ピクセル含めるか"
            )
            
            # 左右の余白
            horizontal_margin = st.number_input(
                "左右の余白 (px)", 
                0.0, 
                float(width/2), 
                100.0, 
                step=10.0, 
                format="%.1f",
                key="horizontal_margin",
                help="左右の端から除外するピクセル数"
            )
            
            # 新しい切り抜き範囲を計算
            new_top = max(0, zero_line_y - pixels_above)
            new_bottom = min(height, zero_line_y + pixels_below)
            new_left = horizontal_margin
            new_right = width - horizontal_margin
            
            # 値が変更されたら更新（小数点の誤差を考慮）
            epsilon = 0.01  # 許容誤差
            if (abs(new_top - top) > epsilon or 
                abs(new_bottom - bottom) > epsilon or 
                abs(new_left - left) > epsilon or 
                abs(new_right - right) > epsilon or
                abs(zero_line_y - st.session_state.get('zero_line', height/2)) > epsilon):
                st.session_state.top = new_top
                st.session_state.bottom = new_bottom
                st.session_state.left = new_left
                st.session_state.right = new_right
                st.session_state.zero_line = zero_line_y
                st.rerun()
            
            if crop_width > 0 and crop_height > 0:
                st.info(f"切り抜きサイズ: {crop_width}×{crop_height}px")
            else:
                st.error("有効な切り抜き範囲を指定してください")
        
        # プレビューセクション
        st.markdown("### 👁️ 切り抜きプレビュー")
        
        if crop_width > 0 and crop_height > 0:
            # 切り抜き実行（整数に変換）
            cropped_img = img_array[int(top):int(bottom), int(left):int(right)]
            
            # プレビュー表示
            preview_cols = st.columns([2, 3, 2])
            with preview_cols[1]:
                st.image(cropped_img, caption="切り抜き結果", use_column_width=True)
                
                # 切り抜き画像をダウンロード可能にする
                # OpenCVのBGRからRGBに変換（必要な場合）
                if len(cropped_img.shape) == 3 and cropped_img.shape[2] == 3:
                    # PILで保存用に準備
                    cropped_pil = Image.fromarray(cropped_img)
                    
                    # バイトストリームに保存
                    buf = io.BytesIO()
                    cropped_pil.save(buf, format='PNG')
                    byte_im = buf.getvalue()
                    
                    # ダウンロードボタン
                    st.download_button(
                        label="切り抜き画像をダウンロード",
                        data=byte_im,
                        file_name=f"cropped_{selected_file.name}",
                        mime="image/png"
                    )
        
        # 元の画像リスト表示
        st.markdown("---")
        st.markdown("### 📸 アップロードされた画像一覧")
        
        # 画像をグリッドで表示（3列）
        cols = st.columns(3)
        for idx, uploaded_file in enumerate(uploaded_files):
            col_idx = idx % 3
            with cols[col_idx]:
                # 選択中の画像はハイライト
                if idx == selected_idx:
                    st.markdown("**🔍 選択中**")
                
                # 画像を表示
                st.image(
                    uploaded_file, 
                    caption=uploaded_file.name,
                    use_column_width=True
                )
                
                # ファイル情報
                file_size_kb = uploaded_file.size / 1024
                st.caption(f"サイズ: {file_size_kb:.1f} KB")
            
    else:
        # アップロード前の表示
        st.info("👆 上のボタンから画像をアップロードしてください")
        
        # 使い方
        with st.expander("💡 使い方"):
            st.markdown("""
            1. **「Browse files」ボタン**をクリック
            2. **グラフ画像を選択**（複数選択可）
            3. **画像が表示されることを確認**
            
            対応フォーマット:
            - JPG/JPEG
            - PNG
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