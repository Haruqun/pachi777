#!/usr/bin/env python3
"""
すべての画像でゼロライン位置（Y=260）をテスト
"""

import cv2
import numpy as np
import os
import glob

def test_zero_line_on_image(img_path, zero_y=260):
    """画像にゼロラインと補助線を描画してテスト"""
    img = cv2.imread(img_path)
    if img is None:
        return None
    
    height, width = img.shape[:2]
    overlay = img.copy()
    
    # ゼロライン（太い黒線）
    cv2.line(overlay, (0, zero_y), (width, zero_y), (0, 0, 0), 2)
    cv2.putText(overlay, "0", (width - 30, zero_y - 5), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    # 10000, 20000, 30000のライン
    value_lines = [10000, 20000, 30000, -10000, -20000, -30000]
    for value in value_lines:
        pixel_offset = int(value / 120)  # 1px = 120
        y_pos = zero_y - pixel_offset
        
        if 0 <= y_pos <= height:
            # 破線
            for x in range(0, width, 20):
                cv2.line(overlay, (x, y_pos), (min(x + 10, width), y_pos), 
                        (150, 150, 150), 1)
            
            # 数値ラベル
            cv2.putText(overlay, str(value), (width - 70, y_pos + 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
    
    return overlay

def main():
    """メイン処理"""
    # すべての切り抜き画像を取得
    image_files = glob.glob("graphs/manual_crop/cropped/*.png")
    image_files.sort()
    
    # 出力ディレクトリ
    output_dir = "graphs/zero_line_test/all_images"
    os.makedirs(output_dir, exist_ok=True)
    
    print("ゼロライン位置テスト (Y=260)")
    print("=" * 50)
    
    # 各画像をテスト
    for i, img_path in enumerate(image_files):
        base_name = os.path.basename(img_path)
        print(f"[{i+1}/{len(image_files)}] 処理中: {base_name}")
        
        # テスト画像作成
        test_img = test_zero_line_on_image(img_path)
        
        if test_img is not None:
            # 保存
            output_path = os.path.join(output_dir, f"test_{base_name}")
            cv2.imwrite(output_path, test_img)
            print(f"  → 保存: {output_path}")
        else:
            print(f"  → エラー: 画像を読み込めません")
    
    print(f"\n完了！")
    print(f"テスト画像保存先: {output_dir}")
    
    # いくつかの画像を表示用に選択
    sample_images = [
        "S__78209088_graph_only.png",
        "S__78209156_graph_only.png", 
        "S__78716957_graph_only.png",
        "S__78848008_graph_only.png"
    ]
    
    print(f"\nサンプル画像:")
    for img_name in sample_images:
        if f"test_{img_name}" in os.listdir(output_dir):
            print(f"  - {img_name}")

if __name__ == "__main__":
    main()