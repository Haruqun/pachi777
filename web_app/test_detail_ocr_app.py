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

# mask.pngから抽出したOCR領域（黒背景左上を基準とした相対座標）
# オフセット: X=0, Y=-191でピッタリ合う
OCR_REGIONS_FROM_MASK = {
    'big_hit_count': {'x': 80, 'y': 117, 'w': 239, 'h': 125, 'color': 'red'},  # 大当り回数 25
    'first_hit_count': {'x': 462, 'y': 117, 'w': 239, 'h': 125, 'color': 'blue'},  # 初当り回数 4
    'total_start': {'x': 859, 'y': 126, 'w': 203, 'h': 61, 'color': 'white'},  # 累計スタート 3721
    'big_hit_rate': {'x': 80, 'y': 244, 'w': 239, 'h': 50, 'color': 'red'},  # (1/148)
    'first_hit_rate': {'x': 462, 'y': 244, 'w': 239, 'h': 50, 'color': 'blue'},  # (1/469)
    'normal': {'x': 758, 'y': 239, 'w': 110, 'h': 50, 'color': 'white'},  # 通常 1877
    'chance': {'x': 868, 'y': 239, 'w': 110, 'h': 50, 'color': 'white'},  # チャンス中 1844
    'ultra': {'x': 80, 'y': 397, 'w': 86, 'h': 50, 'color': 'red'},  # 超 21
    'middle': {'x': 185, 'y': 397, 'w': 56, 'h': 50, 'color': 'red'},  # 中 0
    'small': {'x': 250, 'y': 397, 'w': 86, 'h': 50, 'color': 'red'},  # 小 4
    'start': {'x': 496, 'y': 382, 'w': 171, 'h': 81, 'color': 'white'},  # スタート 369
    'max_payout': {'x': 822, 'y': 382, 'w': 277, 'h': 81, 'color': 'white'},  # 最高出玉 26830
}

# デフォルトで相対座標を使用
OCR_REGIONS = OCR_REGIONS_FROM_MASK

# 黒背景領域からの相対座標を計算する関数
def absolute_to_relative_coords(absolute_coords, black_x, black_y):
    """絶対座標を黒背景からの相対座標に変換"""
    relative_coords = {}
    for key, region in absolute_coords.items():
        relative_coords[key] = {
            'x': region['x'] - black_x,
            'y': region['y'] - black_y,
            'w': region['w'],
            'h': region['h'],
            'color': region['color']
        }
    return relative_coords

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
    
    # マスクオーバーレイ設定
    st.subheader("マスクオーバーレイ")
    use_mask = st.checkbox("mask.pngを使用", value=False)
    if use_mask:
        mask_offset_x = st.number_input("X軸オフセット", min_value=-500, max_value=500, value=0, step=1)
        mask_offset_y = st.number_input("Y軸オフセット", min_value=-500, max_value=500, value=-191, step=1)  # デフォルト値: -191

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
    
    # 黒背景領域を検出
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, black_mask = cv2.threshold(gray, 40, 255, cv2.THRESH_BINARY_INV)
    
    # 輪郭を検出
    contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 最大の輪郭を見つける（黒背景領域）
    black_region_found = False
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # 黒背景領域が十分大きい場合
        if w * h > width * height * 0.2:
            black_region_found = True
            black_x = x
            black_y = y
            black_w = w
            black_h = h
            
            # 黒背景の左上から480pxと730px（480+250）の位置に線を引く
            line1_y = black_y + 480
            line2_y = black_y + 730
            
            # 画像に線を描画（デバッグ用）
            img_with_lines = img_bgr.copy()
            # 1本目の線（赤色）
            cv2.line(img_with_lines, (black_x, line1_y), (black_x + black_w, line1_y), (0, 0, 255), 3)
            # 2本目の線（青色）
            cv2.line(img_with_lines, (black_x, line2_y), (black_x + black_w, line2_y), (255, 0, 0), 3)
            
            # 黒背景の枠も描画（緑色）
            cv2.rectangle(img_with_lines, (black_x, black_y), (black_x + black_w, black_y + black_h), (0, 255, 0), 2)
            
            st.info(f"黒背景領域: 左上({black_x}, {black_y}), サイズ({black_w}x{black_h})")
            st.info(f"赤線: Y={line1_y} (黒背景から480px), 青線: Y={line2_y} (黒背景から730px)")
            
            # OCR用には元画像を使用（線なし）
            img_bgr_for_ocr = img_bgr
            ocr_height, ocr_width = height, width
            offset_x = 0
            offset_y = 0
        else:
            img_bgr_for_ocr = img_bgr
            img_with_lines = img_bgr.copy()
            ocr_height, ocr_width = height, width
            offset_x = 0
            offset_y = 0
    else:
        img_bgr_for_ocr = img_bgr
        img_with_lines = img_bgr.copy()
        ocr_height, ocr_width = height, width
        offset_x = 0
        offset_y = 0
    
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
                
                # 黒背景領域を基準にOCR実行
                if 'black_region_found' in locals() and black_region_found:
                    # 黒背景が見つかった場合、相対座標を使用
                    base_x = black_x
                    base_y = black_y
                    st.info(f"黒背景を基準にOCR実行: ({base_x}, {base_y})")
                else:
                    # 黒背景が見つからない場合は警告
                    st.warning("黒背景が検出されませんでした。画像全体を基準にします。")
                    base_x = 0
                    base_y = 0
                
                # 定義した領域からOCR実行（相対座標を使用）
                total_regions = len(OCR_REGIONS)
                for idx, (region_name, region) in enumerate(OCR_REGIONS.items()):
                    progress.progress((idx + 1) / total_regions)
                    
                    # 黒背景からの相対座標を絶対座標に変換
                    x = base_x + region['x']
                    y = base_y + region['y']
                    w = region['w']
                    h = region['h']
                    
                    # 画像の範囲チェック
                    if x < 0 or y < 0 or x + w > width or y + h > height:
                        st.warning(f"領域 {region_name} が画像範囲外です")
                        continue
                    
                    # 領域を切り抜き
                    roi = img_bgr[y:y+h, x:x+w]
                    
                    # 色に応じた前処理
                    if region['color'] == 'red':
                        # 赤色テキストの処理
                        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                        # 赤色の範囲
                        mask1 = cv2.inRange(hsv_roi, np.array([0, 50, 50]), np.array([10, 255, 255]))
                        mask2 = cv2.inRange(hsv_roi, np.array([170, 50, 50]), np.array([180, 255, 255]))
                        red_mask = cv2.bitwise_or(mask1, mask2)
                        # 白黒反転
                        processed = cv2.bitwise_not(red_mask)
                        
                    elif region['color'] == 'blue':
                        # 青色テキストの処理
                        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                        # 青色の範囲
                        blue_mask = cv2.inRange(hsv_roi, np.array([100, 50, 50]), np.array([130, 255, 255]))
                        # 白黒反転
                        processed = cv2.bitwise_not(blue_mask)
                        
                    else:  # white
                        # 白色テキストの処理
                        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                        _, processed = cv2.threshold(gray_roi, 180, 255, cv2.THRESH_BINARY)
                    
                    # OCR実行
                    try:
                        # 数値と記号のみを対象
                        custom_config = '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789/()'
                        text = pytesseract.image_to_string(processed, config=custom_config, lang='jpn').strip()
                        
                        # 結果を保存
                        if text:
                            detected_data[region_name] = text
                            all_detections.append({
                                'region': region_name,
                                'text': text,
                                'bbox': [x, y, x+w, y+h],
                                'color': region['color']
                            })
                    except Exception as e:
                        st.warning(f"領域 {region_name} のOCRエラー: {str(e)}")
                        continue
            
            # 結果を表示
            st.success(f"検出完了！ {len(all_detections)}個のテキストを検出")
            
            # メトリクス表示
            col1, col2, col3 = st.columns(3)
            
            # 色別カウント
            white_count = len([d for d in all_detections if d['color'] == 'white'])
            red_count = len([d for d in all_detections if d['color'] == 'red'])
            blue_count = len([d for d in all_detections if d['color'] == 'blue'])
            
            with col1:
                st.metric("白色テキスト", white_count)
            with col2:
                st.metric("赤色テキスト", red_count)
            with col3:
                st.metric("青色テキスト", blue_count)
            
            # 検出テキストリスト
            st.divider()
            st.markdown("### 検出されたテキスト")
            
            # 検出されたデータと期待値を比較
            st.divider()
            st.markdown("### 📊 検出結果と期待値の比較")
            
            comparison_data = []
            for key, expected in EXPECTED_DATA.items():
                detected = detected_data.get(key, "未検出")
                status = "✅" if detected == expected else "❌"
                comparison_data.append({
                    "領域": key,
                    "期待値": expected,
                    "検出値": detected,
                    "状態": status
                })
            
            # テーブル形式で表示
            import pandas as pd
            df = pd.DataFrame(comparison_data)
            st.dataframe(df, use_container_width=True)
            
            # 領域ごとの検出結果
            with st.expander("領域別検出結果"):
                for detection in all_detections:
                    color_emoji = {"white": "⚪", "red": "🔴", "blue": "🔵"}.get(detection['color'], "⚫")
                    st.write(f"{color_emoji} **{detection['region']}**: {detection['text']}")
            
            # Save to session state for JSON export
            st.session_state['detections'] = all_detections
            st.session_state['detected_data'] = detected_data
    
    with tab2:
        st.subheader("🎨 色マスク表示")
        
        if show_masks:
            hsv = cv2.cvtColor(img_bgr_for_ocr, cv2.COLOR_BGR2HSV)
            gray = cv2.cvtColor(img_bgr_for_ocr, cv2.COLOR_BGR2GRAY)
            
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
        
        # 検出結果のオーバーレイ画像を作成（線付き画像を使用）
        vis_img = img_with_lines.copy()
        
        # mask.pngを使用する場合
        if 'use_mask' in locals() and use_mask:
            # mask.pngを読み込み（リサイズ禁止）
            import os
            mask_path = os.path.join(os.path.dirname(__file__), 'mask', 'mask.png')
            if os.path.exists(mask_path):
                mask_img = cv2.imread(mask_path)
                
                # マスクはリサイズせずにそのまま使用
                mask_h, mask_w = mask_img.shape[:2]
                st.info(f"マスクサイズ: {mask_w} x {mask_h} (リサイズなし)")
                
                # 赤色領域を検出
                lower_red = np.array([0, 0, 254])
                upper_red = np.array([1, 1, 255])
                red_mask = cv2.inRange(mask_img, lower_red, upper_red)
                
                # 黒背景領域がある場合、そこからのオフセットを適用
                if 'black_region_found' in locals() and black_region_found:
                    base_x = black_x + mask_offset_x
                    base_y = black_y + mask_offset_y
                else:
                    base_x = mask_offset_x
                    base_y = mask_offset_y
                
                # マスクをそのまま使用（オフセットは矩形描画時に適用）
                shifted_mask = red_mask
                
                # マスクの輪郭を検出
                contours, _ = cv2.findContours(shifted_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # 各輪郭に対して半透明の赤い矩形を描画（オフセット適用）
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w > 10 and h > 10:  # 小さすぎる領域は無視
                        # オフセットを適用
                        x_shifted = x + base_x
                        y_shifted = y + base_y
                        
                        # 画像範囲内かチェック
                        if 0 <= x_shifted < width and 0 <= y_shifted < height:
                            # 半透明の赤い矩形
                            overlay = vis_img.copy()
                            cv2.rectangle(overlay, (x_shifted, y_shifted), (x_shifted+w, y_shifted+h), (0, 0, 255), -1)
                            cv2.addWeighted(overlay, 0.3, vis_img, 0.7, 0, vis_img)
                            # 枠線
                            cv2.rectangle(vis_img, (x_shifted, y_shifted), (x_shifted+w, y_shifted+h), (0, 0, 255), 2)
                
                st.info(f"マスクオフセット: X={mask_offset_x}, Y={mask_offset_y}")
                if 'black_region_found' in locals() and black_region_found:
                    st.info(f"黒背景左上: ({black_x}, {black_y}) → 実際の基準点: ({base_x}, {base_y})")
            else:
                st.warning("mask/mask.pngが見つかりません")
        else:
            # OCR領域を描画（Figmaで定義した絶対座標）  
            for name, region in OCR_REGIONS.items():
                x = region['x']
                y = region['y']
                w = region['w']
                h = region['h']
                
                # 色設定
                if region['color'] == 'red':
                    color = (0, 0, 255)
                elif region['color'] == 'blue':
                    color = (255, 0, 0)
                else:
                    color = (200, 200, 200)
                
                # 矩形を描画
                cv2.rectangle(vis_img, (x, y), (x + w, y + h), color, 2)
                
                # ラベルを表示（小さめのフォント）
                cv2.putText(vis_img, name[:8], (x, y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
        
        # 検出結果がある場合は描画
        if 'detections' in st.session_state and st.session_state['detections']:
            for detection in st.session_state['detections']:
                x1, y1, x2, y2 = detection['bbox']
                
                # 検出結果のテキストを領域内に表示
                text = detection.get('text', '')
                if text:
                    # テキストを矩形の中央に配置
                    text_x = x1 + 5
                    text_y = y1 + (y2 - y1) // 2
                    
                    # テキストの背景（半透明風）
                    cv2.putText(vis_img, text, (text_x, text_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
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
        
        # 線の説明
        if 'black_region_found' in locals() and black_region_found:
            st.markdown("### 📏 検出された領域")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.success(f"🟢 緑枠: 黒背景領域")
                st.write(f"左上: ({black_x}, {black_y})")
                st.write(f"サイズ: {black_w} × {black_h}px")
            with col2:
                st.error(f"🔴 赤線: Y={line1_y}")
                st.write(f"黒背景上端から480px")
            with col3:
                st.info(f"🔵 青線: Y={line2_y}")
                st.write(f"黒背景上端から730px")
                st.write(f"(480px + 250px)")
            
            # OCR領域の説明
            st.markdown("### 📋 OCR対象領域")
            st.info(f"{len(OCR_REGIONS)}個の領域がFigmaの座標で正確に定義されています")
        
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