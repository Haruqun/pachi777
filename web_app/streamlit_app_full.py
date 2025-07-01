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
        
        # グリッドライン調整UI
        with st.expander("⚙️ グリッドライン位置調整", expanded=False):
            st.markdown("各グリッドラインの位置を微調整できます（ピクセル単位）")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**プラス側**")
                adjust_30k = st.number_input("+30000ライン調整", -5, 5, -1, 1, key="adj_30k")
                adjust_20k = st.number_input("+20000ライン調整", -5, 5, -2, 1, key="adj_20k")
                adjust_10k = st.number_input("+10000ライン調整", -5, 5, -1, 1, key="adj_10k")
            
            with col2:
                st.markdown("**マイナス側**")
                adjust_0 = st.number_input("0ライン調整", -5, 5, 0, 1, key="adj_0")
                adjust_minus_10k = st.number_input("-10000ライン調整", -5, 5, 1, 1, key="adj_minus_10k")
                adjust_minus_20k = st.number_input("-20000ライン調整", -5, 5, 1, 1, key="adj_minus_20k")
                adjust_minus_30k = st.number_input("-30000ライン調整", -5, 5, 2, 1, key="adj_minus_30k")
        
        # 切り抜き処理
        st.markdown("### ✂️ 切り抜き結果")
        
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
            
            # グリッドライン描画
            # +30000ライン（最上部）
            y_30k = 0 + st.session_state.get('adj_30k', 0)
            cv2.line(cropped_img, (0, y_30k), (cropped_img.shape[1], y_30k), (128, 128, 128), 2)
            cv2.putText(cropped_img, '+30000', (10, max(20, y_30k + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 2)
            
            # +20000ライン
            y_20k = int(zero_line_in_crop - (20000 / scale)) + st.session_state.get('adj_20k', 0)
            if 0 < y_20k < crop_height:
                cv2.line(cropped_img, (0, y_20k), (cropped_img.shape[1], y_20k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '+20000', (10, y_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # +10000ライン
            y_10k = int(zero_line_in_crop - (10000 / scale)) + st.session_state.get('adj_10k', 0)
            if 0 < y_10k < crop_height:
                cv2.line(cropped_img, (0, y_10k), (cropped_img.shape[1], y_10k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '+10000', (10, y_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # 0ライン
            y_0 = int(zero_line_in_crop) + st.session_state.get('adj_0', 0)
            if 0 < y_0 < crop_height:
                cv2.line(cropped_img, (0, y_0), (cropped_img.shape[1], y_0), (255, 0, 0), 2)
                cv2.putText(cropped_img, '0', (10, y_0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            # -10000ライン
            y_minus_10k = int(zero_line_in_crop + (10000 / scale)) + st.session_state.get('adj_minus_10k', 0)
            if 0 < y_minus_10k < crop_height:
                cv2.line(cropped_img, (0, y_minus_10k), (cropped_img.shape[1], y_minus_10k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '-10000', (10, y_minus_10k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # -20000ライン
            y_minus_20k = int(zero_line_in_crop + (20000 / scale)) + st.session_state.get('adj_minus_20k', 1)  # デフォルト1px下
            if 0 < y_minus_20k < crop_height:
                cv2.line(cropped_img, (0, y_minus_20k), (cropped_img.shape[1], y_minus_20k), (128, 128, 128), 1)
                cv2.putText(cropped_img, '-20000', (10, y_minus_20k - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
            
            # -30000ライン（最下部）
            y_minus_30k = crop_height - 1 + st.session_state.get('adj_minus_30k', 0)
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
                
                # PILを使用して日本語を描画
                # OpenCV画像をPIL画像に変換
                overlay_pil = Image.fromarray(cv2.cvtColor(overlay_img, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(overlay_pil)
                
                # 日本語フォントを設定
                try:
                    if platform.system() == 'Darwin':  # macOS
                        font_path = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
                        font = ImageFont.truetype(font_path, 16)
                        font_small = ImageFont.truetype(font_path, 14)
                    else:
                        # Windows/Linux
                        font = ImageFont.load_default()
                        font_small = font
                except:
                    font = ImageFont.load_default()
                    font_small = font
                
                # 横線を描画（最低値、最高値、現在値、初当たり値）
                # 最高値ライン
                max_y = int(zero_line_in_crop - (max_val / analyzer.scale))
                if 0 <= max_y < overlay_img.shape[0]:
                    draw.line([(0, max_y), (overlay_img.shape[1], max_y)], fill=(255, 255, 0), width=1)
                    draw.text((10, max_y - 20), f'最高値: {int(max_val):,}', fill=(255, 255, 0), font=font_small)
                
                # 最低値ライン
                min_y = int(zero_line_in_crop - (min_val / analyzer.scale))
                if 0 <= min_y < overlay_img.shape[0]:
                    draw.line([(0, min_y), (overlay_img.shape[1], min_y)], fill=(255, 0, 255), width=1)
                    draw.text((10, min_y + 5), f'最低値: {int(min_val):,}', fill=(255, 0, 255), font=font_small)
                
                # 現在値ライン
                current_y = int(zero_line_in_crop - (current_val / analyzer.scale))
                if 0 <= current_y < overlay_img.shape[0]:
                    draw.line([(overlay_img.shape[1] - 50, current_y), (overlay_img.shape[1], current_y)], fill=(0, 255, 255), width=2)
                    draw.text((overlay_img.shape[1] - 150, current_y - 20), f'現在値: {int(current_val):,}', fill=(0, 255, 255), font=font_small)
                
                # 初当たり値ライン
                if first_hit_x is not None:
                    first_hit_y = int(zero_line_in_crop - (first_hit_val / analyzer.scale))
                    if 0 <= first_hit_y < overlay_img.shape[0]:
                        # 縦線を描画
                        draw.line([(first_hit_x, 0), (first_hit_x, overlay_img.shape[0])], fill=(0, 255, 0), width=1)
                        draw.text((first_hit_x + 5, 20), f'初当たり: {int(first_hit_val):,}', fill=(0, 255, 0), font=font_small)
                
                # PIL画像をOpenCV画像に戻す
                overlay_img = cv2.cvtColor(np.array(overlay_pil), cv2.COLOR_RGB2BGR)
                
                # 画像を横幅いっぱいで表示
                st.image(overlay_img, use_column_width=True)
                
                # 解析成功メッセージ
                st.success("✅ グラフ解析が完了しました！")
            else:
                # 解析失敗時は元画像を表示
                st.image(cropped_img, use_column_width=True)
                st.warning("⚠️ グラフデータを検出できませんでした")
        
        # 画像情報とダウンロード
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.info(f"📐 サイズ: {cropped_img.shape[1]}×{cropped_img.shape[0]}px")
        
        with col2:
            # グリッドライン表示/非表示トグル
            show_grid = st.checkbox("グリッドラインを表示", value=True, key="show_grid")
            if not show_grid:
                # グリッドラインなしの画像を再生成
                cropped_img_no_grid = img_array[int(top):int(bottom), int(left):int(right)].copy()
                st.rerun()
        
        with col3:
            # ダウンロードボタン
            cropped_pil = Image.fromarray(cropped_img)
            buf = io.BytesIO()
            cropped_pil.save(buf, format='PNG')
            byte_im = buf.getvalue()
            
            st.download_button(
                label="⬇️ ダウンロード",
                data=byte_im,
                file_name=f"cropped_{uploaded_file.name}",
                mime="image/png"
            )
        
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
            
            # グラフを可視化
            st.markdown("#### 📊 解析結果グラフ")
            
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')
            
            # 日本語フォント設定
            if platform.system() == 'Darwin':  # macOS
                plt.rcParams['font.family'] = 'Hiragino Sans GB'
            else:
                plt.rcParams['font.family'] = ['DejaVu Sans', 'sans-serif']
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # グラフをプロット
            x_values = [x for x, _ in graph_data_points]
            ax.plot(x_values, graph_values, linewidth=2, color='green')
            
            # グリッドラインを追加
            ax.axhline(y=0, color='blue', linestyle='-', linewidth=2, alpha=0.7)
            ax.axhline(y=10000, color='gray', linestyle='--', alpha=0.5)
            ax.axhline(y=20000, color='gray', linestyle='--', alpha=0.5)
            ax.axhline(y=30000, color='gray', linestyle='--', alpha=0.5)
            ax.axhline(y=-10000, color='gray', linestyle='--', alpha=0.5)
            ax.axhline(y=-20000, color='gray', linestyle='--', alpha=0.5)
            ax.axhline(y=-30000, color='gray', linestyle='--', alpha=0.5)
            
            # 軸の設定
            ax.set_ylim(-35000, 35000)
            ax.set_xlabel('X座標（ピクセル）')
            ax.set_ylabel('収支（玉）')
            ax.set_title('パチンコ収支グラフ解析結果')
            ax.grid(True, alpha=0.3)
            
            # Y軸のフォーマット
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
            
            plt.tight_layout()
            st.pyplot(fig)
            
            # データをダウンロード可能にする
            st.markdown("#### 💾 データダウンロード")
            
            # CSVデータを作成
            csv_data = "X座標,収支（玉）\n"
            for i, value in enumerate(graph_values):
                csv_data += f"{i},{value}\n"
            
            st.download_button(
                label="📄 CSVファイルをダウンロード",
                data=csv_data,
                file_name=f"graph_data_{uploaded_file.name.split('.')[0]}.csv",
                mime="text/csv"
            )
        
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