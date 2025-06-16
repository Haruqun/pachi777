#!/usr/bin/env python3
"""
線グラフの色分析ツール
- 特定の画像のライン色を分析
- 色範囲を調整するための情報を提供
"""

import os
import numpy as np
from PIL import Image
import cv2
from collections import Counter

def analyze_image_colors(image_path: str, sample_region=None):
    """画像の色を分析"""
    print(f"🔍 画像色分析: {os.path.basename(image_path)}")
    
    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    
    print(f"   画像サイズ: {width} × {height}")
    
    # サンプル領域の設定（グラフ領域の中央部分）
    if sample_region is None:
        # デフォルト: グラフの中央部分
        x1, y1 = width//4, height//4
        x2, y2 = 3*width//4, 3*height//4
    else:
        x1, y1, x2, y2 = sample_region
    
    print(f"   分析領域: ({x1}, {y1}) - ({x2}, {y2})")
    
    # サンプル領域を切り出し
    sample_area = img_array[y1:y2, x1:x2]
    
    # 色の統計
    colors = sample_area.reshape(-1, 3)
    
    # 明るい色（線として使われる可能性が高い）を抽出
    # 白っぽい色は除外（背景として使われることが多い）
    bright_colors = []
    for color in colors:
        r, g, b = color
        # 明るさと彩度をチェック
        brightness = (r + g + b) / 3
        if 50 < brightness < 220:  # 白すぎず、黒すぎない
            saturation = max(r, g, b) - min(r, g, b)
            if saturation > 30:  # 彩度がある
                bright_colors.append(tuple(color))
    
    if bright_colors:
        # 最も頻繁に現れる色を取得
        color_counts = Counter(bright_colors)
        top_colors = color_counts.most_common(10)
        
        print(f"\n📊 上位10色 (R, G, B):")
        for i, (color, count) in enumerate(top_colors, 1):
            r, g, b = color
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            print(f"   {i:2d}. RGB{color} {hex_color} - {count}ピクセル")
    
    return sample_area

def detect_line_colors_detailed(image_path: str):
    """詳細なライン色検出"""
    print(f"\n🎯 詳細ライン色検出: {os.path.basename(image_path)}")
    
    img = Image.open(image_path)
    img_array = np.array(img)
    
    # HSV色空間での分析
    hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
    
    # ピンク系の色範囲（HSV）
    pink_ranges = [
        ([140, 50, 50], [180, 255, 255]),    # マゼンタ～ピンク
        ([300, 50, 50], [330, 255, 255]),    # ピンク～赤
    ]
    
    # ブルー系の色範囲（HSV）
    blue_ranges = [
        ([100, 50, 50], [130, 255, 255]),    # ブルー
        ([200, 50, 50], [240, 255, 255]),    # シアン～ブルー
    ]
    
    print("\n🔴 ピンク系検出:")
    pink_total = 0
    for i, (lower, upper) in enumerate(pink_ranges):
        lower = np.array(lower)
        upper = np.array(upper)
        mask = cv2.inRange(hsv, lower, upper)
        count = np.sum(mask > 0)
        pink_total += count
        print(f"   範囲{i+1}: {count}ピクセル")
    
    print(f"   ピンク系合計: {pink_total}ピクセル")
    
    print("\n🔵 ブルー系検出:")
    blue_total = 0
    for i, (lower, upper) in enumerate(blue_ranges):
        lower = np.array(lower)
        upper = np.array(upper)
        mask = cv2.inRange(hsv, lower, upper)
        count = np.sum(mask > 0)
        blue_total += count
        print(f"   範囲{i+1}: {count}ピクセル")
    
    print(f"   ブルー系合計: {blue_total}ピクセル")
    
    # 主要な色を抽出
    print(f"\n🎨 推奨色範囲:")
    if pink_total > 100:
        print(f"   ピンク線が検出されました ({pink_total}ピクセル)")
        # 実際のピンク色を抽出
        extract_actual_colors(img_array, "ピンク", pink_ranges)
    
    if blue_total > 100:
        print(f"   ブルー線が検出されました ({blue_total}ピクセル)")
        extract_actual_colors(img_array, "ブルー", blue_ranges)

def extract_actual_colors(img_array, color_name, ranges):
    """実際の色を抽出"""
    hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
    
    # 全ての範囲を統合
    combined_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lower, upper in ranges:
        lower = np.array(lower)
        upper = np.array(upper)
        mask = cv2.inRange(hsv, lower, upper)
        combined_mask = cv2.bitwise_or(combined_mask, mask)
    
    # マスクされた色を抽出
    colored_pixels = img_array[combined_mask > 0]
    
    if len(colored_pixels) > 0:
        # 代表色を計算
        avg_color = np.mean(colored_pixels, axis=0).astype(int)
        print(f"   {color_name}平均色: RGB{tuple(avg_color)}")
        
        # 標準偏差
        std_color = np.std(colored_pixels, axis=0).astype(int)
        print(f"   {color_name}標準偏差: RGB{tuple(std_color)}")

def main():
    """メイン処理"""
    test_images = [
        "graphs/cropped_auto/S__78209088_cropped.png",
        "graphs/cropped_auto/IMG_4403_cropped.png",
        "graphs/cropped_auto/S__78209136_cropped.png",
    ]
    
    for image_path in test_images:
        if os.path.exists(image_path):
            print("=" * 70)
            analyze_image_colors(image_path)
            detect_line_colors_detailed(image_path)
            print()
        else:
            print(f"❌ {image_path} が見つかりません")

if __name__ == "__main__":
    main()