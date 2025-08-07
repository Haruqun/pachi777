"""
出玉詳細画像OCRテスト用Streamlitアプリ
既存の機能に影響を与えずにテスト
"""

import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import json
from datetime import datetime

st.set_page_config(
    page_title="出玉詳細OCRテスト",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 出玉詳細画像OCRテスト")
st.caption("IMG_2074.PNGなどの出玉詳細画像からデータを抽出するテスト")

# サイドバーに設定
with st.sidebar:
    st.header("⚙️ OCR設定")
    
    show_regions = st.checkbox("抽出領域を表示", value=True)
    show_raw_text = st.checkbox("生のOCRテキストを表示", value=False)
    
    st.markdown("---")
    st.info("""
    **対応画像**
    - site777の出玉詳細画面
    - iPhone/Androidのスクリーンショット
    
    **抽出データ**
    - 大当り回数・初当り回数
    - 累計スタート
    - 超・中・小
    - 通常・チャンス中
    - その他詳細データ
    """)

# テスト画像をBase64エンコード（事前準備）
import base64
import os

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
    
    # カラムレイアウト
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📷 元画像")
        st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    with col2:
        st.subheader("📊 抽出結果")
        
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
            
            # OCR処理
            with st.spinner("OCR処理中..."):
                results = {}
                
                # 座標定義（IMG_2074.PNGベース）
                regions = {
                    '台番号': {'bbox': (15, 250, 140, 310), 'type': 'text'},
                    '大当り回数': {'bbox': (65, 370, 230, 480), 'type': 'red_number'},
                    '大当り確率': {'bbox': (65, 455, 230, 490), 'type': 'text'},
                    '初当り回数': {'bbox': (300, 370, 465, 480), 'type': 'blue_number'},
                    '初当り確率': {'bbox': (300, 455, 465, 490), 'type': 'text'},
                    '累計スタート': {'bbox': (540, 390, 690, 430), 'type': 'number'},
                    '通常': {'bbox': (495, 460, 595, 500), 'type': 'number'},
                    'チャンス中': {'bbox': (615, 460, 715, 500), 'type': 'number'},
                    '超': {'bbox': (65, 530, 110, 585), 'type': 'number'},
                    '中': {'bbox': (125, 530, 160, 585), 'type': 'number'},
                    '小': {'bbox': (175, 530, 210, 585), 'type': 'number'},
                    'スタート': {'bbox': (315, 530, 425, 585), 'type': 'number'},
                    '最高出玉': {'bbox': (520, 530, 680, 585), 'type': 'number'},
                }
                
                # 各領域を処理
                for name, info in regions.items():
                    x1, y1, x2, y2 = info['bbox']
                    roi = img[y1:y2, x1:x2]
                    
                    try:
                        if info['type'] == 'red_number':
                            # 赤色抽出
                            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                            mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
                            mask2 = cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
                            mask = cv2.bitwise_or(mask1, mask2)
                            text = pytesseract.image_to_string(mask, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                            
                        elif info['type'] == 'blue_number':
                            # 青色抽出
                            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                            mask = cv2.inRange(hsv, np.array([100, 100, 100]), np.array([130, 255, 255]))
                            text = pytesseract.image_to_string(mask, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                            
                        elif info['type'] == 'number':
                            # グレースケール+二値化
                            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                            text = pytesseract.image_to_string(binary, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                            
                        else:
                            # 通常のOCR
                            text = pytesseract.image_to_string(roi, lang='jpn', config='--psm 7')
                        
                        # 数値抽出
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            if '確率' in name and len(numbers) > 0:
                                results[name] = f"1/{numbers[0]}"
                            else:
                                results[name] = numbers[0]
                        else:
                            results[name] = text.strip() if text.strip() else "認識失敗"
                            
                    except Exception as e:
                        results[name] = f"エラー: {str(e)}"
                
                # 結果表示
                st.markdown("### 🎯 抽出データ")
                
                # 基本データ
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("台番号", results.get('台番号', '-'))
                    st.metric("大当り回数", results.get('大当り回数', '-'))
                    st.metric("初当り回数", results.get('初当り回数', '-'))
                    
                with col_b:
                    st.metric("累計スタート", results.get('累計スタート', '-'))
                    st.metric("大当り確率", results.get('大当り確率', '-'))
                    st.metric("初当り確率", results.get('初当り確率', '-'))
                
                # 詳細データ
                st.markdown("#### 📈 詳細データ")
                col_c, col_d, col_e = st.columns(3)
                
                with col_c:
                    st.metric("超", results.get('超', '-'))
                    st.metric("中", results.get('中', '-'))
                    st.metric("小", results.get('小', '-'))
                    
                with col_d:
                    st.metric("スタート", results.get('スタート', '-'))
                    st.metric("通常", results.get('通常', '-'))
                    st.metric("チャンス中", results.get('チャンス中', '-'))
                    
                with col_e:
                    st.metric("最高出玉", results.get('最高出玉', '-'))
                
                # JSON出力
                st.markdown("#### 💾 JSON形式")
                st.json(results)
                
                # 期待値との比較（IMG_2074.PNGの場合）
                if "0026" in str(results.get('台番号', '')):
                    expected = {
                        '台番号': '0026',
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
                        '最高出玉': '26830'
                    }
                    
                    st.markdown("#### 🎯 精度確認（IMG_2074.PNG）")
                    correct = 0
                    total = 0
                    
                    for key, expected_val in expected.items():
                        if key in results:
                            total += 1
                            if str(results[key]) == expected_val:
                                correct += 1
                                st.success(f"✅ {key}: {results[key]}")
                            else:
                                st.error(f"❌ {key}: 期待値={expected_val}, 実際={results[key]}")
                    
                    accuracy = (correct / total * 100) if total > 0 else 0
                    st.info(f"正解率: {correct}/{total} ({accuracy:.1f}%)")
            
            # 抽出領域の可視化
            if show_regions:
                st.markdown("### 🔍 抽出領域の可視化")
                vis_img = img.copy()
                
                for name, info in regions.items():
                    x1, y1, x2, y2 = info['bbox']
                    color = (0, 255, 0)  # 緑
                    if info['type'] == 'red_number':
                        color = (0, 0, 255)  # 赤
                    elif info['type'] == 'blue_number':
                        color = (255, 0, 0)  # 青
                    
                    cv2.rectangle(vis_img, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(vis_img, name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                st.image(cv2.cvtColor(vis_img, cv2.COLOR_BGR2RGB))
            
            # 生のOCRテキスト
            if show_raw_text:
                st.markdown("### 📝 生のOCRテキスト")
                with st.expander("全体のOCRテキスト"):
                    full_text = pytesseract.image_to_string(img, lang='jpn')
                    st.text(full_text)
                    
        else:
            st.warning("⚠️ この画像は出玉詳細画像として認識されませんでした")
            st.info("グラフ画像の可能性があります")

# フッター
st.markdown("---")
st.caption("このアプリは既存の機能に影響を与えずに、出玉詳細画像のOCR機能をテストするためのものです。")