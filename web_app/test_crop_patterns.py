#!/usr/bin/env python3
"""
Web UI版 切り抜きパターンテスト
複数の切り抜きパターンを試して最適なものを選択
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path

def detect_orange_bar(img):
    """オレンジバー検出（共通処理）"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    height, width = img.shape[:2]
    
    # オレンジ色の検出
    orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
    
    # 上半分をスキャン
    orange_bottom = 0
    for y in range(height//2):
        if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
            orange_bottom = y
    
    # もしオレンジバーが見つからない場合のフォールバック
    if orange_bottom == 0:
        orange_bottom = 150  # デフォルト値
    else:
        # オレンジバーの下端を見つける
        for y in range(orange_bottom, min(orange_bottom + 100, height)):
            if np.sum(orange_mask[y, :]) < width * 0.1 * 255:
                orange_bottom = y
                break
    
    return orange_bottom

def pattern1_fixed_offset(img, orange_bottom):
    """パターン1: 固定オフセット（オリジナル）"""
    height, width = img.shape[:2]
    
    # 固定オフセット
    graph_top = orange_bottom + 100
    graph_bottom = height - 200
    graph_left = 120
    graph_right = width - 150
    
    return {
        'name': 'Pattern1: Fixed Offset',
        'top': graph_top,
        'bottom': graph_bottom,
        'left': graph_left,
        'right': graph_right
    }

def pattern2_y_labels(img, orange_bottom):
    """パターン2: Y軸ラベル検出ベース"""
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Y軸ラベル領域を探す（30,000と-30,000）
    label_left = 0
    label_right = width // 3
    
    # 上部の30,000ラベルを探す
    top_label_y = orange_bottom
    for y in range(orange_bottom + 20, min(orange_bottom + 150, height)):
        row_region = gray[y:y+30, label_left:label_right]
        if row_region.shape[0] > 0 and np.var(row_region) > 500:
            top_label_y = y
            break
    
    # 下部の-30,000ラベルを探す
    bottom_label_y = height - 100
    for y in range(height - 150, height - 50):
        row_region = gray[y:y+30, label_left:label_right]
        if row_region.shape[0] > 0 and np.var(row_region) > 500:
            bottom_label_y = y + 30
            break
    
    # グラフ領域
    graph_top = top_label_y - 10
    graph_bottom = bottom_label_y + 10
    graph_left = 100
    graph_right = width - 100
    
    return {
        'name': 'Pattern2: Y-axis Labels',
        'top': graph_top,
        'bottom': graph_bottom,
        'left': graph_left,
        'right': graph_right
    }

def pattern3_zero_line_based(img, orange_bottom):
    """パターン3: ゼロライン検出ベース"""
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # ゼロライン検出
    search_start = orange_bottom + 50
    search_end = min(height - 100, orange_bottom + 400)
    
    best_score = 0
    zero_line_y = (search_start + search_end) // 2
    
    for y in range(search_start, search_end):
        row = gray[y, 100:width-100]
        # 暗い水平線を探す
        darkness = 1.0 - (np.mean(row) / 255.0)
        uniformity = 1.0 - (np.std(row) / 128.0)
        score = darkness * 0.5 + uniformity * 0.5
        
        if score > best_score:
            best_score = score
            zero_line_y = y
    
    # ゼロラインから上下に拡張
    graph_top = max(orange_bottom + 20, zero_line_y - 250)
    graph_bottom = min(height - 50, zero_line_y + 250)
    graph_left = 100
    graph_right = width - 100
    
    return {
        'name': 'Pattern3: Zero Line Based',
        'top': graph_top,
        'bottom': graph_bottom,
        'left': graph_left,
        'right': graph_right,
        'zero_line': zero_line_y
    }

def pattern4_content_based(img, orange_bottom):
    """パターン4: コンテンツベース（エッジ検出）"""
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # エッジ検出
    edges = cv2.Canny(gray, 50, 150)
    
    # 左右の境界を検出
    left_margin = 50
    right_margin = width - 50
    
    # 左側の境界
    for x in range(50, width//3):
        column = edges[orange_bottom:height-100, x]
        if np.sum(column) > height * 0.1 * 255:
            left_margin = x - 10
            break
    
    # 右側の境界
    for x in range(width - 50, width*2//3, -1):
        column = edges[orange_bottom:height-100, x]
        if np.sum(column) > height * 0.1 * 255:
            right_margin = x + 10
            break
    
    # 上下の境界
    top_margin = orange_bottom + 50
    bottom_margin = height - 100
    
    # 上側の境界
    for y in range(orange_bottom + 20, orange_bottom + 200):
        row = edges[y, left_margin:right_margin]
        if np.sum(row) > width * 0.05 * 255:
            top_margin = y - 10
            break
    
    # 下側の境界
    for y in range(height - 50, height - 200, -1):
        row = edges[y, left_margin:right_margin]
        if np.sum(row) > width * 0.05 * 255:
            bottom_margin = y + 10
            break
    
    return {
        'name': 'Pattern4: Content Based',
        'top': top_margin,
        'bottom': bottom_margin,
        'left': left_margin,
        'right': right_margin
    }

def pattern5_adaptive(img, orange_bottom):
    """パターン5: アダプティブ（複数の手法を組み合わせ）"""
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # まずゼロラインを検出
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
    
    # Y軸ラベル位置を推定
    # 上部ラベル（30,000付近）
    top_label_region = orange_bottom + 50
    for y in range(orange_bottom + 30, orange_bottom + 120):
        row_left = gray[y:y+20, 20:100]
        if row_left.shape[0] > 0 and np.var(row_left) > 300:
            top_label_region = y
            break
    
    # 下部ラベル（-30,000付近）
    bottom_label_region = height - 100
    for y in range(height - 150, height - 50):
        row_left = gray[y:y+20, 20:100]
        if row_left.shape[0] > 0 and np.var(row_left) > 300:
            bottom_label_region = y
            break
    
    # 最終的な境界を決定
    graph_top = min(top_label_region - 20, zero_line_y - 260)
    graph_bottom = max(bottom_label_region + 20, zero_line_y + 260)
    
    # 左右の境界（Y軸ラベルの右側から）
    graph_left = 110
    graph_right = width - 120
    
    return {
        'name': 'Pattern5: Adaptive',
        'top': graph_top,
        'bottom': graph_bottom,
        'left': graph_left,
        'right': graph_right,
        'zero_line': zero_line_y
    }

def test_crop_patterns(image_path):
    """全パターンをテストして結果を表示"""
    # 画像読み込み
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Cannot read image {image_path}")
        return
    
    # オレンジバー検出
    orange_bottom = detect_orange_bar(img)
    print(f"Orange bar bottom detected at: {orange_bottom}")
    
    # 各パターンを実行
    patterns = [
        pattern1_fixed_offset(img, orange_bottom),
        pattern2_y_labels(img, orange_bottom),
        pattern3_zero_line_based(img, orange_bottom),
        pattern4_content_based(img, orange_bottom),
        pattern5_adaptive(img, orange_bottom)
    ]
    
    # 結果を表示
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    
    # オリジナル画像
    axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    axes[0].set_title('Original Image')
    axes[0].axis('off')
    
    # 各パターンの結果
    for i, pattern in enumerate(patterns):
        ax = axes[i + 1]
        
        # 切り抜き
        cropped = img[pattern['top']:pattern['bottom'], 
                     pattern['left']:pattern['right']]
        
        if cropped.size > 0:
            ax.imshow(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
            ax.set_title(f"{pattern['name']}\n"
                        f"Size: {cropped.shape[1]}x{cropped.shape[0]}")
        else:
            ax.text(0.5, 0.5, 'Invalid crop', ha='center', va='center')
            ax.set_title(pattern['name'])
        
        ax.axis('off')
    
    plt.tight_layout()
    
    # 結果を保存
    output_dir = 'crop_test_results'
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = Path(image_path).stem
    plt.savefig(f'{output_dir}/{base_name}_crop_patterns.png', dpi=150, bbox_inches='tight')
    
    # 各パターンの個別画像も保存
    for i, pattern in enumerate(patterns):
        cropped = img[pattern['top']:pattern['bottom'], 
                     pattern['left']:pattern['right']]
        if cropped.size > 0:
            cv2.imwrite(f'{output_dir}/{base_name}_pattern{i+1}.png', cropped)
            print(f"\n{pattern['name']}:")
            print(f"  Top: {pattern['top']}, Bottom: {pattern['bottom']}")
            print(f"  Left: {pattern['left']}, Right: {pattern['right']}")
            print(f"  Size: {cropped.shape[1]}x{cropped.shape[0]}")
            if 'zero_line' in pattern:
                print(f"  Zero line: {pattern['zero_line']}")
    
    plt.show()
    print(f"\nResults saved to {output_dir}/")

if __name__ == '__main__':
    # テスト画像
    test_image = '/Users/haruqun/Work/pachi777/graphs/original/S__80158724.jpg'
    
    if os.path.exists(test_image):
        test_crop_patterns(test_image)
    else:
        print(f"Test image not found: {test_image}")
        print("Please provide a valid image path.")