#!/usr/bin/env python3
"""
グリッド線検出の詳細分析ツール
- なぜグリッド線が検出されないか調査
- 最適なパラメータを見つける
"""

import os
import numpy as np
from PIL import Image
import cv2
import matplotlib.pyplot as plt

def analyze_grid_detection(image_path: str):
    """グリッド線検出の詳細分析"""
    print(f"\n📊 分析中: {os.path.basename(image_path)}")
    
    # 画像読み込み
    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    
    print(f"画像サイズ: {width}×{height}")
    
    # グレースケール変換
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # 複数の手法でエッジを検出
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    # 1. 元画像
    axes[0, 0].imshow(img_array)
    axes[0, 0].set_title("Original Image")
    axes[0, 0].axis('off')
    
    # 2. グレースケール
    axes[0, 1].imshow(gray, cmap='gray')
    axes[0, 1].set_title("Grayscale")
    axes[0, 1].axis('off')
    
    # 3. Canny (低しきい値)
    edges1 = cv2.Canny(gray, 20, 60)
    axes[0, 2].imshow(edges1, cmap='gray')
    axes[0, 2].set_title("Canny (20, 60)")
    axes[0, 2].axis('off')
    
    # 4. Canny (中しきい値)
    edges2 = cv2.Canny(gray, 50, 150)
    axes[1, 0].imshow(edges2, cmap='gray')
    axes[1, 0].set_title("Canny (50, 150)")
    axes[1, 0].axis('off')
    
    # 5. Sobel Y方向
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    sobel_y_abs = np.abs(sobel_y)
    axes[1, 1].imshow(sobel_y_abs, cmap='gray')
    axes[1, 1].set_title("Sobel Y")
    axes[1, 1].axis('off')
    
    # 6. 水平投影プロファイル
    # エッジの水平投影
    horizontal_projection = np.sum(edges2, axis=1)
    axes[1, 2].plot(horizontal_projection, range(height))
    axes[1, 2].set_ylim(height, 0)
    axes[1, 2].set_xlabel("Edge Count")
    axes[1, 2].set_ylabel("Y Position")
    axes[1, 2].set_title("Horizontal Projection")
    axes[1, 2].grid(True)
    
    # しきい値のラインを追加
    threshold = width * 0.4
    axes[1, 2].axvline(x=threshold, color='r', linestyle='--', label=f'Threshold={threshold:.0f}')
    axes[1, 2].legend()
    
    plt.tight_layout()
    plt.savefig('grid_detection_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 実際の線検出
    print("\n水平線検出結果:")
    print(f"しきい値: {threshold:.0f}")
    
    detected_lines = []
    for y in range(height):
        if horizontal_projection[y] > threshold:
            detected_lines.append(y)
            print(f"  Y={y}: エッジ数={horizontal_projection[y]}")
    
    print(f"\n検出された線の数: {len(detected_lines)}")
    
    # より詳細な分析
    print("\n詳細分析:")
    
    # グレースケール値の分布
    print(f"グレースケール値: 最小={np.min(gray)}, 最大={np.max(gray)}, 平均={np.mean(gray):.1f}")
    
    # Y方向の変化を分析
    y_gradients = []
    for y in range(1, height-1):
        gradient = np.mean(np.abs(gray[y, :].astype(float) - gray[y-1, :].astype(float)))
        y_gradients.append(gradient)
    
    y_gradients = np.array(y_gradients)
    print(f"Y方向勾配: 最小={np.min(y_gradients):.1f}, 最大={np.max(y_gradients):.1f}, 平均={np.mean(y_gradients):.1f}")
    
    # 勾配のピークを検出
    gradient_threshold = np.mean(y_gradients) + np.std(y_gradients)
    print(f"勾配しきい値: {gradient_threshold:.1f}")
    
    gradient_peaks = []
    for i, grad in enumerate(y_gradients):
        if grad > gradient_threshold:
            gradient_peaks.append(i+1)  # インデックス調整
    
    print(f"勾配ピーク数: {len(gradient_peaks)}")
    
    return {
        "detected_lines": detected_lines,
        "gradient_peaks": gradient_peaks,
        "horizontal_projection": horizontal_projection,
        "y_gradients": y_gradients
    }

def visualize_line_detection(image_path: str, results: dict):
    """検出結果を可視化"""
    img = Image.open(image_path)
    img_array = np.array(img)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 左側: 画像with検出線
    ax1.imshow(img_array)
    
    # Cannyエッジ検出の線
    for y in results["detected_lines"]:
        ax1.axhline(y=y, color='red', alpha=0.5, linewidth=1)
    
    # 勾配ピークの線
    for y in results["gradient_peaks"]:
        ax1.axhline(y=y, color='blue', alpha=0.5, linewidth=1)
    
    ax1.set_title("Detected Lines (Red: Canny, Blue: Gradient)")
    ax1.axis('off')
    
    # 右側: プロファイル
    ax2.plot(results["y_gradients"], range(len(results["y_gradients"])), 'b-', label='Y Gradient')
    ax2.set_ylim(len(results["y_gradients"]), 0)
    ax2.set_xlabel("Gradient Value")
    ax2.set_ylabel("Y Position")
    ax2.set_title("Y Direction Gradient Profile")
    ax2.grid(True)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig('line_detection_visualization.png', dpi=150, bbox_inches='tight')
    plt.close()

def main():
    """メイン処理"""
    # テスト画像
    test_image = "graphs/optimal_v2/S__78209130_optimal.png"
    
    if os.path.exists(test_image):
        results = analyze_grid_detection(test_image)
        visualize_line_detection(test_image, results)
        
        print("\n📊 分析結果を保存しました:")
        print("  - grid_detection_analysis.png")
        print("  - line_detection_visualization.png")
    else:
        print(f"❌ テスト画像が見つかりません: {test_image}")

if __name__ == "__main__":
    main()