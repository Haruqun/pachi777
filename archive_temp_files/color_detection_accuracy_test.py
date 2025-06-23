#!/usr/bin/env python3
"""
正しい画像のみで色検出精度をテスト
"""

import os
import pandas as pd
from improved_color_detector import ImprovedColorDetector

def main():
    """メイン処理"""
    detector = ImprovedColorDetector()
    
    # 正しい画像リスト（results.txtにある画像のみ）
    valid_images = [
        'S__78209088_optimal.png',
        'S__78209128_optimal.png', 
        'S__78209130_optimal.png',
        'S__78209136_optimal.png',
        'S__78209138_optimal.png',
        'S__78209156_optimal.png',
        'S__78209158_optimal.png',
        'S__78209160_optimal.png',
        'S__78209162_optimal.png',
        'S__78209164_optimal.png',
        'S__78209166_optimal.png',
        'S__78209168_optimal.png',
        'S__78209170_optimal.png',
        'S__78209174_optimal.png'
    ]
    
    # 期待される色（extraction_summary.csvから）
    expected_colors = {
        'S__78209088': 'pink',
        'S__78209128': 'pink',
        'S__78209130': 'pink',
        'S__78209136': 'pink',
        'S__78209138': 'pink',
        'S__78209156': 'pink',
        'S__78209158': 'pink',
        'S__78209160': 'blue',
        'S__78209162': 'blue',
        'S__78209164': 'blue',
        'S__78209166': 'purple',
        'S__78209168': 'purple',
        'S__78209170': 'purple',
        'S__78209174': 'purple'
    }
    
    print("正しい画像での色検出テスト")
    print("=" * 100)
    print(f"{'画像':25} {'期待色':10} {'検出色':10} {'一致':8} {'検出率':>10} {'ピンク':>10} {'青':>10} {'紫':>10}")
    print("-" * 100)
    
    correct_count = 0
    total_count = 0
    
    for img_file in valid_images:
        img_path = os.path.join('graphs/cropped', img_file)
        if not os.path.exists(img_path):
            continue
            
        result = detector.analyze_image(img_path)
        if not result:
            continue
        
        # 期待される色を取得
        base_name = img_file.replace('_optimal.png', '')
        expected = expected_colors.get(base_name, 'unknown')
        
        # 一致判定
        is_correct = result['detected_color'] == expected
        if is_correct:
            correct_count += 1
        total_count += 1
        
        match_mark = '○' if is_correct else '×'
        
        print(f"{result['image']:25} {expected:10} {result['detected_color']:10} {match_mark:^8} "
              f"{result['detection_rate']:>9.1f}% "
              f"{result['scores']['pink']:>10} "
              f"{result['scores']['blue']:>10} "
              f"{result['scores']['purple']:>10}")
    
    print("-" * 100)
    print(f"\n検出精度: {correct_count}/{total_count} ({correct_count/total_count*100:.1f}%)")
    
    # 色別の統計
    print("\n色別統計:")
    for color in ['pink', 'blue', 'purple']:
        expected_count = sum(1 for c in expected_colors.values() if c == color)
        detected_count = 0
        for img_file in valid_images:
            img_path = os.path.join('graphs/cropped', img_file)
            if os.path.exists(img_path):
                result = detector.analyze_image(img_path)
                if result and result['detected_color'] == color:
                    detected_count += 1
        
        print(f"  {color}: 期待 {expected_count}枚、検出 {detected_count}枚")

if __name__ == "__main__":
    main()