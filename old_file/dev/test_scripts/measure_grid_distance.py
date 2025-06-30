#!/usr/bin/env python3
"""
グリッド線の実際の距離を測定
"""

import cv2
import numpy as np
import os

def measure_grid_manually():
    """手動で観察したグリッド線の位置から計算"""
    
    # 実際の画像を見て、明確なグリッド線の位置を記録
    # S__78209138_graph_only.png の観察結果
    print("手動測定による分析")
    print("=" * 60)
    
    zero_y = 260
    
    # 実際に見える主要な横線の位置（目視確認）
    print("\nS__78209138_graph_only.png の分析:")
    print(f"ゼロライン: Y={zero_y}")
    
    # 上の線（30000に近い）
    top_line_y = 10  # 画像の最上部付近
    top_distance = zero_y - top_line_y
    print(f"\n最上部の線: Y={top_line_y}")
    print(f"ゼロラインからの距離: {top_distance}px")
    print(f"これが30000だとすると: 1px = {30000 / top_distance:.2f}")
    
    # 下の線（-20000付近）
    bottom_line_y = 426  # 目視で確認される線
    bottom_distance = bottom_line_y - zero_y
    print(f"\n下の主要な線: Y={bottom_line_y}")
    print(f"ゼロラインからの距離: {bottom_distance}px")
    print(f"これが-20000だとすると: 1px = {20000 / bottom_distance:.2f}")
    
    # 平均を計算
    scale1 = 30000 / top_distance
    scale2 = 20000 / bottom_distance
    avg_scale = (scale1 + scale2) / 2
    
    print(f"\n平均スケール: 1px = {avg_scale:.2f}")
    
    # 検証：このスケールで各値の位置を計算
    print(f"\n検証（1px = {avg_scale:.2f}として）:")
    for value in [30000, 20000, 10000, -10000, -20000, -30000]:
        y_pos = zero_y - int(value / avg_scale)
        print(f"  {value:6d}: Y={y_pos}")
    
    return avg_scale

def create_test_overlay(img_path, scale_value):
    """新しいスケールでオーバーレイを作成"""
    img = cv2.imread(img_path)
    if img is None:
        return
    
    height, width = img.shape[:2]
    overlay = img.copy()
    zero_y = 260
    
    # ゼロライン
    cv2.line(overlay, (0, zero_y), (width, zero_y), (0, 0, 0), 2)
    cv2.putText(overlay, "0", (width - 30, zero_y - 5), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    # 新しいスケールで線を描画
    for value in [30000, 20000, 10000, -10000, -20000, -30000]:
        y_pos = zero_y - int(value / scale_value)
        
        if 0 <= y_pos <= height:
            # 破線
            for x in range(0, width, 20):
                cv2.line(overlay, (x, y_pos), (min(x + 10, width), y_pos), 
                        (255, 0, 0), 1)
            
            # ラベル
            cv2.putText(overlay, str(value), (width - 80, y_pos + 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    
    # 旧スケール（120）でも描画（比較用）
    for value in [10000, -10000, -20000]:
        y_pos_old = zero_y - int(value / 120)
        
        if 0 <= y_pos_old <= height:
            # 点線
            for x in range(0, width, 10):
                cv2.line(overlay, (x, y_pos_old), (min(x + 5, width), y_pos_old), 
                        (0, 255, 0), 1)
            
            cv2.putText(overlay, f"{value}(old)", (10, y_pos_old + 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    
    output_path = f"graphs/scale_corrected_{os.path.basename(img_path)}"
    cv2.imwrite(output_path, overlay)
    print(f"\n保存: {output_path}")

# 実行
new_scale = measure_grid_manually()

# テスト画像に適用
test_images = [
    "graphs/manual_crop/cropped/S__78209138_graph_only.png",
    "graphs/manual_crop/cropped/S__78209088_graph_only.png"
]

print(f"\n\n新しいスケール（1px = {new_scale:.2f}）でテスト:")
for img_path in test_images:
    create_test_overlay(img_path, new_scale)