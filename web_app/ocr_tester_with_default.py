import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import os

st.set_page_config(
    page_title="OCRテスター（デフォルト画像付き）",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 OCRテスター - IMG_2074.PNG")

# デフォルト画像のパス
DEFAULT_IMAGE_PATH = "default_test_image.png"

# 初期化
if 'use_default' not in st.session_state:
    st.session_state.use_default = True

# サイドバー
with st.sidebar:
    st.header("📸 画像選択")
    
    # デフォルト画像を使用
    use_default = st.checkbox("デフォルト画像を使用", value=True)
    
    if use_default:
        st.info("デフォルト画像（IMG_2074.PNG）を使用中")
        if os.path.exists(DEFAULT_IMAGE_PATH):
            image = Image.open(DEFAULT_IMAGE_PATH)
            st.image(image, caption="IMG_2074.PNG", use_column_width=True)
        else:
            st.error("デフォルト画像が見つかりません")
            image = None
    else:
        uploaded_file = st.file_uploader("画像をアップロード", type=['png', 'jpg', 'jpeg'])
        if uploaded_file:
            image = Image.open(uploaded_file)
        else:
            image = None

# 期待値（IMG_2074.PNGの正解データ）
EXPECTED_VALUES = {
    '大当り回数': '25',
    '初当り回数': '4',
    '累計スタート': '3721',
    '通常': '1877',
    'チャンス中': '1844',
    '超': '21',
    '中': '0',
    '小': '4',
    'スタート': '369',
    '最高出玉': '26830',
    '最高一撃獲得': '25760',
    'チャンス中大当り': '21',
    'チャンス中確率': '1/87',
    '初回特賞スタート': '220',
    '前日最終スタート': '107',
    '8/6_累計': '3772',
    '8/6_初当り確率': '1/277',
    '8/6_チャンス中確率': '1/166',
    '8/6_最高出玉': '14670',
    '8/5_累計': '3213',
    '8/5_初当り確率': '1/324',
    '8/5_チャンス中確率': '1/79',
    '8/5_最高出玉': '22100'
}

# 実際の検出結果に基づく正確な座標
REGIONS = {
    # 上部メイン数値
    'big_hit': {
        'name': '大当り回数',
        'bbox': (75, 355, 205, 490),  # 赤色の大きな「25」
        'color': 'red',
        'expected': '25'
    },
    'first_hit': {
        'name': '初当り回数',
        'bbox': (345, 355, 415, 490),  # 青色の大きな「4」
        'color': 'blue',
        'expected': '4'
    },
    'total_start': {
        'name': '累計スタート',
        'bbox': (540, 390, 672, 435),  # 白色の「3721」
        'color': 'white',
        'expected': '3721'
    },
    'normal_count': {
        'name': '通常',
        'bbox': (495, 455, 585, 495),  # 「1877」
        'color': 'white',
        'expected': '1877'
    },
    'chance_count': {
        'name': 'チャンス中',
        'bbox': (605, 455, 695, 495),  # 「1844」
        'color': 'white',
        'expected': '1844'
    },
    
    # 超中小（赤色）
    'ultra': {
        'name': '超',
        'bbox': (75, 540, 117, 590),  # 赤色の「21」
        'color': 'red',
        'expected': '21'
    },
    'middle': {
        'name': '中',
        'bbox': (125, 540, 155, 590),  # 赤色の「0」
        'color': 'red',
        'expected': '0'
    },
    'small': {
        'name': '小',
        'bbox': (165, 540, 195, 590),  # 赤色の「4」
        'color': 'red',
        'expected': '4'
    },
    
    # 中段データ
    'start': {
        'name': 'スタート',
        'bbox': (315, 540, 410, 590),  # 白色の「369」
        'color': 'white',
        'expected': '369'
    },
    'max_payout': {
        'name': '最高出玉',
        'bbox': (520, 540, 665, 590),  # 白色の「26830」
        'color': 'white',
        'expected': '26830'
    },
    
    # 下段データ
    'max_hit': {
        'name': '最高一撃獲得',
        'bbox': (37, 655, 155, 690),  # 「25760」
        'color': 'white',
        'expected': '25760'
    },
    'chance_hits': {
        'name': 'チャンス中大当り',
        'bbox': (210, 655, 260, 690),  # 「21」
        'color': 'white',
        'expected': '21'
    },
    'chance_rate': {
        'name': 'チャンス中確率',
        'bbox': (338, 655, 420, 690),  # 「1/87」
        'color': 'white',
        'expected': '1/87'
    },
    
    # 初回・前日データ
    'initial_start': {
        'name': '初回特賞スタート',
        'bbox': (55, 725, 120, 760),  # 「220」
        'color': 'white',
        'expected': '220'
    },
    'prev_final': {
        'name': '前日最終スタート',
        'bbox': (210, 725, 275, 760),  # 「107」
        'color': 'white',
        'expected': '107'
    },
    
    # 累計テーブル（8/6）
    'date_86': {
        'name': '8/6',
        'bbox': (30, 815, 75, 850),
        'color': 'white',
        'expected': '8/6'
    },
    'total_86': {
        'name': '8/6_累計',
        'bbox': (120, 815, 200, 850),
        'color': 'white',
        'expected': '3772'
    },
    'first_rate_86': {
        'name': '8/6_初当り確率',
        'bbox': (260, 815, 350, 850),
        'color': 'white',
        'expected': '1/277'
    },
    'chance_rate_86': {
        'name': '8/6_チャンス中確率',
        'bbox': (420, 815, 510, 850),
        'color': 'white',
        'expected': '1/166'
    },
    'payout_86': {
        'name': '8/6_最高出玉',
        'bbox': (580, 815, 680, 850),
        'color': 'white',
        'expected': '14670'
    },
    
    # 累計テーブル（8/5）
    'date_85': {
        'name': '8/5',
        'bbox': (30, 860, 75, 895),
        'color': 'white',
        'expected': '8/5'
    },
    'total_85': {
        'name': '8/5_累計',
        'bbox': (120, 860, 200, 895),
        'color': 'white',
        'expected': '3213'
    },
    'first_rate_85': {
        'name': '8/5_初当り確率',
        'bbox': (260, 860, 350, 895),
        'color': 'white',
        'expected': '1/324'
    },
    'chance_rate_85': {
        'name': '8/5_チャンス中確率',
        'bbox': (420, 860, 500, 895),
        'color': 'white',
        'expected': '1/79'
    },
    'payout_85': {
        'name': '8/5_最高出玉',
        'bbox': (580, 860, 680, 895),
        'color': 'white',
        'expected': '22100'
    }
}

# メインエリア
if image:
    img_array = np.array(image)
    
    # BGRに変換
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img_array
    
    height, width = img_bgr.shape[:2]
    
    st.header("📊 OCR実行")
    
    # 2列レイアウト
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📷 検出領域")
        
        # 領域を描画
        vis_img = img_bgr.copy()
        for key, region in REGIONS.items():
            x1, y1, x2, y2 = region['bbox']
            color_map = {
                'red': (0, 0, 255),
                'blue': (255, 0, 0),
                'white': (200, 200, 200)
            }
            color = color_map.get(region['color'], (255, 255, 255))
            cv2.rectangle(vis_img, (x1, y1), (x2, y2), color, 2)
            
            # 領域名を表示（見やすい位置に）
            label_y = y1 - 5 if y1 > 20 else y2 + 15
            cv2.putText(vis_img, region['name'][:6], (x1, label_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        st.image(cv2.cvtColor(vis_img, cv2.COLOR_BGR2RGB), use_column_width=True)
    
    with col2:
        st.subheader("🔍 OCR結果")
        
        if st.button("OCR実行", type="primary", use_container_width=True):
            results = {}
            correct_count = 0
            total_count = len(REGIONS)
            
            with st.spinner("OCR処理中..."):
                for key, region in REGIONS.items():
                    x1, y1, x2, y2 = region['bbox']
                    roi = img_bgr[y1:y2, x1:x2]
                    
                    # 色別処理
                    if region['color'] == 'red':
                        # 赤色抽出（改善版）
                        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                        # ピンク〜赤の範囲を拡大
                        mask1 = cv2.inRange(hsv, np.array([0, 30, 30]), np.array([15, 255, 255]))
                        mask2 = cv2.inRange(hsv, np.array([160, 30, 30]), np.array([180, 255, 255]))
                        mask = cv2.bitwise_or(mask1, mask2)
                        # モルフォロジー処理
                        kernel = np.ones((2,2), np.uint8)
                        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                        mask = cv2.bitwise_not(mask)
                        # 複数のPSMモードを試す
                        for psm in [8, 7, 13]:
                            text = pytesseract.image_to_string(mask, config=f'--psm {psm} -c tessedit_char_whitelist=0123456789/')
                            text = text.strip()
                            if text:
                                break
                        
                    elif region['color'] == 'blue':
                        # 青色抽出（改善版）
                        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                        # シアン〜青の範囲を拡大
                        mask = cv2.inRange(hsv, np.array([90, 30, 30]), np.array([120, 255, 255]))
                        # モルフォロジー処理
                        kernel = np.ones((2,2), np.uint8)
                        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                        mask = cv2.bitwise_not(mask)
                        # 複数のPSMモードを試す
                        for psm in [8, 7, 13]:
                            text = pytesseract.image_to_string(mask, config=f'--psm {psm} -c tessedit_char_whitelist=0123456789/')
                            text = text.strip()
                            if text:
                                break
                        
                    else:  # white
                        # 白色抽出（改善版）
                        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                        # 適応的闾値処理
                        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                      cv2.THRESH_BINARY, 11, 2)
                        # エッジ強調
                        edges = cv2.Canny(gray, 50, 150)
                        combined = cv2.bitwise_or(binary, edges)
                        
                        if '/' in region['expected']:
                            whitelist = '0123456789/'
                        else:
                            whitelist = '0123456789'
                        
                        # 複数のPSMモードを試す
                        for psm in [7, 8, 13]:
                            text = pytesseract.image_to_string(combined, config=f'--psm {psm} -c tessedit_char_whitelist={whitelist}')
                            text = text.strip()
                            if text:
                                break
                    
                    if not text:
                        text = ""
                    results[region['name']] = {
                        'detected': text,
                        'expected': region['expected'],
                        'match': text == region['expected']
                    }
                    
                    if text == region['expected']:
                        correct_count += 1
            
            # 結果表示
            st.success(f"完了！ 正解率: {correct_count}/{total_count} ({correct_count/total_count*100:.1f}%)")
            
            # カテゴリ別表示
            st.markdown("#### 🎯 メイン数値")
            cols = st.columns(5)
            main_items = ['大当り回数', '初当り回数', '累計スタート', '通常', 'チャンス中']
            for idx, item in enumerate(main_items):
                if item in results:
                    with cols[idx]:
                        res = results[item]
                        if res['match']:
                            st.metric(item, res['detected'], "✅")
                        else:
                            st.metric(item, res['detected'] or "❌", f"({res['expected']})")
            
            st.markdown("#### 🔴 超中小")
            cols = st.columns(3)
            for idx, item in enumerate(['超', '中', '小']):
                if item in results:
                    with cols[idx]:
                        res = results[item]
                        if res['match']:
                            st.metric(item, res['detected'], "✅")
                        else:
                            st.metric(item, res['detected'] or "❌", f"({res['expected']})")
            
            # 問題のある項目を強調
            st.divider()
            errors = [name for name, res in results.items() if not res['match']]
            if errors:
                st.error(f"❌ 検出失敗: {', '.join(errors)}")
            else:
                st.success("🎉 すべて正しく検出できました！")
            
            # 詳細データ
            with st.expander("詳細結果"):
                import pandas as pd
                df_data = []
                for name, res in results.items():
                    df_data.append({
                        '項目': name,
                        '検出値': res['detected'],
                        '期待値': res['expected'],
                        '結果': '✅' if res['match'] else '❌'
                    })
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True)

else:
    st.info("画像を選択してください")