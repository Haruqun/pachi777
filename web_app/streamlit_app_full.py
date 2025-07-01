#!/usr/bin/env python3
"""
パチンコグラフ解析システム - シンプル版
画像アップロード機能のみ
"""

import streamlit as st
from datetime import datetime
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
from web_analyzer import WebCompatibleAnalyzer
import platform

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
    uploaded_file = st.file_uploader(
        "グラフ画像を選択してください",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=False,
        help="グラフ画像をアップロードしてください（JPG, PNG形式）"
    )
    
    if uploaded_file:
        st.success(f"✅ 画像がアップロードされました: {uploaded_file.name}")
        
        # 切り抜き処理
        st.markdown("### ✂️ 解析結果")
        
        # 画像処理
        with st.spinner('画像を処理中...'):
            
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
            
            # グリッドライン描画（固定値）
            # +30000ライン（最上部）
            y_30k = -1  # 固定調整値
            cv2.line(cropped_img, (0, y_30k), (cropped_img.shape[1], y_30k), (128, 128, 128), 2)
            cv2.putText(cropped_img, '+30000', (10, max(20, y_30k + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 2)
            
            # +20000ライン
            y_20k = int(zero_line_in_crop - (20000 / scale)) - 2  # 固定調整値
            if 0 < y_20k < crop_height:
                cv2.line(cropped_img, (0, y_20k), (cropped_img.shape[1], y_20k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '+20000', (10, y_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # +10000ライン
            y_10k = int(zero_line_in_crop - (10000 / scale)) - 1  # 固定調整値
            if 0 < y_10k < crop_height:
                cv2.line(cropped_img, (0, y_10k), (cropped_img.shape[1], y_10k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '+10000', (10, y_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # 0ライン
            y_0 = int(zero_line_in_crop)  # 調整なし
            if 0 < y_0 < crop_height:
                cv2.line(cropped_img, (0, y_0), (cropped_img.shape[1], y_0), (255, 0, 0), 2)
                cv2.putText(cropped_img, '0', (10, y_0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            # -10000ライン
            y_minus_10k = int(zero_line_in_crop + (10000 / scale)) + 1  # 固定調整値
            if 0 < y_minus_10k < crop_height:
                cv2.line(cropped_img, (0, y_minus_10k), (cropped_img.shape[1], y_minus_10k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '-10000', (10, y_minus_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # -20000ライン
            y_minus_20k = int(zero_line_in_crop + (20000 / scale)) + 1  # 固定調整値
            if 0 < y_minus_20k < crop_height:
                cv2.line(cropped_img, (0, y_minus_20k), (cropped_img.shape[1], y_minus_20k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '-20000', (10, y_minus_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # -30000ライン（最下部）
            y_minus_30k = crop_height - 1 + 2  # 固定調整値
            y_minus_30k = min(max(0, y_minus_30k), crop_height - 1)  # 画像範囲内に制限
            cv2.line(cropped_img, (0, y_minus_30k), (cropped_img.shape[1], y_minus_30k), (128, 128, 128), 2)
            cv2.putText(cropped_img, '-30000', (10, max(10, y_minus_30k - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 2)
            
        # 解析を自動実行
        with st.spinner("グラフを解析中..."):
            # アナライザーを初期化
            analyzer = WebCompatibleAnalyzer()
            
            # グリッドラインなしの画像を使用
            analysis_img = img_array[int(top):int(bottom), int(left):int(right)].copy()
            
            # 0ラインの位置を設定
            analyzer.zero_y = zero_line_in_crop
            analyzer.scale = 30000 / 246  # スケール設定
            
            # グラフデータを抽出
            graph_data_points, dominant_color, _ = analyzer.extract_graph_data(analysis_img)
            
            if graph_data_points:
                # データポイントから値のみを抽出
                graph_values = [value for x, value in graph_data_points]
                
                # 統計情報を計算
                max_val = max(graph_values)
                min_val = min(graph_values)
                current_val = graph_values[-1] if graph_values else 0
                
                # 初当たり値を探す（最初にプラスになったポイント）
                first_hit_val = 0
                first_hit_x = None
                for i, val in enumerate(graph_values):
                    if val > 0:
                        first_hit_val = val
                        first_hit_x = i
                        break
                
                # オーバーレイ画像を作成
                overlay_img = cropped_img.copy()
                
                # 検出されたグラフラインを描画
                prev_x = None
                prev_y = None
                
                # 色の設定（検出色に応じて変更）
                color_map = {
                    'green': (0, 255, 0),
                    'red': (0, 0, 255),
                    'blue': (255, 0, 0),
                    'yellow': (0, 255, 255),
                    'cyan': (255, 255, 0),
                    'magenta': (255, 0, 255),
                    'orange': (0, 165, 255),
                    'pink': (203, 192, 255),
                    'purple': (255, 0, 255)
                }
                draw_color = color_map.get(dominant_color, (0, 255, 0))
                
                # グラフポイントを描画
                for x, value in graph_data_points:
                    # Y座標を計算（0ラインからの相対位置）
                    y = int(zero_line_in_crop - (value / analyzer.scale))
                    
                    # 画像範囲内かチェック
                    if 0 <= y < overlay_img.shape[0] and 0 <= x < overlay_img.shape[1]:
                        # 点を描画（より見やすくするため）
                        cv2.circle(overlay_img, (int(x), y), 2, draw_color, -1)
                        
                        # 線で接続
                        if prev_x is not None and prev_y is not None:
                            cv2.line(overlay_img, (int(prev_x), int(prev_y)), (int(x), y), draw_color, 2)
                        
                        prev_x = x
                        prev_y = y
                
                # 横線を描画（最低値、最高値、現在値、初当たり値）
                # 最高値ライン
                max_y = int(zero_line_in_crop - (max_val / analyzer.scale))
                if 0 <= max_y < overlay_img.shape[0]:
                    cv2.line(overlay_img, (0, max_y), (overlay_img.shape[1], max_y), (0, 255, 255), 1)
                    # 背景付きテキスト（白背景、濃い黄色文字）
                    text = f'MAX: {int(max_val):,}'
                    cv2.rectangle(overlay_img, (10, max_y - 25), (150, max_y - 5), (255, 255, 255), -1)
                    cv2.putText(overlay_img, text, (15, max_y - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 150), 2, cv2.LINE_AA)
                
                # 最低値ライン
                min_y = int(zero_line_in_crop - (min_val / analyzer.scale))
                if 0 <= min_y < overlay_img.shape[0]:
                    cv2.line(overlay_img, (0, min_y), (overlay_img.shape[1], min_y), (255, 0, 255), 1)
                    # 背景付きテキスト（白背景、濃いマゼンタ文字）
                    text = f'MIN: {int(min_val):,}'
                    cv2.rectangle(overlay_img, (10, min_y + 5), (150, min_y + 25), (255, 255, 255), -1)
                    cv2.putText(overlay_img, text, (15, min_y + 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 0, 150), 2, cv2.LINE_AA)
                
                # 現在値ライン
                current_y = int(zero_line_in_crop - (current_val / analyzer.scale))
                if 0 <= current_y < overlay_img.shape[0]:
                    cv2.line(overlay_img, (overlay_img.shape[1] - 50, current_y), (overlay_img.shape[1], current_y), (255, 255, 0), 2)
                    # 背景付きテキスト（白背景、濃いシアン文字）
                    text = f'CURRENT: {int(current_val):,}'
                    text_width = 160
                    cv2.rectangle(overlay_img, (overlay_img.shape[1] - text_width - 10, current_y - 25), 
                                 (overlay_img.shape[1] - 10, current_y - 5), (255, 255, 255), -1)
                    cv2.putText(overlay_img, text, (overlay_img.shape[1] - text_width - 5, current_y - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 0), 2, cv2.LINE_AA)
                
                # 初当たり値（垂直線と横線）
                if first_hit_x is not None:
                    # 初当たりのx座標を取得
                    first_hit_x_coord = None
                    for i, (x, value) in enumerate(graph_data_points):
                        if value > 0:
                            first_hit_x_coord = x
                            break
                    
                    if first_hit_x_coord is not None:
                        first_hit_y = int(zero_line_in_crop - (first_hit_val / analyzer.scale))
                        
                        # 垂直線を描画（初当たり位置）
                        cv2.line(overlay_img, (first_hit_x_coord, 0), (first_hit_x_coord, overlay_img.shape[0]), (155, 48, 255), 2)
                        
                        # 横線も描画
                        if 0 <= first_hit_y < overlay_img.shape[0]:
                            cv2.line(overlay_img, (0, first_hit_y), (overlay_img.shape[1], first_hit_y), (155, 48, 255), 1)
                        
                        # 背景付きテキスト（白背景、紫文字）
                        text = f'FIRST HIT: {int(first_hit_val):,}'
                        text_y = 30
                        if first_hit_x_coord < overlay_img.shape[1] // 2:
                            # 左側の場合は右にテキスト配置
                            cv2.rectangle(overlay_img, (first_hit_x_coord + 5, text_y - 20), 
                                         (first_hit_x_coord + 165, text_y), (255, 255, 255), -1)
                            cv2.putText(overlay_img, text, (first_hit_x_coord + 10, text_y - 5), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 0, 150), 2, cv2.LINE_AA)
                        else:
                            # 右側の場合は左にテキスト配置
                            cv2.rectangle(overlay_img, (first_hit_x_coord - 165, text_y - 20), 
                                         (first_hit_x_coord - 5, text_y), (255, 255, 255), -1)
                            cv2.putText(overlay_img, text, (first_hit_x_coord - 160, text_y - 5), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 0, 150), 2, cv2.LINE_AA)
                
                # 画像を横幅いっぱいで表示
                st.image(overlay_img, use_column_width=True)
                
                # 解析成功メッセージ
                st.success("✅ グラフ解析が完了しました！")
            else:
                # 解析失敗時は元画像を表示
                st.image(cropped_img, use_column_width=True)
                st.warning("⚠️ グラフデータを検出できませんでした")
        
        # 詳細解析セクション
        if graph_data_points:
            st.markdown("---")
            st.markdown("### 📈 詳細解析")
            
            # 統計情報を表示
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("最高値", f"{int(max_val):,}玉")
            
            with col2:
                st.metric("最低値", f"{int(min_val):,}玉")
            
            with col3:
                st.metric("現在値", f"{int(current_val):,}玉")
            
            with col4:
                st.metric("初当たり", f"{int(first_hit_val):,}玉" if first_hit_x else "なし")
            
            with col5:
                st.metric("検出色", dominant_color)
        
    else:
        # アップロード前の表示
        st.info("👆 上のボタンから画像をアップロードしてください")
        
        # 使い方
        with st.expander("💡 使い方"):
            st.markdown("""
            1. **「Browse files」ボタン**をクリック
            2. **グラフ画像を選択**
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