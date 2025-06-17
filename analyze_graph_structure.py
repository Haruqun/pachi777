#!/usr/bin/env python3
"""
グラフ構造分析ツール
- 画像の各要素の位置を詳細に分析
- グラフ描画領域の正確な境界を特定
"""

import os
import numpy as np
from PIL import Image, ImageDraw
import cv2
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Tuple, Dict, List

def analyze_graph_structure(image_path: str):
    """グラフ構造を詳細に分析"""
    print(f"📊 分析中: {os.path.basename(image_path)}")
    
    # 画像読み込み
    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    
    print(f"画像サイズ: {width}×{height}")
    
    # グレースケール変換
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # 1. オレンジヘッダーの検出
    orange_header_bottom = detect_orange_header(img_array)
    print(f"オレンジヘッダー下端: Y={orange_header_bottom}")
    
    # 2. グラフエリアの背景色検出
    graph_bg_bounds = detect_graph_background(img_array)
    print(f"グラフ背景領域: {graph_bg_bounds}")
    
    # 3. グリッド線の検出
    grid_lines = detect_grid_lines(gray)
    print(f"水平グリッド線: {len(grid_lines['horizontal'])}本")
    print(f"垂直グリッド線: {len(grid_lines['vertical'])}本")
    
    # 4. グラフラインの検出
    graph_line_bounds = detect_graph_line(img_array)
    print(f"グラフライン境界: {graph_line_bounds}")
    
    # 5. テキスト要素の検出
    text_regions = detect_text_regions(gray)
    print(f"テキスト領域: {len(text_regions)}個")
    
    # 可視化
    visualize_analysis(img_array, orange_header_bottom, graph_bg_bounds, 
                      grid_lines, graph_line_bounds, text_regions)
    
    return {
        "orange_header_bottom": orange_header_bottom,
        "graph_bg_bounds": graph_bg_bounds,
        "grid_lines": grid_lines,
        "graph_line_bounds": graph_line_bounds,
        "text_regions": text_regions
    }

def detect_orange_header(img_array: np.ndarray) -> int:
    """オレンジヘッダーの下端を検出"""
    height, width = img_array.shape[:2]
    
    # HSV変換
    hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
    
    # オレンジ色の範囲
    orange_lower = np.array([10, 100, 100])
    orange_upper = np.array([25, 255, 255])
    
    # マスク作成
    mask = cv2.inRange(hsv, orange_lower, orange_upper)
    
    # 上から下に走査してオレンジ色が終わる位置を探す
    for y in range(height):
        orange_ratio = np.sum(mask[y, :] > 0) / width
        if y > 50 and orange_ratio < 0.1:  # オレンジ色が10%未満
            return y
    
    return 100  # デフォルト値

def detect_graph_background(img_array: np.ndarray) -> Tuple[int, int, int, int]:
    """グラフ背景領域を検出"""
    height, width = img_array.shape[:2]
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # エッジ検出
    edges = cv2.Canny(gray, 30, 100)
    
    # 背景色の特定（薄いグレー/ベージュ）
    bg_color_range = (200, 250)  # グレースケール値の範囲
    
    # 背景領域のマスク
    bg_mask = (gray > bg_color_range[0]) & (gray < bg_color_range[1])
    
    # 連続した背景領域を探す
    top = 0
    bottom = height
    left = 0
    right = width
    
    # 上端を探す
    for y in range(50, height//2):
        if np.sum(bg_mask[y, width//4:3*width//4]) > width//2:
            top = y
            break
    
    # 下端を探す
    for y in range(height-50, height//2, -1):
        if np.sum(bg_mask[y, width//4:3*width//4]) > width//2:
            bottom = y
            break
    
    # 左端を探す（Y軸ラベルを除く）
    for x in range(width//4):
        if np.sum(bg_mask[top:bottom, x]) > (bottom-top)*0.8:
            left = x
            break
    
    # 右端を探す
    for x in range(width-1, 3*width//4, -1):
        if np.sum(bg_mask[top:bottom, x]) > (bottom-top)*0.8:
            right = x
            break
    
    return (left, top, right, bottom)

def detect_grid_lines(gray: np.ndarray) -> Dict[str, list]:
    """グリッド線を検出"""
    height, width = gray.shape
    
    # Sobelフィルタでエッジ強調
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    
    # 水平線検出
    horizontal_lines = []
    for y in range(height):
        if np.mean(np.abs(sobel_y[y, :])) > 5:
            horizontal_lines.append(y)
    
    # 連続した線をグループ化
    h_lines = []
    if horizontal_lines:
        current_group = [horizontal_lines[0]]
        for i in range(1, len(horizontal_lines)):
            if horizontal_lines[i] - horizontal_lines[i-1] <= 2:
                current_group.append(horizontal_lines[i])
            else:
                h_lines.append(int(np.mean(current_group)))
                current_group = [horizontal_lines[i]]
        h_lines.append(int(np.mean(current_group)))
    
    # 垂直線検出
    vertical_lines = []
    for x in range(width):
        if np.mean(np.abs(sobel_x[:, x])) > 5:
            vertical_lines.append(x)
    
    # 連続した線をグループ化
    v_lines = []
    if vertical_lines:
        current_group = [vertical_lines[0]]
        for i in range(1, len(vertical_lines)):
            if vertical_lines[i] - vertical_lines[i-1] <= 2:
                current_group.append(vertical_lines[i])
            else:
                v_lines.append(int(np.mean(current_group)))
                current_group = [vertical_lines[i]]
        v_lines.append(int(np.mean(current_group)))
    
    return {"horizontal": h_lines, "vertical": v_lines}

def detect_graph_line(img_array: np.ndarray) -> Tuple[int, int, int, int]:
    """グラフライン（ピンク/紫/青）の境界を検出"""
    height, width = img_array.shape[:2]
    
    # グラフラインの色を検出
    # ピンク、紫、青の範囲
    line_colors = []
    
    # 各行でグラフラインの色を探す
    min_x, max_x = width, 0
    min_y, max_y = height, 0
    
    for y in range(height):
        for x in range(width):
            r, g, b = img_array[y, x]
            
            # ピンク系 (R > G, B)
            if r > 200 and g < 150 and b > 150:
                line_colors.append((x, y))
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
            # 紫系
            elif r > 150 and b > 150 and g < 100:
                line_colors.append((x, y))
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
            # 青系
            elif b > 200 and r < 150 and g < 200:
                line_colors.append((x, y))
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
    
    if line_colors:
        return (min_x, min_y, max_x, max_y)
    else:
        return (0, 0, width, height)

def detect_text_regions(gray: np.ndarray) -> list:
    """テキスト領域を検出"""
    height, width = gray.shape
    
    # 二値化
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    
    # 連結成分検出
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    
    text_regions = []
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        
        # テキストらしいサイズの領域を選択
        if 10 < w < width//2 and 5 < h < 50 and area > 50:
            text_regions.append((x, y, x+w, y+h))
    
    return text_regions

def visualize_analysis(img_array, orange_header_bottom, graph_bg_bounds, 
                      grid_lines, graph_line_bounds, text_regions):
    """分析結果を可視化"""
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    # 元画像表示
    ax.imshow(img_array)
    ax.set_title("グラフ構造分析結果")
    
    # オレンジヘッダー境界
    ax.axhline(y=orange_header_bottom, color='orange', linewidth=2, 
               label=f'オレンジヘッダー下端 (Y={orange_header_bottom})')
    
    # グラフ背景領域
    if graph_bg_bounds:
        left, top, right, bottom = graph_bg_bounds
        rect = patches.Rectangle((left, top), right-left, bottom-top,
                               linewidth=2, edgecolor='green', 
                               facecolor='none', label='グラフ背景領域')
        ax.add_patch(rect)
    
    # グリッド線
    for y in grid_lines['horizontal'][:5]:  # 最初の5本のみ表示
        ax.axhline(y=y, color='yellow', alpha=0.5, linewidth=1)
    
    for x in grid_lines['vertical'][:5]:  # 最初の5本のみ表示
        ax.axvline(x=x, color='yellow', alpha=0.5, linewidth=1)
    
    # グラフライン境界
    if graph_line_bounds:
        left, top, right, bottom = graph_line_bounds
        rect = patches.Rectangle((left, top), right-left, bottom-top,
                               linewidth=2, edgecolor='red', 
                               facecolor='none', label='グラフライン境界')
        ax.add_patch(rect)
    
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('graph_structure_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"📊 分析結果を保存: graph_structure_analysis.png")

def main():
    """メイン処理"""
    # テスト画像を選択
    test_images = [
        "graphs/cropped_perfect/S__78209130_perfect.png",
        "graphs/cropped_perfect/S__78209132_perfect.png",
        "graphs/cropped_perfect/S__78209174_perfect.png"
    ]
    
    for image_path in test_images:
        if os.path.exists(image_path):
            print(f"\n{'='*60}")
            results = analyze_graph_structure(image_path)
            break

if __name__ == "__main__":
    main()