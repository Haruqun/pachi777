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
        'Machine_No': {'bbox': (15, 211, 72, 240), 'type': 'text'},
        'Jackpot_Count': {'bbox': (61, 310, 186, 391), 'type': 'red_number'},
        'Jackpot_Prob': {'bbox': (64, 375, 165, 397), 'type': 'text'},
        'First_Hit_Count': {'bbox': (251, 310, 335, 391), 'type': 'blue_number'},
        'First_Hit_Prob': {'bbox': (254, 375, 332, 397), 'type': 'text'},
        'Total_Start': {'bbox': (445, 316, 549, 349), 'type': 'number'},
        'Normal': {'bbox': (405, 368, 474, 399), 'type': 'number'},
        'Chance': {'bbox': (497, 368, 566, 399), 'type': 'number'},
        'Ultra': {'bbox': (53, 440, 88, 474), 'type': 'red_number'},
        'Middle': {'bbox': (96, 440, 131, 474), 'type': 'red_number'},
        'Small': {'bbox': (140, 440, 175, 474), 'type': 'red_number'},
        'Start': {'bbox': (259, 436, 358, 481), 'type': 'number'},
        'Max_Payout': {'bbox': (424, 436, 556, 481), 'type': 'number'},
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
    local_path = os.path.join(os.path.dirname(__file__), "..", "data_image", filename)
    if os.path.exists(local_path):
        with open(local_path, "rb") as f:
            img_data = f.read()
            test_images_data[f"{filename} (台番号: {machine_num})"] = img_data

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
        type=['png', 'jpg', 'jpeg'],
        help="site777の出玉詳細画面のスクリーンショットをアップロードしてください"
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
    
    image_type = detect_image_type(img)
    
    if image_type == "detail":
        st.success("✅ 出玉詳細画像として認識されました")
        
        # 3カラムレイアウト（座標調整、画像、結果）
        col_adjust, col_image, col_result = st.columns([1, 1.5, 1])
        
        # 左カラム：座標調整ツール
        with col_adjust:
            st.subheader("🎯 座標調整")
            
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
                        st.session_state.regions[selected_region]['bbox'] = (int(new_x1)-1, int(new_y1), int(new_x2)-1, int(new_y2))
                        st.rerun()
                with col6:
                    if st.button("➡️ 右へ", use_container_width=True):
                        st.session_state.regions[selected_region]['bbox'] = (int(new_x1)+1, int(new_y1), int(new_x2)+1, int(new_y2))
                        st.rerun()
                with col7:
                    if st.button("⬆️ 上へ", use_container_width=True):
                        st.session_state.regions[selected_region]['bbox'] = (int(new_x1), int(new_y1)-1, int(new_x2), int(new_y2)-1)
                        st.rerun()
                with col8:
                    if st.button("⬇️ 下へ", use_container_width=True):
                        st.session_state.regions[selected_region]['bbox'] = (int(new_x1), int(new_y1)+1, int(new_x2), int(new_y2)+1)
                        st.rerun()
                
                # 座標を更新
                if st.button("座標を更新", type="primary"):
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
                            st.image(binary, caption="二値化結果")
        
        # 中央カラム：画像表示
        with col_image:
            st.subheader("📷 画像")
            
            # タブで元画像と可視化画像を切り替え
            tab1, tab2 = st.tabs(["元画像", "抽出領域"])
            
            with tab1:
                st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            
            with tab2:
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
                    cv2.putText(vis_img, name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
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
                                
                                # 大当り回数は大きな数字なのでPSM 8を使用
                                if name == 'Jackpot_Count' or name == 'First_Hit_Count':
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
                                
                                # 初当り回数は大きな数字なのでPSM 8を使用
                                if name == 'First_Hit_Count':
                                    text = pytesseract.image_to_string(mask, config='--psm 8 -c tessedit_char_whitelist=0123456789')
                                else:
                                    text = pytesseract.image_to_string(mask, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                                
                            elif info['type'] == 'number':
                                # 白文字の抽出（黒背景）
                                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                                # 白い文字を抽出
                                _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
                                # PSM 8: 単一の単語として扱う
                                text = pytesseract.image_to_string(binary, config='--psm 8 -c tessedit_char_whitelist=0123456789')
                                
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