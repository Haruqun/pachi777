#!/usr/bin/env python3
"""
複数のゼロライン位置をテストして最適値を見つける
"""

import cv2
import numpy as np
import os

def test_zero_positions(img_path, positions):
    """複数のゼロライン位置をテスト"""
    img = cv2.imread(img_path)
    if img is None:
        return
    
    height, width = img.shape[:2]
    
    # 各位置でオーバーレイを作成
    for i, y_pos in enumerate(positions):
        overlay = img.copy()
        
        # ゼロライン
        cv2.line(overlay, (0, y_pos), (width, y_pos), (0, 0, 0), 2)
        cv2.putText(overlay, f"Y={y_pos}", (width - 100, y_pos - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        
        # 10000, 20000のライン
        for value in [10000, 20000, -10000, -20000]:
            pixel_offset = int(value / 120)  # 1px = 120
            y = y_pos - pixel_offset
            
            if 0 <= y <= height:
                cv2.line(overlay, (0, y), (width, y), (150, 150, 150), 1)
                cv2.putText(overlay, str(value), (10, y + 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
        
        # 保存
        output_path = f"graphs/zero_line_test/test_y{y_pos}.png"
        cv2.imwrite(output_path, overlay)
        print(f"保存: Y={y_pos}")

# テスト実行
test_positions = [250, 255, 258, 260, 262, 265, 268]
test_image = "graphs/manual_crop/cropped/S__78209138_graph_only.png"

print("ゼロライン位置テスト")
print("=" * 40)
test_zero_positions(test_image, test_positions)