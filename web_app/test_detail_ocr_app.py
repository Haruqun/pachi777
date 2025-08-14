import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image

st.set_page_config(
    page_title="パチンコOCR",
    page_icon="🎰",
    layout="wide"
)

st.title("🎰 パチンコ画像OCR - シンプル版")

# サイドバー
with st.sidebar:
    st.header("📸 画像アップロード")
    uploaded_file = st.file_uploader(
        "パチンコ画像を選択",
        type=['png', 'jpg', 'jpeg'],
        help="画像をアップロード"
    )

# メインエリア
if uploaded_file is not None:
    # 画像読み込み
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    # 2カラムレイアウト
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("🖼️ 元画像")
        st.image(image, use_column_width=True)
        st.info(f"画像サイズ: {img_array.shape[1]} x {img_array.shape[0]}px")
    
    with col_right:
        st.subheader("📊 OCR結果")
        
        if st.button("🔍 OCR実行", type="primary", use_container_width=True):
            with st.spinner("OCR処理中..."):
                try:
                    # シンプルにOCR実行（日本語）
                    text = pytesseract.image_to_string(image, lang='jpn')
                    
                    # 結果表示
                    st.success("OCR完了！")
                    
                    # 抽出されたテキスト
                    st.markdown("### 📝 抽出されたテキスト")
                    st.text_area("", text, height=400)
                    
                except Exception as e:
                    st.error(f"OCRエラー: {str(e)}")

else:
    # 使い方説明
    st.info("👈 サイドバーから画像をアップロードしてください")
    
    st.markdown("""
    ### 使い方
    1. サイドバーから画像をアップロード
    2. 「OCR実行」ボタンをクリック
    3. 結果を確認
    """)