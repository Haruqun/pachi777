import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image

st.set_page_config(
    page_title="パチンコ出玉詳細OCRテスト（修正版）",
    page_icon="🎰",
    layout="wide"
)

st.title("🎰 パチンコ出玉詳細OCRテスト（修正版）")

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
    
    # 実際の検出結果に基づく座標定義（検出成功したもののみ）
    regions = {
        # 上部データ
        'total_start': {
            'name': '累計スタート',
            'bbox': (886, 638, 1040, 691),
            'color': 'white'
        },
        
        # 中段データ
        'max_payout': {
            'name': '最高出玉',
            'bbox': (851, 897, 1087, 957),
            'color': 'white'
        },
        
        # 下段第1行
        'max_hit': {
            'name': '最高一撃獲得',
            'bbox': (65, 1066, 213, 1102),
            'color': 'white'
        },
        'chance_hits': {
            'name': 'チャンス中大当り',
            'bbox': (180, 1066, 260, 1102),
            'color': 'white'
        },
        'chance_rate': {
            'name': 'チャンス中確率',
            'bbox': (555, 1066, 663, 1104),
            'color': 'white'
        },
        
        # 下段第2行
        'initial_start': {
            'name': '初回特賞スタート',
            'bbox': (96, 1184, 182, 1220),
            'color': 'white'
        },
        'prev_final': {
            'name': '前日最終スタート',
            'bbox': (210, 1184, 295, 1220),
            'color': 'white'
        },
        
        # 累計テーブル（8/6）
        'date_86': {
            'name': '日付8/6',
            'bbox': (50, 1326, 124, 1364),
            'color': 'white'
        },
        'total_86': {
            'name': '累計8/6',
            'bbox': (204, 1326, 322, 1362),
            'color': 'white'
        },
        'first_rate_86': {
            'name': '初当り確率8/6',
            'bbox': (432, 1326, 570, 1364),
            'color': 'white'
        },
        'chance_rate_86': {
            'name': 'チャンス中確率8/6',
            'bbox': (693, 1326, 831, 1364),
            'color': 'white'
        },
        'payout_86': {
            'name': '最高出玉8/6',
            'bbox': (953, 1326, 1099, 1362),
            'color': 'white'
        },
        
        # 累計テーブル（8/5）
        'date_85': {
            'name': '日付8/5',
            'bbox': (50, 1386, 124, 1424),
            'color': 'white'
        },
        'total_85': {
            'name': '累計8/5',
            'bbox': (204, 1386, 321, 1422),
            'color': 'white'
        },
        'first_rate_85': {
            'name': '初当り確率8/5',
            'bbox': (432, 1386, 570, 1424),
            'color': 'white'
        },
        'chance_rate_85': {
            'name': 'チャンス中確率8/5',
            'bbox': (709, 1386, 815, 1424),
            'color': 'white'
        },
        'payout_85': {
            'name': '最高出玉8/5',
            'bbox': (951, 1386, 1099, 1422),
            'color': 'white'
        },
        
        # 下部統計データ（黒背景外だが実際に検出された領域）
        'bottom_start': {
            'name': 'スタート（下部）',
            'bbox': (45, 2035, 106, 2063),
            'color': 'white'
        },
        'bottom_stat1': {
            'name': '現在',
            'bbox': (169, 2035, 210, 2063),
            'color': 'white'
        },
        'bottom_stat2': {
            'name': 'チャンス',
            'bbox': (283, 2035, 324, 2063),
            'color': 'white'
        },
        'bottom_stat3': {
            'name': '突時回数',
            'bbox': (512, 2035, 552, 2063),
            'color': 'white'
        },
        'bottom_stat4': {
            'name': '低確スタート',
            'bbox': (968, 2035, 1009, 2063),
            'color': 'white'
        },
        'bottom_stat5': {
            'name': '遊タイム',
            'bbox': (1082, 2035, 1123, 2063),
            'color': 'white'
        }
    }
    
    # メインレイアウト：左に画像、右に操作
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📷 検出領域")
        
        # 画像のコピーを作成
        vis_img = img_bgr.copy()
        
        # 黒背景領域を表示（参考）
        black_region = (11, 507, 1172, 2080)
        bx1, by1, bx2, by2 = black_region
        cv2.rectangle(vis_img, (bx1, by1), (bx2, by2), (0, 0, 255), 2)
        cv2.putText(vis_img, "Black Region", (bx1, by1-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
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
        st.info(f"黒背景領域: {black_region}")
    
    with col2:
        st.subheader("📊 OCR操作")
        
        if st.button("🔍 OCR実行", type="primary", use_container_width=True):
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
                        # 白色抽出（グレースケール + 二値化）
                        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
                        
                        # '/'を含む場合は分数として認識
                        if 'rate' in key or '/' in region['name']:
                            config = '--psm 7 -c tessedit_char_whitelist=0123456789/'
                        else:
                            config = '--psm 7 -c tessedit_char_whitelist=0123456789'
                        
                        text = pytesseract.image_to_string(binary, config=config)
                        results[region['name']] = text.strip()
                        
                    except Exception as e:
                        results[region['name']] = f"エラー: {str(e)}"
            
            # 結果表示
            st.success("OCR完了！")
            st.divider()
            
            # 結果をカテゴリ別に表示
            st.markdown("### 抽出結果")
            
            # 上段
            col_a, col_b = st.columns(2)
            with col_a:
                value = results.get('累計スタート', '')
                st.metric("累計スタート", value if value else "認識失敗")
            
            with col_b:
                value = results.get('最高出玉', '')
                st.metric("最高出玉", value if value else "認識失敗")
            
            # 下段データ
            st.markdown("#### 下段データ")
            col_c, col_d, col_e = st.columns(3)
            with col_c:
                st.metric("最高一撃獲得", results.get('最高一撃獲得', '-'))
            with col_d:
                st.metric("チャンス中大当り", results.get('チャンス中大当り', '-'))
            with col_e:
                st.metric("チャンス中確率", results.get('チャンス中確率', '-'))
            
            # 累計テーブル
            st.markdown("#### 累計テーブル")
            import pandas as pd
            table_data = []
            for date in ['86', '85']:
                row = {
                    '日付': results.get(f'日付8/{date[1]}', '-'),
                    '累計': results.get(f'累計8/{date[1]}', '-'),
                    '初当り確率': results.get(f'初当り確率8/{date[1]}', '-'),
                    'チャンス中確率': results.get(f'チャンス中確率8/{date[1]}', '-'),
                    '最高出玉': results.get(f'最高出玉8/{date[1]}', '-')
                }
                table_data.append(row)
            
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True)
            
            # 下部統計
            st.markdown("#### 下部統計")
            col_f = st.columns(6)
            stats = ['スタート（下部）', '現在', 'チャンス', '突時回数', '低確スタート', '遊タイム']
            for idx, stat in enumerate(stats):
                with col_f[idx]:
                    st.metric(stat, results.get(stat, '-'))
            
            # JSON出力
            with st.expander("詳細データ (JSON)"):
                st.json(results)