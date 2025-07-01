#!/usr/bin/env python3
"""
パチンコグラフ解析システム - シンプル版
画像アップロード機能のみ
"""

import streamlit as st
from datetime import datetime

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
        
        # アップロードされた画像を表示
        st.markdown("### 📸 アップロードされた画像")
        
        # 画像をグリッドで表示（3列）
        cols = st.columns(3)
        for idx, uploaded_file in enumerate(uploaded_files):
            col_idx = idx % 3
            with cols[col_idx]:
                # 画像を表示
                st.image(
                    uploaded_file, 
                    caption=uploaded_file.name,
                    use_column_width=True
                )
                
                # ファイル情報
                file_size_kb = uploaded_file.size / 1024
                st.caption(f"サイズ: {file_size_kb:.1f} KB")
                
                # セパレーター（最後の画像以外）
                if idx < len(uploaded_files) - 1:
                    st.markdown("---")
        
        # 統計情報
        st.markdown("### 📊 アップロード統計")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("総画像数", f"{len(uploaded_files)}枚")
        
        with col2:
            total_size_mb = sum(f.size for f in uploaded_files) / (1024 * 1024)
            st.metric("合計サイズ", f"{total_size_mb:.1f} MB")
        
        with col3:
            current_time = datetime.now().strftime("%H:%M:%S")
            st.metric("アップロード時刻", current_time)
            
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