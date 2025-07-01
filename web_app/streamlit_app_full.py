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

# Tailwind風カスタムCSS
st.markdown("""
<style>
    /* グローバルスタイル */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        min-height: 100vh;
    }
    
    /* メインコンテナ */
    .main > div {
        padding: 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* タイトル */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem !important;
    }
    
    /* サブタイトル */
    h3 {
        color: #4a5568;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    
    /* カードスタイル */
    .stExpander {
        background: white;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 1rem;
        border: none;
    }
    
    /* ファイルアップローダー */
    .stFileUploader {
        background: white;
        padding: 2rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 2px dashed #cbd5e0;
        transition: all 0.3s ease;
    }
    
    .stFileUploader:hover {
        border-color: #667eea;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    /* メトリックス */
    [data-testid="metric-container"] {
        background: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease;
    }
    
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    /* メトリックラベル */
    [data-testid="metric-container"] label {
        color: #718096;
        font-size: 0.875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* メトリック値 */
    [data-testid="metric-container"] > div:nth-child(2) {
        font-size: 1.875rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* 成功メッセージ */
    .stSuccess {
        background-color: #f0fdf4;
        border: 1px solid #86efac;
        border-radius: 0.5rem;
        padding: 1rem;
        color: #166534;
        font-weight: 500;
    }
    
    /* 警告メッセージ */
    .stWarning {
        background-color: #fef3c7;
        border: 1px solid #fcd34d;
        border-radius: 0.5rem;
        padding: 1rem;
        color: #92400e;
        font-weight: 500;
    }
    
    /* スピナー */
    .stSpinner > div {
        color: #667eea;
    }
    
    /* 区切り線 */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, #cbd5e0, transparent);
        margin: 2rem 0;
    }
    
    /* フッター */
    .footer-text {
        color: #718096;
        font-size: 0.875rem;
        text-align: center;
        margin-top: 3rem;
        padding: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# タイトルセクション
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h1 style="font-size: 3rem; margin-bottom: 0.5rem;">🎰 パチンコグラフ解析システム</h1>
    <p style="color: #718096; font-size: 1.125rem; margin-top: 0;">グラフ画像を瞬時に解析し、収支データを可視化</p>
</div>
""", unsafe_allow_html=True)

# 機能紹介カード
st.markdown("""
<div style="background: white; padding: 1.5rem; border-radius: 0.75rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 2rem;">
    <h4 style="color: #4a5568; margin-bottom: 1rem; font-weight: 600;">🚀 主な機能</h4>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
        <div style="padding: 1rem; background: #f7fafc; border-radius: 0.5rem;">
            <span style="font-size: 1.5rem;">📈</span>
            <h5 style="margin: 0.5rem 0; color: #2d3748;">AIグラフ解析</h5>
            <p style="color: #718096; font-size: 0.875rem;">AIがグラフを自動認識し、正確なデータを抽出</p>
        </div>
        <div style="padding: 1rem; background: #f7fafc; border-radius: 0.5rem;">
            <span style="font-size: 1.5rem;">✂️</span>
            <h5 style="margin: 0.5rem 0; color: #2d3748;">自動切り抜き</h5>
            <p style="color: #718096; font-size: 0.875rem;">グラフ領域を自動検出して最適化</p>
        </div>
        <div style="padding: 1rem; background: #f7fafc; border-radius: 0.5rem;">
            <span style="font-size: 1.5rem;">💡</span>
            <h5 style="margin: 0.5rem 0; color: #2d3748;">統計分析</h5>
            <p style="color: #718096; font-size: 0.875rem;">最高値、最低値、初当たり等を瞬時に計算</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# セパレーター
st.markdown("---")

# メインコンテナ
main_container = st.container()

with main_container:
    # アップロードセクション
    st.markdown("""
    <h3 style="color: #4a5568; font-weight: 600; margin-bottom: 1rem;">
        <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">📤</span> 
        画像をアップロード
    </h3>
    """, unsafe_allow_html=True)
    
    # ファイルアップローダー
    uploaded_files = st.file_uploader(
        "グラフ画像を選択してください",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        help="複数の画像を一度にアップロードできます（JPG, PNG形式）"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)}枚の画像がアップロードされました")
        
        # 解析結果セクション
        st.markdown("""
        <h3 style="color: #4a5568; font-weight: 600; margin-top: 2rem; margin-bottom: 1rem;">
            <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🎯</span> 
            解析結果
        </h3>
        """, unsafe_allow_html=True)
        
        # プログレスバー
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 解析結果を格納
        analysis_results = []
        
        # 各画像を処理
        for idx, uploaded_file in enumerate(uploaded_files):
            # 進捗更新
            progress = (idx + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            status_text.text(f'処理中... ({idx + 1}/{len(uploaded_files)})')
            
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
                
                # 初当たり値を探す（production版と同じロジック）
                first_hit_val = 0
                first_hit_x = None
                min_payout = 100  # 最低払い出し玉数
                
                # 方法1: 100玉以上の急激な増加を検出
                for i in range(1, min(len(graph_values)-2, 150)):  # 最大150点まで探索
                    current_increase = graph_values[i+1] - graph_values[i]
                    
                    # 100玉以上の増加を検出
                    if current_increase > min_payout:
                        # 次の点も上昇または維持していることを確認（ノイズ除外）
                        if graph_values[i+2] >= graph_values[i+1] - 50:
                            # 初当たりは必ずマイナス値から
                            if graph_values[i] < 0:
                                first_hit_val = graph_values[i]
                                first_hit_x = i
                                break
                
                # 方法2: 減少傾向からの急上昇を検出
                if first_hit_x is None:
                    window_size = 5
                    for i in range(window_size, len(graph_values)-1):
                        # 過去の傾向を計算
                        past_window = graph_values[max(0, i-window_size):i]
                        if len(past_window) >= 2:
                            avg_slope = (past_window[-1] - past_window[0]) / len(past_window)
                            
                            # 現在の変化
                            current_change = graph_values[i+1] - graph_values[i]
                            
                            # 減少傾向からの急上昇
                            if avg_slope <= 0 and current_change > min_payout:
                                if i + 2 < len(graph_values) and graph_values[i+2] > graph_values[i+1] - 50:
                                    # 初当たりは必ずマイナス値
                                    if graph_values[i] < 0:
                                        first_hit_val = graph_values[i]
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
                # 最高値ライン（右端に短い線）
                max_y = int(zero_line_in_crop - (max_val / analyzer.scale))
                if 0 <= max_y < overlay_img.shape[0]:
                    # 右端に短い線
                    line_start = overlay_img.shape[1] - 100
                    cv2.line(overlay_img, (line_start, max_y), (overlay_img.shape[1], max_y), (0, 255, 255), 2)
                    # 背景付きテキスト（白背景、濃い黄色文字）
                    text = f'MAX: {int(max_val):,}'
                    text_width = 120
                    cv2.rectangle(overlay_img, (line_start - text_width - 10, max_y - 15), 
                                 (line_start - 5, max_y + 5), (255, 255, 255), -1)
                    cv2.putText(overlay_img, text, (line_start - text_width - 5, max_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 150), 1, cv2.LINE_AA)
                
                # 最低値ライン（右端に短い線）
                min_y = int(zero_line_in_crop - (min_val / analyzer.scale))
                if 0 <= min_y < overlay_img.shape[0]:
                    # 右端に短い線
                    line_start = overlay_img.shape[1] - 100
                    cv2.line(overlay_img, (line_start, min_y), (overlay_img.shape[1], min_y), (255, 0, 255), 2)
                    # 背景付きテキスト（白背景、濃いマゼンタ文字）
                    text = f'MIN: {int(min_val):,}'
                    text_width = 120
                    cv2.rectangle(overlay_img, (line_start - text_width - 10, min_y - 15), 
                                 (line_start - 5, min_y + 5), (255, 255, 255), -1)
                    cv2.putText(overlay_img, text, (line_start - text_width - 5, min_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 0, 150), 1, cv2.LINE_AA)
                
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
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 0), 1, cv2.LINE_AA)
                
                # 初当たり値ライン（右端に短い線）
                if first_hit_val > 0:  # 初当たりがある場合
                    first_hit_y = int(zero_line_in_crop - (first_hit_val / analyzer.scale))
                    if 0 <= first_hit_y < overlay_img.shape[0]:
                        # 右端に短い線
                        line_start = overlay_img.shape[1] - 100
                        cv2.line(overlay_img, (line_start, first_hit_y), (overlay_img.shape[1], first_hit_y), (155, 48, 255), 2)
                        # 背景付きテキスト（白背景、紫文字）
                        text = f'FIRST HIT: {int(first_hit_val):,}'
                        text_width = 120
                        cv2.rectangle(overlay_img, (line_start - text_width - 10, first_hit_y - 15), 
                                     (line_start - 5, first_hit_y + 5), (255, 255, 255), -1)
                        cv2.putText(overlay_img, text, (line_start - text_width - 5, first_hit_y), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 0, 150), 1, cv2.LINE_AA)
                
                # 結果を保存
                analysis_results.append({
                    'name': uploaded_file.name,
                    'image': overlay_img,
                    'success': True,
                    'max_val': int(max_val),
                    'min_val': int(min_val),
                    'current_val': int(current_val),
                    'first_hit_val': int(first_hit_val) if first_hit_val > 0 else None,
                    'dominant_color': dominant_color
                })
            else:
                # 解析失敗時
                analysis_results.append({
                    'name': uploaded_file.name,
                    'image': cropped_img,
                    'success': False
                })
        
        # プログレスバーを完了
        progress_bar.progress(1.0)
        status_text.text('✅ 全ての画像の処理が完了しました！')
        
        # 結果をグリッド表示
        st.markdown("""
        <h3 style="color: #4a5568; font-weight: 600; margin-top: 2rem; margin-bottom: 1rem;">
            <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">📊</span> 
            解析結果一覧
        </h3>
        """, unsafe_allow_html=True)
        
        # 2列のグリッドで表示
        cols = st.columns(2)
        for idx, result in enumerate(analysis_results):
            col_idx = idx % 2
            with cols[col_idx]:
                # カードスタイルのコンテナ
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; padding: 1.5rem; border-radius: 0.75rem; 
                                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); 
                                margin-bottom: 1.5rem; overflow: hidden;">
                        <h4 style="color: #4a5568; margin-bottom: 1rem; font-weight: 600;">
                            {result['name']}
                        </h4>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 画像表示
                    st.image(result['image'], use_column_width=True)
                    
                    # 成功時は統計情報を表示
                    if result['success']:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("最高値", f"{result['max_val']:,}玉")
                            st.metric("最低値", f"{result['min_val']:,}玉")
                        with col2:
                            st.metric("現在値", f"{result['current_val']:,}玉")
                            if result['first_hit_val']:
                                st.metric("初当たり", f"{result['first_hit_val']:,}玉")
                    else:
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
            2. **グラフ画像を選択**（複数選択可）
            3. **自動的に切り抜きと解析が実行されます**
            
            対応フォーマット:
            - JPG/JPEG
            - PNG
            
            切り抜き設定:
            - 0ラインを自動検出
            - 0ラインから上246px、下247px
            - 左右125pxの余白を除外
            """)

# フッター
st.markdown("""
<div class="footer-text">
    <hr style="margin-bottom: 2rem;"/>
    <p style="margin: 0;">🎰 パチンコグラフ解析システム v2.0</p>
    <p style="margin: 0.5rem 0; color: #a0aec0;">更新日: {}</p>
    <p style="margin: 0.5rem 0; font-size: 0.75rem; color: #cbd5e0;">Made with ❤️ using Streamlit</p>
</div>
""".format(datetime.now().strftime('%Y/%m/%d')), unsafe_allow_html=True)