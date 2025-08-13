import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image

st.set_page_config(
    page_title="赤色テキスト検出専用デバッガー",
    page_icon="🔴",
    layout="wide"
)

st.title("🔴 赤色テキスト検出専用デバッガー")
st.markdown("大当り回数（25）と超中小の検出問題を解決")

# 赤色検出の複数アプローチ
def extract_red_method1(roi):
    """方法1: HSV標準範囲"""
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # 赤色の2つの範囲
    mask1 = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([170, 50, 50]), np.array([180, 255, 255]))
    return cv2.bitwise_or(mask1, mask2)

def extract_red_method2(roi):
    """方法2: HSV拡張範囲（より広い赤）"""
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0, 20, 20]), np.array([30, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([150, 20, 20]), np.array([180, 255, 255]))
    return cv2.bitwise_or(mask1, mask2)

def extract_red_method3(roi):
    """方法3: RGB直接比較"""
    b, g, r = cv2.split(roi)
    # 赤が最も強く、他の色より明確に大きい
    mask = np.zeros_like(r)
    mask[(r > 100) & (r > g * 1.5) & (r > b * 1.5)] = 255
    return mask

def extract_red_method4(roi):
    """方法4: RGB差分方式"""
    b, g, r = cv2.split(roi)
    # 赤から他の色を引く
    red_dominance = np.clip(r.astype(int) - np.maximum(g, b).astype(int), 0, 255).astype(np.uint8)
    _, mask = cv2.threshold(red_dominance, 30, 255, cv2.THRESH_BINARY)
    return mask

def extract_red_method5(roi):
    """方法5: LAB色空間でa成分（赤-緑軸）"""
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    l, a, b_channel = cv2.split(lab)
    # a成分が高い = 赤方向
    _, mask = cv2.threshold(a, 135, 255, cv2.THRESH_BINARY)
    return mask

def extract_red_method6(roi):
    """方法6: YCrCb色空間でCr成分"""
    ycrcb = cv2.cvtColor(roi, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    # Cr成分が高い = 赤
    _, mask = cv2.threshold(cr, 140, 255, cv2.THRESH_BINARY)
    return mask

def extract_red_method7(roi):
    """方法7: HSVのS（彩度）も考慮"""
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # 彩度が高い赤
    mask1 = cv2.inRange(hsv, np.array([0, 100, 50]), np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([170, 100, 50]), np.array([180, 255, 255]))
    return cv2.bitwise_or(mask1, mask2)

def extract_red_method8(roi):
    """方法8: 複合条件（HSV + RGB）"""
    # HSVで大まかに赤を抽出
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask_hsv1 = cv2.inRange(hsv, np.array([0, 30, 30]), np.array([20, 255, 255]))
    mask_hsv2 = cv2.inRange(hsv, np.array([160, 30, 30]), np.array([180, 255, 255]))
    mask_hsv = cv2.bitwise_or(mask_hsv1, mask_hsv2)
    
    # RGBでも確認
    b, g, r = cv2.split(roi)
    mask_rgb = np.zeros_like(r)
    mask_rgb[(r > 80) & (r > g * 1.3) & (r > b * 1.3)] = 255
    
    # 両方の条件を満たす
    return cv2.bitwise_and(mask_hsv, mask_rgb)

# 画像アップロード
uploaded_file = st.file_uploader("画像をアップロード", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    # 画像読み込み
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
        height, width = img_bgr.shape[:2]
    
    # 赤色テキストの領域定義
    red_regions = {
        '大当り回数（25）': {
            'bbox': (128, 636, 287, 741),
            'expected': '25',
            'psm': 8
        },
        '超（21）': {
            'bbox': (106, 908, 163, 951),
            'expected': '21',
            'psm': 8
        },
        '中（0）': {
            'bbox': (208, 908, 237, 952),
            'expected': '0',
            'psm': 10
        },
        '小（4）': {
            'bbox': (275, 908, 307, 951),
            'expected': '4',
            'psm': 10
        }
    }
    
    # 抽出方法リスト
    methods = [
        ("HSV標準", extract_red_method1),
        ("HSV拡張", extract_red_method2),
        ("RGB比較", extract_red_method3),
        ("RGB差分", extract_red_method4),
        ("LAB-a成分", extract_red_method5),
        ("YCrCb-Cr成分", extract_red_method6),
        ("HSV高彩度", extract_red_method7),
        ("複合条件", extract_red_method8)
    ]
    
    # 各領域のテスト
    for region_name, region_info in red_regions.items():
        st.divider()
        st.header(f"🎯 {region_name}")
        
        x1, y1, x2, y2 = region_info['bbox']
        
        # パディング追加
        padding = 10
        y1_pad = max(0, y1 - padding)
        y2_pad = min(height, y2 + padding)
        x1_pad = max(0, x1 - padding)
        x2_pad = min(width, x2 + padding)
        
        roi = img_bgr[y1_pad:y2_pad, x1_pad:x2_pad]
        
        # 元画像と情報
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB), caption="元画像", width=200)
            
            # 色情報分析
            b_mean = np.mean(roi[:,:,0])
            g_mean = np.mean(roi[:,:,1])
            r_mean = np.mean(roi[:,:,2])
            st.caption(f"RGB平均: R={r_mean:.0f}, G={g_mean:.0f}, B={b_mean:.0f}")
            
            hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            h_mean = np.mean(hsv_roi[:,:,0])
            s_mean = np.mean(hsv_roi[:,:,1])
            v_mean = np.mean(hsv_roi[:,:,2])
            st.caption(f"HSV平均: H={h_mean:.0f}, S={s_mean:.0f}, V={v_mean:.0f}")
        
        with col2:
            st.write(f"**期待値:** {region_info['expected']}")
            st.write(f"**座標:** {region_info['bbox']}")
            st.write(f"**PSM:** {region_info['psm']}")
        
        # 各方法のテスト
        st.subheader("検出方法の比較")
        
        # 4列×2行で表示
        for i in range(0, len(methods), 4):
            cols = st.columns(4)
            for j in range(min(4, len(methods) - i)):
                method_name, method_func = methods[i + j]
                
                with cols[j]:
                    st.markdown(f"**{method_name}**")
                    
                    try:
                        # マスク生成
                        mask = method_func(roi)
                        
                        # ノイズ除去
                        kernel = np.ones((2,2), np.uint8)
                        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                        
                        # マスク表示
                        st.image(mask, caption="マスク", width=150)
                        
                        # OCR実行（複数の設定を試す）
                        results = []
                        
                        # 設定1: 白背景に黒文字
                        mask_inv = cv2.bitwise_not(mask)
                        config = f'--psm {region_info["psm"]} -c tessedit_char_whitelist=0123456789'
                        text1 = pytesseract.image_to_string(mask_inv, config=config).strip()
                        if text1:
                            results.append(text1)
                        
                        # 設定2: そのまま
                        text2 = pytesseract.image_to_string(mask, config=config).strip()
                        if text2:
                            results.append(text2)
                        
                        # 結果表示
                        if region_info['expected'] in results:
                            st.success(f"✅ {region_info['expected']}")
                        elif results:
                            st.warning(f"⚠️ {', '.join(results)}")
                        else:
                            st.error("❌ 失敗")
                            
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    # 総合結果
    st.divider()
    st.header("📊 分析結果")
    
    # 推奨事項
    st.info("""
    **赤色テキストが検出できない原因と対策:**
    
    1. **色の範囲が狭すぎる** → HSV範囲を拡張
    2. **ノイズの影響** → モルフォロジー処理を追加
    3. **PSM設定が不適切** → 単一数字はPSM 10、複数数字はPSM 8
    4. **前処理不足** → コントラスト強調、シャープ化を追加
    5. **赤色の定義が不正確** → RGB/HSV/LAB等の複数色空間で確認
    """)
    
    # デバッグ用コード生成
    if st.button("🔧 最適な検出コードを生成"):
        code = """
# 赤色テキスト検出の最適化コード
def extract_red_text_optimized(roi):
    # 複数の色空間で赤を検出
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    
    # HSVで赤色検出（広い範囲）
    mask1 = cv2.inRange(hsv, np.array([0, 20, 20]), np.array([30, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([150, 20, 20]), np.array([180, 255, 255]))
    mask_hsv = cv2.bitwise_or(mask1, mask2)
    
    # RGB条件も追加
    b, g, r = cv2.split(roi)
    mask_rgb = np.zeros_like(r)
    mask_rgb[(r > 80) & (r > g * 1.3) & (r > b * 1.3)] = 255
    
    # 結合
    mask = cv2.bitwise_or(mask_hsv, mask_rgb)
    
    # ノイズ除去
    kernel = np.ones((2,2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    return mask
"""
        st.code(code, language='python')