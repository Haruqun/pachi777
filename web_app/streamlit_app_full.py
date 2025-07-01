#!/usr/bin/env python3
"""
パチンコグラフ解析システム - シンプル版
画像アップロード機能のみ
"""

import streamlit as st
from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import io

# ページ設定
st.set_page_config(
    page_title="パチンコグラフ解析 - シンプル版",
    page_icon="🎰",
    layout="wide"
)

# カスタムCSS
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    .upload-section {
        background-color: #f0f2f6;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .image-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1rem;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# タイトル
st.title("🎰 パチンコグラフ解析システム")
st.markdown("### シンプル版 - 画像アップロード")

# 説明文
st.markdown("""
このシステムは、パチンコの収支グラフを解析するためのツールです。
グラフ画像をアップロードすると、自動的に最適な範囲で切り抜きを行います。
""")

# セパレーター
st.markdown("---")

# メインコンテナ
main_container = st.container()

with main_container:
    # アップロードセクション
    st.markdown("### 📤 画像をアップロード")
    
    # ファイルアップローダー
    uploaded_files = st.file_uploader(
        "グラフ画像を選択してください",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        help="複数の画像を一度にアップロードできます（JPG, PNG形式）"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)}枚の画像がアップロードされました")
        
        # 切り抜き処理
        st.markdown("### ✂️ 切り抜き結果")
        
        # プログレスバー
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 切り抜き画像を格納するリスト
        cropped_images = []
        
        for idx, uploaded_file in enumerate(uploaded_files):
            # 進捗更新
            progress = (idx + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            status_text.text(f"処理中... ({idx + 1}/{len(uploaded_files)})")
            
            # 画像を読み込み
            image = Image.open(uploaded_file)
            img_array = np.array(image)
            height, width = img_array.shape[:2]
            
            # Pattern3: Zero Line Based の自動検出
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
            orange_bottom = 0
            
            # オレンジバーの検出
            for y in range(height//2):
                if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
                    orange_bottom = y
            
            # オレンジバーの下端を正確に見つける
            if orange_bottom > 0:
                for y in range(orange_bottom, min(orange_bottom + 100, height)):
                    if np.sum(orange_mask[y, :]) < width * 0.1 * 255:
                        orange_bottom = y
                        break
            else:
                orange_bottom = 150
            
            # ゼロライン検出
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            search_start = orange_bottom + 50
            search_end = min(height - 100, orange_bottom + 400)
            
            best_score = 0
            zero_line_y = (search_start + search_end) // 2
            
            for y in range(search_start, search_end):
                row = gray[y, 100:width-100]
                darkness = 1.0 - (np.mean(row) / 255.0)
                uniformity = 1.0 - (np.std(row) / 128.0)
                score = darkness * 0.5 + uniformity * 0.5
                
                if score > best_score:
                    best_score = score
                    zero_line_y = y
            
            # 切り抜き範囲を設定（最終調整値）
            top = max(0, zero_line_y - 246)  # 0ラインから上246px
            bottom = min(height, zero_line_y + 247)  # 0ラインから下247px
            left = 125  # 左右の余白125px
            right = width - 125  # 左右の余白125px
            
            # 切り抜き実行
            cropped_img = img_array[int(top):int(bottom), int(left):int(right)].copy()
            
            # グリッドラインを追加
            # 切り抜き画像の高さは493px（246+247）
            # 最上部が+30000、最下部が-30000なので、60000の範囲を493pxで表現
            # 1pxあたり約121.7玉
            crop_height = cropped_img.shape[0]
            zero_line_in_crop = zero_line_y - top  # 切り抜き画像内での0ライン位置
            
            # スケール計算（上下246,247pxで±30000）
            scale = 30000 / 246  # 約121.95玉/px
            
            # グリッドライン描画
            # +30000ライン（最上部）
            cv2.line(cropped_img, (0, 0), (cropped_img.shape[1], 0), (128, 128, 128), 2)
            cv2.putText(cropped_img, '+30000', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 2)
            
            # +20000ライン
            y_20k = int(zero_line_in_crop - (20000 / scale))
            if 0 < y_20k < crop_height:
                cv2.line(cropped_img, (0, y_20k), (cropped_img.shape[1], y_20k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '+20000', (10, y_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # +10000ライン
            y_10k = int(zero_line_in_crop - (10000 / scale))
            if 0 < y_10k < crop_height:
                cv2.line(cropped_img, (0, y_10k), (cropped_img.shape[1], y_10k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '+10000', (10, y_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # 0ライン
            y_0 = int(zero_line_in_crop)
            if 0 < y_0 < crop_height:
                cv2.line(cropped_img, (0, y_0), (cropped_img.shape[1], y_0), (255, 0, 0), 2)
                cv2.putText(cropped_img, '0', (10, y_0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            # -10000ライン
            y_minus_10k = int(zero_line_in_crop + (10000 / scale))
            if 0 < y_minus_10k < crop_height:
                cv2.line(cropped_img, (0, y_minus_10k), (cropped_img.shape[1], y_minus_10k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '-10000', (10, y_minus_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # -20000ライン
            y_minus_20k = int(zero_line_in_crop + (20000 / scale))
            if 0 < y_minus_20k < crop_height:
                cv2.line(cropped_img, (0, y_minus_20k), (cropped_img.shape[1], y_minus_20k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '-20000', (10, y_minus_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # -30000ライン（最下部）
            cv2.line(cropped_img, (0, crop_height - 1), (cropped_img.shape[1], crop_height - 1), (128, 128, 128), 2)
            cv2.putText(cropped_img, '-30000', (10, crop_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 2)
            
            # 切り抜き結果を保存
            cropped_images.append({
                'name': uploaded_file.name,
                'image': cropped_img,
                'size': (cropped_img.shape[1], cropped_img.shape[0]),
                'zero_line': zero_line_in_crop
            })
        
        # プログレスバーを完了状態に
        progress_bar.progress(1.0)
        status_text.text("✅ 処理完了！")
        
        # 切り抜き画像をグリッド表示
        st.markdown("### 📸 切り抜き画像一覧")
        
        # 3列のグリッドで表示
        cols = st.columns(3)
        for idx, crop_data in enumerate(cropped_images):
            col_idx = idx % 3
            with cols[col_idx]:
                # 画像表示
                st.image(
                    crop_data['image'],
                    caption=crop_data['name'],
                    use_column_width=True
                )
                
                # 画像情報
                st.caption(f"サイズ: {crop_data['size'][0]}×{crop_data['size'][1]}px")
                
                # ダウンロードボタン
                # OpenCVのBGRからRGBに変換（必要な場合）
                cropped_pil = Image.fromarray(crop_data['image'])
                
                # バイトストリームに保存
                buf = io.BytesIO()
                cropped_pil.save(buf, format='PNG')
                byte_im = buf.getvalue()
                
                st.download_button(
                    label="ダウンロード",
                    data=byte_im,
                    file_name=f"cropped_{crop_data['name']}",
                    mime="image/png",
                    key=f"download_{idx}"
                )
        
        # 一括ダウンロード機能
        st.markdown("---")
        st.markdown("### 📦 一括ダウンロード")
        
        # ZIPファイルを作成
        import zipfile
        from datetime import datetime
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, crop_data in enumerate(cropped_images):
                # 画像をPNGとして保存
                img_buffer = io.BytesIO()
                cropped_pil = Image.fromarray(crop_data['image'])
                cropped_pil.save(img_buffer, format='PNG')
                
                # ZIPに追加
                zip_file.writestr(
                    f"cropped_{crop_data['name']}",
                    img_buffer.getvalue()
                )
        
        # ダウンロードボタン
        st.download_button(
            label="🗜️ すべての切り抜き画像をZIPでダウンロード",
            data=zip_buffer.getvalue(),
            file_name=f"cropped_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip"
        )
        
    else:
        # アップロード前の表示
        st.info("👆 上のボタンから画像をアップロードしてください")
        
        # 使い方
        with st.expander("💡 使い方"):
            st.markdown("""
            1. **「Browse files」ボタン**をクリック
            2. **グラフ画像を選択**（複数選択可）
            3. **自動的に切り抜きが実行されます**
            
            対応フォーマット:
            - JPG/JPEG
            - PNG
            
            切り抜き設定:
            - 0ラインを自動検出
            - 0ラインから上246px、下247px
            - 左右125pxの余白を除外
            """)

# フッター
st.markdown("---")
footer_col1, footer_col2 = st.columns([2, 1])

with footer_col1:
    st.markdown("パチンコグラフ解析システム v2.0")
    
with footer_col2:
    st.markdown(
        f"<div style='text-align: right'>更新日: {datetime.now().strftime('%Y/%m/%d')}</div>",
        unsafe_allow_html=True
    )