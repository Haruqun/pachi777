import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image

st.set_page_config(
    page_title="パチンコ出玉詳細OCRテスト",
    page_icon="🎰",
    layout="wide"
)

st.title("🎰 パチンコ出玉詳細OCRテスト")

# 画像アップロード
uploaded_file = st.file_uploader(
    "画像をアップロード", 
    type=['png', 'jpg', 'jpeg'],
    help="パチンコ台の出玉詳細画面の画像をアップロードしてください"
)

if uploaded_file is not None:
    # 画像を読み込み
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    # BGRに変換（OpenCV用）
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img_array
    
    # 画像を表示
    st.image(image, caption="アップロードされた画像", use_column_width=True)
    
    # 画像サイズを表示
    height, width = img_bgr.shape[:2]
    st.info(f"画像サイズ: {width} x {height} px")