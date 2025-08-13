import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import json

st.set_page_config(
    page_title="完全OCR検出器",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 完全OCR検出器 - すべてのテキストを検出")

# サイドバー
with st.sidebar:
    st.header("設定")
    confidence_threshold = st.slider("信頼度閾値", 0, 100, 50)
    min_text_length = st.slider("最小文字数", 1, 10, 1)
    
    st.header("PSM設定")
    psm_mode = st.selectbox("PSM モード", [
        (3, "3: 自動ページセグメンテーション（デフォルト）"),
        (6, "6: 単一の均一なブロック"),
        (7, "7: 単一のテキスト行"),
        (8, "8: 単一の単語"),
        (11, "11: 可能な限り多くのテキスト"),
        (12, "12: PSMなしのスパーステキスト")
    ], format_func=lambda x: x[1])

# テスト画像のパス
test_images = {
    "IMG_2074.PNG": "/Users/haruqun/Work/pachi777/test_images/IMG_2074.PNG",
    "IMG_2075.PNG": "/Users/haruqun/Work/pachi777/test_images/IMG_2075.PNG",
    "IMG_2076.PNG": "/Users/haruqun/Work/pachi777/test_images/IMG_2076.PNG",
    "IMG_2077.PNG": "/Users/haruqun/Work/pachi777/test_images/IMG_2077.PNG",
    "IMG_2078.PNG": "/Users/haruqun/Work/pachi777/test_images/IMG_2078.PNG"
}

# 画像選択
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
    
    st.info(f"画像サイズ: {width} x {height}")
    
    # OCR実行ボタン
    if st.button("🔍 完全OCR実行", type="primary"):
        
        # タブで表示方法を選択
        tab1, tab2, tab3, tab4 = st.tabs(["検出結果", "色別検出", "領域マップ", "JSON出力"])
        
        with tab1:
            st.subheader("📊 検出されたすべてのテキスト")
            
            # OCR実行（詳細情報付き）
            config = f'--psm {psm_mode[0]} --oem 3'
            data = pytesseract.image_to_data(img_bgr, output_type=pytesseract.Output.DICT, lang='jpn', config=config)
            
            # 検出結果をフィルタリング
            detected_texts = []
            vis_img = img_bgr.copy()
            
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                if int(data['conf'][i]) > confidence_threshold:
                    text = data['text'][i].strip()
                    if len(text) >= min_text_length:
                        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                        detected_texts.append({
                            'text': text,
                            'confidence': data['conf'][i],
                            'bbox': [x, y, x + w, y + h]
                        })
                        
                        # 描画
                        cv2.rectangle(vis_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(vis_img, text[:10], (x, y - 5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # 結果表示
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.image(cv2.cvtColor(vis_img, cv2.COLOR_BGR2RGB), use_column_width=True)
            
            with col2:
                st.metric("検出数", len(detected_texts))
                
                # 検出テキスト一覧
                st.markdown("### 検出テキスト")
                for item in detected_texts:
                    st.write(f"• **{item['text']}** (信頼度: {item['confidence']}%)")
                    st.caption(f"  座標: {item['bbox']}")
        
        with tab2:
            st.subheader("🎨 色別検出")
            
            # HSV変換
            hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            
            # 色別マスク
            color_masks = {
                '赤': [(np.array([0, 50, 50]), np.array([10, 255, 255])),
                       (np.array([170, 50, 50]), np.array([180, 255, 255]))],
                '青': [(np.array([100, 50, 50]), np.array([130, 255, 255]))],
                '白': None  # 特別処理
            }
            
            cols = st.columns(3)
            color_results = {}
            
            for idx, (color_name, masks) in enumerate(color_masks.items()):
                with cols[idx]:
                    st.markdown(f"#### {color_name}色テキスト")
                    
                    if color_name == '白':
                        # 白色は閾値処理
                        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                        _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
                    else:
                        # HSVマスク作成
                        mask = None
                        for lower, upper in masks:
                            temp_mask = cv2.inRange(hsv, lower, upper)
                            if mask is None:
                                mask = temp_mask
                            else:
                                mask = cv2.bitwise_or(mask, temp_mask)
                    
                    # OCR実行
                    text_data = pytesseract.image_to_data(mask, output_type=pytesseract.Output.DICT, config=config)
                    
                    color_texts = []
                    for i in range(len(text_data['text'])):
                        if int(text_data['conf'][i]) > confidence_threshold:
                            text = text_data['text'][i].strip()
                            if len(text) >= min_text_length:
                                color_texts.append(text)
                    
                    color_results[color_name] = color_texts
                    
                    for text in color_texts:
                        st.write(f"• {text}")
        
        with tab3:
            st.subheader("🗺️ 領域マップ")
            
            # 黒背景領域検出
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 最大の矩形を見つける
            black_region = None
            max_area = 0
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                if area > max_area and area > (width * height * 0.3):  # 画像の30%以上
                    max_area = area
                    black_region = [x, y, x + w, y + h]
            
            # マップ描画
            map_img = img_bgr.copy()
            
            # 黒背景領域
            if black_region:
                x1, y1, x2, y2 = black_region
                cv2.rectangle(map_img, (x1, y1), (x2, y2), (255, 0, 0), 3)
                cv2.putText(map_img, "Black Region", (x1, y1 - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            
            # 重要領域をハイライト
            important_regions = [
                item for item in detected_texts 
                if any(char.isdigit() for char in item['text'])  # 数字を含むもの
            ]
            
            for item in important_regions:
                x1, y1, x2, y2 = item['bbox']
                cv2.rectangle(map_img, (x1, y1), (x2, y2), (0, 255, 255), 2)
            
            st.image(cv2.cvtColor(map_img, cv2.COLOR_BGR2RGB), use_column_width=True)
            
            if black_region:
                st.info(f"黒背景領域: {black_region}")
        
        with tab4:
            st.subheader("📄 JSON出力")
            
            # JSON形式で出力
            output_data = {
                "image_size": {
                    "width": width,
                    "height": height
                },
                "black_region": black_region if black_region else None,
                "detected_regions": detected_texts,
                "color_regions": color_results
            }
            
            # JSON表示
            st.json(output_data)
            
            # ダウンロードボタン
            json_str = json.dumps(output_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 JSONをダウンロード",
                data=json_str,
                file_name=f"ocr_result_{selected_image}.json",
                mime="application/json"
            )
            
            # 重要な座標を抽出して表示
            st.markdown("### 📍 重要な座標（test_detail_ocr_app.py用）")
            
            important_coords = {}
            for item in detected_texts:
                text = item['text']
                bbox = item['bbox']
                
                # パターンマッチング
                if text == '25':
                    important_coords['大当り回数'] = bbox
                elif text == '4' and bbox[1] < 800:  # 上部の4
                    important_coords['初当り回数'] = bbox
                elif text == '3721':
                    important_coords['累計スタート'] = bbox
                elif text == '1877':
                    important_coords['通常'] = bbox
                elif text == '1844':
                    important_coords['チャンス中'] = bbox
                elif text == '21' and bbox[1] > 800 and bbox[1] < 1000:
                    important_coords['超'] = bbox
                elif text == '0' and bbox[1] > 800 and bbox[1] < 1000:
                    important_coords['中'] = bbox
                elif text == '4' and bbox[1] > 800 and bbox[1] < 1000:
                    important_coords['小'] = bbox
                elif text == '369':
                    important_coords['スタート'] = bbox
                elif text == '26830':
                    important_coords['最高出玉'] = bbox
            
            st.code(f"""
# 検出された重要座標
{json.dumps(important_coords, ensure_ascii=False, indent=2)}
            """, language="python")

except Exception as e:
    st.error(f"エラーが発生しました: {str(e)}")
    st.exception(e)