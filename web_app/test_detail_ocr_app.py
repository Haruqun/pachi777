"""
出玉詳細画像OCRテスト用Streamlitアプリ（改良版レイアウト）
"""

import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import json
from datetime import datetime
import base64
import os

st.set_page_config(
    page_title="出玉詳細OCRテスト",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 出玉詳細画像OCRテスト")
st.caption("IMG_2074.PNGなどの出玉詳細画像からデータを抽出するテスト")

# 座標定義をリセット
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 座標定義をリセット", key="reset_coords"):
        if 'relative_regions' in st.session_state:
            del st.session_state.relative_regions
        st.rerun()
with col2:
    if st.button("🗑️ 全セッションをクリア", key="clear_all"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# 黒背景領域内での座標定義
# 検出結果の座標から黒背景位置を引いた相対座標
if 'relative_regions' not in st.session_state or st.button("座標を強制更新", key="force_update"):
    # 座標は(left, top, right, bottom)の形式で定義
    # 黒背景位置を差し引いた相対座標として保存
    # 実際の検出結果に基づく座標（黒背景内での相対座標）
    # 黒背景内での相対座標で定義（黒背景左上を0,0とする）
    st.session_state.relative_regions = {
        # メイン数値（赤・青の大きい数字）
        'big_hit_count': {
            'bbox': (30, 60, 130, 130),  # 大当り回数 25 (赤大数字)
            'type': 'red_number',
            'inside_black': True,
            'size_pattern': 'large',
            'name': '大当り回数'
        },
        'first_hit_count': {
            'bbox': (180, 60, 270, 130),  # 初当り回数 4 (青大数字)
            'type': 'blue_number',
            'inside_black': True,
            'size_pattern': 'large',
            'name': '初当り回数'
        },
        'cumulative_start': {
            'bbox': (330, 60, 430, 95),  # 累計スタート 3721
            'type': 'white_number',
            'inside_black': True,
            'size_pattern': 'medium',
            'name': '累計スタート'
        },
        
        # 中段の数値
        'ultra_count': {
            'bbox': (20, 155, 70, 180),  # 超 21
            'type': 'red_number',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '超'
        },
        'medium_count': {
            'bbox': (75, 155, 110, 180),  # 中 0
            'type': 'red_number',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '中'
        },
        'small_count': {
            'bbox': (115, 155, 155, 180),  # 小 4
            'type': 'red_number',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '小'
        },
        'start_number': {
            'bbox': (200, 155, 300, 185),  # スタート 369 (318, 549から)
            'type': 'white_number',
            'inside_black': True,
            'size_pattern': 'medium',
            'name': 'スタート'
        },
        'max_payout': {
            'bbox': (340, 155, 465, 185),  # 最高出玉 26830 (522, 549から)
            'type': 'white_number',
            'inside_black': True,
            'size_pattern': 'medium',
            'name': '最高出玉'
        },
        
        # 最高一撃獲得セクション  
        'highest_single_win': {
            'bbox': (15, 210, 110, 235),  # 最高一撃獲得 25760 (40, 653から)
            'type': 'white_number',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '最高一撃獲得'
        },
        'chance_bonus_count': {
            'bbox': (115, 210, 165, 235),  # チャンス中大当り 21
            'type': 'white_number',
            'inside_black': True,
            'size_pattern': 'small',
            'name': 'チャンス中大当り'
        },
        'chance_probability': {
            'bbox': (210, 210, 280, 235),  # チャンス中確率 1/87 (340, 653から)
            'type': 'white_text',
            'inside_black': True,
            'size_pattern': 'small',
            'name': 'チャンス中確率'
        },
        
        # 初回特賞・前日最終セクション
        'initial_bonus_start': {
            'bbox': (15, 255, 100, 280),  # 初回特賞スタート 220 (59, 725から)
            'type': 'white_number',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '初回特賞スタート'
        },
        'previous_day_final': {
            'bbox': (105, 255, 185, 280),  # 前日最終スタート 107
            'type': 'white_number',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '前日最終スタート'
        },
        
        # テーブルデータ（1行目）
        'date_1': {
            'bbox': (10, 315, 65, 340),  # 8/6 (31, 813から)
            'type': 'white_text',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '日付1'
        },
        'cumulative_start_1': {
            'bbox': (80, 315, 150, 340),  # 3772
            'type': 'white_number',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '累計スタート1'
        },
        'first_hit_prob_1': {
            'bbox': (160, 315, 235, 340),  # 1/277
            'type': 'white_text',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '初当り確率1'
        },
        'chance_hit_prob_1': {
            'bbox': (245, 315, 320, 340),  # 1/166 (425, 813から)
            'type': 'white_text',
            'inside_black': True,
            'size_pattern': 'small',
            'name': 'チャンス中確率1'
        },
        'highest_payout_1': {
            'bbox': (405, 315, 475, 340),  # 14670 (584, 812から)
            'type': 'white_number',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '最高出玉1'
        },
        
        # テーブルデータ（2行目）
        'date_2': {
            'bbox': (10, 350, 65, 375),  # 8/5 (31, 849から)
            'type': 'white_text',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '日付2'
        },
        'cumulative_start_2': {
            'bbox': (80, 350, 165, 375),  # 3213 (125, 849から)
            'type': 'white_number',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '累計スタート2'
        },
        'first_hit_prob_2': {
            'bbox': (180, 350, 255, 375),  # 1/324
            'type': 'white_text',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '初当り確率2'
        },
        'chance_hit_prob_2': {
            'bbox': (270, 350, 340, 375),  # 1/79 (434, 849から)
            'type': 'white_text',
            'inside_black': True,
            'size_pattern': 'small',
            'name': 'チャンス中確率2'
        },
        'highest_payout_2': {
            'bbox': (405, 350, 475, 375),  # 22100
            'type': 'white_number',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '最高出玉2'
        },
        
        # 右上の数値（モツ中など）
        'top_right_values': {
            'bbox': (340, 90, 430, 120),  # 1877 1844など
            'type': 'white_number',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '右上数値'
        },
        
        # その他の統計（低確中大当りなど）  
        'low_prob_hit': {
            'bbox': (230, 195, 300, 220),  # 低確中大当り
            'type': 'white_text',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '低確中大当り'
        },
        'low_prob_rate': {
            'bbox': (305, 195, 375, 220),  # 低確中確率
            'type': 'white_text',
            'inside_black': True,
            'size_pattern': 'small',
            'name': '低確中確率'
        },
    }

# 文字サイズパターンに応じた微調整オフセット
if 'size_adjustments' not in st.session_state:
    st.session_state.size_adjustments = {
        'large': {'padding': 5},  # 大きい数字用の余白
        'large_white': {'padding': 3},  # 大きい白数字用
        'medium': {'padding': 2},  # 中サイズ
        'medium_wide': {'padding': 2},  # 中サイズ横長
        'small': {'padding': 1},  # 小サイズ
        'small_red': {'padding': 2},  # 小さい赤数字
    }

# 元画像のサイズ（722x1584）に基づく座標（後方互換性のため残す）
if 'base_regions' not in st.session_state:
    st.session_state.base_regions = {
        'Machine_No': {'bbox': (15, 210, 72, 240), 'type': 'text'},
        'Jackpot_Count': {'bbox': (52, 310, 187, 374), 'type': 'red_number'},
        'Jackpot_Prob': {'bbox': (52, 371, 167, 399), 'type': 'text'},
        'First_Hit_Count': {'bbox': (252, 311, 338, 374), 'type': 'blue_number'},
        'First_Hit_Prob': {'bbox': (255, 372, 334, 399), 'type': 'text'},
        'Total_Start': {'bbox': (425, 314, 553, 350), 'type': 'number'},
        'Normal': {'bbox': (390, 374, 485, 402), 'type': 'number'},
        'Chance': {'bbox': (501, 371, 569, 399), 'type': 'number'},
        'Ultra': {'bbox': (48, 446, 82, 480), 'type': 'red_number'},
        'Middle': {'bbox': (97, 444, 131, 478), 'type': 'red_number'},
        'Small': {'bbox': (129, 448, 163, 482), 'type': 'red_number'},
        'Start': {'bbox': (260, 440, 360, 487), 'type': 'number'},
        'Max_Payout': {'bbox': (429, 440, 560, 487), 'type': 'number'},
    }

# セッションステートで座標を管理
if 'regions' not in st.session_state:
    st.session_state.regions = st.session_state.base_regions.copy()

# テスト画像のBase64データを保持する辞書
test_images_data = {}

# ローカルの画像ファイルを読み込んでBase64エンコード
test_image_files = [
    ("IMG_2074.PNG", "0026"),
    ("IMG_2075.PNG", "0027"),
    ("IMG_2076.PNG", "0028"),
    ("IMG_2077.PNG", "0030")
]

for filename, machine_num in test_image_files:
    # PNGとJPEGの両方を試す
    for ext in ['.PNG', '.png', '.JPG', '.jpg', '.JPEG', '.jpeg']:
        base_name = filename.rsplit('.', 1)[0]
        test_filename = base_name + ext
        local_path = os.path.join(os.path.dirname(__file__), "..", "data_image", test_filename)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                img_data = f.read()
                test_images_data[f"{test_filename} (台番号: {machine_num})"] = img_data
            break

# 画像選択方法
if test_images_data:
    image_source = st.radio(
        "画像の選択方法",
        ["テスト画像を使用", "画像をアップロード"],
        horizontal=True
    )
else:
    image_source = "画像をアップロード"
    st.info("テスト画像が見つかりません。画像をアップロードしてください。")

uploaded_file = None
selected_test_image = None
img = None

if image_source == "テスト画像を使用" and test_images_data:
    selected_test_image = st.selectbox(
        "テスト画像を選択",
        list(test_images_data.keys())
    )
    # 選択された画像データを取得
    img_data = test_images_data[selected_test_image]
    file_bytes = np.frombuffer(img_data, dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
else:
    # メインエリア
    uploaded_file = st.file_uploader(
        "出玉詳細画像をアップロード",
        type=['png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG'],
        help="site777の出玉詳細画面のスクリーンショットをアップロードしてください（PNG/JPEG対応）"
    )

if uploaded_file is not None:
    # 画像を読み込み
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

# テスト画像またはアップロード画像がある場合
if (image_source == "テスト画像を使用" and selected_test_image and 'img' in locals() and img is not None) or uploaded_file is not None:
    
    # オリジナル画像情報を表示
    original_size = (img.shape[1], img.shape[0])
    st.info(f"オリジナル画像サイズ: {original_size[0]} x {original_size[1]} px")
    
    # 横幅を722pxに統一し、アスペクト比を保持
    target_width = 722
    
    if img.shape[1] != target_width:
        # アスペクト比を計算
        aspect_ratio = img.shape[0] / img.shape[1]
        target_height = int(target_width * aspect_ratio)
        
        # リサイズ実行
        img = cv2.resize(img, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)
        st.success(f"画像を横幅 {target_width}px にリサイズしました (新サイズ: {target_width}x{target_height})")
    else:
        st.success(f"画像サイズ: {img.shape[1]} x {img.shape[0]} px (リサイズ不要)")
        target_height = img.shape[0]
    
    # スケールは常に1.0になる
    scale_x = 1.0
    scale_y = 1.0
    
    # 画像タイプの判定
    def detect_image_type(image):
        """画像タイプを判別（グラフ or 詳細）"""
        height, width = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 黒い背景の検出
        center_y = height // 2
        center_region = hsv[center_y-100:center_y+100, :]
        black_mask = cv2.inRange(center_region, np.array([0, 0, 0]), np.array([180, 255, 30]))
        black_ratio = np.sum(black_mask) / (black_mask.shape[0] * black_mask.shape[1] * 255)
        
        # 赤と青の大きな数字の検出
        red_mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        red_mask2 = cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        red_ratio = np.sum(red_mask) / (height * width * 255)
        
        blue_mask = cv2.inRange(hsv, np.array([100, 100, 100]), np.array([130, 255, 255]))
        blue_ratio = np.sum(blue_mask) / (height * width * 255)
        
        if black_ratio > 0.3 and red_ratio > 0.001 and blue_ratio > 0.001:
            return "detail"
        else:
            return "graph"
    
    # 黒い背景領域の上端を検出
    def find_black_region_top(image):
        """黒い背景領域の上端Y座標を検出"""
        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # より広い範囲で黒い領域を探す（画像の上部1/5から）
        for y in range(height // 5, height * 2 // 3):
            row_mean = np.mean(gray[y, :])
            if row_mean < 50:  # 閾値を緩和（30→50）
                # 数行連続で暗いことを確認
                if y + 20 < height:
                    next_rows_mean = np.mean(gray[y:y+20, :])
                    if next_rows_mean < 50:
                        # エッジ検出で境界をより正確に
                        edges = cv2.Canny(gray[max(0, y-10):y+30, :], 50, 150)
                        edge_rows = np.sum(edges, axis=1)
                        # 最もエッジが強い行を境界とする
                        if len(edge_rows) > 0:
                            max_edge_idx = np.argmax(edge_rows)
                            return max(0, y - 10) + max_edge_idx
                        return y
        return None
    
    # スケールを自動検出
    def auto_detect_scale(image):
        """黒い背景領域のサイズからスケールを自動検出"""
        height, width = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 黒い背景領域を検出
        # 黒い領域（暗いピクセル）を検出
        _, black_mask = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
        
        # ノイズ除去
        kernel = np.ones((5, 5), np.uint8)
        black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
        black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)
        
        # 輪郭検出
        contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 最大の黒い領域を探す（メインの黒背景）
        best_scale_x = 1.0
        best_scale_y = 1.0
        found_black_region = False
        black_region_rect = None
        
        if contours:
            # 最大の輪郭を取得
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # 黒い背景領域の特徴を確認
            # - 画面の大部分を占める
            # - 中央付近にある
            area_ratio = (w * h) / (width * height)
            if area_ratio > 0.3 and area_ratio < 0.8:  # 画面の30%～80%
                # 中央部分が含まれているか確認
                center_x = x + w / 2
                center_y = y + h / 2
                if abs(center_x - width / 2) < width * 0.3 and y < height * 0.5:
                    # 黒背景領域の幅は画面全幅と同じはず
                    # 高さは画像によって異なるため、幅のみで判定
                    calc_scale = w / width
                    
                    # 黒背景が画面全幅の90%以上を占める場合は正しいと判定
                    if calc_scale > 0.9:
                        best_scale_x = 1.0
                        best_scale_y = 1.0
                        found_black_region = True
                        black_region_rect = (x, y, w, h)
                    
        
        # 黒背景が見つからない場合のフォールバック処理
        # （現在は黒背景検出のみに特化）
        
        return best_scale_x, best_scale_y, found_black_region, black_region_rect
    
    # 台番号の白い領域を検出
    def find_machine_number_box(image):
        """台番号の白い領域を検出して位置を返す"""
        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 左上の領域を探索（画像の左側上部）
        search_height = min(height//2, 500)  # 上半分まで探索
        search_width = min(width//4, 150)    # 左1/4まで探索
        search_region = gray[:search_height, :search_width]
        
        # 白い領域を検出（より低い閾値で）
        _, binary = cv2.threshold(search_region, 200, 255, cv2.THRESH_BINARY)
        
        # ノイズ除去
        kernel = np.ones((3,3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # 輪郭検出
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 適切なサイズの白い矩形を探す
        best_box = None
        best_score = 0
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # 台番号のボックスとして妥当なサイズか確認
            # サイズ条件を緩和
            if 15 < w < 120 and 10 < h < 80 and w > h:
                # 左上の特定の領域にあるかチェック（台番号は通常左端から10-30px、上から100-300px）
                if x < 50 and 50 < y < 350:
                    # 白い領域の充填率を計算
                    roi = binary[y:y+h, x:x+w]
                    fill_ratio = np.sum(roi) / (255 * w * h)
                    
                    # 充填率が高い（0.7以上）場合は台番号の可能性が高い
                    if fill_ratio > 0.7:
                        # 位置スコア（左上に近いほど高い）
                        position_score = 1.0 - (x + y) / (search_width + search_height)
                        # サイズスコア（適切なサイズほど高い）
                        size_score = 1.0 - abs(w/h - 2.0) / 3.0  # 縦横比2.0が理想
                        
                        total_score = position_score * 0.6 + size_score * 0.2 + fill_ratio * 0.2
                        
                        if total_score > best_score:
                            best_score = total_score
                            best_box = (x, y, x+w, y+h)
        
        return best_box
    
    image_type = detect_image_type(img)
    
    if image_type == "detail":
        st.success("✅ 出玉詳細画像として認識されました")
        
        # 自動位置調整フラグの初期化
        if 'auto_adjust' not in st.session_state:
            st.session_state.auto_adjust = True
        
        # 3カラムレイアウト（座標調整、画像、結果）
        col_adjust, col_image, col_result = st.columns([1, 1.5, 1])
        
        # 左カラム：座標調整ツール
        with col_adjust:
            st.subheader("🎯 座標調整")
            
            # リサイズ情報を表示
            if original_size[0] != target_width:
                st.caption(f"リサイズ済: {original_size[0]}x{original_size[1]} → {img.shape[1]}x{img.shape[0]}")
            
            # グリッド表示ボタン
            if st.button("📐 10pxグリッドで検証", use_container_width=True):
                with st.spinner("グリッドを生成中..."):
                    # 黒い領域を検出
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    _, black_mask = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
                    
                    kernel = np.ones((5, 5), np.uint8)
                    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
                    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)
                    
                    contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    if contours:
                        # 最大の領域のみを使用
                        largest = max(contours, key=cv2.contourArea)
                        x, y, w, h = cv2.boundingRect(largest)
                        
                        # デバッグ画像を作成
                        debug_img = img.copy()
                        
                        # 10pxグリッドを描画
                        grid_color = (200, 200, 200)  # 薄いグレー
                        # 縦線
                        for i in range(0, img.shape[1], 10):
                            cv2.line(debug_img, (i, 0), (i, img.shape[0]), grid_color, 1)
                            if i % 50 == 0:  # 50px毎に太線
                                cv2.line(debug_img, (i, 0), (i, img.shape[0]), (150, 150, 150), 2)
                                cv2.putText(debug_img, str(i), (i+2, 20), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
                        
                        # 横線
                        for i in range(0, img.shape[0], 10):
                            cv2.line(debug_img, (0, i), (img.shape[1], i), grid_color, 1)
                            if i % 50 == 0:  # 50px毎に太線
                                cv2.line(debug_img, (0, i), (img.shape[1], i), (150, 150, 150), 2)
                                if i > 0:
                                    cv2.putText(debug_img, str(i), (5, i-2), 
                                              cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
                        
                        # 黒背景領域を赤枠で囲む
                        cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 0, 255), 3)
                        cv2.putText(debug_img, f"Black: ({x},{y}) {w}x{h}", (x+10, y+30), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                        
                        # First_Hit_Countだけを描画
                        for name, region_info in st.session_state.relative_regions.items():
                            if name == 'First_Hit_Count':
                                x1, y1, x2, y2 = region_info['bbox']
                                # 黒背景左上基準の絶対座標
                                abs_x1 = int(x + x1)
                                abs_y1 = int(y + y1)
                                abs_x2 = int(x + x2)
                                abs_y2 = int(y + y2)
                                
                                # 青色で描画
                                color = (255, 0, 0)  # 青
                                cv2.rectangle(debug_img, (abs_x1, abs_y1), (abs_x2, abs_y2), color, 3)
                                # 座標情報も表示
                                coord_text = f"First_Hit_Count ({x1},{y1})-({x2},{y2})"
                                cv2.putText(debug_img, coord_text, (abs_x1, abs_y1-10), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                                
                                # 詳細情報を表示
                                st.info(f"First_Hit_Count: 相対座標({x1},{y1})-({x2},{y2}) → 絶対座標({abs_x1},{abs_y1})-({abs_x2},{abs_y2})")
                        
                        # 縮小して表示
                        display_scale = 0.7
                        display_img = cv2.resize(debug_img, (int(img.shape[1]*display_scale), int(img.shape[0]*display_scale)))
                        st.image(cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB), 
                               caption="10pxグリッド検証画面")
                        
                        st.info(f"黒背景領域: 左上({x}, {y}) サイズ{w}x{h}px")
                        
                        # デバッグ用: 最初の領域の座標を表示
                        first_region = list(st.session_state.relative_regions.items())[0]
                        st.info(f"デバッグ: {first_region[0]} = {first_region[1]['bbox']}")
                        
                        # 想定と実際の差を表示
                        expected_y = 310
                        st.warning(f"⚠️ 黒背景Y座標: 実際={y}px, 想定={expected_y}px, 差={y - expected_y}px")
                        
                        # 実際の座標計算を表示
                        x1, y1, x2, y2 = first_region[1]['bbox']
                        st.info(f"座標計算: 相対({x1},{y1}) + 黒背景({x},{y}) = 絶対({x+x1},{y+y1})")
                        
                        # 各領域の座標を表形式で表示
                        st.markdown("### OCR領域の絶対座標")
                        coord_data = []
                        for name, region_info in st.session_state.relative_regions.items():
                            x1, y1, x2, y2 = region_info['bbox']
                            # 黒背景左上基準の絶対座標
                            abs_x1 = int(x + x1)
                            abs_y1 = int(y + y1)
                            abs_x2 = int(x + x2)
                            abs_y2 = int(y + y2)
                            coord_data.append({
                                "領域名": name,
                                "左上X": abs_x1,
                                "左上Y": abs_y1,
                                "右下X": abs_x2,
                                "右下Y": abs_y2,
                                "幅": abs_x2 - abs_x1,
                                "高さ": abs_y2 - abs_y1
                            })
                        import pandas as pd
                        df = pd.DataFrame(coord_data)
                        st.dataframe(df, use_container_width=True)
                        
                        # セッションステートに黒背景情報を保存
                        st.session_state.black_region = (x, y, w, h)
            
            # 定義済み領域でOCRテスト
            if st.button("🎯 定義済み領域でOCRテスト", use_container_width=True):
                with st.spinner("OCR処理中..."):
                    import pytesseract
                    
                    # 黒背景領域を検出
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    _, black_mask = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
                    kernel = np.ones((5, 5), np.uint8)
                    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
                    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)
                    contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    if contours:
                        largest = max(contours, key=cv2.contourArea)
                        x_black, y_black, w_black, h_black = cv2.boundingRect(largest)
                        
                        # 結果格納用
                        ocr_results = {}
                        debug_img = img.copy()
                        
                        # 各領域を処理
                        for name, region_info in st.session_state.relative_regions.items():
                            x1, y1, x2, y2 = region_info['bbox']
                            
                            # 黒背景左上基準の絶対座標
                            abs_x1 = x_black + x1
                            abs_y1 = y_black + y1
                            abs_x2 = x_black + x2
                            abs_y2 = y_black + y2
                            
                            # 境界チェック
                            abs_x1 = max(0, min(abs_x1, img.shape[1]))
                            abs_y1 = max(0, min(abs_y1, img.shape[0]))
                            abs_x2 = max(0, min(abs_x2, img.shape[1]))
                            abs_y2 = max(0, min(abs_y2, img.shape[0]))
                            
                            # 領域を切り出し
                            roi = img[abs_y1:abs_y2, abs_x1:abs_x2]
                            
                            if roi.size > 0:
                                # タイプに応じた処理
                                if region_info['type'] == 'red_number':
                                    # 赤数字抽出
                                    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                                    # より広い色範囲で赤を検出
                                    mask1 = cv2.inRange(hsv_roi, np.array([0, 30, 30]), np.array([15, 255, 255]))
                                    mask2 = cv2.inRange(hsv_roi, np.array([165, 30, 30]), np.array([180, 255, 255]))
                                    mask = cv2.bitwise_or(mask1, mask2)
                                    
                                    # サイズに応じた処理
                                    if region_info.get('size_pattern') == 'large':
                                        # 大きい数字は膨張して結合後、2倍に拡大
                                        kernel_d = np.ones((5, 5), np.uint8)
                                        mask = cv2.dilate(mask, kernel_d, iterations=3)
                                        mask = cv2.resize(mask, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                                        # PSM 8: 単一単語として認識
                                        text = pytesseract.image_to_string(mask, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()
                                    else:
                                        # 小さい赤数字（括弧付きも含む）
                                        text = pytesseract.image_to_string(mask, config='--psm 7 -c tessedit_char_whitelist=0123456789/()').strip()
                                    color = (0, 0, 255)
                                    
                                elif region_info['type'] == 'blue_number':
                                    # 青数字抽出
                                    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                                    # より広い色範囲で青を検出
                                    mask = cv2.inRange(hsv_roi, np.array([95, 30, 30]), np.array([135, 255, 255]))
                                    
                                    if region_info.get('size_pattern') == 'large':
                                        # 大きい数字は膨張して結合後、2倍に拡大
                                        kernel_d = np.ones((5, 5), np.uint8)
                                        mask = cv2.dilate(mask, kernel_d, iterations=3)
                                        mask = cv2.resize(mask, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                                        text = pytesseract.image_to_string(mask, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()
                                    else:
                                        # 小さい青数字（括弧付きも含む）
                                        text = pytesseract.image_to_string(mask, config='--psm 7 -c tessedit_char_whitelist=0123456789/()').strip()
                                    color = (255, 0, 0)
                                    
                                elif region_info['type'] == 'number':
                                    # 白数字抽出
                                    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                                    # 適応的二値化で白文字を抽出
                                    mask = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                                cv2.THRESH_BINARY, 11, 2)
                                    # 反転（白背景に黒文字にする）
                                    mask = cv2.bitwise_not(mask)
                                    
                                    # サイズに応じた処理
                                    if region_info.get('size_pattern') in ['large_white', 'medium_wide']:
                                        # 大きい/中サイズの白数字は拡大してOCR
                                        mask = cv2.resize(mask, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                                        text = pytesseract.image_to_string(mask, config='--psm 8 -c tessedit_char_whitelist=0123456789/()').strip()
                                    else:
                                        text = pytesseract.image_to_string(mask, config='--psm 7 -c tessedit_char_whitelist=0123456789/()').strip()
                                    color = (255, 255, 255)
                                    
                                else:  # text
                                    # テキスト
                                    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                                    text = pytesseract.image_to_string(gray_roi, lang='jpn', config='--psm 7').strip()
                                    color = (0, 255, 0)
                                
                                # 結果を保存
                                ocr_results[name] = text
                                
                                # First_Hit_Countのみ枠とテキストを描画
                                if name == 'First_Hit_Count':
                                    cv2.rectangle(debug_img, (abs_x1, abs_y1), (abs_x2, abs_y2), color, 2)
                                    label = f"{name}: {text[:20] if text else 'N/A'}"
                                    cv2.putText(debug_img, label, (abs_x1, abs_y1 - 5), 
                                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                        
                        # 結果表示
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # 画像表示
                            display_scale = 0.7
                            display_img = cv2.resize(debug_img, (int(img.shape[1]*display_scale), int(img.shape[0]*display_scale)))
                            st.image(cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB), 
                                   caption="OCR結果")
                        
                        with col2:
                            # OCR結果表示
                            st.markdown("### OCR結果")
                            for name, text in ocr_results.items():
                                if text:
                                    st.success(f"**{name}**: {text}")
                                else:
                                    st.warning(f"**{name}**: 未検出")
                    else:
                        st.error("黒背景領域が検出できませんでした")
            
            # OCR検出領域表示ボタン
            if st.button("🔤 OCR検出領域を表示", use_container_width=True):
                with st.spinner("OCR検出中..."):
                    import pytesseract
                    
                    # 黒背景領域を検出
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    _, black_mask = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
                    kernel = np.ones((5, 5), np.uint8)
                    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
                    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)
                    contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    # 黒背景領域を切り出し
                    if contours:
                        largest = max(contours, key=cv2.contourArea)
                        x_black, y_black, w_black, h_black = cv2.boundingRect(largest)
                        black_region = img[y_black:y_black+h_black, x_black:x_black+w_black]
                    else:
                        black_region = img
                        x_black, y_black = 0, 0
                    
                    # 黒背景領域に対して前処理
                    # 1. コントラストを強化
                    lab = cv2.cvtColor(black_region, cv2.COLOR_BGR2LAB)
                    l, a, b = cv2.split(lab)
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
                    l = clahe.apply(l)
                    enhanced = cv2.merge([l, a, b])
                    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
                    
                    # 2. 白文字を抽出（黒背景に白文字）
                    gray_enhanced = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
                    _, white_text = cv2.threshold(gray_enhanced, 200, 255, cv2.THRESH_BINARY)
                    
                    # 白文字OCR（数字と記号のみ）
                    white_data = pytesseract.image_to_data(white_text, config='--psm 11 -c tessedit_char_whitelist=0123456789/()', output_type=pytesseract.Output.DICT)
                    
                    # デバッグ画像を作成
                    ocr_img = img.copy()
                    detected_regions = []
                    
                    # 白文字のOCR結果を描画
                    for i in range(len(white_data['text'])):
                        if int(white_data['conf'][i]) > 20 and white_data['text'][i].strip():
                            (x, y, w, h) = (white_data['left'][i], white_data['top'][i], white_data['width'][i], white_data['height'][i])
                            # 黒背景領域のオフセットを考慮
                            x += x_black
                            y += y_black
                            
                            cv2.rectangle(ocr_img, (x, y), (x + w, y + h), (255, 255, 255), 2)  # 白枠
                            label = f"W:{white_data['text'][i][:10]} ({white_data['conf'][i]}%)"
                            cv2.putText(ocr_img, label, (x, y - 5), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                            
                            detected_regions.append({
                                "タイプ": "白文字",
                                "テキスト": white_data['text'][i],
                                "X": x,
                                "Y": y,
                                "幅": w,
                                "高さ": h,
                                "信頼度": white_data['conf'][i]
                            })
                    
                    # 色付き文字の検出（黒背景領域内）
                    hsv_black = cv2.cvtColor(black_region, cv2.COLOR_BGR2HSV)
                    
                    # 赤色検出（大当り回数など）- より広い範囲
                    red_mask1 = cv2.inRange(hsv_black, np.array([0, 30, 30]), np.array([15, 255, 255]))
                    red_mask2 = cv2.inRange(hsv_black, np.array([165, 30, 30]), np.array([180, 255, 255]))
                    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
                    
                    # 膨張処理で数字を結合（より強く）
                    kernel_dilate = np.ones((5, 5), np.uint8)
                    red_mask_dilated = cv2.dilate(red_mask, kernel_dilate, iterations=3)
                    
                    # 輪郭検出で大きい数字領域を特定
                    red_contours, _ = cv2.findContours(red_mask_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    for contour in red_contours:
                        x, y, w, h = cv2.boundingRect(contour)
                        # 大きい数字サイズ（幅30px以上、高さ40px以上）
                        if w > 30 and h > 40:
                            # この領域を切り出してOCR
                            roi = red_mask[y:y+h, x:x+w]
                            # 画像を拡大してOCR精度向上
                            roi_scaled = cv2.resize(roi, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                            # PSM 8: 単一単語として認識
                            text = pytesseract.image_to_string(roi_scaled, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()
                            
                            if text:
                                # 元画像での座標
                                abs_x = x + x_black
                                abs_y = y + y_black
                                cv2.rectangle(ocr_img, (abs_x, abs_y), (abs_x + w, abs_y + h), (0, 0, 255), 3)
                                label = f"R-Large:{text}"
                                cv2.putText(ocr_img, label, (abs_x, abs_y - 5), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                                
                                detected_regions.append({
                                    "タイプ": "赤大数字",
                                    "テキスト": text,
                                    "X": abs_x,
                                    "Y": abs_y,
                                    "幅": w,
                                    "高さ": h,
                                    "信頼度": "輪郭検出"
                                })
                    
                    # 小さい赤数字用のOCR（既存の処理）
                    red_data = pytesseract.image_to_data(red_mask, config='--psm 11 -c tessedit_char_whitelist=0123456789/()', output_type=pytesseract.Output.DICT)
                    
                    for i in range(len(red_data['text'])):
                        if int(red_data['conf'][i]) > 20 and red_data['text'][i].strip():
                            (x, y, w, h) = (red_data['left'][i], red_data['top'][i], red_data['width'][i], red_data['height'][i])
                            x += x_black
                            y += y_black
                            cv2.rectangle(ocr_img, (x, y), (x + w, y + h), (0, 0, 255), 2)
                            label = f"R:{red_data['text'][i]} ({red_data['conf'][i]}%)"
                            cv2.putText(ocr_img, label, (x, y - 5), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                            
                            detected_regions.append({
                                "タイプ": "赤数字",
                                "テキスト": red_data['text'][i],
                                "X": x,
                                "Y": y,
                                "幅": w,
                                "高さ": h,
                                "信頼度": red_data['conf'][i]
                            })
                    
                    # 青色検出（初当り回数）- より広い範囲
                    blue_mask = cv2.inRange(hsv_black, np.array([95, 30, 30]), np.array([135, 255, 255]))
                    
                    # 膨張処理で数字を結合（より強く）
                    blue_mask_dilated = cv2.dilate(blue_mask, kernel_dilate, iterations=3)
                    
                    # 輪郭検出で大きい数字領域を特定
                    blue_contours, _ = cv2.findContours(blue_mask_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    for contour in blue_contours:
                        x, y, w, h = cv2.boundingRect(contour)
                        # 大きい数字サイズ
                        if w > 30 and h > 40:
                            # この領域を切り出してOCR
                            roi = blue_mask[y:y+h, x:x+w]
                            roi_scaled = cv2.resize(roi, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                            # PSM 8: 単一単語として認識
                            text = pytesseract.image_to_string(roi_scaled, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()
                            
                            if text:
                                abs_x = x + x_black
                                abs_y = y + y_black
                                cv2.rectangle(ocr_img, (abs_x, abs_y), (abs_x + w, abs_y + h), (255, 0, 0), 3)
                                label = f"B-Large:{text}"
                                cv2.putText(ocr_img, label, (abs_x, abs_y - 5), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                                
                                detected_regions.append({
                                    "タイプ": "青大数字",
                                    "テキスト": text,
                                    "X": abs_x,
                                    "Y": abs_y,
                                    "幅": w,
                                    "高さ": h,
                                    "信頼度": "輪郭検出"
                                })
                    
                    # 小さい青数字用のOCR
                    blue_data = pytesseract.image_to_data(blue_mask, config='--psm 11 -c tessedit_char_whitelist=0123456789/()', output_type=pytesseract.Output.DICT)
                    
                    for i in range(len(blue_data['text'])):
                        if int(blue_data['conf'][i]) > 20 and blue_data['text'][i].strip():
                            (x, y, w, h) = (blue_data['left'][i], blue_data['top'][i], blue_data['width'][i], blue_data['height'][i])
                            x += x_black
                            y += y_black
                            cv2.rectangle(ocr_img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                            label = f"B:{blue_data['text'][i]} ({blue_data['conf'][i]}%)"
                            cv2.putText(ocr_img, label, (x, y - 5), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
                            
                            detected_regions.append({
                                "タイプ": "青数字",
                                "テキスト": blue_data['text'][i],
                                "X": x,
                                "Y": y,
                                "幅": w,
                                "高さ": h,
                                "信頼度": blue_data['conf'][i]
                            })
                    
                    # マスク画像も表示（デバッグ用）
                    with st.expander("マスク画像（デバッグ用）"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.image(white_text, caption="白文字マスク", use_column_width=True)
                        with col2:
                            st.image(red_mask, caption="赤文字マスク", use_column_width=True)
                        with col3:
                            st.image(blue_mask, caption="青文字マスク", use_column_width=True)
                    
                    # 画像を表示
                    display_scale = 0.7
                    display_img = cv2.resize(ocr_img, (int(img.shape[1]*display_scale), int(img.shape[0]*display_scale)))
                    st.image(cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB), 
                           caption="OCR検出領域（白：白文字、赤：赤数字、青：青数字）")
                    
                    # 検出されたテキストを表形式で表示
                    if detected_regions:
                        st.markdown("### 検出されたテキスト")
                        import pandas as pd
                        df = pd.DataFrame(detected_regions)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.warning("テキストが検出されませんでした")
            
            # 黒背景検出デバッグボタン
            if st.button("🔍 黒背景領域を検出して表示", use_container_width=True):
                with st.spinner("黒背景領域を検出中..."):
                    # 黒い領域を検出
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    _, black_mask = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
                    
                    kernel = np.ones((5, 5), np.uint8)
                    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
                    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)
                    
                    contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    if contours:
                        # 最大の領域のみを使用
                        largest = max(contours, key=cv2.contourArea)
                        x, y, w, h = cv2.boundingRect(largest)
                        
                        # デバッグ画像を作成
                        debug_img = img.copy()
                        # 黒背景領域を赤枠で囲む
                        cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 0, 255), 3)
                        cv2.putText(debug_img, f"Black Region: {w}x{h}", (x+10, y+30), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                        
                        # 相対座標でOCR領域を描画
                        for name, region_info in st.session_state.relative_regions.items():
                            x1, y1, x2, y2 = region_info['bbox']
                            # 黒背景左上基準の絶対座標
                            abs_x1 = int(x + x1)
                            abs_y1 = int(y + y1)
                            abs_x2 = int(x + x2)
                            abs_y2 = int(y + y2)
                            
                            # 領域の色を決定
                            color = (0, 255, 0)  # 緑
                            if 'red' in region_info['type']:
                                color = (0, 0, 255)  # 赤
                            elif 'blue' in region_info['type']:
                                color = (255, 0, 0)  # 青
                            
                            # First_Hit_Countのみ描画
                            if name == 'First_Hit_Count':
                                cv2.rectangle(debug_img, (abs_x1, abs_y1), (abs_x2, abs_y2), color, 2)
                                cv2.putText(debug_img, name, (abs_x1, abs_y1-5), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                        
                        # 縮小して表示
                        display_scale = 0.5
                        display_img = cv2.resize(debug_img, (int(img.shape[1]*display_scale), int(img.shape[0]*display_scale)))
                        st.image(cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB), 
                               caption="黒背景領域とOCR領域")
                        
                        st.info(f"黒背景領域: {w}x{h}px (位置: {x}, {y})")
                        
                        # セッションステートに黒背景情報を保存
                        st.session_state.black_region = (x, y, w, h)
            
            
            
            
            # 黒背景が検出されている場合、相対座標から絶対座標に変換
            if 'black_region' in st.session_state:
                x, y, w, h = st.session_state.black_region
                st.info(f"黒背景基準で座標を自動設定中")
                
                # 相対座標から絶対座標に変換
                for region_name, region_info in st.session_state.relative_regions.items():
                    x1, y1, x2, y2 = region_info['bbox']
                    
                    # 黒背景左上基準の絶対座標
                    abs_x1 = int(x + x1)
                    abs_y1 = int(y + y1)
                    abs_x2 = int(x + x2)
                    abs_y2 = int(y + y2)
                    
                    st.session_state.regions[region_name] = {
                        'bbox': (abs_x1, abs_y1, abs_x2, abs_y2),
                        'type': region_info['type']
                    }
            
            # 座標設定の読み込み
            uploaded_config = st.file_uploader(
                "座標設定を読み込み",
                type=['json'],
                help="以前保存した座標設定ファイルをアップロード"
            )
            
            if uploaded_config is not None:
                try:
                    config_data = json.loads(uploaded_config.read())
                    if st.button("座標設定を適用", type="primary", use_container_width=True):
                        st.session_state.regions = config_data
                        st.success("座標設定を読み込みました")
                        st.rerun()
                except Exception as e:
                    st.error(f"読み込みエラー: {str(e)}")
            
            st.divider()
            
            # デフォルト設定にリセット
            if st.button("🔄 デフォルト設定に戻す", use_container_width=True):
                st.session_state.regions = st.session_state.base_regions.copy()
                st.success("デフォルト設定にリセットしました")
                st.rerun()
            
            st.divider()
            
            # 調整する領域を選択
            selected_region = st.selectbox(
                "調整する領域",
                list(st.session_state.regions.keys())
            )
            
            if selected_region:
                current_bbox = st.session_state.regions[selected_region]['bbox']
                height, width = img.shape[:2]
                
                st.caption(f"現在: ({current_bbox[0]}, {current_bbox[1]}) - ({current_bbox[2]}, {current_bbox[3]})")
                
                # 数値入力で座標を調整（キーボードの上下キーで操作可能）
                st.markdown("**開始座標**")
                col1, col2 = st.columns(2)
                with col1:
                    new_x1 = st.number_input("X1 (左)", 0, width, current_bbox[0], step=1, key=f"x1_{selected_region}")
                with col2:
                    new_y1 = st.number_input("Y1 (上)", 0, height, current_bbox[1], step=1, key=f"y1_{selected_region}")
                
                st.markdown("**終了座標**")
                col3, col4 = st.columns(2)
                with col3:
                    new_x2 = st.number_input("X2 (右)", 0, width, current_bbox[2], step=1, key=f"x2_{selected_region}")
                with col4:
                    new_y2 = st.number_input("Y2 (下)", 0, height, current_bbox[3], step=1, key=f"y2_{selected_region}")
                
                # 微調整ボタン
                st.markdown("**微調整**")
                col5, col6, col7, col8 = st.columns(4)
                with col5:
                    if st.button("⬅️ 左へ", use_container_width=True):
                        if scale_x != 1.0 or scale_y != 1.0:
                            # 元の座標を更新
                            orig_bbox = st.session_state.base_regions[selected_region]['bbox']
                            st.session_state.base_regions[selected_region]['bbox'] = (orig_bbox[0]-1, orig_bbox[1], orig_bbox[2]-1, orig_bbox[3])
                        st.session_state.regions[selected_region]['bbox'] = (int(new_x1)-1, int(new_y1), int(new_x2)-1, int(new_y2))
                        st.rerun()
                with col6:
                    if st.button("➡️ 右へ", use_container_width=True):
                        if scale_x != 1.0 or scale_y != 1.0:
                            orig_bbox = st.session_state.base_regions[selected_region]['bbox']
                            st.session_state.base_regions[selected_region]['bbox'] = (orig_bbox[0]+1, orig_bbox[1], orig_bbox[2]+1, orig_bbox[3])
                        st.session_state.regions[selected_region]['bbox'] = (int(new_x1)+1, int(new_y1), int(new_x2)+1, int(new_y2))
                        st.rerun()
                with col7:
                    if st.button("⬆️ 上へ", use_container_width=True):
                        if scale_x != 1.0 or scale_y != 1.0:
                            orig_bbox = st.session_state.base_regions[selected_region]['bbox']
                            st.session_state.base_regions[selected_region]['bbox'] = (orig_bbox[0], orig_bbox[1]-1, orig_bbox[2], orig_bbox[3]-1)
                        st.session_state.regions[selected_region]['bbox'] = (int(new_x1), int(new_y1)-1, int(new_x2), int(new_y2)-1)
                        st.rerun()
                with col8:
                    if st.button("⬇️ 下へ", use_container_width=True):
                        if scale_x != 1.0 or scale_y != 1.0:
                            orig_bbox = st.session_state.base_regions[selected_region]['bbox']
                            st.session_state.base_regions[selected_region]['bbox'] = (orig_bbox[0], orig_bbox[1]+1, orig_bbox[2], orig_bbox[3]+1)
                        st.session_state.regions[selected_region]['bbox'] = (int(new_x1), int(new_y1)+1, int(new_x2), int(new_y2)+1)
                        st.rerun()
                
                # 座標を更新
                if st.button("座標を更新", type="primary"):
                    # スケーリングを考慮して元のサイズの座標として保存
                    if 'scale_x' in locals() and 'scale_y' in locals():
                        original_x1 = int(new_x1 / scale_x)
                        original_y1 = int(new_y1 / scale_y)
                        original_x2 = int(new_x2 / scale_x)
                        original_y2 = int(new_y2 / scale_y)
                        st.session_state.base_regions[selected_region]['bbox'] = (original_x1, original_y1, original_x2, original_y2)
                    st.session_state.regions[selected_region]['bbox'] = (int(new_x1), int(new_y1), int(new_x2), int(new_y2))
                    st.rerun()
                
                # 切り出し領域のプレビュー
                if new_x2 > new_x1 and new_y2 > new_y1:
                    roi = img[int(new_y1):int(new_y2), int(new_x1):int(new_x2)]
                    st.markdown("**切り出し領域**")
                    st.image(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
                    
                    # デバッグ用：処理後の画像も表示
                    if st.checkbox("OCR前処理画像を表示", key=f"debug_{selected_region}"):
                        info = st.session_state.regions[selected_region]
                        if info['type'] == 'red_number':
                            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                            mask1 = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([10, 255, 255]))
                            mask2 = cv2.inRange(hsv, np.array([160, 50, 50]), np.array([180, 255, 255]))
                            mask = cv2.bitwise_or(mask1, mask2)
                            kernel = np.ones((2, 2), np.uint8)
                            mask = cv2.dilate(mask, kernel, iterations=1)
                            st.image(mask, caption="赤色抽出結果")
                        elif info['type'] == 'blue_number':
                            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                            mask = cv2.inRange(hsv, np.array([90, 50, 50]), np.array([130, 255, 255]))
                            kernel = np.ones((2, 2), np.uint8)
                            mask = cv2.dilate(mask, kernel, iterations=1)
                            st.image(mask, caption="青色抽出結果")
                        elif info['type'] == 'number':
                            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
                            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
                            st.image(binary, caption="二値化結果")
        
        # 中央カラム：画像表示
        with col_image:
            st.subheader("📷 抽出領域")
            
            # 抽出領域の可視化
            vis_img = img.copy()
            
            for name, info in st.session_state.regions.items():
                x1, y1, x2, y2 = info['bbox']
                color = (0, 255, 0)  # 緑
                if info['type'] == 'red_number':
                    color = (0, 0, 255)  # 赤
                elif info['type'] == 'blue_number':
                    color = (255, 0, 0)  # 青
                
                # 選択中の領域は黄色で強調
                if name == selected_region:
                    color = (0, 255, 255)
                    thickness = 3
                else:
                    thickness = 2
                
                cv2.rectangle(vis_img, (x1, y1), (x2, y2), color, thickness)
                # テキストを枠の中央上部に配置
                text_size = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                text_x = x1 + (x2 - x1 - text_size[0]) // 2
                cv2.putText(vis_img, name, (text_x, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            st.image(cv2.cvtColor(vis_img, cv2.COLOR_BGR2RGB))
        
        # 右カラム：OCR結果
        with col_result:
            st.subheader("📊 抽出結果")
            
            # OCR実行ボタン
            if st.button("🔍 OCR実行", type="primary", use_container_width=True):
                with st.spinner("OCR処理中..."):
                    results = {}
                    
                    # 各領域を処理
                    for name, info in st.session_state.regions.items():
                        x1, y1, x2, y2 = info['bbox']
                        roi = img[y1:y2, x1:x2]
                        
                        try:
                            if info['type'] == 'red_number':
                                # 赤色抽出（より広い範囲）
                                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                                # 赤色の範囲を広げる
                                mask1 = cv2.inRange(hsv, np.array([0, 30, 30]), np.array([10, 255, 255]))
                                mask2 = cv2.inRange(hsv, np.array([160, 30, 30]), np.array([180, 255, 255]))
                                mask = cv2.bitwise_or(mask1, mask2)
                                
                                # ノイズ除去
                                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                                
                                if name in ['Jackpot_Count', 'First_Hit_Count']:
                                    # 大当り/初当り回数の大きな数字
                                    # マスクを反転（白背景に黒文字）してみる
                                    mask_inv = cv2.bitwise_not(mask)
                                    text = pytesseract.image_to_string(mask_inv, config='--psm 8 -c tessedit_char_whitelist=0123456789')
                                    if not text.strip():
                                        # 反転がダメなら元のマスクで再試行
                                        text = pytesseract.image_to_string(mask, config='--psm 8 -c tessedit_char_whitelist=0123456789')
                                elif name in ['Ultra', 'Middle', 'Small']:
                                    # 超/中/小は単一または2桁の数字
                                    # まずマスクを反転してみる
                                    mask_inv = cv2.bitwise_not(mask)
                                    text = pytesseract.image_to_string(mask_inv, config='--psm 8 -c tessedit_char_whitelist=0123456789')
                                    if not text.strip() or (name == 'Ultra' and text.strip() == '1'):
                                        # 反転がダメまたは「21」を「1」と認識した場合は元のマスクで再試行
                                        text = pytesseract.image_to_string(mask, config='--psm 8 -c tessedit_char_whitelist=0123456789')
                                else:
                                    text = pytesseract.image_to_string(mask, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                                
                            elif info['type'] == 'blue_number':
                                # 青色抽出（より広い範囲）
                                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                                mask = cv2.inRange(hsv, np.array([90, 30, 30]), np.array([130, 255, 255]))
                                
                                # ノイズ除去
                                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                                
                                if name == 'First_Hit_Count':
                                    # 初当り回数の大きな数字
                                    # マスクを反転してみる
                                    mask_inv = cv2.bitwise_not(mask)
                                    text = pytesseract.image_to_string(mask_inv, config='--psm 8 -c tessedit_char_whitelist=0123456789')
                                    if not text.strip():
                                        text = pytesseract.image_to_string(mask, config='--psm 8 -c tessedit_char_whitelist=0123456789')
                                else:
                                    text = pytesseract.image_to_string(mask, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                                
                            elif info['type'] == 'number':
                                # 白文字の抽出（黒背景）
                                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                                
                                # 複数の閾値を試す
                                best_text = ""
                                for threshold_val in [180, 200, 220]:
                                    _, binary = cv2.threshold(gray, threshold_val, 255, cv2.THRESH_BINARY)
                                    
                                    # ノイズ除去
                                    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                                    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
                                    
                                    # PSM 7: 単一のテキストライン
                                    temp_text = pytesseract.image_to_string(binary, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                                    if temp_text.strip() and len(temp_text.strip()) > len(best_text):
                                        best_text = temp_text.strip()
                                
                                text = best_text if best_text else pytesseract.image_to_string(gray, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                                
                            else:
                                # 通常のOCR（台番号など）
                                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                                # コントラスト強調
                                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                                enhanced = clahe.apply(gray)
                                text = pytesseract.image_to_string(enhanced, lang='jpn', config='--psm 8')
                            
                            # 結果の処理
                            text = text.strip()
                            
                            if name == 'Machine_No':
                                # 台番号は4桁の数字
                                numbers = re.findall(r'\d{4}', text)
                                results[name] = numbers[0] if numbers else text if text else "認識失敗"
                            elif 'Prob' in name:
                                # 確率は括弧内の数値
                                numbers = re.findall(r'\d+', text)
                                if numbers:
                                    results[name] = f"1/{numbers[-1]}"  # 最後の数字を使用
                                else:
                                    results[name] = text if text else "認識失敗"
                            elif name in ['Jackpot_Count', 'First_Hit_Count']:
                                # 大当り/初当り回数は大きな数字
                                numbers = re.findall(r'\d+', text)
                                if numbers:
                                    # 最も大きい数字を選択（通常は最初の数字）
                                    results[name] = max(numbers, key=lambda x: len(x))
                                else:
                                    results[name] = text if text else "0"
                            else:
                                # その他は最初の数字
                                numbers = re.findall(r'\d+', text)
                                if numbers:
                                    results[name] = numbers[0]
                                else:
                                    results[name] = text if text else "認識失敗"
                                
                        except Exception as e:
                            results[name] = f"エラー: {str(e)}"
                    
                    # 結果をセッションステートに保存
                    st.session_state.ocr_results = results
            
            # 結果表示
            if 'ocr_results' in st.session_state:
                results = st.session_state.ocr_results
                
                # 基本データ
                st.markdown("**基本データ**")
                st.text(f"台番号: {results.get('Machine_No', '-')}")
                st.text(f"大当り: {results.get('Jackpot_Count', '-')} ({results.get('Jackpot_Prob', '-')})")
                st.text(f"初当り: {results.get('First_Hit_Count', '-')} ({results.get('First_Hit_Prob', '-')})")
                st.text(f"累計スタート: {results.get('Total_Start', '-')}")
                
                st.markdown("**詳細データ**")
                st.text(f"超/中/小: {results.get('Ultra', '-')}/{results.get('Middle', '-')}/{results.get('Small', '-')}")
                st.text(f"スタート: {results.get('Start', '-')}")
                st.text(f"通常/チャンス中: {results.get('Normal', '-')}/{results.get('Chance', '-')}")
                st.text(f"最高出玉: {results.get('Max_Payout', '-')}")
                
                # JSON出力
                with st.expander("JSON形式で表示"):
                    st.json(results)
                
                # 座標設定のエクスポート
                with st.expander("現在の座標設定"):
                    st.code(json.dumps(st.session_state.regions, indent=2))
                    
                # 座標設定の保存ボタン
                if st.download_button(
                    label="📥 座標設定をダウンロード",
                    data=json.dumps(st.session_state.regions, indent=2),
                    file_name=f"ocr_regions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                ):
                    st.success("座標設定をダウンロードしました")
    
    else:
        st.warning("⚠️ この画像は出玉詳細画像として認識されませんでした")