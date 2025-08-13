import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import json

st.set_page_config(
    page_title="パチンコOCR",
    page_icon="🎰",
    layout="wide"
)

st.title("🎰 パチンコ詳細OCR - Site777")

# Expected data items from the image
EXPECTED_DATA = {
    'big_hit_count': '25',
    'big_hit_rate': '1/148',
    'first_hit_count': '4',
    'first_hit_rate': '1/469',
    'total_start': '3721',
    'normal': '1877',
    'chance': '1844',
    'ultra': '21',
    'middle': '0',
    'small': '4',
    'start': '369',
    'max_payout': '26830',
    'max_hit': '25760',
    'chance_hits': '21',
    'chance_rate': '1/87',
    'initial_start': '220',
    'prev_final': '107'
}

# サイドバー
with st.sidebar:
    st.header("📸 画像アップロード")
    uploaded_file = st.file_uploader(
        "パチンコ画像を選択",
        type=['png', 'jpg', 'jpeg'],
        help="site777.jpの詳細画面をアップロード"
    )
    
    st.divider()
    
    st.header("⚙️ OCR設定")
    
    # 検出モード
    detection_mode = st.radio(
        "検出モード",
        ["高速", "標準", "詳細"]
    )
    
    # 色検出オプション
    st.subheader("色検出")
    detect_red = st.checkbox("赤色テキスト", value=True)
    detect_blue = st.checkbox("青色テキスト", value=True)
    detect_white = st.checkbox("白色テキスト", value=True)
    
    # 閾値設定
    st.subheader("検出閾値")
    conf_threshold = st.slider("信頼度閾値", 0, 100, 30)
    
    # デバッグオプション
    show_masks = st.checkbox("マスク画像を表示", value=False)
    show_grid = st.checkbox("グリッドを表示", value=False)

# Main area
if uploaded_file is not None:
    # Load image
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    # Convert to BGR
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img_array
    
    # Get image size
    height, width = img_bgr.shape[:2]
    
    # Resize to 1179px width
    if width != 1179:
        scale = 1179 / width
        new_width = 1179
        new_height = int(height * scale)
        img_bgr = cv2.resize(img_bgr, (new_width, new_height))
        height, width = new_height, new_width
    
    # タブを作成
    tab1, tab2, tab3, tab4 = st.tabs(["📊 OCR結果", "🎨 色検出", "📍 座標マップ", "📄 JSON出力"])
    
    with tab1:
        st.subheader("📊 OCR検出結果")
        
        if st.button("🔍 OCR実行", type="primary", use_container_width=True):
            
            # Save detection results
            detected_data = {}
            all_detections = []
            
            with st.spinner("OCR処理中..."):
                # Progress bar
                progress = st.progress(0)
                
                # Color space conversions
                hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
                lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
                
                # 1. White text detection
                if detect_white:
                    progress.progress(0.2)
                    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                    
                    # Try multiple thresholds for better coverage
                    for threshold in [180, 160, 200, 140, 220]:
                        _, white_mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
                        
                        # Also try adaptive threshold
                        adaptive_mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                             cv2.THRESH_BINARY, 11, 2)
                        combined_white = cv2.bitwise_or(white_mask, adaptive_mask)
                        
                        # Try multiple PSM modes
                        for psm in [11, 6, 8, 7, 13]:
                            try:
                                config = f'--psm {psm} --oem 3 -c tessedit_char_whitelist=0123456789/'
                                data = pytesseract.image_to_data(combined_white, output_type=pytesseract.Output.DICT, config=config)
                                
                                for i in range(len(data['text'])):
                                    text = str(data['text'][i]).strip()
                                    conf = int(data['conf'][i])
                                    
                                    if conf > conf_threshold and text:
                                        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                                        all_detections.append({
                                            'text': text,
                                            'confidence': conf,
                                            'bbox': [x, y, x + w, y + h],
                                            'color': 'white'
                                        })
                            except:
                                continue
                
                # 2. Red text detection
                if detect_red:
                    progress.progress(0.5)
                    
                    # Method 1: HSV-based detection
                    red_mask1 = cv2.inRange(hsv, np.array([0, 20, 50]), np.array([10, 255, 255]))
                    red_mask2 = cv2.inRange(hsv, np.array([170, 20, 50]), np.array([180, 255, 255]))
                    pink_mask = cv2.inRange(hsv, np.array([150, 10, 100]), np.array([170, 100, 255]))
                    magenta_mask = cv2.inRange(hsv, np.array([140, 20, 100]), np.array([160, 100, 255]))
                    
                    hsv_red_mask = cv2.bitwise_or(red_mask1, red_mask2)
                    hsv_red_mask = cv2.bitwise_or(hsv_red_mask, pink_mask)
                    hsv_red_mask = cv2.bitwise_or(hsv_red_mask, magenta_mask)
                    
                    # Method 2: Channel difference (R > G and R > B)
                    b, g, r = cv2.split(img_bgr)
                    channel_red_mask = np.zeros_like(r)
                    channel_red_mask[(r > g + 20) & (r > b + 20) & (r > 100)] = 255
                    
                    # Combine both methods
                    red_mask = cv2.bitwise_or(hsv_red_mask, channel_red_mask)
                    
                    # Noise removal with smaller kernel
                    kernel = np.ones((1,1), np.uint8)
                    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
                    red_mask = cv2.bitwise_not(red_mask)
                    
                    # Try different PSM modes for better detection
                    for psm in [11, 8, 7, 13, 6]:
                        try:
                            config = f'--psm {psm} --oem 3 -c tessedit_char_whitelist=0123456789/'
                            data = pytesseract.image_to_data(red_mask, output_type=pytesseract.Output.DICT, config=config)
                            
                            for i in range(len(data['text'])):
                                text = str(data['text'][i]).strip()
                                conf = int(data['conf'][i])
                                
                                if conf > conf_threshold and text:
                                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                                    all_detections.append({
                                        'text': text,
                                        'confidence': conf,
                                        'bbox': [x, y, x + w, y + h],
                                        'color': 'red'
                                    })
                        except:
                            continue
                
                # 3. Blue text detection
                if detect_blue:
                    progress.progress(0.8)
                    
                    # Method 1: HSV-based detection
                    blue_mask_hsv = cv2.inRange(hsv, np.array([100, 20, 50]), np.array([120, 255, 255]))
                    cyan_mask = cv2.inRange(hsv, np.array([80, 20, 50]), np.array([100, 255, 255]))
                    light_blue_mask = cv2.inRange(hsv, np.array([90, 10, 100]), np.array([110, 100, 255]))
                    
                    hsv_blue_mask = cv2.bitwise_or(blue_mask_hsv, cyan_mask)
                    hsv_blue_mask = cv2.bitwise_or(hsv_blue_mask, light_blue_mask)
                    
                    # Method 2: Channel difference (B > R and B > G)
                    b, g, r = cv2.split(img_bgr)
                    channel_blue_mask = np.zeros_like(b)
                    channel_blue_mask[(b > r + 20) & (b > g + 20) & (b > 100)] = 255
                    
                    # Combine both methods
                    blue_mask = cv2.bitwise_or(hsv_blue_mask, channel_blue_mask)
                    
                    # Noise removal with smaller kernel
                    kernel = np.ones((1,1), np.uint8)
                    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)
                    blue_mask = cv2.bitwise_not(blue_mask)
                    
                    # Try different PSM modes for better detection
                    for psm in [11, 8, 7, 13, 6]:
                        try:
                            config = f'--psm {psm} --oem 3 -c tessedit_char_whitelist=0123456789/'
                            data = pytesseract.image_to_data(blue_mask, output_type=pytesseract.Output.DICT, config=config)
                            
                            for i in range(len(data['text'])):
                                text = str(data['text'][i]).strip()
                                conf = int(data['conf'][i])
                                
                                if conf > conf_threshold and text:
                                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                                    all_detections.append({
                                        'text': text,
                                        'confidence': conf,
                                        'bbox': [x, y, x + w, y + h],
                                        'color': 'blue'
                                    })
                        except:
                            continue
                
                progress.progress(1.0)
            
            # Remove duplicates
            unique_detections = []
            for detection in all_detections:
                is_duplicate = False
                for existing in unique_detections:
                    if (abs(existing['bbox'][0] - detection['bbox'][0]) < 20 and 
                        abs(existing['bbox'][1] - detection['bbox'][1]) < 20 and
                        existing['text'] == detection['text']):
                        # Keep higher confidence
                        if detection['confidence'] > existing['confidence']:
                            unique_detections.remove(existing)
                        else:
                            is_duplicate = True
                        break
                if not is_duplicate:
                    unique_detections.append(detection)
            
            # 結果を表示
            st.success(f"検出完了！ {len(unique_detections)}個のテキストを検出")
            
            # メトリクス表示
            col1, col2, col3 = st.columns(3)
            
            # 色別カウント
            white_count = len([d for d in unique_detections if d['color'] == 'white'])
            red_count = len([d for d in unique_detections if d['color'] == 'red'])
            blue_count = len([d for d in unique_detections if d['color'] == 'blue'])
            
            with col1:
                st.metric("白色テキスト", white_count)
            with col2:
                st.metric("赤色テキスト", red_count)
            with col3:
                st.metric("青色テキスト", blue_count)
            
            # 検出テキストリスト
            st.divider()
            st.markdown("### 検出されたテキスト")
            
            # Compare with expected values
            detected_texts = [d['text'] for d in unique_detections]
            
            # 重要項目をチェック
            important_items = {
                '大当り回数 (赤)': '25',
                '初当り回数 (青)': '4',
                '累計スタート': '3721',
                'スタート': '369',
                '最高出玉': '26830'
            }
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### ✅ 検出成功")
                for name, expected in important_items.items():
                    if expected in detected_texts:
                        st.success(f"{name}: {expected}")
            
            with col2:
                st.markdown("#### ❌ 未検出")
                for name, expected in important_items.items():
                    if expected not in detected_texts:
                        st.error(f"{name}: {expected}")
            
            # 全検出結果
            with st.expander("全検出結果"):
                for idx, detection in enumerate(unique_detections):
                    color_emoji = {"white": "⚪", "red": "🔴", "blue": "🔵"}.get(detection['color'], "⚫")
                    st.write(f"{idx+1}. {color_emoji} **{detection['text']}** (信頼度: {detection['confidence']}%)")
            
            # Save to session state for JSON export
            st.session_state['detections'] = unique_detections
    
    with tab2:
        st.subheader("🎨 色マスク表示")
        
        if show_masks:
            hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### ⚪ 白色マスク")
                _, white_mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
                st.image(white_mask, use_column_width=True)
            
            with col2:
                st.markdown("### 🔴 赤色マスク")
                red_mask1 = cv2.inRange(hsv, np.array([0, 30, 30]), np.array([15, 255, 255]))
                red_mask2 = cv2.inRange(hsv, np.array([160, 30, 30]), np.array([180, 255, 255]))
                red_mask = cv2.bitwise_or(red_mask1, red_mask2)
                st.image(red_mask, use_column_width=True)
            
            with col3:
                st.markdown("### 🔵 青色マスク")
                blue_mask = cv2.inRange(hsv, np.array([90, 30, 30]), np.array([120, 255, 255]))
                st.image(blue_mask, use_column_width=True)
    
    with tab3:
        st.subheader("📍 座標マップ")
        
        # 検出結果のオーバーレイ画像を作成
        vis_img = img_bgr.copy()
        
        # 検出結果がある場合は描画
        if 'detections' in st.session_state and st.session_state['detections']:
            color_map = {
                'white': (200, 200, 200),
                'red': (0, 0, 255),
                'blue': (255, 100, 0)
            }
            
            for detection in st.session_state['detections']:
                x1, y1, x2, y2 = detection['bbox']
                color = color_map.get(detection['color'], (255, 255, 255))
                
                # 矩形を描画
                cv2.rectangle(vis_img, (x1, y1), (x2, y2), color, 2)
                
                # テキストを表示（小さいフォントで）
                text = detection['text']
                conf = detection['confidence']
                label = f"{text} ({conf}%)"
                
                # テキストの背景を描画
                (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                cv2.rectangle(vis_img, (x1, y1 - text_height - 4), (x1 + text_width, y1), color, -1)
                
                # テキストを描画
                cv2.putText(vis_img, label, (x1, y1 - 2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        if show_grid:
            # 10px グリッド
            for x in range(0, width, 10):
                if x % 100 == 0:
                    cv2.line(vis_img, (x, 0), (x, height), (100, 100, 100), 1)
                    if x > 0:
                        cv2.putText(vis_img, str(x), (x-20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
            for y in range(0, height, 10):
                if y % 100 == 0:
                    cv2.line(vis_img, (0, y), (width, y), (100, 100, 100), 1)
                    if y > 0:
                        cv2.putText(vis_img, str(y), (5, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        
        st.image(cv2.cvtColor(vis_img, cv2.COLOR_BGR2RGB), use_column_width=True)
        
        # 統計情報を表示
        if 'detections' in st.session_state and st.session_state['detections']:
            st.info(f"検出数: {len(st.session_state['detections'])}個")
            
            # 色別の統計
            col1, col2, col3 = st.columns(3)
            with col1:
                white_count = len([d for d in st.session_state['detections'] if d['color'] == 'white'])
                st.metric("白色", white_count)
            with col2:
                red_count = len([d for d in st.session_state['detections'] if d['color'] == 'red'])
                st.metric("赤色", red_count)
            with col3:
                blue_count = len([d for d in st.session_state['detections'] if d['color'] == 'blue'])
                st.metric("青色", blue_count)
    
    with tab4:
        st.subheader("📄 JSON出力")
        
        if 'detections' in st.session_state:
            json_data = {
                "image_size": {"width": width, "height": height},
                "detected_regions": st.session_state['detections']
            }
            
            st.json(json_data)
            
            # ダウンロードボタン
            json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 JSONをダウンロード",
                data=json_str,
                file_name="ocr_result.json",
                mime="application/json"
            )
        else:
            st.info("OCRを実行するとJSON出力が表示されます")

else:
    # デフォルトメッセージ
    st.info("👈 サイドバーから画像をアップロードしてください")
    
    # 期待されるデータを表示
    st.markdown("### 📋 検出対象項目")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🔴 赤色")
        st.write("- 大当り回数: 25")
        st.write("- 大当り確率: 1/148")
        st.write("- 超: 21")
        st.write("- 中: 0")
        st.write("- 小: 4")
    
    with col2:
        st.markdown("#### 🔵 青色")
        st.write("- 初当り回数: 4")
        st.write("- 初当り確率: 1/469")
    
    with col3:
        st.markdown("#### ⚪ 白色")
        st.write("- 累計スタート: 3721")
        st.write("- 通常: 1877")
        st.write("- チャンス: 1844")
        st.write("- スタート: 369")
        st.write("- 最高出玉: 26830")