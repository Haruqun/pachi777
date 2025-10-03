"""グラフ解析関連の機能"""
import cv2
import numpy as np
from PIL import Image
import streamlit as st
import os
import re


def calculate_black_ratio(image, black_threshold=50):
    """画像内の黒色の割合を計算する"""
    # numpyに変換
    img_array = np.array(image)
    
    # RGB画像の場合
    if len(img_array.shape) == 3:
        # グレースケールに変換
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # 黒ピクセルのカウント
    black_pixels = np.sum(gray < black_threshold)
    total_pixels = gray.shape[0] * gray.shape[1]
    
    # 黒色の割合を計算
    black_ratio = black_pixels / total_pixels
    
    return black_ratio


def detect_and_draw_black_frames(image, overlay_mask=True, crop_upper_half=False):
    """黒枠を検出してoverlay.pngを重ねる、オプションで上半分を切り抜く"""
    # OpenCV形式に変換
    img_array = np.array(image)
    
    # 画像のサイズを取得
    height, width = img_array.shape[:2]
    
    # 上半分を切り抜く場合
    if crop_upper_half:
        img_array = img_array[:height//2, :]
        height = height // 2
    
    # RGB変換（もしBGRの場合）
    if len(img_array.shape) == 3:
        img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
    else:
        img_rgb = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
    
    # グレースケール変換
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    
    # 黒枠検出のための閾値処理
    threshold = 30  # 黒とみなす最大値
    black_mask = gray < threshold
    
    # モルフォロジー処理でノイズ除去
    kernel = np.ones((5,5), np.uint8)
    black_mask = cv2.morphologyEx(black_mask.astype(np.uint8) * 255, cv2.MORPH_CLOSE, kernel)
    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)
    
    # 輪郭検出
    contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 検出された黒枠を保存
    black_frames = []
    
    # 有効な輪郭のみフィルタリング（面積が一定以上）
    min_area = width * height * 0.01  # 画像の1%以上
    valid_contours = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(contour)
            
            # 黒枠の条件：幅と高さが画像の10%以上
            if w > width * 0.1 and h > height * 0.1:
                black_frames.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'area': area
                })
                valid_contours.append(contour)
    
    # overlay.pngを探す
    overlay_path = None
    if overlay_mask and black_frames:
        # スクリプトのディレクトリから探す
        script_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths = [
            os.path.join(script_dir, '..', '..', 'overlay.png'),
            os.path.join(script_dir, '..', 'overlay.png'),
            'overlay.png',
            '/tmp/overlay.png'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                overlay_path = path
                break
    
    # 結果画像の作成
    result = img_rgb.copy()
    
    # 緑色で輪郭を描画
    cv2.drawContours(result, valid_contours, -1, (0, 255, 0), 2)
    
    # 黒枠の座標を描画
    for i, frame in enumerate(black_frames):
        # 枠を描画
        cv2.rectangle(result, 
                     (frame['x'], frame['y']), 
                     (frame['x'] + frame['width'], frame['y'] + frame['height']), 
                     (255, 0, 0), 2)
        
        # ラベルを描画
        label = f"Frame {i+1}"
        cv2.putText(result, label, 
                   (frame['x'], frame['y'] - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    
    # overlay.pngを重ねる
    if overlay_path and black_frames:
        try:
            # 最も大きい黒枠を選択
            largest_frame = max(black_frames, key=lambda x: x['area'])
            
            # overlay画像を読み込み
            overlay = Image.open(overlay_path).convert("RGBA")
            
            # 黒枠のサイズに合わせてリサイズ
            overlay_resized = overlay.resize(
                (largest_frame['width'], largest_frame['height']), 
                Image.Resampling.LANCZOS
            )
            
            # PIL形式に変換
            result_pil = Image.fromarray(result)
            
            # 透明度を考慮して合成
            if result_pil.mode != 'RGBA':
                result_pil = result_pil.convert('RGBA')
            
            # overlay画像を貼り付け
            result_pil.paste(overlay_resized, 
                           (largest_frame['x'], largest_frame['y']), 
                           overlay_resized)
            
            # numpy配列に戻す
            result = np.array(result_pil.convert('RGB'))
            
        except Exception as e:
            st.error(f"オーバーレイ画像の処理中にエラー: {str(e)}")
    
    # デバッグ情報を生成
    debug_info = {
        'detected_frames': len(black_frames),
        'frames': black_frames,
        'overlay_applied': overlay_path is not None and len(black_frames) > 0,
        'overlay_path': overlay_path,
        'image_size': (width, height),
        'cropped': crop_upper_half
    }
    
    return Image.fromarray(result), debug_info


def get_graph_limit(game_type='パチンコ'):
    """遊技種別に応じたグラフの上下限を返す"""
    return 30000 if game_type == 'パチンコ' else 5000


def get_unit(game_type='パチンコ'):
    """遊技種別に応じた単位を返す"""
    return '玉' if game_type == 'パチンコ' else '枚'


def get_unit_per_1000yen(game_type='パチンコ'):
    """遊技種別に応じた1000円あたりの単位を返す"""
    return 250 if game_type == 'パチンコ' else 50


def detect_first_hit(graph_values, game_type='パチンコ', small_jackpot_balls=450):
    """グラフデータから初当たりを検出する
    
    Args:
        graph_values: グラフの値のリスト
        game_type: 遊技種別（'パチンコ' or 'パチスロ'）
        small_jackpot_balls: 小当たりの払い出し球数
        
    Returns:
        dict: 初当たり検出結果
            - first_hit_val: 初当たり時の値
            - first_hit_x: 初当たり位置（x座標）
            - debug_info: デバッグ情報
    """
    # 初期値
    first_hit_val = 0
    first_hit_x = None
    
    # 機種や設定により動的に閾値を調整
    if game_type == 'パチンコ':
        # 小当たりの払い出し球数を基準に（通常300-450球）
        min_payout = small_jackpot_balls * 0.8  # 80%を閾値に
    else:
        min_payout = 20  # パチスロは20枚
    
    # 初当たり検出デバッグ情報
    first_hit_debug_info = {
        'detected_position': None,
        'detected_value': None,
        'detection_method': None,
        'candidates': []
    }

    # 方法1: 閾値以上の急激な増加を検出
    for i in range(1, min(len(graph_values)-2, 150)):  # 最大150点まで探索
        current_increase = graph_values[i+1] - graph_values[i]

        # 閾値以上の増加を検出
        if current_increase > min_payout:
            # 候補として記録
            if graph_values[i] < 0:
                first_hit_debug_info['candidates'].append({
                    'position': i,
                    'value': graph_values[i],
                    'increase': current_increase,
                    'next_point': graph_values[i+1] if i+1 < len(graph_values) else None,
                    'reason': f'{current_increase:.0f}玉の上昇検出'
                })
            # 次の点も上昇または維持していることを確認（ノイズ除外）
            noise_threshold = 50 if game_type == 'パチンコ' else 10
            if graph_values[i+2] >= graph_values[i+1] - noise_threshold:
                # 初当たりは必ずマイナス値から
                if graph_values[i] < 0:
                    # 補正なしで純粋な検出位置を使用
                    first_hit_val = graph_values[i]
                    first_hit_x = i
                    first_hit_debug_info['detection_method'] = '方法1: 急激な増加検出'
                    first_hit_debug_info['candidates'].append({
                        'position': i,
                        'value': graph_values[i],
                        'increase': current_increase,
                        'reason': f'{current_increase:.0f}玉の急上昇'
                    })
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
                    noise_threshold = 50 if game_type == 'パチンコ' else 10
                    if i + 2 < len(graph_values) and graph_values[i+2] > graph_values[i+1] - noise_threshold:
                        # 初当たりは必ずマイナス値
                        if graph_values[i] < 0:
                            # 補正なしで純粋な検出位置を使用
                            first_hit_val = graph_values[i]
                            first_hit_x = i
                            first_hit_debug_info['detection_method'] = '方法2: 減少傾向からの急上昇'
                            first_hit_debug_info['candidates'].append({
                                'position': i,
                                'value': graph_values[i],
                                'slope': avg_slope,
                                'increase': current_change,
                                'reason': f'傾き{avg_slope:.1f}から{current_change:.0f}玉上昇'
                            })
                            break

    # 初当たり値がプラスの場合は0を表示
    if first_hit_val > 0:
        first_hit_val = 0
    
    first_hit_debug_info['detected_position'] = first_hit_x
    first_hit_debug_info['detected_value'] = first_hit_val if first_hit_x is not None else None
    
    return {
        'first_hit_val': first_hit_val,
        'first_hit_x': first_hit_x,
        'debug_info': first_hit_debug_info
    }