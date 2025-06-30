#!/usr/bin/env python3
"""
スケール校正テスト
実際の10000区切りの位置を確認して正確な1ピクセルあたりの値を計算
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

def analyze_scale(img_path, zero_y=260):
    """画像のスケールを分析"""
    img = cv2.imread(img_path)
    if img is None:
        return
    
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    print(f"\n画像: {os.path.basename(img_path)}")
    print(f"ゼロライン: Y={zero_y}")
    
    # 水平線を検出（グリッド線）
    horizontal_lines = []
    
    # ゼロラインより上（正の値）
    for y in range(max(0, zero_y - 300), zero_y):
        row = gray[y, :]
        # グリッド線の特徴（薄いグレー）
        if 180 < np.mean(row) < 220 and np.std(row) < 10:
            horizontal_lines.append((y, 'above'))
    
    # ゼロラインより下（負の値）
    for y in range(zero_y + 1, min(height, zero_y + 300)):
        row = gray[y, :]
        if 180 < np.mean(row) < 220 and np.std(row) < 10:
            horizontal_lines.append((y, 'below'))
    
    print(f"\n検出されたグリッド線:")
    
    # 10000区切りの線を推定
    # 上方向
    above_lines = [(y, abs(y - zero_y)) for y, pos in horizontal_lines if pos == 'above']
    above_lines.sort(key=lambda x: x[1])
    
    print("\n上方向（正の値）:")
    if len(above_lines) >= 2:
        # 最初の主要な線を10000と仮定
        first_major = above_lines[-1]  # 最も遠い線
        pixels_per_10000 = first_major[1]
        print(f"  10000と推定される線: Y={first_major[0]}, 距離={first_major[1]}px")
        print(f"  → 1ピクセル = {10000 / first_major[1]:.1f}")
        
        # 20000の線を探す
        for y, dist in above_lines:
            if abs(dist - pixels_per_10000 * 2) < 5:
                print(f"  20000と推定される線: Y={y}, 距離={dist}px")
                print(f"  → 1ピクセル = {20000 / dist:.1f}")
    
    # 下方向
    below_lines = [(y, abs(y - zero_y)) for y, pos in horizontal_lines if pos == 'below']
    below_lines.sort(key=lambda x: x[1])
    
    print("\n下方向（負の値）:")
    if len(below_lines) >= 2:
        first_major = below_lines[-1]
        pixels_per_10000 = first_major[1]
        print(f"  -10000と推定される線: Y={first_major[0]}, 距離={first_major[1]}px")
        print(f"  → 1ピクセル = {10000 / first_major[1]:.1f}")
        
        for y, dist in below_lines:
            if abs(dist - pixels_per_10000 * 2) < 5:
                print(f"  -20000と推定される線: Y={y}, 距離={dist}px")
                print(f"  → 1ピクセル = {20000 / dist:.1f}")
    
    # 可視化
    overlay = img.copy()
    
    # ゼロライン
    cv2.line(overlay, (0, zero_y), (width, zero_y), (0, 0, 0), 2)
    cv2.putText(overlay, "0", (width - 30, zero_y - 5), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    # 検出されたグリッド線
    for y, pos in horizontal_lines:
        color = (0, 255, 0) if pos == 'above' else (255, 0, 0)
        cv2.line(overlay, (0, y), (width, y), color, 1)
        dist = abs(y - zero_y)
        cv2.putText(overlay, f"{dist}px", (10, y + 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # 現在の想定値（1px = 120）で描画
    for value in [10000, 20000, -10000, -20000]:
        y_120 = zero_y - int(value / 120)
        if 0 <= y_120 <= height:
            cv2.line(overlay, (0, y_120), (width, y_120), (255, 255, 0), 1)
            cv2.putText(overlay, f"{value} (120)", (width - 100, y_120 + 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    
    # 保存
    output_path = f"graphs/scale_test_{os.path.basename(img_path)}"
    cv2.imwrite(output_path, overlay)
    print(f"\n保存: {output_path}")

# テスト実行
test_images = [
    "graphs/manual_crop/cropped/S__78209138_graph_only.png",
    "graphs/manual_crop/cropped/S__78209088_graph_only.png",
    "graphs/manual_crop/cropped/S__78716957_graph_only.png"
]

print("スケール校正テスト")
print("=" * 60)

for img_path in test_images:
    analyze_scale(img_path)