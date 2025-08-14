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
        help="site777の画像をアップロード"
    )
    
    st.divider()
    
    st.header("⚙️ OCR設定")
    
    # OCR言語設定
    use_japanese = st.checkbox("日本語OCR有効", value=True)
    ocr_lang = 'jpn' if use_japanese else 'eng'
    
    # PSMモード選択
    psm_mode = st.selectbox(
        "PSMモード",
        options=[3, 6, 7, 8, 11, 13],
        format_func=lambda x: {
            3: "3 - 自動ページセグメンテーション",
            6: "6 - 均一なテキストブロック",
            7: "7 - 単一テキスト行",
            8: "8 - 単一単語",
            11: "11 - 疎なテキスト",
            13: "13 - 生のライン"
        }.get(x, str(x)),
        index=0
    )
    
    # 前処理オプション
    st.subheader("前処理")
    scale_factor = st.slider("拡大率", 1.0, 4.0, 2.0, 0.5)
    apply_threshold = st.checkbox("二値化適用", value=True)
    threshold_value = st.slider("二値化閾値", 0, 255, 180, 
                                disabled=not apply_threshold)

# メインエリア
if uploaded_file is not None:
    # 画像読み込み
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    # BGRに変換
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
        st.subheader("🖼️ 元画像")
        
        # オーバーレイ表示オプション
        show_overlay = st.checkbox("OCR領域を表示", value=False)
        
        if show_overlay and 'ocr_regions' in st.session_state:
            # オーバーレイ画像を作成
            overlay_img = img_bgr.copy()
            
            for region in st.session_state['ocr_regions']:
                x, y, w, h = region['x'], region['y'], region['w'], region['h']
                conf = region.get('confidence', 0)
                
                # 信頼度に応じて色を変更
                if conf > 80:
                    color = (0, 255, 0)  # 緑（高信頼度）
                elif conf > 50:
                    color = (0, 165, 255)  # オレンジ（中信頼度）
                else:
                    color = (0, 0, 255)  # 赤（低信頼度）
                
                # 矩形を描画
                cv2.rectangle(overlay_img, (x, y), (x+w, y+h), color, 2)
                
                # テキストラベル（信頼度）
                label = f"{conf}%"
                cv2.putText(overlay_img, label, (x, y-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # RGB変換して表示
            display_img = cv2.cvtColor(overlay_img, cv2.COLOR_BGR2RGB)
            st.image(display_img, use_column_width=True)
        else:
            st.image(image, use_column_width=True)
        
        st.info(f"画像サイズ: {img_bgr.shape[1]} x {img_bgr.shape[0]}px")
    
    with col_right:
        # タブ作成
        tab1, tab2 = st.tabs(["📊 OCR結果", "🔧 前処理画像"])
        
        with tab1:
            st.subheader("OCR実行結果")
            
            if st.button("🔍 OCR実行", type="primary", use_container_width=True):
                with st.spinner("OCR処理中..."):
                    # 前処理
                    # 1. リサイズ
                    if scale_factor != 1.0:
                        new_width = int(img_bgr.shape[1] * scale_factor)
                        new_height = int(img_bgr.shape[0] * scale_factor)
                        processed_img = cv2.resize(img_bgr, (new_width, new_height), 
                                                  interpolation=cv2.INTER_CUBIC)
                    else:
                        processed_img = img_bgr.copy()
                
                    # 2. グレースケール変換
                    if len(processed_img.shape) == 3:
                        gray = cv2.cvtColor(processed_img, cv2.COLOR_BGR2GRAY)
                    else:
                        gray = processed_img
                
                    # 3. 二値化
                    if apply_threshold:
                        _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
                        ocr_input = binary
                    else:
                        ocr_input = gray
                
                    # OCR実行
                    try:
                        # OCR設定
                        custom_config = f'--psm {psm_mode} --oem 3'
                        
                        # テキスト抽出
                        text = pytesseract.image_to_string(
                            ocr_input, 
                            lang=ocr_lang,
                            config=custom_config
                        )
                        
                        # データ付きで取得（信頼度含む）
                        data = pytesseract.image_to_data(
                            ocr_input,
                            lang=ocr_lang,
                            config=custom_config,
                            output_type=pytesseract.Output.DICT
                        )
                    
                        # 結果表示
                        st.success("OCR完了！")
                        
                        # 全体テキスト表示
                        st.markdown("### 📝 抽出されたテキスト")
                        st.text_area("全文", text, height=300)
                        
                        # OCR領域を保存（オーバーレイ表示用）
                        ocr_regions = []
                        for i in range(len(data['text'])):
                            if int(data['conf'][i]) > 0:
                                # スケールを元に戻す
                                scale_back = 1.0 / scale_factor if scale_factor != 1.0 else 1.0
                                ocr_regions.append({
                                    'x': int(data['left'][i] * scale_back),
                                    'y': int(data['top'][i] * scale_back),
                                    'w': int(data['width'][i] * scale_back),
                                    'h': int(data['height'][i] * scale_back),
                                    'confidence': int(data['conf'][i]),
                                    'text': data['text'][i]
                                })
                        st.session_state['ocr_regions'] = ocr_regions
                        
                        # 詳細データ表示
                        with st.expander("📊 詳細データ（単語ごと）"):
                            # 信頼度が0以上のテキストのみ抽出
                            detected_words = []
                            for i in range(len(data['text'])):
                                if int(data['conf'][i]) > 0:
                                    detected_words.append({
                                        'テキスト': data['text'][i],
                                        '信頼度': f"{data['conf'][i]}%",
                                        '位置': f"({data['left'][i]}, {data['top'][i]})",
                                        'サイズ': f"{data['width'][i]}x{data['height'][i]}"
                                    })
                            
                            if detected_words:
                                import pandas as pd
                                df = pd.DataFrame(detected_words)
                                st.dataframe(df, use_container_width=True)
                            else:
                                st.warning("信頼度の高いテキストが検出されませんでした")
                        
                        # 統計情報
                        st.markdown("### 📈 統計情報")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            word_count = len([w for w in data['text'] if w.strip()])
                            st.metric("検出単語数", word_count)
                        
                        with col2:
                            if word_count > 0:
                                avg_conf = np.mean([int(c) for c in data['conf'] if c > 0])
                                st.metric("平均信頼度", f"{avg_conf:.1f}%")
                            else:
                                st.metric("平均信頼度", "N/A")
                        
                        with col3:
                            line_count = len(text.split('\n'))
                            st.metric("行数", line_count)
                    
                    except Exception as e:
                        st.error(f"OCRエラー: {str(e)}")
                    
                    # 前処理画像を保存
                    st.session_state['processed_image'] = ocr_input
        
        with tab2:
            st.subheader("前処理後の画像")
            if 'processed_image' in st.session_state:
                st.image(st.session_state['processed_image'], use_column_width=True)
                st.info(f"処理後サイズ: {st.session_state['processed_image'].shape[1]} x {st.session_state['processed_image'].shape[0]}px")
            else:
                st.info("OCRを実行すると前処理画像が表示されます")

else:
    # 使い方説明
    st.info("👈 サイドバーから画像をアップロードしてください")
    
    st.markdown("""
    ### 使い方
    1. サイドバーから画像をアップロード
    2. OCR設定を調整（必要に応じて）
    3. 「OCR実行」ボタンをクリック
    4. 結果を確認
    
    ### OCR設定について
    - **日本語OCR**: 日本語テキストを含む場合は有効に
    - **PSMモード**: テキストの配置に応じて選択
    - **拡大率**: 小さい文字の場合は大きくする
    - **二値化**: 白黒にしてOCR精度を向上
    """)