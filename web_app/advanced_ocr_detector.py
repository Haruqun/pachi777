import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import json

st.set_page_config(
    page_title="高精度OCR検出器",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 高精度OCR検出器 - 完全検出版")

# サイドバー
with st.sidebar:
    st.header("🔧 検出設定")
    
    # 前処理設定
    st.subheader("前処理")
    apply_denoise = st.checkbox("ノイズ除去", value=True)
    apply_sharpen = st.checkbox("シャープ化", value=True)
    apply_contrast = st.checkbox("コントラスト強調", value=True)
    
    # 閾値設定
    st.subheader("閾値設定")
    white_threshold = st.slider("白文字閾値", 100, 255, 180)
    conf_threshold = st.slider("信頼度閾値", 0, 100, 30)
    
    # OCR設定
    st.subheader("OCR設定")
    use_multiple_psm = st.checkbox("複数PSMモード使用", value=True)

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

def preprocess_image(img, denoise=True, sharpen=True, enhance_contrast=True):
    """画像の前処理"""
    result = img.copy()
    
    if denoise:
        result = cv2.fastNlMeansDenoisingColored(result, None, 10, 10, 7, 21)
    
    if sharpen:
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]])
        result = cv2.filter2D(result, -1, kernel)
    
    if enhance_contrast:
        lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        result = cv2.cvtColor(cv2.merge([l,a,b]), cv2.COLOR_LAB2BGR)
    
    return result

def extract_by_color(img, color_type):
    """色別にテキスト領域を抽出（数字のみ）"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    if color_type == 'red':
        # 赤色テキストの抽出（ピンク〜赤の範囲）
        # 低彩度のピンク
        mask1 = cv2.inRange(hsv, np.array([320/2, 20, 50]), np.array([360/2, 255, 255]))
        # 高彩度の赤
        mask2 = cv2.inRange(hsv, np.array([0, 20, 50]), np.array([20/2, 255, 255]))
        mask = cv2.bitwise_or(mask1, mask2)
        # ノイズ除去
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        # 白黒反転（テキストを黒に）
        return cv2.bitwise_not(mask)
    
    elif color_type == 'blue':
        # 青色テキストの抽出（シアン〜青の範囲）
        mask = cv2.inRange(hsv, np.array([180/2, 20, 50]), np.array([240/2, 255, 255]))
        # ノイズ除去
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        # 白黒反転（テキストを黒に）
        return cv2.bitwise_not(mask)
    
    elif color_type == 'white':
        # 白色テキストの抽出
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 明るい部分を抽出
        _, binary = cv2.threshold(gray, white_threshold, 255, cv2.THRESH_BINARY)
        # エッジ強調
        edges = cv2.Canny(gray, 50, 150)
        binary = cv2.bitwise_or(binary, edges)
        return binary
    
    elif color_type == 'all':
        # すべての明るい部分を抽出
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        return binary

def detect_text_regions(img, preprocessed_img, color_type='all', white_threshold=180):
    """テキスト領域を検出（数字のみ）"""
    # 色別抽出（white_thresholdを渡す）
    if color_type == 'white':
        gray = cv2.cvtColor(preprocessed_img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, white_threshold, 255, cv2.THRESH_BINARY)
    else:
        mask = extract_by_color(preprocessed_img, color_type)
    
    # 複数のPSMモードで試行
    psm_modes = [6, 7, 8, 11, 13] if use_multiple_psm else [7]
    all_detections = []
    
    for psm in psm_modes:
        try:
            # 数字のみを検出するよう設定
            config = f'--psm {psm} --oem 3 -c tessedit_char_whitelist=0123456789/'
            data = pytesseract.image_to_data(mask, output_type=pytesseract.Output.DICT, config=config)
            
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                if int(data['conf'][i]) > conf_threshold:
                    text = data['text'][i].strip()
                    # 数字または分数形式のみ受け入れる
                    if text and len(text) > 0 and (text.replace('/', '').isdigit() or '/' in text):
                        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                        
                        # 重複チェック
                        is_duplicate = False
                        for existing in all_detections:
                            if (abs(existing['bbox'][0] - x) < 10 and 
                                abs(existing['bbox'][1] - y) < 10 and
                                existing['text'] == text):
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            all_detections.append({
                                'text': text,
                                'confidence': data['conf'][i],
                                'bbox': [x, y, x + w, y + h],
                                'color': color_type,
                                'psm': psm
                            })
        except:
            continue
    
    return all_detections

# メイン処理
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
    if st.button("🎯 高精度OCR実行", type="primary"):
        
        # 前処理
        preprocessed = preprocess_image(img_bgr, apply_denoise, apply_sharpen, apply_contrast)
        
        # プログレスバー
        progress = st.progress(0)
        status = st.empty()
        
        # 色別に検出
        all_results = []
        colors = ['red', 'blue', 'white', 'all']
        
        for idx, color in enumerate(colors):
            status.text(f"検出中... {color}色テキスト")
            progress.progress((idx + 1) / len(colors))
            results = detect_text_regions(img_bgr, preprocessed, color, white_threshold)
            all_results.extend(results)
        
        # 重複除去（より高い信頼度を残す）
        unique_results = []
        for result in all_results:
            is_duplicate = False
            for i, unique in enumerate(unique_results):
                if (abs(unique['bbox'][0] - result['bbox'][0]) < 20 and 
                    abs(unique['bbox'][1] - result['bbox'][1]) < 20):
                    # 同じ位置の場合、信頼度が高い方を残す
                    if result['confidence'] > unique['confidence']:
                        unique_results[i] = result
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_results.append(result)
        
        progress.progress(1.0)
        status.text("検出完了！")
        
        # タブで結果表示
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 検出結果", "🎨 色別", "📍 座標マップ", "📄 JSON", "✅ 期待値確認"])
        
        with tab1:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # 検出結果を描画
                vis_img = img_bgr.copy()
                color_map = {
                    'red': (0, 0, 255),
                    'blue': (255, 0, 0),
                    'white': (200, 200, 200),
                    'all': (0, 255, 0)
                }
                
                for result in unique_results:
                    x1, y1, x2, y2 = result['bbox']
                    color = color_map.get(result['color'], (255, 255, 255))
                    cv2.rectangle(vis_img, (x1, y1), (x2, y2), color, 2)
                    # テキストを表示
                    cv2.putText(vis_img, result['text'][:10], (x1, y1 - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                st.image(cv2.cvtColor(vis_img, cv2.COLOR_BGR2RGB), use_column_width=True)
            
            with col2:
                st.metric("総検出数", len(unique_results))
                st.metric("高信頼度(>80%)", len([r for r in unique_results if r['confidence'] > 80]))
                
                # カテゴリ別カウント
                st.markdown("### カテゴリ別")
                for color in ['red', 'blue', 'white', 'all']:
                    count = len([r for r in unique_results if r['color'] == color])
                    st.write(f"**{color}**: {count}件")
        
        with tab2:
            # 色別表示
            cols = st.columns(4)
            for idx, color in enumerate(['red', 'blue', 'white', 'all']):
                with cols[idx]:
                    st.markdown(f"### {color.upper()}")
                    color_results = [r for r in unique_results if r['color'] == color]
                    for r in color_results:
                        st.write(f"• **{r['text']}**")
                        st.caption(f"信頼度: {r['confidence']}%")
        
        with tab3:
            # 座標マップ
            coord_img = img_bgr.copy()
            
            # グリッド描画（10px単位）
            for x in range(0, width, 10):
                if x % 100 == 0:
                    cv2.line(coord_img, (x, 0), (x, height), (100, 100, 100), 1)
            for y in range(0, height, 10):
                if y % 100 == 0:
                    cv2.line(coord_img, (0, y), (width, y), (100, 100, 100), 1)
            
            # 検出領域を描画
            for result in unique_results:
                x1, y1, x2, y2 = result['bbox']
                # 数字を含む重要なテキストを強調
                if any(c.isdigit() for c in result['text']):
                    cv2.rectangle(coord_img, (x1, y1), (x2, y2), (0, 255, 255), 3)
                    cv2.putText(coord_img, result['text'], (x1, y1 - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            st.image(cv2.cvtColor(coord_img, cv2.COLOR_BGR2RGB), use_column_width=True)
        
        with tab4:
            # JSON出力
            output_data = {
                "image_size": {"width": width, "height": height},
                "total_detections": len(unique_results),
                "detections": sorted(unique_results, key=lambda x: (x['bbox'][1], x['bbox'][0]))
            }
            
            st.json(output_data)
            
            # ダウンロードボタン
            json_str = json.dumps(output_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 JSONダウンロード",
                data=json_str,
                file_name=f"advanced_ocr_{selected_image}.json",
                mime="application/json"
            )
        
        with tab5:
            # 期待値との比較
            st.markdown("### ✅ 重要項目の検出状況")
            
            expected_items = {
                '大当り回数': '25',
                '大当り確率': '1/148',
                '初当り回数': '4',
                '初当り確率': '1/469',
                '累計スタート': '3721',
                '通常': '1877',
                'チャンス中': '1844',
                '超': '21',
                '中': '0',
                '小': '4',
                'スタート': '369',
                '最高出玉': '26830',
                '最高一撃': '25760',
                'チャンス中大当り': '21',
                'チャンス中確率': '1/87',
                '初回特賞': '220',
                '前日最終': '107',
                '8/6累計': '3772',
                '8/6初当り': '1/277',
                '8/6チャンス': '1/166',
                '8/6最高': '14670',
                '8/5累計': '3213',
                '8/5初当り': '1/324',
                '8/5チャンス': '1/79',
                '8/5最高': '22100'
            }
            
            # 検出テキストのセット
            detected_texts = set([r['text'] for r in unique_results])
            
            # チェック結果表示
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 検出成功 ✅")
                for name, expected in expected_items.items():
                    if expected in detected_texts:
                        matching = [r for r in unique_results if r['text'] == expected]
                        if matching:
                            r = matching[0]
                            st.success(f"**{name}**: {expected} (座標: {r['bbox']})")
            
            with col2:
                st.markdown("#### 未検出 ❌")
                for name, expected in expected_items.items():
                    if expected not in detected_texts:
                        st.error(f"**{name}**: {expected}")
            
            # 検出率
            detected_count = sum(1 for v in expected_items.values() if v in detected_texts)
            total_count = len(expected_items)
            st.metric("検出率", f"{detected_count}/{total_count} ({detected_count/total_count*100:.1f}%)")

except Exception as e:
    st.error(f"エラーが発生しました: {str(e)}")
    st.exception(e)