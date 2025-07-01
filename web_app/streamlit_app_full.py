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
        
        # 2列レイアウト
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### 元画像")
            
            # 切り抜き範囲を描画した画像を作成
            display_img = img_array.copy()
            
            # 切り抜き範囲を赤い四角で表示
            if crop_width > 0 and crop_height > 0:
                # OpenCVで四角を描画
                cv2.rectangle(display_img, (left, top), (right, bottom), (255, 0, 0), 3)
                
                # 切り抜き範囲外を半透明にする
                overlay = display_img.copy()
                # 上部
                if top > 0:
                    overlay[0:top, :] = (overlay[0:top, :] * 0.3).astype(np.uint8)
                # 下部
                if bottom < height:
                    overlay[bottom:height, :] = (overlay[bottom:height, :] * 0.3).astype(np.uint8)
                # 左部
                if left > 0:
                    overlay[top:bottom, 0:left] = (overlay[top:bottom, 0:left] * 0.3).astype(np.uint8)
                # 右部
                if right < width:
                    overlay[top:bottom, right:width] = (overlay[top:bottom, right:width] * 0.3).astype(np.uint8)
                
                display_img = overlay
            
            st.image(display_img, use_column_width=True)
            st.caption(f"サイズ: {width}×{height}px")
        
        with col2:
            st.markdown("#### 切り抜き範囲設定")
            
            # プリセットボタン
            st.markdown("**プリセット**")
            preset_cols = st.columns(3)
            
            with preset_cols[0]:
                if st.button("自動検出", use_container_width=True):
                    # Pattern3のロジックを使用
                    # オレンジバー検出（簡易版）
                    hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
                    orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
                    orange_bottom = 150  # デフォルト
                    for y in range(height//2):
                        if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
                            orange_bottom = y
                            break
                    
                    # ゼロライン検出（簡易版）
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                    zero_line_y = orange_bottom + 300  # デフォルト
                    
                    # 切り抜き範囲設定
                    st.session_state.top = max(0, zero_line_y - 250)
                    st.session_state.bottom = min(height, zero_line_y + 250)
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
            
            # スライダーで切り抜き範囲を指定
            st.markdown("**手動調整**")
            top = st.slider("上端位置", 0, height, st.session_state.get('top', 0), key="top")
            bottom = st.slider("下端位置", 0, height, st.session_state.get('bottom', height), key="bottom")
            left = st.slider("左端位置", 0, width, st.session_state.get('left', 0), key="left")
            right = st.slider("右端位置", 0, width, st.session_state.get('right', width), key="right")
            
            # 切り抜きサイズを表示
            crop_width = right - left
            crop_height = bottom - top
            
            if crop_width > 0 and crop_height > 0:
                st.info(f"切り抜きサイズ: {crop_width}×{crop_height}px")
            else:
                st.error("有効な切り抜き範囲を指定してください")
        
        # プレビューセクション
        st.markdown("### 👁️ 切り抜きプレビュー")
        
        if crop_width > 0 and crop_height > 0:
            # 切り抜き実行
            cropped_img = img_array[top:bottom, left:right]
            
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