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
    
    # 画像サイズを取得
    height, width = img_bgr.shape[:2]
    
    # 画像を1179px幅にリサイズ（アスペクト比保持）
    target_width = 1179
    if width != target_width:
        scale = target_width / width
        new_height = int(height * scale)
        img_bgr = cv2.resize(img_bgr, (target_width, new_height), interpolation=cv2.INTER_AREA)
        height, width = img_bgr.shape[:2]
    
    # 黒背景領域を検出
    def detect_black_region(img):
        """黒背景領域を検出して座標を返す"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 黒い領域を検出（閾値20以下を黒とする）
        _, black_mask = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY_INV)
        
        # ノイズ除去
        kernel = np.ones((5,5), np.uint8)
        black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
        black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)
        
        # 輪郭検出
        contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # 最大の輪郭を黒背景とする
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # 面積が画像の30%以上なら有効な黒背景とする
            if w * h > img.shape[0] * img.shape[1] * 0.3:
                return (x, y, x + w, y + h)
        
        return None
    
    black_region = detect_black_region(img_bgr)
    
    # カスタム領域定義の読み込み
    custom_regions_loaded = None
    uploaded_region_file = st.sidebar.file_uploader(
        "領域定義ファイルを読み込み",
        type=['json'],
        help="保存した領域定義ファイル(region_definitions.json)をアップロード"
    )
    
    if uploaded_region_file is not None:
        try:
            import json
            custom_regions_loaded = json.loads(uploaded_region_file.read())
            st.sidebar.success(f"{len(custom_regions_loaded)}個の領域を読み込みました")
        except Exception as e:
            st.sidebar.error(f"読み込みエラー: {str(e)}")
    
    # 座標定義（カスタム定義があればそれを使用、なければデフォルト）
    if custom_regions_loaded:
        # カスタム領域定義を使用
        regions = {}
        for key, value in custom_regions_loaded.items():
            regions[key] = {
                'name': value['name'],
                'bbox': tuple(value['bbox']),
                'color': value['color']
            }
    elif black_region:
        bx1, by1, bx2, by2 = black_region
        # 黒背景内での相対座標を絶対座標に変換（実際の検出結果に基づく）
        regions = {
            # メイン数値（黒背景内での位置）
            'big_hit': {
                'name': '大当り回数',
                'bbox': (128, 636, 287, 741),  # "25"の実際の位置
                'color': 'red'
            },
            'first_hit': {
                'name': '初当り回数',
                'bbox': (493, 636, 640, 741),  # 初当り数値の推定位置（"4"の可能性）
                'color': 'blue'
            },
            'total_start': {
                'name': '累計スタート',
                'bbox': (845, 638, 1040, 715),  # "_3721"の実際の位置
                'color': 'white'
            },
            'start': {
                'name': 'スタート',
                'bbox': (521, 842, 654, 873),  # "スタート"ラベルの位置（実際の数値は別）
                'color': 'white'
            },
            'max_payout': {
                'name': '最高出玉',
                'bbox': (851, 897, 1086, 957),  # "26830"の実際の位置
                'color': 'white'
            },
        }
    else:
        bx1, by1, bx2, by2 = 0, 0, width, height
        # 黒背景が検出できない場合は実際の検出座標を使用
        regions = {
            'big_hit': {
                'name': '大当り回数',
                'bbox': (128, 636, 287, 741),  # "25"の実際の位置
                'color': 'red'
            },
            'first_hit': {
                'name': '初当り回数', 
                'bbox': (493, 636, 640, 741),  # 初当り数値の推定位置
                'color': 'blue'
            },
            'total_start': {
                'name': '累計スタート',
                'bbox': (845, 638, 1040, 715),  # "_3721"の実際の位置
                'color': 'white'
            },
            'start': {
                'name': 'スタート',
                'bbox': (520, 897, 660, 957),  # スタート数値の領域（"369"より広め）
                'color': 'white'
            },
            'max_payout': {
                'name': '最高出玉',
                'bbox': (851, 897, 1086, 957),  # "26830"の実際の位置
                'color': 'white'
            },
        }
    
    # メインレイアウト：左に画像、右に操作
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📷 検出領域")
        
        # 画像のコピーを作成
        vis_img = img_bgr.copy()
        
        # 黒背景領域を表示
        if black_region:
            cv2.rectangle(vis_img, (bx1, by1), (bx2, by2), (0, 255, 0), 3)
            cv2.putText(vis_img, "Black Region", (bx1, by1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 領域を描画
        for key, region in regions.items():
            x1, y1, x2, y2 = region['bbox']
            color_map = {
                'red': (0, 0, 255),
                'blue': (255, 0, 0),
                'white': (255, 255, 255)
            }
            color = color_map.get(region['color'], (255, 255, 255))
            cv2.rectangle(vis_img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(vis_img, region['name'], (x1, y1-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 表示
        st.image(cv2.cvtColor(vis_img, cv2.COLOR_BGR2RGB), 
                caption="OCR対象領域", use_column_width=True)
        
        # 画像情報
        st.info(f"画像サイズ: {width} x {height} px")
        if black_region:
            st.success(f"黒背景領域: ({bx1}, {by1}) - ({bx2}, {by2})")
        else:
            st.warning("黒背景領域が検出できませんでした")
    
    with col2:
        st.subheader("📊 OCR操作")
        
        # OCRモード選択
        ocr_mode = st.radio(
            "OCRモード",
            ["5項目抽出", "全体OCR検出"],
            help="5項目抽出：主要データのみ\n全体OCR検出：すべての文字を検出"
        )
        
        if st.button("🔍 OCR実行", type="primary", use_container_width=True):
            if ocr_mode == "5項目抽出":
                results = {}
                
                with st.spinner("OCR処理中..."):
                    for key, region in regions.items():
                        x1, y1, x2, y2 = region['bbox']
                        roi = img_bgr[y1:y2, x1:x2]
                        
                        try:
                            if region['color'] == 'red':
                                # 赤色抽出
                                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                                mask1 = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([10, 255, 255]))
                                mask2 = cv2.inRange(hsv, np.array([170, 50, 50]), np.array([180, 255, 255]))
                                mask = cv2.bitwise_or(mask1, mask2)
                                text = pytesseract.image_to_string(mask, config='--psm 8 -c tessedit_char_whitelist=0123456789')
                                
                            elif region['color'] == 'blue':
                                # 青色抽出
                                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                                mask = cv2.inRange(hsv, np.array([100, 50, 50]), np.array([130, 255, 255]))
                                text = pytesseract.image_to_string(mask, config='--psm 8 -c tessedit_char_whitelist=0123456789')
                                
                            else:  # white
                                # 白色抽出（グレースケール + 二値化）
                                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                                _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
                                text = pytesseract.image_to_string(binary, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                            
                            results[region['name']] = text.strip()
                            
                        except Exception as e:
                            results[region['name']] = f"エラー: {str(e)}"
                
                # 結果表示
                st.success("OCR完了！")
                st.divider()
                
                # 結果をメトリクスで表示
                st.markdown("### 抽出結果")
                
                # 上段：大当り・初当り・累計
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    value = results.get('大当り回数', '')
                    if value and not value.startswith('エラー'):
                        st.metric("大当り回数", value)
                    else:
                        st.error("大当り回数: 認識失敗")
                
                with col_b:
                    value = results.get('初当り回数', '')
                    if value and not value.startswith('エラー'):
                        st.metric("初当り回数", value)
                    else:
                        st.error("初当り回数: 認識失敗")
                
                with col_c:
                    value = results.get('累計スタート', '')
                    if value and not value.startswith('エラー'):
                        st.metric("累計スタート", value)
                    else:
                        st.error("累計スタート: 認識失敗")
                
                # 下段：スタート・最高出玉
                col_d, col_e = st.columns(2)
                with col_d:
                    value = results.get('スタート', '')
                    if value and not value.startswith('エラー'):
                        st.metric("スタート", value)
                    else:
                        st.error("スタート: 認識失敗")
                
                with col_e:
                    value = results.get('最高出玉', '')
                    if value and not value.startswith('エラー'):
                        st.metric("最高出玉", value)
                    else:
                        st.error("最高出玉: 認識失敗")
                
                # JSON出力
                with st.expander("詳細データ (JSON)"):
                    st.json(results)
            
            elif ocr_mode == "全体OCR検出":
                # 黒背景領域内でOCR実行
                if black_region:
                    target_img = img_bgr[by1:by2, bx1:bx2]
                else:
                    target_img = img_bgr
                
                # Tesseractで文字検出
                with st.spinner("文字検出中..."):
                    # グレースケール化
                    gray = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
                    
                    # コントラスト調整
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                    enhanced = clahe.apply(gray)
                    
                    # OCR実行（バウンディングボックス情報も取得）
                    data = pytesseract.image_to_data(enhanced, lang='jpn', output_type=pytesseract.Output.DICT)
                    
                    # 検出結果をフィルタリング
                    detected_regions = []
                    vis_full_img = img_bgr.copy()
                    
                    for i in range(len(data['text'])):
                        text = str(data['text'][i]).strip()
                        conf = int(data['conf'][i])
                        
                        # 信頼度30以上かつ空でないテキストのみ
                        if conf > 30 and text and text != '':
                            # バウンディングボックス情報
                            x = int(data['left'][i])
                            y = int(data['top'][i])
                            w = int(data['width'][i])
                            h = int(data['height'][i])
                            
                            # 黒背景領域からのオフセットを考慮
                            if black_region:
                                abs_x = bx1 + x
                                abs_y = by1 + y
                            else:
                                abs_x = x
                                abs_y = y
                            
                            # 検出情報を保存
                            region_info = {
                                'text': text,
                                'confidence': conf,
                                'bbox': [abs_x, abs_y, abs_x + w, abs_y + h]
                            }
                            detected_regions.append(region_info)
                            
                            # 枠線を描画
                            cv2.rectangle(vis_full_img, (abs_x, abs_y), (abs_x + w, abs_y + h), (0, 255, 0), 2)
                            cv2.putText(vis_full_img, text[:10], (abs_x, abs_y - 5),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                # 結果表示
                st.success(f"OCR完了！ {len(detected_regions)}個のテキストを検出")
                st.divider()
                
                # 検出結果画像
                st.markdown("### 検出結果")
                st.image(cv2.cvtColor(vis_full_img, cv2.COLOR_BGR2RGB), 
                        caption="検出されたテキスト領域", use_column_width=True)
                
                # 検出データの表示
                with st.expander(f"検出データ ({len(detected_regions)}件)"):
                    for idx, region in enumerate(detected_regions):
                        st.text(f"{idx+1}. テキスト: '{region['text']}' (信頼度: {region['confidence']}%)")
                
                # JSONエクスポート
                st.markdown("### データエクスポート")
                json_data = {
                    'image_size': {'width': width, 'height': height},
                    'black_region': list(black_region) if black_region else None,
                    'detected_regions': detected_regions
                }
                
                # JSON表示
                with st.expander("JSONデータ"):
                    st.json(json_data)
                
                # ダウンロードボタン
                import json
                json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="💾 JSONデータをダウンロード",
                    data=json_str,
                    file_name="ocr_detection_result.json",
                    mime="application/json",
                    use_container_width=True
                )
                
                # 領域定義生成機能
                st.markdown("### 🎯 領域定義生成")
                st.info("検出されたテキストから重要な領域を選択して定義できます")
                
                # 検出された主要な数値をフィルタリング
                important_texts = []
                for region in detected_regions:
                    text = region['text']
                    # 数値のみ、または重要なキーワードを含むテキスト
                    if (text.isdigit() and len(text) >= 2) or any(kw in text for kw in ['大当り', '初当り', '累計', 'スタート', '出玉']):
                        important_texts.append(region)
                
                if important_texts:
                    selected_regions = st.multiselect(
                        "定義したい領域を選択",
                        options=range(len(important_texts)),
                        format_func=lambda x: f"{important_texts[x]['text']} (座標: {important_texts[x]['bbox']})",
                        default=[]
                    )
                    
                    if selected_regions:
                        # 選択された領域から定義を生成
                        custom_regions = {}
                        for idx in selected_regions:
                            region = important_texts[idx]
                            text = region['text']
                            bbox = region['bbox']
                            
                            # 領域名を自動生成
                            if '大当り' in text:
                                name = 'big_hit_label'
                                display_name = '大当りラベル'
                                color = 'red'
                            elif '初当り' in text:
                                name = 'first_hit_label'
                                display_name = '初当りラベル'
                                color = 'blue'
                            elif '累計' in text:
                                name = 'total_label'
                                display_name = '累計ラベル'
                                color = 'white'
                            elif text == '25':
                                name = 'big_hit_value'
                                display_name = '大当り回数値'
                                color = 'red'
                            elif text == '4':
                                name = 'first_hit_value'
                                display_name = '初当り回数値'
                                color = 'blue'
                            elif text in ['3721', '_3721']:
                                name = 'total_start'
                                display_name = '累計スタート'
                                color = 'white'
                            elif text == '26830':
                                name = 'max_payout'
                                display_name = '最高出玉'
                                color = 'white'
                            elif text == '369':
                                name = 'start'
                                display_name = 'スタート'
                                color = 'white'
                            elif text in ['1877', '1844']:
                                name = f'value_{text}'
                                display_name = f'数値 {text}'
                                color = 'white'
                            else:
                                name = f'region_{idx}'
                                display_name = text
                                color = 'white'
                            
                            custom_regions[name] = {
                                'name': display_name,
                                'bbox': bbox,
                                'color': color,
                                'detected_text': text
                            }
                        
                        # 定義を表示
                        st.success(f"{len(custom_regions)}個の領域を定義しました")
                        
                        # 定義をJSONで表示
                        with st.expander("領域定義 (JSON)"):
                            st.json(custom_regions)
                        
                        # 定義をダウンロード
                        region_json = json.dumps(custom_regions, ensure_ascii=False, indent=2)
                        st.download_button(
                            label="💾 領域定義をダウンロード",
                            data=region_json,
                            file_name="region_definitions.json",
                            mime="application/json",
                            use_container_width=True
                        )