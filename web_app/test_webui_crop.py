#!/usr/bin/env python3
"""
Web UI版の切り抜きテスト
"""

import os
import sys
import cv2
import matplotlib.pyplot as plt
from pathlib import Path

# web_analyzerをインポート
from web_analyzer import WebCompatibleAnalyzer

def test_webui_crop(image_path):
    """Web UI版の切り抜きをテスト"""
    
    # アナライザーを初期化
    analyzer = WebCompatibleAnalyzer(work_dir=".")
    
    # 画像を切り抜き
    print(f"Testing Web UI crop on: {image_path}")
    cropped = analyzer.crop_graph_area(image_path)
    
    if cropped is None:
        print("Error: Crop failed")
        return
    
    # 元画像を読み込み
    original = cv2.imread(image_path)
    
    # 結果を表示
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    # 元画像
    ax1.imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))
    ax1.set_title('Original Image')
    ax1.axis('off')
    
    # 切り抜き画像
    ax2.imshow(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
    ax2.set_title(f'Web UI Crop (Pattern3)\nSize: {cropped.shape[1]}x{cropped.shape[0]}')
    ax2.axis('off')
    
    # ゼロライン位置を表示
    if hasattr(analyzer, 'zero_y'):
        ax2.axhline(y=analyzer.zero_y, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax2.text(10, analyzer.zero_y - 10, 'Zero Line', color='red', fontsize=10, weight='bold')
    
    plt.tight_layout()
    
    # 結果を保存
    output_dir = 'webui_crop_test'
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = Path(image_path).stem
    output_path = f'{output_dir}/{base_name}_webui_crop_result.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    
    # 切り抜き画像も個別に保存
    cropped_output = f'{output_dir}/{base_name}_webui_cropped.png'
    cv2.imwrite(cropped_output, cropped)
    
    print(f"\nWeb UI Crop Result:")
    print(f"  Size: {cropped.shape[1]}x{cropped.shape[0]}")
    print(f"  Zero line position: {analyzer.zero_y}")
    print(f"  Results saved to: {output_dir}/")
    
    plt.show()

if __name__ == '__main__':
    # テスト画像
    test_images = [
        '/Users/haruqun/Work/pachi777/graphs/original/S__80158724.jpg',
        '/Users/haruqun/Work/pachi777/graphs/original/S__80158728.jpg',
        '/Users/haruqun/Work/pachi777/graphs/original/S__79781905.jpg'
    ]
    
    # 最初の画像でテスト
    if os.path.exists(test_images[0]):
        test_webui_crop(test_images[0])
    else:
        print(f"Test image not found: {test_images[0]}")