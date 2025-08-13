import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import json

st.set_page_config(
    page_title="パチンコ出玉詳細OCRテスト（改良版）",
    page_icon="🎰",
    layout="wide"
)

st.title("🎰 パチンコ出玉詳細OCRテスト（改良版）")

# 改良されたOCR処理関数
def extract_colored_text(roi, color, text_hint=None):
    """色別にテキストを抽出する改良版"""
    try:
        if color == 'red':
            # 赤色抽出（改良版）
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            # より広い範囲で赤を検出
            mask1 = cv2.inRange(hsv, np.array([0, 30, 30]), np.array([15, 255, 255]))
            mask2 = cv2.inRange(hsv, np.array([165, 30, 30]), np.array([180, 255, 255]))
            mask = cv2.bitwise_or(mask1, mask2)
            
            # ノイズ除去
            kernel = np.ones((2,2), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # 反転（白背景に黒文字）
            mask = cv2.bitwise_not(mask)
            
            # PSMモード選択
            if text_hint and len(text_hint) <= 2:
                config = '--psm 8 -c tessedit_char_whitelist=0123456789'
            else:
                config = '--psm 7 -c tessedit_char_whitelist=0123456789'
            
            text = pytesseract.image_to_string(mask, config=config)
            
        elif color == 'blue':
            # 青色抽出（改良版）
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            # より広い範囲で青を検出
            mask = cv2.inRange(hsv, np.array([90, 30, 30]), np.array([130, 255, 255]))
            
            # ノイズ除去
            kernel = np.ones((2,2), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # 反転
            mask = cv2.bitwise_not(mask)
            
            config = '--psm 8 -c tessedit_char_whitelist=0123456789'
            text = pytesseract.image_to_string(mask, config=config)
            
        else:  # white
            # 白色抽出（改良版）
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # コントラスト強調
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # 適応的二値化
            binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY, 11, 2)
            
            # テキストに応じたPSM選択
            if text_hint and '/' in text_hint:
                config = '--psm 7 -c tessedit_char_whitelist=0123456789/'
            elif text_hint and len(text_hint) <= 3:
                config = '--psm 8 -c tessedit_char_whitelist=0123456789'
            else:
                config = '--psm 7 -c tessedit_char_whitelist=0123456789'
            
            text = pytesseract.image_to_string(binary, config=config)
        
        return text.strip()
    
    except Exception as e:
        return f"エラー: {str(e)}"

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
    
    # 改良された座標定義（実際の検出結果に基づく）
    regions = {
        # 上部メイン数値
        'big_hit': {
            'name': '大当り回数',
            'bbox': (128, 636, 287, 741),
            'color': 'red',
            'expected': '25'
        },
        'first_hit': {
            'name': '初当り回数',
            'bbox': (493, 636, 640, 741),
            'color': 'blue',
            'expected': '4'
        },
        'total_start': {
            'name': '累計スタート',
            'bbox': (886, 638, 1040, 691),
            'color': 'white',
            'expected': '3721'
        },
        
        # 中段データ（超中小）
        'ultra': {
            'name': '超',
            'bbox': (106, 908, 163, 951),
            'color': 'red',
            'expected': '21'
        },
        'middle': {
            'name': '中',
            'bbox': (208, 908, 237, 952),
            'color': 'red',
            'expected': '0'
        },
        'small': {
            'name': '小',
            'bbox': (275, 908, 307, 951),
            'color': 'red',
            'expected': '4'
        },
        
        # 中段データ（スタート・最高出玉）
        'start': {
            'name': 'スタート',
            'bbox': (520, 897, 660, 957),
            'color': 'white',
            'expected': '369'
        },
        'max_payout': {
            'name': '最高出玉',
            'bbox': (851, 897, 1087, 957),
            'color': 'white',
            'expected': '26830'
        },
        
        # 下段データ
        'max_hit': {
            'name': '最高一撃獲得',
            'bbox': (65, 1066, 213, 1102),
            'color': 'white',
            'expected': '25760'
        },
        'chance_hits': {
            'name': 'チャンス中大当り',
            'bbox': (395, 1066, 440, 1104),
            'color': 'white',
            'expected': '21'
        },
        'chance_rate': {
            'name': 'チャンス中確率',
            'bbox': (555, 1066, 663, 1104),
            'color': 'white',
            'expected': '1/87'
        },
        'initial_start': {
            'name': '初回特賞スタート',
            'bbox': (96, 1184, 182, 1220),
            'color': 'white',
            'expected': '220'
        },
        'prev_final': {
            'name': '前日最終スタート',
            'bbox': (343, 1184, 427, 1220),
            'color': 'white',
            'expected': '107'
        },
        
        # 累計テーブル（8/6）
        'date_86': {
            'name': '日付8/6',
            'bbox': (50, 1326, 124, 1364),
            'color': 'white',
            'expected': '8/6'
        },
        'total_86': {
            'name': '累計8/6',
            'bbox': (204, 1326, 322, 1362),
            'color': 'white',
            'expected': '3772'
        },
        'first_rate_86': {
            'name': '初当り確率8/6',
            'bbox': (432, 1326, 570, 1364),
            'color': 'white',
            'expected': '1/277'
        },
        'chance_rate_86': {
            'name': 'チャンス中確率8/6',
            'bbox': (693, 1326, 831, 1364),
            'color': 'white',
            'expected': '1/166'
        },
        'payout_86': {
            'name': '最高出玉8/6',
            'bbox': (953, 1326, 1099, 1362),
            'color': 'white',
            'expected': '14670'
        },
        
        # 累計テーブル（8/5）
        'date_85': {
            'name': '日付8/5',
            'bbox': (50, 1386, 124, 1424),
            'color': 'white',
            'expected': '8/5'
        },
        'total_85': {
            'name': '累計8/5',
            'bbox': (204, 1386, 321, 1422),
            'color': 'white',
            'expected': '3213'
        },
        'first_rate_85': {
            'name': '初当り確率8/5',
            'bbox': (432, 1386, 570, 1424),
            'color': 'white',
            'expected': '1/324'
        },
        'chance_rate_85': {
            'name': 'チャンス中確率8/5',
            'bbox': (709, 1386, 815, 1424),
            'color': 'white',
            'expected': '1/79'
        },
        'payout_85': {
            'name': '最高出玉8/5',
            'bbox': (951, 1386, 1099, 1422),
            'color': 'white',
            'expected': '22100'
        }
    }
    
    # メインレイアウト
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📷 検出領域")
        
        # 画像のコピーを作成
        vis_img = img_bgr.copy()
        
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
        
        st.info(f"画像サイズ: {width} x {height} px")
    
    with col2:
        st.subheader("📊 OCR操作")
        
        if st.button("🔍 改良版OCR実行", type="primary", use_container_width=True):
            results = {}
            successful = 0
            failed = 0
            
            with st.spinner("OCR処理中..."):
                progress_bar = st.progress(0)
                total_regions = len(regions)
                
                for idx, (key, region) in enumerate(regions.items()):
                    x1, y1, x2, y2 = region['bbox']
                    
                    # 余白を追加
                    padding = 10
                    y1_pad = max(0, y1 - padding)
                    y2_pad = min(height, y2 + padding)
                    x1_pad = max(0, x1 - padding)
                    x2_pad = min(width, x2 + padding)
                    roi = img_bgr[y1_pad:y2_pad, x1_pad:x2_pad]
                    
                    # 改良版OCR実行
                    text = extract_colored_text(roi, region['color'], region.get('expected'))
                    
                    results[region['name']] = {
                        'detected': text,
                        'expected': region.get('expected', ''),
                        'match': text == region.get('expected', '')
                    }
                    
                    if text and not text.startswith('エラー'):
                        successful += 1
                    else:
                        failed += 1
                    
                    # プログレスバー更新
                    progress_bar.progress((idx + 1) / total_regions)
            
            # 結果表示
            st.success(f"OCR完了！ 成功: {successful}/{total_regions}, 失敗: {failed}/{total_regions}")
            st.divider()
            
            # 結果をセクション別に表示
            st.markdown("### 📊 抽出結果")
            
            # メイン数値
            st.markdown("#### メイン数値")
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                res = results.get('大当り回数', {})
                if res.get('match'):
                    st.metric("大当り回数", res['detected'], "✅")
                else:
                    st.error(f"大当り回数: {res.get('detected', '認識失敗')} (期待値: {res.get('expected', '')})")
            
            with col_b:
                res = results.get('初当り回数', {})
                if res.get('match'):
                    st.metric("初当り回数", res['detected'], "✅")
                else:
                    st.error(f"初当り回数: {res.get('detected', '認識失敗')} (期待値: {res.get('expected', '')})")
            
            with col_c:
                res = results.get('累計スタート', {})
                if res.get('match'):
                    st.metric("累計スタート", res['detected'], "✅")
                else:
                    st.warning(f"累計スタート: {res.get('detected', '認識失敗')} (期待値: {res.get('expected', '')})")
            
            # 超中小
            st.markdown("#### 超中小")
            col_d, col_e, col_f = st.columns(3)
            
            with col_d:
                res = results.get('超', {})
                st.metric("超", res.get('detected', '-'))
            
            with col_e:
                res = results.get('中', {})
                st.metric("中", res.get('detected', '-'))
            
            with col_f:
                res = results.get('小', {})
                st.metric("小", res.get('detected', '-'))
            
            # その他のデータ
            st.markdown("#### その他のデータ")
            
            # 表形式で表示
            import pandas as pd
            
            data_rows = []
            for name, res in results.items():
                if name not in ['大当り回数', '初当り回数', '累計スタート', '超', '中', '小']:
                    data_rows.append({
                        '項目': name,
                        '検出値': res.get('detected', '-'),
                        '期待値': res.get('expected', '-'),
                        '一致': '✅' if res.get('match') else '❌'
                    })
            
            if data_rows:
                df = pd.DataFrame(data_rows)
                st.dataframe(df, use_container_width=True)
            
            # JSON出力
            with st.expander("詳細データ (JSON)"):
                st.json(results)
            
            # ダウンロードボタン
            json_str = json.dumps(results, ensure_ascii=False, indent=2)
            st.download_button(
                label="💾 結果をダウンロード",
                data=json_str,
                file_name="ocr_results_improved.json",
                mime="application/json",
                use_container_width=True
            )