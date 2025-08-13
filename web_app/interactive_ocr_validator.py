import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import json
from datetime import datetime

st.set_page_config(
    page_title="OCR検証システム",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 インタラクティブOCR検証システム")
st.markdown("OCR結果を検証し、問題を分析するためのツール")

# セッション状態の初期化
if 'ocr_results' not in st.session_state:
    st.session_state.ocr_results = {}
if 'validation_results' not in st.session_state:
    st.session_state.validation_results = {}
if 'analysis_log' not in st.session_state:
    st.session_state.analysis_log = []

# 期待値の定義（実際の正解データ）
EXPECTED_VALUES = {
    '大当り回数': '25',
    '初当り回数': '4',
    '累計スタート': '3721',
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
    '日付8/6': '8/6',
    '累計8/6': '3772',
    '初当り確率8/6': '1/277',
    'チャンス中確率8/6': '1/166',
    '最高出玉8/6': '14670',
    '日付8/5': '8/5',
    '累計8/5': '3213',
    '初当り確率8/5': '1/324',
    'チャンス中確率8/5': '1/79',
    '最高出玉8/5': '22100'
}

# 改良された座標定義（黒枠検出結果を基に調整）
REGIONS = {
    # 上部メイン数値（黒枠基準で調整）
    'big_hit': {
        'name': '大当り回数',
        'bbox': (128, 636, 287, 741),
        'color': 'red',
        'psm': 8,
        'preprocess': 'red_enhance'
    },
    'first_hit': {
        'name': '初当り回数',
        'bbox': (493, 636, 640, 741),
        'color': 'blue',
        'psm': 8,
        'preprocess': 'blue_enhance'
    },
    'total_start': {
        'name': '累計スタート',
        'bbox': (886, 638, 1040, 691),
        'color': 'white',
        'psm': 7,
        'preprocess': 'white_enhance'
    },
    
    # 中段データ（超中小）
    'ultra': {
        'name': '超',
        'bbox': (106, 908, 163, 951),
        'color': 'red',
        'psm': 8,
        'preprocess': 'red_enhance'
    },
    'middle': {
        'name': '中',
        'bbox': (208, 908, 237, 952),
        'color': 'red',
        'psm': 10,  # 単一文字
        'preprocess': 'red_enhance'
    },
    'small': {
        'name': '小',
        'bbox': (275, 908, 307, 951),
        'color': 'red',
        'psm': 10,  # 単一文字
        'preprocess': 'red_enhance'
    },
    
    # スタート（下部で検出された369を正しい位置にマッピング）
    'start': {
        'name': 'スタート',
        'bbox': (45, 2035, 106, 2063),  # 実際に検出された位置
        'color': 'white',
        'psm': 7,
        'preprocess': 'white_enhance'
    },
    
    # その他の正確に検出された領域
    'max_payout': {
        'name': '最高出玉',
        'bbox': (851, 897, 1087, 957),
        'color': 'white',
        'psm': 7,
        'preprocess': 'white_enhance'
    },
    'max_hit': {
        'name': '最高一撃獲得',
        'bbox': (65, 1066, 213, 1102),
        'color': 'white',
        'psm': 7,
        'preprocess': 'white_enhance'
    },
    'chance_rate': {
        'name': 'チャンス中確率',
        'bbox': (555, 1066, 663, 1104),
        'color': 'white',
        'psm': 7,
        'preprocess': 'white_enhance'
    },
    'initial_start': {
        'name': '初回特賞スタート',
        'bbox': (96, 1184, 182, 1220),
        'color': 'white',
        'psm': 7,
        'preprocess': 'white_enhance'
    }
}

def preprocess_image(img, method):
    """画像の前処理"""
    if method == 'red_enhance':
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # 赤色の範囲を拡大
        mask1 = cv2.inRange(hsv, np.array([0, 20, 20]), np.array([20, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([160, 20, 20]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(mask1, mask2)
        # モルフォロジー処理
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return cv2.bitwise_not(mask)
    
    elif method == 'blue_enhance':
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([85, 20, 20]), np.array([135, 255, 255]))
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return cv2.bitwise_not(mask)
    
    elif method == 'white_enhance':
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        _, binary = cv2.threshold(enhanced, 180, 255, cv2.THRESH_BINARY)
        return binary
    
    else:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

def perform_ocr(img, region_info):
    """領域に対してOCRを実行"""
    x1, y1, x2, y2 = region_info['bbox']
    roi = img[y1:y2, x1:x2]
    
    # 前処理
    processed = preprocess_image(roi, region_info.get('preprocess', 'default'))
    
    # PSM設定
    psm = region_info.get('psm', 7)
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789/'
    
    try:
        text = pytesseract.image_to_string(processed, config=config)
        return text.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# サイドバー：検証コントロール
with st.sidebar:
    st.header("🎮 検証コントロール")
    
    # 画像アップロード
    uploaded_file = st.file_uploader(
        "画像をアップロード",
        type=['png', 'jpg', 'jpeg'],
        help="テスト画像をアップロード"
    )
    
    if uploaded_file:
        # OCR実行ボタン
        if st.button("🔍 OCR実行", type="primary", use_container_width=True):
            # 画像処理
            image = Image.open(uploaded_file)
            img_array = np.array(image)
            
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            else:
                img_bgr = img_array
            
            # リサイズ
            height, width = img_bgr.shape[:2]
            if width != 1179:
                scale = 1179 / width
                new_height = int(height * scale)
                img_bgr = cv2.resize(img_bgr, (1179, new_height))
            
            # OCR実行
            results = {}
            for key, region in REGIONS.items():
                text = perform_ocr(img_bgr, region)
                results[region['name']] = {
                    'detected': text,
                    'expected': EXPECTED_VALUES.get(region['name'], ''),
                    'bbox': region['bbox'],
                    'color': region['color']
                }
            
            st.session_state.ocr_results = results
            st.success("OCR完了！")
    
    # 分析ログエクスポート
    if st.session_state.analysis_log:
        st.divider()
        log_json = json.dumps(st.session_state.analysis_log, ensure_ascii=False, indent=2)
        st.download_button(
            "📥 分析ログをダウンロード",
            data=log_json,
            file_name=f"ocr_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

# メインエリア
if st.session_state.ocr_results:
    st.header("📊 OCR結果の検証")
    
    # タブ作成
    tab1, tab2, tab3 = st.tabs(["✅ 検証", "📈 分析", "🔧 デバッグ"])
    
    with tab1:
        st.markdown("### 各項目の検証")
        st.info("正しく認識できた項目にチェックを入れてください")
        
        # 検証フォーム
        validation = {}
        
        # カテゴリ別に表示
        categories = {
            'メイン数値': ['大当り回数', '初当り回数', '累計スタート'],
            '超中小': ['超', '中', '小'],
            '統計データ': ['スタート', '最高出玉', '最高一撃獲得'],
            'チャンス中': ['チャンス中大当り', 'チャンス中確率'],
            'その他': ['初回特賞スタート', '前日最終スタート']
        }
        
        for category, items in categories.items():
            st.markdown(f"#### {category}")
            cols = st.columns(len(items))
            
            for idx, item in enumerate(items):
                if item in st.session_state.ocr_results:
                    result = st.session_state.ocr_results[item]
                    with cols[idx]:
                        detected = result.get('detected', '-')
                        expected = result.get('expected', '-')
                        
                        # 表示
                        st.metric(item, detected)
                        st.caption(f"期待値: {expected}")
                        
                        # チェックボックス
                        is_correct = st.checkbox(
                            "正しい",
                            key=f"check_{item}",
                            value=(detected == expected)
                        )
                        validation[item] = {
                            'correct': is_correct,
                            'detected': detected,
                            'expected': expected
                        }
        
        # 検証結果を保存
        if st.button("💾 検証結果を保存", type="primary"):
            st.session_state.validation_results = validation
            
            # 分析ログに追加
            analysis_entry = {
                'timestamp': datetime.now().isoformat(),
                'validation': validation,
                'summary': {
                    'total': len(validation),
                    'correct': sum(1 for v in validation.values() if v['correct']),
                    'incorrect': sum(1 for v in validation.values() if not v['correct'])
                }
            }
            st.session_state.analysis_log.append(analysis_entry)
            st.success("検証結果を保存しました！")
    
    with tab2:
        st.markdown("### 📊 問題分析")
        
        if st.session_state.validation_results:
            # 統計表示
            total = len(st.session_state.validation_results)
            correct = sum(1 for v in st.session_state.validation_results.values() if v['correct'])
            incorrect = total - correct
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("全項目", total)
            with col2:
                st.metric("正解", correct, f"{(correct/total*100):.1f}%")
            with col3:
                st.metric("不正解", incorrect, f"{(incorrect/total*100):.1f}%")
            
            # 問題のある項目の分析
            st.divider()
            st.markdown("### 🔍 エラー分析")
            
            errors = {k: v for k, v in st.session_state.validation_results.items() if not v['correct']}
            
            if errors:
                for name, error_info in errors.items():
                    with st.expander(f"❌ {name}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**検出値:** {error_info['detected']}")
                            st.write(f"**期待値:** {error_info['expected']}")
                        
                        with col2:
                            # 領域情報
                            if name in st.session_state.ocr_results:
                                region = st.session_state.ocr_results[name]
                                st.write(f"**色:** {region.get('color', 'unknown')}")
                                st.write(f"**座標:** {region.get('bbox', 'unknown')}")
                        
                        # 問題の原因を推測
                        st.markdown("**可能性のある原因:**")
                        
                        if error_info['detected'] == '' or error_info['detected'] == '-':
                            st.write("- 領域が正しく設定されていない")
                            st.write("- 色抽出の閾値が不適切")
                            st.write("- 前処理が不十分")
                        else:
                            st.write("- 文字の一部が欠けている")
                            st.write("- PSMモードが不適切")
                            st.write("- ノイズの影響")
            else:
                st.success("すべての項目が正しく認識されました！")
            
            # 色別の成功率
            st.divider()
            st.markdown("### 🎨 色別成功率")
            
            color_stats = {}
            for name, result in st.session_state.validation_results.items():
                if name in st.session_state.ocr_results:
                    color = st.session_state.ocr_results[name].get('color', 'unknown')
                    if color not in color_stats:
                        color_stats[color] = {'correct': 0, 'total': 0}
                    color_stats[color]['total'] += 1
                    if result['correct']:
                        color_stats[color]['correct'] += 1
            
            for color, stats in color_stats.items():
                rate = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
                st.metric(
                    f"{color}色テキスト",
                    f"{stats['correct']}/{stats['total']}",
                    f"{rate:.1f}%"
                )
    
    with tab3:
        st.markdown("### 🔧 デバッグ情報")
        
        # OCR結果の生データ
        st.markdown("#### OCR結果（JSON）")
        st.json(st.session_state.ocr_results)
        
        # 検証結果
        if st.session_state.validation_results:
            st.markdown("#### 検証結果（JSON）")
            st.json(st.session_state.validation_results)
        
        # Claudeへの共有用データ
        st.markdown("#### 📤 Claudeへ共有するデータ")
        
        share_data = {
            'ocr_results': st.session_state.ocr_results,
            'validation': st.session_state.validation_results,
            'timestamp': datetime.now().isoformat()
        }
        
        share_json = json.dumps(share_data, ensure_ascii=False, indent=2)
        st.text_area(
            "このJSONをコピーしてClaudeに共有してください:",
            share_json,
            height=300
        )
        
        if st.button("📋 クリップボードにコピー"):
            st.code(share_json)
            st.info("上記のコードをコピーしてください")

else:
    st.info("👈 サイドバーから画像をアップロードしてOCRを実行してください")