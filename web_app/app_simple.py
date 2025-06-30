#!/usr/bin/env python3
"""
パチンコグラフ解析システム - シンプル版Webアプリ
"""

import streamlit as st
import tempfile
import os
from datetime import datetime
import zipfile
from pathlib import Path

# ページ設定
st.set_page_config(
    page_title="パチンコグラフ解析システム",
    page_icon="🎰",
    layout="wide"
)

# タイトル
st.title("🎰 パチンコグラフ解析システム")
st.markdown("### 画像をアップロードして解析を開始")

# セッション状態の初期化
if 'processed' not in st.session_state:
    st.session_state.processed = False

# メインエリア
col1, col2 = st.columns([2, 1])

with col1:
    # ファイルアップローダー
    uploaded_files = st.file_uploader(
        "パチンコ台のスクリーンショットを選択",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        help="ドラッグ&ドロップまたはクリックして選択"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)}枚の画像をアップロードしました")
        
        # プレビュー表示
        with st.expander("📸 画像プレビュー"):
            cols = st.columns(3)
            for idx, file in enumerate(uploaded_files[:6]):
                with cols[idx % 3]:
                    st.image(file, caption=file.name, use_column_width=True)
            if len(uploaded_files) > 6:
                st.info(f"他 {len(uploaded_files) - 6}枚...")

with col2:
    st.metric("アップロード済み", f"{len(uploaded_files) if uploaded_files else 0} 枚")
    
    if uploaded_files:
        if st.button("🚀 解析開始", type="primary", use_container_width=True):
            with st.spinner("処理中... しばらくお待ちください"):
                try:
                    # 一時ディレクトリで処理
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # 画像を保存
                        saved_files = []
                        for file in uploaded_files:
                            file_path = os.path.join(temp_dir, file.name)
                            with open(file_path, "wb") as f:
                                f.write(file.getbuffer())
                            saved_files.append(file_path)
                        
                        # 簡易的なデモ処理
                        st.info("🔄 画像を処理中...")
                        
                        # デモ用のHTMLレポート作成
                        html_content = f"""
                        <html>
                        <head>
                            <title>パチンコグラフ解析レポート</title>
                            <style>
                                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                                h1 {{ color: #4CAF50; }}
                                .summary {{ background: #f0f0f0; padding: 20px; border-radius: 10px; }}
                            </style>
                        </head>
                        <body>
                            <h1>パチンコグラフ解析レポート</h1>
                            <div class="summary">
                                <h2>処理結果</h2>
                                <p>処理画像数: {len(uploaded_files)}枚</p>
                                <p>処理日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
                                <p>※ これはデモ版のレポートです</p>
                            </div>
                        </body>
                        </html>
                        """
                        
                        # ZIPファイル作成
                        zip_path = os.path.join(temp_dir, "demo_package.zip")
                        with zipfile.ZipFile(zip_path, 'w') as zipf:
                            # HTMLレポートを追加
                            zipf.writestr("report.html", html_content)
                            # 画像を追加
                            for file_path in saved_files:
                                zipf.write(file_path, os.path.basename(file_path))
                        
                        # ZIPファイルを読み込み
                        with open(zip_path, 'rb') as f:
                            zip_data = f.read()
                        
                        st.session_state.processed = True
                        st.session_state.zip_data = zip_data
                        st.session_state.html_content = html_content
                        
                        st.balloons()
                        st.success("✅ 処理完了！")
                        
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
    else:
        st.info("👆 画像をアップロードしてください")

# 結果表示
if st.session_state.processed:
    st.markdown("---")
    st.header("📊 解析結果")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.download_button(
            label="📄 HTMLレポート",
            data=st.session_state.html_content,
            file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html"
        )
    
    with col2:
        st.download_button(
            label="📦 ZIPパッケージ",
            data=st.session_state.zip_data,
            file_name=f"package_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip"
        )
    
    with col3:
        if st.button("🔄 新しい解析"):
            st.session_state.processed = False
            st.rerun()

# フッター
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>© 2024 デモ版 | パチンコグラフ解析システム</p>
</div>
""", unsafe_allow_html=True)