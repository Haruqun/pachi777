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
    
    # 黒背景領域を検出（複数の方法を試す）
    def detect_black_region(img):
        """黒背景領域を検出して座標を返す（改善版）"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # 複数の検出方法を試す
        methods = []
        
        # 方法1: 緩い閾値での検出（閾値40）
        _, mask1 = cv2.threshold(gray, 40, 255, cv2.THRESH_BINARY_INV)
        kernel = np.ones((10,10), np.uint8)
        mask1 = cv2.morphologyEx(mask1, cv2.MORPH_CLOSE, kernel)
        mask1 = cv2.morphologyEx(mask1, cv2.MORPH_OPEN, kernel)
        contours1, _ = cv2.findContours(mask1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 方法2: 適応的閾値処理
        mask2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                      cv2.THRESH_BINARY_INV, 51, 10)
        mask2 = cv2.morphologyEx(mask2, cv2.MORPH_CLOSE, kernel)
        mask2 = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel)
        contours2, _ = cv2.findContours(mask2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 方法3: エッジ検出ベース
        edges = cv2.Canny(gray, 30, 100)
        kernel_small = np.ones((3,3), np.uint8)
        edges = cv2.dilate(edges, kernel_small, iterations=2)
        edges = cv2.erode(edges, kernel_small, iterations=1)
        # エッジを反転して黒い領域を白に
        mask3 = 255 - edges
        contours3, _ = cv2.findContours(mask3, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 方法4: HSV色空間での黒検出
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # 黒い領域：低い明度（V値）
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 50])  # V値50以下
        mask4 = cv2.inRange(hsv, lower_black, upper_black)
        mask4 = cv2.morphologyEx(mask4, cv2.MORPH_CLOSE, kernel)
        mask4 = cv2.morphologyEx(mask4, cv2.MORPH_OPEN, kernel)
        contours4, _ = cv2.findContours(mask4, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 各方法から最適な輪郭を選択
        all_contours = []
        if contours1:
            all_contours.extend([(c, "threshold_40") for c in contours1])
        if contours2:
            all_contours.extend([(c, "adaptive") for c in contours2])
        if contours3:
            all_contours.extend([(c, "edge") for c in contours3])
        if contours4:
            all_contours.extend([(c, "hsv") for c in contours4])
        
        if all_contours:
            # 面積が画像の20%以上、80%以下の輪郭を候補とする
            min_area = width * height * 0.2
            max_area = width * height * 0.8
            
            valid_contours = []
            for contour, method in all_contours:
                area = cv2.contourArea(contour)
                if min_area < area < max_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    # アスペクト比も考慮（横長の矩形を優先）
                    aspect_ratio = w / h if h > 0 else 0
                    if 0.3 < aspect_ratio < 1.5:  # 適切なアスペクト比
                        valid_contours.append((contour, area, method, (x, y, w, h)))
            
            if valid_contours:
                # 最大面積の輪郭を選択
                best_contour = max(valid_contours, key=lambda x: x[1])
                x, y, w, h = best_contour[3]
                method_used = best_contour[2]
                
                # デバッグ情報を含めて返す
                return (x, y, x + w, y + h), method_used
        
        return None, None
    
    black_region, detection_method = detect_black_region(img_bgr)
    
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
    else:
        # 画像の赤枠で示された正確な座標を使用
        regions = {
            # 上部メイン数値
            'big_hit': {
                'name': '大当り回数',
                'bbox': (80, 600, 260, 740),  # 赤色の大きな25
                'color': 'red'
            },
            'big_hit_rate': {
                'name': '大当り確率',
                'bbox': (80, 740, 260, 790),  # (1/148)
                'color': 'red'
            },
            'first_hit': {
                'name': '初当り回数',
                'bbox': (480, 600, 660, 740),  # 青色の大きな4
                'color': 'blue'
            },
            'first_hit_rate': {
                'name': '初当り確率',
                'bbox': (480, 740, 660, 790),  # (1/469)
                'color': 'blue'
            },
            'total_start': {
                'name': '累計スタート',
                'bbox': (886, 638, 1040, 691),  # 3721 - 実際の検出座標
                'color': 'white'
            },
            'normal_count': {
                'name': '通常',
                'bbox': (790, 740, 920, 790),  # 1877
                'color': 'white'
            },
            'chance_count': {
                'name': 'チャンス中',
                'bbox': (1000, 740, 1160, 790),  # 1844
                'color': 'white'
            },
            
            # 超中小（赤色）
            'ultra': {
                'name': '超',
                'bbox': (80, 860, 150, 930),  # 21
                'color': 'red'
            },
            'middle': {
                'name': '中',
                'bbox': (200, 860, 240, 930),  # 0
                'color': 'red'
            },
            'small': {
                'name': '小',
                'bbox': (290, 860, 330, 930),  # 4
                'color': 'red'
            },
            
            # 中段データ
            'start': {
                'name': 'スタート',
                'bbox': (520, 860, 670, 930),  # 369
                'color': 'white'
            },
            'max_payout': {
                'name': '最高出玉',
                'bbox': (851, 897, 1087, 957),  # 26830 - 実際の検出座標
                'color': 'white'
            },
            
            # 下段第1行
            'max_hit': {
                'name': '最高一撃獲得',
                'bbox': (65, 1066, 213, 1102),  # 25760 - 実際の検出座標
                'color': 'white'
            },
            'chance_hits': {
                'name': 'チャンス中大当り',
                'bbox': (280, 1070, 390, 1110),  # 21
                'color': 'white'
            },
            'chance_rate': {
                'name': 'チャンス中確率',
                'bbox': (555, 1066, 663, 1104),  # 1/87 - 実際の検出座標
                'color': 'white'
            },
            'low_chance_hits': {
                'name': '低確中大当り',
                'bbox': (760, 1070, 870, 1110),  # --
                'color': 'white'
            },
            'low_chance_rate': {
                'name': '低確中確率',
                'bbox': (990, 1070, 1160, 1110),  # --
                'color': 'white'
            },
            
            # 下段第2行
            'initial_start': {
                'name': '初回特賞スタート',
                'bbox': (96, 1184, 182, 1220),  # 220 - 実際の検出座標
                'color': 'white'
            },
            'prev_final': {
                'name': '前日最終スタート',
                'bbox': (280, 1190, 390, 1230),  # 107
                'color': 'white'
            },
            'break_count': {
                'name': '突時回数',
                'bbox': (550, 1190, 670, 1230),  # --
                'color': 'white'
            },
            'low_start': {
                'name': '低確スタート',
                'bbox': (760, 1190, 870, 1230),  # --
                'color': 'white'
            },
            'play_time': {
                'name': '遊タイム',
                'bbox': (990, 1190, 1160, 1230),  # --
                'color': 'white'
            },
            
            # 累計テーブル（8/6）
            'date_86': {
                'name': '日付8/6',
                'bbox': (50, 1326, 124, 1364),  # 8/6 - 実際の検出座標
                'color': 'white'
            },
            'total_86': {
                'name': '累計8/6',
                'bbox': (204, 1326, 322, 1362),  # 3772 - 実際の検出座標
                'color': 'white'
            },
            'first_rate_86': {
                'name': '初当り確率8/6',
                'bbox': (430, 1326, 580, 1364),  # 1/277
                'color': 'white'
            },
            'chance_rate_86': {
                'name': 'チャンス中確率8/6',
                'bbox': (693, 1326, 831, 1364),  # 1/166 - 実際の検出座標
                'color': 'white'
            },
            'payout_86': {
                'name': '最高出玉8/6',
                'bbox': (953, 1326, 1099, 1362),  # 14670 - 実際の検出座標
                'color': 'white'
            },
            
            # 累計テーブル（8/5）
            'date_85': {
                'name': '日付8/5',
                'bbox': (50, 1386, 124, 1424),  # 8/5 - 実際の検出座標
                'color': 'white'
            },
            'total_85': {
                'name': '累計8/5',
                'bbox': (204, 1386, 321, 1422),  # 3213 - 実際の検出座標
                'color': 'white'
            },
            'first_rate_85': {
                'name': '初当り確率8/5',
                'bbox': (430, 1386, 580, 1424),  # 1/324
                'color': 'white'
            },
            'chance_rate_85': {
                'name': 'チャンス中確率8/5',
                'bbox': (709, 1386, 815, 1424),  # 1/79 - 実際の検出座標
                'color': 'white'
            },
            'payout_85': {
                'name': '最高出玉8/5',
                'bbox': (951, 1386, 1099, 1422),  # 22100 - 実際の検出座標
                'color': 'white'
            }
        }
    
    # メインレイアウト：左に画像、右に操作
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📷 検出領域")
        
        # グリッド表示オプション
        show_grid = st.checkbox("10pxグリッドを表示", value=True)
        
        # 画像のコピーを作成
        vis_img = img_bgr.copy()
        
        # 10pxごとのグリッドを描画
        if show_grid:
            # 垂直線（10pxごと）
            for x in range(0, width, 10):
                # 50pxごとに太線
                if x % 50 == 0:
                    cv2.line(vis_img, (x, 0), (x, height), (100, 100, 100), 1)
                    # 100pxごとに番号表示
                    if x % 100 == 0 and x > 0:
                        cv2.putText(vis_img, str(x), (x-15, 20), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
                else:
                    cv2.line(vis_img, (x, 0), (x, height), (50, 50, 50), 1)
            
            # 水平線（10pxごと）
            for y in range(0, height, 10):
                # 50pxごとに太線
                if y % 50 == 0:
                    cv2.line(vis_img, (0, y), (width, y), (100, 100, 100), 1)
                    # 100pxごとに番号表示
                    if y % 100 == 0 and y > 0:
                        cv2.putText(vis_img, str(y), (5, y+5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
                else:
                    cv2.line(vis_img, (0, y), (width, y), (50, 50, 50), 1)
        
        # 黒背景領域を赤色の太い枠で表示
        if black_region:
            bx1, by1, bx2, by2 = black_region
            # 赤色の太い枠で黒背景領域を強調
            cv2.rectangle(vis_img, (bx1, by1), (bx2, by2), (0, 0, 255), 5)  # 赤色、線の太さ5
            
            # 左上隅に大きな黄色の点（マーカー）を追加
            # 塗りつぶした円で目立つようにする
            cv2.circle(vis_img, (bx1, by1), 15, (0, 255, 255), -1)  # 黄色、半径15px、塗りつぶし
            # さらに赤い輪郭を追加して強調
            cv2.circle(vis_img, (bx1, by1), 15, (0, 0, 255), 3)  # 赤色の輪郭、線の太さ3
            
            # 座標テキストも左上に表示
            coord_text = f"({bx1}, {by1})"
            cv2.putText(vis_img, coord_text, (bx1 + 25, by1 + 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # 検出方法も表示
            text = f"Black Region ({detection_method})"
            cv2.putText(vis_img, text, (bx1, by1-25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
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
            
            # 座標値を枠の内側に表示（デバッグ用）
            if show_grid:
                coord_text = f"({x1},{y1})"
                cv2.putText(vis_img, coord_text, (x1+2, y1+15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
        
        # 表示
        st.image(cv2.cvtColor(vis_img, cv2.COLOR_BGR2RGB), 
                caption="OCR対象領域", use_column_width=True)
        
        # 画像情報
        st.info(f"画像サイズ: {width} x {height} px")
        if black_region:
            bx1, by1, bx2, by2 = black_region
            st.success(f"黒背景領域: ({bx1}, {by1}) - ({bx2}, {by2})")
            st.info(f"検出方法: {detection_method}")
            st.info(f"黒背景サイズ: {bx2-bx1} x {by2-by1} px")
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
                        # 余白を追加してOCR精度向上
                        padding = 5
                        y1_pad = max(0, y1 - padding)
                        y2_pad = min(height, y2 + padding)
                        x1_pad = max(0, x1 - padding)
                        x2_pad = min(width, x2 + padding)
                        roi = img_bgr[y1_pad:y2_pad, x1_pad:x2_pad]
                        
                        try:
                            if region['color'] == 'red':
                                # 赤色抽出（改善版）
                                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                                # ピンク〜赤の範囲を拡大
                                mask1 = cv2.inRange(hsv, np.array([0, 20, 20]), np.array([20, 255, 255]))
                                mask2 = cv2.inRange(hsv, np.array([160, 20, 20]), np.array([180, 255, 255]))
                                mask = cv2.bitwise_or(mask1, mask2)
                                # モルフォロジー処理でノイズ除去
                                kernel = np.ones((2,2), np.uint8)
                                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                                # 白黒反転（テキストを黒に）
                                mask = cv2.bitwise_not(mask)
                                # 複数のPSMモードを試す
                                text = ''
                                for psm in [8, 7, 13, 6]:
                                    try:
                                        temp_text = pytesseract.image_to_string(mask, config=f'--psm {psm} -c tessedit_char_whitelist=0123456789/')
                                        temp_text = temp_text.strip()
                                        if temp_text and (not text or len(temp_text) > len(text)):
                                            text = temp_text
                                    except:
                                        continue
                                
                            elif region['color'] == 'blue':
                                # 青色抽出（改善版）
                                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                                # シアン〜青の範囲を拡大
                                mask = cv2.inRange(hsv, np.array([85, 20, 20]), np.array([125, 255, 255]))
                                # モルフォロジー処理
                                kernel = np.ones((2,2), np.uint8)
                                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                                # 白黒反転
                                mask = cv2.bitwise_not(mask)
                                # 複数のPSMモードを試す
                                text = ''
                                for psm in [8, 7, 13, 6]:
                                    try:
                                        temp_text = pytesseract.image_to_string(mask, config=f'--psm {psm} -c tessedit_char_whitelist=0123456789/')
                                        temp_text = temp_text.strip()
                                        if temp_text and (not text or len(temp_text) > len(text)):
                                            text = temp_text
                                    except:
                                        continue
                                
                            else:  # white
                                # 白色抽出（改善版）
                                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                                # 適応的闾値処理
                                binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                              cv2.THRESH_BINARY, 11, 2)
                                # 通常の闾値処理も試す
                                _, binary2 = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
                                
                                # 複数のバイナリ画像でOCRを試す
                                text = ''
                                for img in [binary, binary2]:
                                    for psm in [7, 8, 13, 6]:
                                        try:
                                            temp_text = pytesseract.image_to_string(img, config=f'--psm {psm} -c tessedit_char_whitelist=0123456789/')
                                            temp_text = temp_text.strip()
                                            if temp_text and (not text or len(temp_text) > len(text)):
                                                text = temp_text
                                        except:
                                            continue
                            
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
                with st.spinner("文字検出中（複数手法で検出中）..."):
                    detected_regions = []
                    vis_full_img = img_bgr.copy()
                    
                    # デバッグ情報を保存
                    debug_info = {
                        'attempts': [],
                        'success_count': {'white': 0, 'red': 0, 'blue': 0, 'inverted': 0, 'mono_blue': 0, 'mono_red': 0, 'mono_green': 0},
                        'psm_count': {6: 0, 8: 0, 11: 0, 13: 0}
                    }
                    
                    # HSV変換
                    hsv = cv2.cvtColor(target_img, cv2.COLOR_BGR2HSV)
                    
                    # 1. 白色テキスト検出（複数の手法を組み合わせ）
                    gray = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
                    
                    # 複数の閾値で白色マスクを作成
                    _, white_mask1 = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
                    _, white_mask2 = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
                    _, white_mask3 = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
                    
                    # 適応的閾値処理
                    white_mask_adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                                cv2.THRESH_BINARY, 11, 2)
                    
                    # CLAHE（コントラスト強調）後の閾値処理
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                    enhanced = clahe.apply(gray)
                    _, white_mask_enhanced = cv2.threshold(enhanced, 180, 255, cv2.THRESH_BINARY)
                    
                    # 2. 赤色テキスト検出（ピンク〜赤の広い範囲）
                    # ピンク系（明度高め）
                    pink_mask = cv2.inRange(hsv, np.array([150, 10, 100]), np.array([180, 60, 255]))
                    # 赤系（彩度高め）
                    red_mask1 = cv2.inRange(hsv, np.array([0, 40, 40]), np.array([10, 255, 255]))
                    red_mask2 = cv2.inRange(hsv, np.array([170, 40, 40]), np.array([180, 255, 255]))
                    # マゼンタ系
                    magenta_mask = cv2.inRange(hsv, np.array([140, 30, 50]), np.array([170, 255, 255]))
                    # 組み合わせ
                    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
                    red_mask = cv2.bitwise_or(red_mask, pink_mask)
                    red_mask = cv2.bitwise_or(red_mask, magenta_mask)
                    # モルフォロジー処理
                    kernel = np.ones((2,2), np.uint8)
                    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
                    red_mask = cv2.bitwise_not(red_mask)
                    
                    # 3. 青色テキスト検出（シアン〜青の広い範囲）
                    # シアン系
                    cyan_mask = cv2.inRange(hsv, np.array([80, 30, 50]), np.array([100, 255, 255]))
                    # 青系
                    blue_mask = cv2.inRange(hsv, np.array([100, 30, 50]), np.array([120, 255, 255]))
                    # 組み合わせ
                    blue_mask = cv2.bitwise_or(cyan_mask, blue_mask)
                    # モルフォロジー処理
                    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)
                    blue_mask = cv2.bitwise_not(blue_mask)
                    
                    # 4. 色調反転とモノクロ化
                    # 元画像の反転
                    inverted = cv2.bitwise_not(target_img)
                    inverted_gray = cv2.cvtColor(inverted, cv2.COLOR_BGR2GRAY)
                    _, inverted_mask = cv2.threshold(inverted_gray, 127, 255, cv2.THRESH_BINARY)
                    
                    # モノクロ化（グレースケール）の複数パターン
                    # 標準グレースケール
                    mono_standard = gray.copy()
                    
                    # 青チャンネル強調（青文字に効果的）
                    b, g, r = cv2.split(target_img)
                    mono_blue_emphasis = b
                    
                    # 赤チャンネル強調（赤文字に効果的）
                    mono_red_emphasis = r
                    
                    # 緑チャンネル（中間的）
                    mono_green = g
                    
                    # 各チャンネルの二値化
                    _, mono_blue_binary = cv2.threshold(mono_blue_emphasis, 127, 255, cv2.THRESH_BINARY_INV)
                    _, mono_red_binary = cv2.threshold(mono_red_emphasis, 127, 255, cv2.THRESH_BINARY_INV)
                    _, mono_green_binary = cv2.threshold(mono_green, 180, 255, cv2.THRESH_BINARY)
                    
                    # 各マスクでOCR実行（白色は複数のマスクを試す）
                    masks = [
                        ('white', white_mask1),
                        ('white', white_mask2),
                        ('white', white_mask3),
                        ('white', white_mask_adaptive),
                        ('white', white_mask_enhanced),
                        ('red', red_mask),
                        ('blue', blue_mask),
                        ('inverted', inverted_mask),
                        ('mono_blue', mono_blue_binary),
                        ('mono_red', mono_red_binary),
                        ('mono_green', mono_green_binary)
                    ]
                    
                    for mask_idx, (color_name, mask) in enumerate(masks):
                        # 複数のPSMモードで試行
                        for psm in [11, 6, 8, 13]:
                            try:
                                debug_info['attempts'].append(f"{color_name}_mask{mask_idx}_psm{psm}")
                                
                                custom_config = f'--psm {psm} -c tessedit_char_whitelist=0123456789/'
                                data = pytesseract.image_to_data(mask, config=custom_config, output_type=pytesseract.Output.DICT)
                                
                                for i in range(len(data['text'])):
                                    text = str(data['text'][i]).strip()
                                    conf = int(data['conf'][i])
                                    
                                    # 信頼度20以上かつ空でないテキストのみ
                                    if conf > 20 and text and text != '':
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
                                        
                                        # 重複チェック
                                        is_duplicate = False
                                        for existing in detected_regions:
                                            if (abs(existing['bbox'][0] - abs_x) < 20 and 
                                                abs(existing['bbox'][1] - abs_y) < 20 and
                                                existing['text'] == text):
                                                is_duplicate = True
                                                break
                                        
                                        if not is_duplicate:
                                            region_info = {
                                                'text': text,
                                                'confidence': conf,
                                                'bbox': [abs_x, abs_y, abs_x + w, abs_y + h],
                                                'color': color_name,
                                                'psm': psm
                                            }
                                            detected_regions.append(region_info)
                                            if color_name in debug_info['success_count']:
                                                debug_info['success_count'][color_name] += 1
                                            debug_info['psm_count'][psm] += 1
                            except Exception as e:
                                debug_info['attempts'].append(f"ERROR: {color_name}_mask{mask_idx}_psm{psm}: {str(e)[:50]}")
                                continue
                    
                    # 検出結果を描画
                    for region in detected_regions:
                        abs_x, abs_y, x2, y2 = region['bbox']
                        color_map = {
                            'white': (200, 200, 200),
                            'red': (0, 0, 255),
                            'blue': (255, 0, 0)
                        }
                        color = color_map.get(region['color'], (0, 255, 0))
                        cv2.rectangle(vis_full_img, (abs_x, abs_y), (x2, y2), color, 2)
                        cv2.putText(vis_full_img, region['text'][:10], (abs_x, abs_y - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                # 結果表示
                st.success(f"OCR完了！ {len(detected_regions)}個のテキストを検出")
                
                # デバッグ情報表示
                with st.expander("🔍 OCRデバッグ情報"):
                    st.markdown("### 検出統計")
                    
                    # 基本色
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("白色テキスト", debug_info['success_count']['white'])
                    with col2:
                        st.metric("赤色テキスト", debug_info['success_count']['red'])
                    with col3:
                        st.metric("青色テキスト", debug_info['success_count']['blue'])
                    
                    # 追加手法
                    col4, col5, col6, col7 = st.columns(4)
                    with col4:
                        st.metric("反転", debug_info['success_count']['inverted'])
                    with col5:
                        st.metric("青Ch", debug_info['success_count']['mono_blue'])
                    with col6:
                        st.metric("赤Ch", debug_info['success_count']['mono_red'])
                    with col7:
                        st.metric("緑Ch", debug_info['success_count']['mono_green'])
                    
                    st.markdown("### PSMモード別検出数")
                    psm_cols = st.columns(4)
                    for idx, (psm, count) in enumerate(debug_info['psm_count'].items()):
                        with psm_cols[idx]:
                            st.metric(f"PSM {psm}", count)
                    
                    st.markdown("### 試行ログ")
                    st.text_area("OCR試行履歴", "\n".join(debug_info['attempts'][:100]), height=200)
                
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
                
                # 検出された数値をフィルタリング（2桁以上の数字と分数形式）
                important_texts = []
                for region in detected_regions:
                    text = region['text']
                    # 数値のみ（2桁以上）または分数形式（1/xxx）
                    if (text.replace('/', '').isdigit() and len(text.replace('/', '')) >= 2):
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
                            
                            # 領域名を自動生成（数値ベース）
                            # Y座標で位置を判定
                            y_pos = bbox[1]
                            
                            # 上部（600-750px）: メイン数値
                            if 600 <= y_pos <= 750:
                                if bbox[0] < 300:  # 左側
                                    name = 'big_hit_value'
                                    display_name = '大当り回数'
                                    color = 'red'
                                elif bbox[0] < 600:  # 中央
                                    name = 'first_hit_value'
                                    display_name = '初当り回数'
                                    color = 'blue'
                                else:  # 右側
                                    name = 'total_start'
                                    display_name = '累計スタート'
                                    color = 'white'
                            
                            # 中段（850-1000px）: 超中小、スタート、最高出玉
                            elif 850 <= y_pos <= 1000:
                                if text == '21':
                                    name = 'ultra'
                                    display_name = '超'
                                    color = 'red'
                                elif text == '0':
                                    name = 'middle'
                                    display_name = '中'
                                    color = 'red'
                                elif text == '4':
                                    name = 'small'
                                    display_name = '小'
                                    color = 'red'
                                elif text == '369':
                                    name = 'start'
                                    display_name = 'スタート'
                                    color = 'white'
                                elif text == '26830':
                                    name = 'max_payout'
                                    display_name = '最高出玉'
                                    color = 'white'
                                else:
                                    name = f'mid_{text}'
                                    display_name = f'中段_{text}'
                                    color = 'white'
                            
                            # 下段テーブル（1000-1250px）
                            elif 1000 <= y_pos <= 1250:
                                if text == '25760':
                                    name = 'max_hit'
                                    display_name = '最高一撃獲得'
                                elif text == '220':
                                    name = 'initial_start'
                                    display_name = '初回特賞スタート'
                                elif text == '107':
                                    name = 'prev_final'
                                    display_name = '前日最終スタート'
                                elif '/' in text:
                                    name = f'rate_{text.replace("/", "_")}'
                                    display_name = f'確率_{text}'
                                else:
                                    name = f'lower_{text}'
                                    display_name = f'下段_{text}'
                                color = 'white'
                            
                            # 累計テーブル（1300px以降）
                            elif y_pos >= 1300:
                                if '/' in text:
                                    name = f'table_rate_{text.replace("/", "_")}'
                                    display_name = f'テーブル確率_{text}'
                                elif text in ['3772', '3213']:
                                    name = f'table_total_{text}'
                                    display_name = f'累計_{text}'
                                elif text in ['14670', '22100']:
                                    name = f'table_payout_{text}'
                                    display_name = f'出玉_{text}'
                                else:
                                    name = f'table_{text}'
                                    display_name = f'テーブル_{text}'
                                color = 'white'
                            
                            else:
                                name = f'value_{text}'
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