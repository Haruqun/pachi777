import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image

st.set_page_config(
    page_title="色別OCRテスト",
    page_icon="🎨",
    layout="wide"
)

st.title("🎨 色別OCRテスト - シンプル版")

# テスト画像
test_images = {
    "IMG_2074.PNG": "/Users/haruqun/Work/pachi777/test_images/IMG_2074.PNG",
    "IMG_2075.PNG": "/Users/haruqun/Work/pachi777/test_images/IMG_2075.PNG",
    "IMG_2076.PNG": "/Users/haruqun/Work/pachi777/test_images/IMG_2076.PNG",
    "IMG_2077.PNG": "/Users/haruqun/Work/pachi777/test_images/IMG_2077.PNG",
    "IMG_2078.PNG": "/Users/haruqun/Work/pachi777/test_images/IMG_2078.PNG"
}

selected_image = st.selectbox("テスト画像を選択", list(test_images.keys()))
image_path = test_images[selected_image]

# 画像読み込み
try:
    image = Image.open(image_path)
    img_array = np.array(image)
    
    # BGRに変換
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img_array
    
    # リサイズ（1179pxに統一）
    height, width = img_bgr.shape[:2]
    if width != 1179:
        scale = 1179 / width
        new_width = 1179
        new_height = int(height * scale)
        img_bgr = cv2.resize(img_bgr, (new_width, new_height))
        height, width = new_height, new_width
    
    # 重要な領域を切り出し（大当り回数、初当り回数、累計スタート付近）
    roi_main = img_bgr[580:800, 50:1100]  # メイン数値エリア
    roi_middle = img_bgr[840:960, 50:1100]  # 超中小、スタート、最高出玉
    
    st.subheader("🔍 色別マスク表示")
    
    # タブで色別に表示
    tab1, tab2, tab3, tab4 = st.tabs(["元画像", "赤色検出", "青色検出", "白色検出"])
    
    with tab1:
        st.image(cv2.cvtColor(roi_main, cv2.COLOR_BGR2RGB))
        st.caption("メイン数値エリア（580-800px）")
        st.image(cv2.cvtColor(roi_middle, cv2.COLOR_BGR2RGB))
        st.caption("中段エリア（840-960px）")
    
    with tab2:
        st.markdown("### 🔴 赤色テキスト検出")
        
        # HSV変換
        hsv = cv2.cvtColor(roi_main, cv2.COLOR_BGR2HSV)
        
        # 複数の赤色検出方法
        col1, col2 = st.columns(2)
        
        with col1:
            # 方法1: 標準的な赤色範囲
            red_lower1 = np.array([0, 50, 50])
            red_upper1 = np.array([10, 255, 255])
            red_lower2 = np.array([170, 50, 50])
            red_upper2 = np.array([180, 255, 255])
            
            mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
            mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
            red_mask_standard = cv2.bitwise_or(mask1, mask2)
            
            st.image(red_mask_standard, caption="標準的な赤色範囲")
            
            # OCR実行
            text = pytesseract.image_to_string(cv2.bitwise_not(red_mask_standard), 
                                              config='--psm 11 -c tessedit_char_whitelist=0123456789/')
            st.info(f"検出テキスト: {text.strip()}")
        
        with col2:
            # 方法2: ピンク〜赤の広い範囲
            pink_lower = np.array([140, 20, 100])
            pink_upper = np.array([180, 100, 255])
            red_mask_wide = cv2.inRange(hsv, pink_lower, pink_upper)
            
            # 標準赤と結合
            red_mask_wide = cv2.bitwise_or(red_mask_wide, red_mask_standard)
            
            st.image(red_mask_wide, caption="ピンク〜赤（広範囲）")
            
            # OCR実行
            text = pytesseract.image_to_string(cv2.bitwise_not(red_mask_wide), 
                                              config='--psm 11 -c tessedit_char_whitelist=0123456789/')
            st.info(f"検出テキスト: {text.strip()}")
    
    with tab3:
        st.markdown("### 🔵 青色テキスト検出")
        
        hsv = cv2.cvtColor(roi_main, cv2.COLOR_BGR2HSV)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 方法1: HSV青色範囲
            blue_lower = np.array([100, 50, 50])
            blue_upper = np.array([120, 255, 255])
            blue_mask_hsv = cv2.inRange(hsv, blue_lower, blue_upper)
            
            st.image(blue_mask_hsv, caption="HSV青色範囲")
            
            # OCR実行
            text = pytesseract.image_to_string(cv2.bitwise_not(blue_mask_hsv), 
                                              config='--psm 11 -c tessedit_char_whitelist=0123456789/')
            st.info(f"検出テキスト: {text.strip()}")
        
        with col2:
            # 方法2: BGRチャンネル差分
            b, g, r = cv2.split(roi_main)
            
            # 青が赤と緑より大きい領域
            blue_dominant = np.zeros_like(b)
            blue_dominant[(b > r + 30) & (b > g + 30)] = 255
            
            st.image(blue_dominant, caption="青チャンネル優勢")
            
            # OCR実行
            text = pytesseract.image_to_string(cv2.bitwise_not(blue_dominant), 
                                              config='--psm 11 -c tessedit_char_whitelist=0123456789/')
            st.info(f"検出テキスト: {text.strip()}")
        
        with col3:
            # 方法3: シアン系も含む
            cyan_lower = np.array([80, 30, 50])
            cyan_upper = np.array([100, 255, 255])
            cyan_mask = cv2.inRange(hsv, cyan_lower, cyan_upper)
            
            blue_cyan_mask = cv2.bitwise_or(blue_mask_hsv, cyan_mask)
            
            st.image(blue_cyan_mask, caption="青＋シアン")
            
            # OCR実行
            text = pytesseract.image_to_string(cv2.bitwise_not(blue_cyan_mask), 
                                              config='--psm 11 -c tessedit_char_whitelist=0123456789/')
            st.info(f"検出テキスト: {text.strip()}")
    
    with tab4:
        st.markdown("### ⚪ 白色テキスト検出")
        
        gray = cv2.cvtColor(roi_middle, cv2.COLOR_BGR2GRAY)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 方法1: 単純な閾値処理
            _, white_mask_simple = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            
            st.image(white_mask_simple, caption="単純閾値（180）")
            
            # OCR実行
            text = pytesseract.image_to_string(white_mask_simple, 
                                              config='--psm 11 -c tessedit_char_whitelist=0123456789/')
            st.info(f"検出テキスト: {text.strip()}")
        
        with col2:
            # 方法2: 適応的閾値処理
            white_mask_adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                        cv2.THRESH_BINARY, 11, 2)
            
            st.image(white_mask_adaptive, caption="適応的閾値")
            
            # OCR実行
            text = pytesseract.image_to_string(white_mask_adaptive, 
                                              config='--psm 11 -c tessedit_char_whitelist=0123456789/')
            st.info(f"検出テキスト: {text.strip()}")
    
    # HSV値の確認用
    with st.expander("🎨 特定座標のHSV値を確認"):
        col1, col2 = st.columns(2)
        
        with col1:
            x = st.number_input("X座標", 0, width-1, 100)
            y = st.number_input("Y座標", 0, height-1, 600)
        
        with col2:
            if st.button("HSV値を取得"):
                hsv_full = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
                h, s, v = hsv_full[y, x]
                b, g, r = img_bgr[y, x]
                
                st.info(f"BGR: ({b}, {g}, {r})")
                st.info(f"HSV: ({h}, {s}, {v})")
                
                # 色の判定
                if s < 50:
                    st.success("白/グレー系")
                elif 0 <= h <= 10 or 170 <= h <= 180:
                    st.error("赤系")
                elif 100 <= h <= 120:
                    st.info("青系")
                elif 80 <= h <= 100:
                    st.warning("シアン系")

except Exception as e:
    st.error(f"エラーが発生しました: {str(e)}")
    st.exception(e)