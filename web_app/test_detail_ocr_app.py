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

# Expected data items from the image（簡略版）
EXPECTED_DATA = {
    'header': 'エヴァンゲリオン',  # ヘッダー（実際のタイトル）
    'store_info': '0026',  # 店舗情報
    'date_info': '12/1',  # 日付（実際の日付）
    'total_start': '3721',  # 累計スタート
    'normal': '1877',  # 通常
    'chance': '1844',  # チャンス中
    'ultra': '21',  # 超
    'middle': '0',  # 中
    'small': '4',  # 小
    'start': '369',  # スタート
    'max_payout': '26830',  # 最高出玉
    'max_hit': '25760',  # 最高一撃獲得
    'initial_start': '40'  # 初回特賞スタート
}

# mask2.pngから抽出したOCR領域（黒背景左上を基準とした相対座標）
# オフセット: X=0, Y=-188でピッタリ合う（最適値）
# 統合領域を使用して精度向上
OCR_REGIONS_FROM_MASK2 = {
    # ヘッダー（黒枠外）
    'header': {'x': 21, 'y': -188, 'w': 1129, 'h': 64, 'color': 'white'},
    'store_info': {'x': 0, 'y': -106, 'w': 211, 'h': 99, 'color': 'white'},
    'date_info': {'x': 4, 'y': 3, 'w': 80, 'h': 61, 'color': 'white'},
    
    # 統合領域（複数のデータを含む）
    'big_first_hit_combined': {'x': 79, 'y': 116, 'w': 236, 'h': 192, 'color': 'mixed'},  # 大当り回数と確率
    'first_hit_combined': {'x': 457, 'y': 116, 'w': 236, 'h': 192, 'color': 'mixed'},  # 初当り回数と確率
    'total_start_combined': {'x': 786, 'y': 116, 'w': 346, 'h': 80, 'color': 'white'},  # 累計スタート
    
    # 通常/チャンス
    'normal': {'x': 786, 'y': 234, 'w': 164, 'h': 77, 'color': 'white'},
    'chance': {'x': 961, 'y': 234, 'w': 174, 'h': 77, 'color': 'white'},
    
    # 中段
    'start': {'x': 471, 'y': 373, 'w': 208, 'h': 105, 'color': 'white'},
    'max_payout': {'x': 813, 'y': 373, 'w': 274, 'h': 107, 'color': 'white'},
    'ultra': {'x': 79, 'y': 389, 'w': 82, 'h': 72, 'color': 'red'},
    'middle': {'x': 166, 'y': 389, 'w': 74, 'h': 72, 'color': 'red'},
    'small': {'x': 244, 'y': 389, 'w': 73, 'h': 72, 'color': 'red'},
    
    # 下段テーブル
    'max_hit': {'x': 33, 'y': 549, 'w': 202, 'h': 61, 'color': 'white'},
    'chance_hits': {'x': 264, 'y': 549, 'w': 201, 'h': 61, 'color': 'white'},
    'chance_rate': {'x': 494, 'y': 549, 'w': 202, 'h': 61, 'color': 'white'},
    'low_hits': {'x': 725, 'y': 549, 'w': 201, 'h': 61, 'color': 'white'},
    'play_time': {'x': 955, 'y': 549, 'w': 202, 'h': 61, 'color': 'white'},
    'initial_start': {'x': 35, 'y': 665, 'w': 201, 'h': 61, 'color': 'white'},
    'prev_final': {'x': 262, 'y': 665, 'w': 201, 'h': 61, 'color': 'white'},
    'rush_count': {'x': 492, 'y': 665, 'w': 202, 'h': 61, 'color': 'white'},
    'low_start': {'x': 723, 'y': 665, 'w': 201, 'h': 61, 'color': 'white'},
    'lost_time': {'x': 953, 'y': 665, 'w': 202, 'h': 61, 'color': 'white'},
}

# mask.pngから抽出したOCR領域（黒背景左上を基準とした相対座標）
# オフセット: X=0, Y=-191でピッタリ合う（黒枠外の領域も含む）
OCR_REGIONS_FROM_MASK = {
    # ヘッダー（黒枠外）
    'header': {'x': 21, 'y': -191, 'w': 1129, 'h': 64, 'color': 'white'},  # トップバー
    'store_info': {'x': 0, 'y': -109, 'w': 211, 'h': 99, 'color': 'white'},  # 店舗情報
    'date_info': {'x': 4, 'y': 0, 'w': 80, 'h': 61, 'color': 'white'},  # 日付
    
    # メイン数値
    'big_hit_count': {'x': 79, 'y': 113, 'w': 237, 'h': 125, 'color': 'red'},  # 大当り回数 25
    'first_hit_count': {'x': 456, 'y': 113, 'w': 238, 'h': 125, 'color': 'blue'},  # 初当り回数 4
    'total_start': {'x': 849, 'y': 126, 'w': 202, 'h': 61, 'color': 'white'},  # 累計スタート 3721
    
    # 確率表示
    'big_hit_rate': {'x': 79, 'y': 241, 'w': 237, 'h': 50, 'color': 'red'},  # (1/148)
    'first_hit_rate': {'x': 456, 'y': 241, 'w': 238, 'h': 50, 'color': 'blue'},  # (1/469)
    
    # 通常/チャンス
    'normal': {'x': 786, 'y': 239, 'w': 164, 'h': 61, 'color': 'white'},  # 通常 1877
    'chance': {'x': 967, 'y': 239, 'w': 165, 'h': 61, 'color': 'white'},  # チャンス中 1844
    
    # 中段の数値
    'ultra': {'x': 89, 'y': 397, 'w': 72, 'h': 50, 'color': 'red'},  # 超 21
    'middle': {'x': 177, 'y': 397, 'w': 67, 'h': 50, 'color': 'red'},  # 中 0
    'small': {'x': 250, 'y': 397, 'w': 67, 'h': 50, 'color': 'red'},  # 小 4
    'start': {'x': 490, 'y': 382, 'w': 170, 'h': 81, 'color': 'white'},  # スタート 369
    'max_payout': {'x': 812, 'y': 382, 'w': 275, 'h': 81, 'color': 'white'},  # 最高出玉 26830
    
    # 下段テーブル（上の行）
    'max_hit': {'x': 33, 'y': 546, 'w': 202, 'h': 61, 'color': 'white'},  # 最高一撃獲得 25760
    'chance_hits': {'x': 264, 'y': 546, 'w': 201, 'h': 61, 'color': 'white'},  # チャンス中大当り 21
    'chance_rate': {'x': 494, 'y': 546, 'w': 202, 'h': 61, 'color': 'white'},  # チャンス中確率 1/87
    'low_hits': {'x': 725, 'y': 546, 'w': 201, 'h': 61, 'color': 'white'},  # 低確中大当り
    'play_time': {'x': 955, 'y': 546, 'w': 202, 'h': 61, 'color': 'white'},  # 遊タイム
    
    # 下段テーブル（下の行）
    'initial_start': {'x': 35, 'y': 662, 'w': 201, 'h': 61, 'color': 'white'},  # 初回特賞スタート 220
    'prev_final': {'x': 262, 'y': 662, 'w': 201, 'h': 61, 'color': 'white'},  # 前日最終スタート 107
    'rush_count': {'x': 492, 'y': 662, 'w': 202, 'h': 61, 'color': 'white'},  # 突時回数
    'low_start': {'x': 723, 'y': 662, 'w': 201, 'h': 61, 'color': 'white'},  # 低確スタート
    'lost_time': {'x': 953, 'y': 662, 'w': 202, 'h': 61, 'color': 'white'},  # 遊タイム
}

# mask3.pngから抽出したOCR領域（黒背景左上を基準とした相対座標）
# オフセット: X=0, Y=-188（最適値）
# 不要な領域を削除した簡略版
OCR_REGIONS_FROM_MASK3 = {
    # ヘッダー（黒枠外）
    'header': {'x': 21, 'y': -188, 'w': 1129, 'h': 64, 'color': 'white'},
    'store_info': {'x': 0, 'y': -106, 'w': 211, 'h': 99, 'color': 'white'},
    'date_info': {'x': 4, 'y': 3, 'w': 80, 'h': 61, 'color': 'white'},
    
    # メイン数値
    # 大当り・初当りの回数と確率は削除
    'total_start': {'x': 786, 'y': 116, 'w': 346, 'h': 80, 'color': 'white'},  # 累計スタート
    'normal': {'x': 786, 'y': 234, 'w': 164, 'h': 77, 'color': 'white'},  # 通常
    'chance': {'x': 961, 'y': 234, 'w': 174, 'h': 77, 'color': 'white'},  # チャンス中
    
    # 中段
    'ultra': {'x': 79, 'y': 389, 'w': 82, 'h': 72, 'color': 'red'},  # 超
    'middle': {'x': 166, 'y': 389, 'w': 74, 'h': 72, 'color': 'red'},  # 中
    'small': {'x': 244, 'y': 389, 'w': 73, 'h': 72, 'color': 'red'},  # 小
    'start': {'x': 471, 'y': 373, 'w': 208, 'h': 105, 'color': 'white'},  # スタート
    'max_payout': {'x': 813, 'y': 373, 'w': 274, 'h': 107, 'color': 'white'},  # 最高出玉
    
    # 下段テーブル（必要な項目のみ）
    'max_hit': {'x': 33, 'y': 549, 'w': 202, 'h': 61, 'color': 'white'},  # 最高一撃獲得
    'initial_start': {'x': 35, 'y': 665, 'w': 201, 'h': 61, 'color': 'white'},  # 初回特賞スタート
}

# デフォルトでmask3を使用（上下分離で精度向上）
OCR_REGIONS = OCR_REGIONS_FROM_MASK3

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
    use_mask = st.checkbox("mask3.pngを使用", value=False)
    if use_mask:
        mask_offset_x = st.number_input("X軸オフセット", min_value=-500, max_value=500, value=0, step=1)
        mask_offset_y = st.number_input("Y軸オフセット", min_value=-500, max_value=500, value=-188, step=1)  # デフォルト値: -188（最適値）

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
    _, black_mask = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY_INV)  # 閾値を30に下げる
    
    # ノイズ除去
    kernel = np.ones((5,5), np.uint8)
    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
    
    # 輪郭を検出
    contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 最大の輪郭を見つける（黒背景領域）
    black_region_found = False
    if contours:
        # 面積でソートして、最大の輪郭を取得
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # 黒背景領域の条件:
            # 1. 十分な大きさ（画像の15%以上）
            # 2. 縦横比が妥当（極端に細長くない）
            # 3. 画像の中央付近にある
            if (w * h > width * height * 0.15 and 
                0.3 < w/h < 3.0 and
                x < width * 0.6 and y < height * 0.8):
                black_region_found = True
                black_x = x
                black_y = y
                black_w = w
                black_h = h
                break
    
    # 黒背景が見つかった場合、線を引く
    if black_region_found:
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
    
    # タブを作成
    tab1, tab2, tab3, tab4 = st.tabs(["📊 OCR結果", "🎨 色検出", "📍 座標マップ", "📄 JSON出力"])
    
    with tab1:
        st.subheader("📊 OCR検出結果")
        
        if st.button("🔍 OCR実行", type="primary", use_container_width=True):
            
            # Save detection results
            detected_data = {}
            all_detections = []
            debug_results = []  # デバッグ情報を保存
            
            with st.spinner("OCR処理中..."):
                # Progress bar
                progress = st.progress(0)
                
                # 黒背景領域を基準にOCR実行
                if 'black_region_found' in locals() and black_region_found:
                    # 黒背景が見つかった場合、相対座標を使用
                    base_x = black_x
                    base_y = black_y
                    st.info(f"黒背景を基準にOCR実行: ({base_x}, {base_y})")
                    st.info(f"黒背景サイズ: {black_w} x {black_h}")
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
                    
                    # 画像の範囲チェック（負のY座標も許可）
                    if x < 0:
                        x_start = 0
                    else:
                        x_start = x
                    
                    if y < 0:
                        # 黒枠外の領域の場合、y座標が負になる
                        y_start = 0
                    else:
                        y_start = y
                    
                    # 終了座標の調整
                    x_end = min(x + w, width)
                    y_end = min(y + h, height)
                    
                    # 完全に画像範囲外の場合のみスキップ
                    if x_end <= 0 or y_end <= 0 or x_start >= width or y_start >= height:
                        st.warning(f"領域 {region_name} が完全に画像範囲外です: ({x}, {y}, {w}, {h})")
                        continue
                    
                    # 領域を切り抜き
                    roi = img_bgr[y_start:y_end, x_start:x_end]
                    
                    # 切り抜いた領域が小さすぎる場合はスキップ
                    if roi.shape[0] < 10 or roi.shape[1] < 10:
                        st.warning(f"領域 {region_name} が小さすぎます: {roi.shape}")
                        continue
                    
                    # 領域に余白を追加（文字の切れ防止）
                    padding = 5
                    y_start_pad = max(0, y_start - padding)
                    y_end_pad = min(height, y_end + padding)
                    x_start_pad = max(0, x_start - padding)
                    x_end_pad = min(width, x_end + padding)
                    roi_padded = img_bgr[y_start_pad:y_end_pad, x_start_pad:x_end_pad]
                    
                    # まず画像を拡大（OCR精度向上のため）
                    scale_factor = 2
                    roi_large = cv2.resize(roi_padded, (roi_padded.shape[1] * scale_factor, roi_padded.shape[0] * scale_factor), 
                                          interpolation=cv2.INTER_CUBIC)
                    
                    # 超、中、小の特別処理
                    if region_name in ['ultra', 'middle', 'small']:
                        # 赤色を強調して処理
                        b, g, r = cv2.split(roi_large)
                        
                        # 赤チャンネルから青と緑の最大値を減算
                        bg_max = cv2.max(b, g)
                        red_emphasis = cv2.subtract(r, bg_max)
                        
                        # 固定閾値で二値化（赤い文字は明るいので高い閾値）
                        _, processed = cv2.threshold(red_emphasis, 100, 255, cv2.THRESH_BINARY)
                        
                        # 処理済み（白背景に黒文字）
                    
                    # 大当り回数の特別処理
                    elif region_name == 'big_hit_count':
                        # 赤色チャンネルを使用
                        b, g, r = cv2.split(roi_large)
                        
                        # 赤チャンネルから青と緑の最大値を減算
                        bg_max = cv2.max(b, g)
                        red_emphasis = cv2.subtract(r, bg_max)
                        
                        # 固定閾値で二値化
                        _, processed = cv2.threshold(red_emphasis, 100, 255, cv2.THRESH_BINARY)
                        
                        # 処理済み（白背景に黒文字）
                        
                    # mixed（統合領域）の処理
                    elif region['color'] == 'mixed':
                        # 統合領域は複数の色を含むので、グレースケールで処理
                        gray_roi = cv2.cvtColor(roi_large, cv2.COLOR_BGR2GRAY)
                        # 大津の方法で二値化
                        _, processed = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        
                    # 色に応じた前処理
                    elif region['color'] == 'red':
                        # 赤色テキストの処理
                        b, g, r = cv2.split(roi_large)
                        # 赤チャンネルから青と緑の最大値を減算
                        bg_max = cv2.max(b, g)
                        red_emphasis = cv2.subtract(r, bg_max)
                        # 固定閾値で二値化
                        _, processed = cv2.threshold(red_emphasis, 80, 255, cv2.THRESH_BINARY)
                        
                    elif region['color'] == 'blue':
                        # 青色テキストの処理
                        b, g, r = cv2.split(roi_large)
                        # 青チャンネルから赤と緑の最大値を減算
                        rg_max = cv2.max(r, g)
                        blue_emphasis = cv2.subtract(b, rg_max)
                        # 固定閾値で二値化
                        _, processed = cv2.threshold(blue_emphasis, 50, 255, cv2.THRESH_BINARY)
                        
                    else:  # white
                        # 白色テキストの処理
                        gray_roi = cv2.cvtColor(roi_large, cv2.COLOR_BGR2GRAY)
                        
                        # initial_startは特別処理（より強力な前処理）
                        if region_name == 'initial_start':
                            # ノイズ除去
                            denoised = cv2.fastNlMeansDenoising(gray_roi, None, 10, 7, 21)
                            # CLAHE（Contrast Limited Adaptive Histogram Equalization）を適用
                            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4,4))
                            enhanced = clahe.apply(denoised)
                            # 大津の二値化
                            _, processed = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        else:
                            # 通常の白色テキスト処理
                            _, processed = cv2.threshold(gray_roi, 180, 255, cv2.THRESH_BINARY)
                    
                    # 既に反転済みなので追加の反転は不要
                    
                    # OCR実行（複数の設定を試す）
                    detected_text = None
                    best_confidence = 0
                    best_psm = None
                    all_texts = []  # デバッグ用：全ての検出結果を保存
                    
                    # PSMモードのリスト（領域によって調整）
                    if region_name == 'header':
                        # ヘッダーは長いテキスト行
                        psm_modes = [7, 13, 8]  # 7:単一テキスト行, 13:生のライン, 8:単一単語
                    elif region_name == 'date_info':
                        # 日付は短いテキスト
                        psm_modes = [8, 7, 13]  # 8:単一単語, 7:単一テキスト行, 13:生のライン
                    elif region_name in ['ultra', 'middle', 'small']:
                        # 超、中、小は単一数字なので特化したPSMモード
                        psm_modes = [10, 8, 13, 7]  # 10:単一文字, 8:単一単語, 13:生のライン, 7:単一テキスト行
                    elif region_name == 'initial_start':
                        # 初回特賞は2-3桁の数値
                        psm_modes = [8, 7, 13, 6]  # 8:単一単語, 7:単一テキスト行, 13:生のライン, 6:均一ブロック
                    elif 'combined' in region_name:
                        # 統合領域は複数行を含むのでブロックモード
                        psm_modes = [6, 11, 4, 3]  # 6:均一ブロック, 11:疎テキスト, 4:可変カラム, 3:自動
                    else:
                        psm_modes = [7, 8, 13, 11]  # 通常のPSMモード
                    
                    for psm in psm_modes:
                        try:
                            # 領域によって文字制限を設定
                            # ヘッダーと店舗情報は日本語を含む
                            if region_name in ['header', 'store_info']:
                                custom_config = f'--psm {psm} --oem 3'
                            # 日付は数字と/のみ
                            elif region_name == 'date_info':
                                custom_config = f'--psm {psm} --oem 3 -c tessedit_char_whitelist=0123456789/'
                            # 確率を含む領域は/を許可
                            elif 'rate' in region_name or 'chance_rate' in region_name:
                                custom_config = f'--psm {psm} --oem 3 -c tessedit_char_whitelist=0123456789/'
                            # 純粋な数値の領域
                            elif region_name in ['total_start', 'normal', 'chance', 'ultra', 'middle', 'small', 
                                               'start', 'max_payout', 'max_hit', 'initial_start', 'prev_final']:
                                custom_config = f'--psm {psm} --oem 3 -c tessedit_char_whitelist=0123456789'
                            # その他
                            else:
                                custom_config = f'--psm {psm} --oem 3'
                            
                            # OCR実行して信頼度も取得
                            if region_name in ['header', 'store_info']:
                                # 日本語を含む領域
                                data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT, 
                                                                config=custom_config, lang='jpn')
                            else:
                                # 数字のみの領域
                                data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT, 
                                                                config=custom_config)
                            
                            # 全てのテキストを収集
                            for i in range(len(data['text'])):
                                text = str(data['text'][i]).strip()
                                conf = int(data['conf'][i]) if data['conf'][i] != -1 else 0
                                
                                if text:
                                    # 統合領域と確率領域はそのまま保存
                                    if 'combined' in region_name or 'rate' in region_name:
                                        pass  # そのまま保存
                                    
                                    all_texts.append(f"PSM{psm}: {text} ({conf}%)")
                                    
                                    if conf > best_confidence:
                                        detected_text = text
                                        best_confidence = conf
                                        best_psm = psm
                                    
                        except Exception as e:
                            continue
                    
                    # 信頼度が低い場合、あるいは何も検出されなかった場合、別の方法を試す
                    if (best_confidence < 50 or not detected_text) and len(all_texts) > 0:
                        # 複数のPSMモードで同じテキストが検出されたか確認
                        text_counts = {}
                        for txt in all_texts:
                            # PSM情報を除いてテキストのみ抽出
                            actual_text = txt.split(": ")[1].split(" (")[0]
                            text_counts[actual_text] = text_counts.get(actual_text, 0) + 1
                        
                        # 最も頻繁に検出されたテキストを選択
                        if text_counts:
                            most_common = max(text_counts.items(), key=lambda x: x[1])
                            if most_common[1] > 1:  # 複数回検出された場合
                                detected_text = most_common[0]
                                best_confidence = 50  # 信頼度を調整
                    
                    # デバッグ情報を保存
                    debug_info = {
                        'region': region_name,
                        'position': f"({x}, {y})",
                        'size': f"{w}x{h}",
                        'color': region['color'],
                        'detected': detected_text if detected_text else "未検出",
                        'raw_text': detected_text if detected_text else "",  # 生のOCR結果
                        'confidence': best_confidence,
                        'best_psm': best_psm if best_psm else "N/A",
                        'roi_shape': roi.shape,
                        'processed_shape': processed.shape if 'processed' in locals() else None,
                        'all_detections': all_texts if show_masks else []
                    }
                    debug_results.append(debug_info)
                    
                    # ヘッダーの場合は生のテキストを表示
                    if region_name == 'header' and detected_text:
                        st.info(f"🔍 ヘッダーOCR生データ: '{detected_text}'")
                    
                    # 結果を保存
                    if detected_text:
                        detected_data[region_name] = detected_text
                        all_detections.append({
                            'region': region_name,
                            'text': detected_text,
                            'bbox': [x, y, x+w, y+h],
                            'color': region['color'],
                            'confidence': best_confidence
                        })
                        continue
            
            # 統合領域から個別データを抽出
            import re
            
            # デバッグ: 統合領域の内容を表示
            if show_masks:
                st.write("### 統合領域のOCR結果（デバッグ）")
                for key in ['big_first_hit_combined', 'first_hit_combined', 'total_start_combined']:
                    if key in detected_data:
                        st.write(f"**{key}**: {detected_data[key]}")
            
            # big_first_hit_combinedから大当り回数と確率を抽出
            if 'big_first_hit_combined' in detected_data:
                combined_text = str(detected_data['big_first_hit_combined'])
                # 改行で分割してみる
                lines = combined_text.split('\n') if '\n' in combined_text else [combined_text]
                
                # 各行から数字を抽出
                all_numbers = []
                for line in lines:
                    numbers = re.findall(r'\d+', line)
                    all_numbers.extend(numbers)
                
                # 最大の数字が大当り回数（通常25のような大きな数字）
                if all_numbers:
                    # 100以下の数字で最大のものを大当り回数とする
                    hit_candidates = [n for n in all_numbers if int(n) <= 100]
                    if hit_candidates:
                        detected_data['big_hit_count'] = max(hit_candidates, key=int)
                    
                    # 100より大きい数字は確率の分母
                    rate_candidates = [n for n in all_numbers if int(n) > 100]
                    if rate_candidates:
                        detected_data['big_hit_rate'] = f"(1/{rate_candidates[0]})"
            
            # first_hit_combinedから初当り回数と確率を抽出
            if 'first_hit_combined' in detected_data:
                combined_text = str(detected_data['first_hit_combined'])
                # 改行で分割
                lines = combined_text.split('\n') if '\n' in combined_text else [combined_text]
                
                # 各行から数字を抽出
                all_numbers = []
                for line in lines:
                    numbers = re.findall(r'\d+', line)
                    all_numbers.extend(numbers)
                
                if all_numbers:
                    # 100以下の数字で最小のものを初当り回数とする（通常1桁）
                    hit_candidates = [n for n in all_numbers if int(n) <= 100]
                    if hit_candidates:
                        detected_data['first_hit_count'] = min(hit_candidates, key=int)
                    
                    # 100より大きい数字は確率の分母
                    rate_candidates = [n for n in all_numbers if int(n) > 100]
                    if rate_candidates:
                        detected_data['first_hit_rate'] = f"(1/{rate_candidates[0]})"
            
            # total_start_combinedから累計スタートを抽出
            if 'total_start_combined' in detected_data:
                combined_text = str(detected_data['total_start_combined'])
                # 全ての数字を抽出
                numbers = re.findall(r'\d+', combined_text)
                if numbers:
                    # 最大の数字が累計スタート（通常最も大きい）
                    detected_data['total_start'] = max(numbers, key=lambda x: int(x))
            
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
            
            # デバッグ情報を表示
            with st.expander("🔧 OCRデバッグ情報", expanded=True):
                st.markdown("### 各領域の処理詳細")
                
                # デバッグテーブルを作成
                debug_data = []
                for debug in debug_results:
                    color_emoji = {"white": "⚪", "red": "🔴", "blue": "🔵"}.get(debug['color'], "⚫")
                    debug_data.append({
                        "領域名": debug['region'],
                        "色": color_emoji,
                        "座標": debug['position'],
                        "サイズ": debug['size'],
                        "検出値": debug['detected'],
                        "信頼度": f"{debug['confidence']}%",
                        "PSM": debug['best_psm'],
                        "ROI形状": str(debug['roi_shape']),
                        "処理後形状": str(debug['processed_shape'])
                    })
                
                import pandas as pd
                debug_df = pd.DataFrame(debug_data)
                st.dataframe(debug_df, use_container_width=True, height=600)
                
                # 未検出の領域を強調表示
                undetected = [d for d in debug_results if d['detected'] == "未検出"]
                if undetected:
                    st.warning(f"⚠️ {len(undetected)}個の領域で検出失敗:")
                    for u in undetected:
                        st.write(f"- **{u['region']}** (座標: {u['position']}, サイズ: {u['size']})")
                
                # 低信頼度の領域を表示
                low_conf = [d for d in debug_results if d['confidence'] < 50 and d['detected'] != "未検出"]
                if low_conf:
                    st.info(f"ℹ️ {len(low_conf)}個の領域で信頼度が低い:")
                    for l in low_conf:
                        st.write(f"- **{l['region']}**: {l['detected']} (信頼度: {l['confidence']}%)")
            
            # 詳細デバッグ情報（マスク表示がONの場合） - expanderの外に移動
            if show_masks and 'debug_results' in locals():
                with st.expander("🔍 詳細な検出結果"):
                    for debug in debug_results:
                        if debug.get('all_detections'):
                            st.write(f"**{debug['region']}**:")
                            for detection in debug['all_detections']:
                                st.write(f"  - {detection}")
            
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
        
        # mask3.pngを使用する場合
        if 'use_mask' in locals() and use_mask:
            # mask3.pngを読み込み（リサイズ禁止）
            import os
            mask_path = os.path.join(os.path.dirname(__file__), 'mask', 'mask3.png')
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
                st.warning("mask/mask3.pngが見つかりません")
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
                
                # 検出結果のテキストを領域の左上に表示
                text = detection.get('text', '')
                if text:
                    # テキストを矩形の左上に配置
                    text_x = x1 + 5
                    text_y = y1 + 20  # 左上に表示
                    
                    # 緑色で表示
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
            st.info(f"{len(OCR_REGIONS)}個の領域が定義されています（黒枠外の領域を含む）")
        
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