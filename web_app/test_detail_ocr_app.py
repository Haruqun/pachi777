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

# 元画像のサイズ（722x1584）に基づく座標
# 実際の画像サイズに応じて自動スケーリングされる
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
    
    # 画像情報を表示
    st.success(f"画像サイズ: {img.shape[1]} x {img.shape[0]} px")
    
    # デバッグ用：画像の実際のサイズと期待されるサイズを表示
    st.info(f"デバッグ情報 - 幅: {img.shape[1]}px, 高さ: {img.shape[0]}px")
    
    # 元画像サイズとのスケール比を計算
    original_width = 722
    original_height = 1584
    scale_x = img.shape[1] / original_width
    scale_y = img.shape[0] / original_height
    
    # スケーリングされた座標を計算
    if scale_x != 1.0 or scale_y != 1.0:
        st.warning(f"画像がスケーリングされています。スケール比 - X: {scale_x:.2f}, Y: {scale_y:.2f}")
        # 座標を自動調整
        for region_name, region_info in st.session_state.base_regions.items():
            x1, y1, x2, y2 = region_info['bbox']
            st.session_state.regions[region_name] = {
                'bbox': (
                    int(x1 * scale_x),
                    int(y1 * scale_y),
                    int(x2 * scale_x),
                    int(y2 * scale_y)
                ),
                'type': region_info['type']
            }
    
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
            
            # スケール情報を表示
            if scale_x != 1.0 or scale_y != 1.0:
                st.caption(f"スケール: X={scale_x:.2f}, Y={scale_y:.2f}")
            
            # 自動位置調整のオン/オフ
            st.session_state.auto_adjust = st.checkbox("位置ずれ自動調整", value=st.session_state.get('auto_adjust', True), 
                                                       help="スクリーンショットの位置ずれを自動的に検出して調整します")
            
            # 手動調整モード
            st.divider()
            st.markdown("**手動調整**")
            
            # 基準点の手動設定
            manual_mode = st.checkbox("手動で基準点を設定", value=False)
            
            if manual_mode:
                col1, col2 = st.columns(2)
                with col1:
                    base_x = st.number_input("基準X座標", 0, img.shape[1], 15, help="台番号の左端X座標")
                    base_y = st.number_input("基準Y座標", 0, img.shape[0], 210, help="台番号の上端Y座標")
                with col2:
                    manual_scale_x = st.number_input("X拡大率", 0.1, 3.0, 1.0, step=0.1, help="横方向の拡大率")
                    manual_scale_y = st.number_input("Y拡大率", 0.1, 3.0, 1.0, step=0.1, help="縦方向の拡大率")
                
                if st.button("手動設定を適用", type="primary"):
                    # 手動設定で座標を更新
                    for region_name in list(st.session_state.regions.keys()):
                        original_bbox = st.session_state.base_regions[region_name]['bbox']
                        # 元の座標を手動設定の基準点とスケールで変換
                        new_x1 = int(base_x + (original_bbox[0] - 15) * manual_scale_x)
                        new_y1 = int(base_y + (original_bbox[1] - 210) * manual_scale_y)
                        new_x2 = int(base_x + (original_bbox[2] - 15) * manual_scale_x)
                        new_y2 = int(base_y + (original_bbox[3] - 210) * manual_scale_y)
                        
                        st.session_state.regions[region_name] = {
                            'bbox': (new_x1, new_y1, new_x2, new_y2),
                            'type': st.session_state.regions[region_name]['type']
                        }
                    st.session_state.manual_adjusted = True
                    st.rerun()
            
            # 自動調整が有効な場合、要素を検出して調整
            if st.session_state.auto_adjust:
                # 台番号の位置を検出
                machine_box = find_machine_number_box(img)
                x_offset = 0
                y_offset = 0
                
                if machine_box is not None:
                    # 基準となる台番号の位置
                    base_machine_x = int(15 * scale_x)
                    base_machine_y = int(210 * scale_y)
                    
                    # オフセットを計算
                    x_offset = machine_box[0] - base_machine_x
                    y_offset = machine_box[1] - base_machine_y
                else:
                    # 台番号が見つからない場合は黒い背景で調整
                    black_top = find_black_region_top(img)
                    if black_top is not None:
                        if scale_y < 0.6:
                            base_black_top = 165
                        else:
                            base_black_top = int(330 * scale_y)
                        y_offset = black_top - base_black_top
                
                # デバッグ情報
                with st.expander("位置検出デバッグ情報"):
                    if machine_box:
                        st.write(f"台番号検出: {machine_box}")
                        # 検出された領域を表示
                        debug_img = img.copy()
                        cv2.rectangle(debug_img, (machine_box[0], machine_box[1]), 
                                    (machine_box[2], machine_box[3]), (0, 255, 0), 2)
                        st.image(cv2.cvtColor(debug_img[:400, :400], cv2.COLOR_BGR2RGB), 
                               caption="台番号検出結果（緑枠）", width=200)
                    else:
                        st.write("台番号が検出できませんでした")
                    st.write(f"オフセット: X={x_offset}px, Y={y_offset}px")
                
                if abs(x_offset) > 5 or abs(y_offset) > 5:  # 5px以上のずれがある場合
                    st.info(f"位置ずれ検出: X={x_offset}px, Y={y_offset}px（自動調整中）")
                    
                    # リアルタイムで座標を調整
                    offset_key = f"{x_offset},{y_offset}"
                    if 'offset_applied' not in st.session_state or st.session_state.offset_applied != offset_key:
                        for region_name in list(st.session_state.regions.keys()):
                            region_info = st.session_state.regions[region_name]
                            original_bbox = st.session_state.base_regions[region_name]['bbox']
                            scaled_x1 = int(original_bbox[0] * scale_x)
                            scaled_y1 = int(original_bbox[1] * scale_y)
                            scaled_x2 = int(original_bbox[2] * scale_x)
                            scaled_y2 = int(original_bbox[3] * scale_y)
                            st.session_state.regions[region_name] = {
                                'bbox': (scaled_x1 + x_offset, scaled_y1 + y_offset, 
                                       scaled_x2 + x_offset, scaled_y2 + y_offset),
                                'type': region_info['type']
                            }
                        st.session_state.offset_applied = offset_key
            
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