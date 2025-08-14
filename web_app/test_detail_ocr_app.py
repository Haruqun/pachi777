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
    
    st.divider()
    
    # オーバーレイ設定
    st.header("⚙️ 表示設定")
    show_overlay = st.checkbox("検出領域を表示", value=True)

# メインエリア
if uploaded_file is not None:
    # 画像読み込み
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    # BGRに変換（OpenCV用）
    if len(img_array.shape) == 3:
        if img_array.shape[2] == 4:  # RGBA
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        elif img_array.shape[2] == 3:  # RGB
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img_array
    else:
        img_bgr = img_array
    
    # 2カラムレイアウト
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("🖼️ 画像")
        
        # オーバーレイ表示
        if show_overlay and 'ocr_data' in st.session_state:
            overlay_img = img_bgr.copy()
            data = st.session_state['ocr_data']
            
            # 各検出領域に枠を描画
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:  # 信頼度が0より大きい場合のみ
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    conf = int(data['conf'][i])
                    
                    # 信頼度に応じて色を変更
                    if conf > 80:
                        color = (0, 255, 0)  # 緑（高信頼度）
                    elif conf > 50:
                        color = (0, 165, 255)  # オレンジ（中信頼度）
                    else:
                        color = (0, 0, 255)  # 赤（低信頼度）
                    
                    # 矩形を描画
                    cv2.rectangle(overlay_img, (x, y), (x+w, y+h), color, 2)
                    
                    # 信頼度を表示
                    label = f"{conf}%"
                    cv2.putText(overlay_img, label, (x, y-5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # RGB変換して表示
            display_img = cv2.cvtColor(overlay_img, cv2.COLOR_BGR2RGB)
            st.image(display_img, use_column_width=True)
        else:
            st.image(image, use_column_width=True)
        
        st.info(f"画像サイズ: {img_array.shape[1]} x {img_array.shape[0]}px")
    
    with col_right:
        st.subheader("📊 OCR結果")
        
        if st.button("🔍 OCR実行", type="primary", use_container_width=True):
            with st.spinner("OCR処理中..."):
                try:
                    # テキスト抽出
                    text = pytesseract.image_to_string(image, lang='jpn')
                    
                    # 詳細データも取得（枠表示用）
                    data = pytesseract.image_to_data(
                        image, 
                        lang='jpn',
                        output_type=pytesseract.Output.DICT
                    )
                    
                    # セッションに保存
                    st.session_state['ocr_data'] = data
                    
                    # 結果表示
                    st.success("OCR完了！")
                    
                    # 検出統計
                    word_count = len([w for w in data['text'] if w.strip()])
                    avg_conf = np.mean([int(c) for c in data['conf'] if c > 0]) if word_count > 0 else 0
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("検出単語数", word_count)
                    with col2:
                        st.metric("平均信頼度", f"{avg_conf:.1f}%")
                    
                    # 抽出されたテキスト
                    st.markdown("### 📝 抽出されたテキスト")
                    st.text_area("", text, height=400)
                    
                    # 再実行でオーバーレイを更新
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"OCRエラー: {str(e)}")

else:
    # 使い方説明
    st.info("👈 サイドバーから画像をアップロードしてください")
    
    st.markdown("""
    ### 使い方
    1. サイドバーから画像をアップロード
    2. 「OCR実行」ボタンをクリック
    3. 検出領域が枠で表示されます
    
    ### 枠の色
    - 🟢 緑: 信頼度 80%以上
    - 🟠 オレンジ: 信頼度 50-80%
    - 🔴 赤: 信頼度 50%未満
    """)