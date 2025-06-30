#!/usr/bin/env python3
"""
改良版色検出器 - ピンク、青、紫の3色を確実に検出
"""

import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd

class ImprovedColorDetector:
    """3色（ピンク、青、紫）の検出精度を向上させた検出器"""
    
    def __init__(self):
        # 最適化された色範囲（HSV）
        self.color_ranges_hsv = {
            # ピンク: 赤みがかったピンク色
            "pink": [
                [(160, 30, 100), (180, 255, 255)],  # 赤寄りのピンク
                [(0, 30, 100), (10, 255, 255)],     # 赤の折り返し部分
                [(150, 20, 120), (170, 150, 255)]   # 薄いピンク
            ],
            # 青: 水色からシアンまで含む
            "blue": [
                [(85, 30, 80), (115, 255, 255)],    # 標準的な青
                [(75, 20, 100), (125, 200, 255)],   # 薄い青・水色
                [(90, 15, 120), (110, 150, 255)],   # より薄い青
                [(100, 25, 90), (120, 255, 255)]    # シアン寄り
            ],
            # 紫: 青紫から赤紫まで
            "purple": [
                [(120, 30, 70), (150, 255, 255)],   # 青紫
                [(130, 20, 80), (145, 200, 255)],   # 薄い紫
                [(140, 25, 60), (160, 255, 255)]    # 赤紫寄り
            ]
        }
        
        # RGB色範囲（補助的に使用）
        self.color_ranges_rgb = {
            "pink": {
                "r_min": 180, "r_max": 255,
                "g_min": 100, "g_max": 200,
                "b_min": 150, "b_max": 220
            },
            "blue": {
                "r_min": 100, "r_max": 200,
                "g_min": 150, "g_max": 255,
                "b_min": 180, "b_max": 255
            },
            "purple": {
                "r_min": 150, "r_max": 220,
                "g_min": 100, "g_max": 180,
                "b_min": 180, "b_max": 255
            }
        }
        
        # 日本語フォント設定
        self.setup_japanese_font()
    
    def setup_japanese_font(self):
        """日本語フォント設定"""
        font_paths = [
            '/Library/Fonts/Osaka.ttf',
            '/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc'
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font_prop = font_manager.FontProperties(fname=font_path)
                    plt.rcParams['font.family'] = font_prop.get_name()
                    break
                except:
                    continue
    
    def detect_color_multi_method(self, img):
        """複数の方法を組み合わせた色検出"""
        h, w = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 各色のスコアを計算
        color_scores = {}
        color_masks = {}
        
        for color_name in ["pink", "blue", "purple"]:
            # HSVベースの検出
            hsv_mask = np.zeros((h, w), dtype=np.uint8)
            for lower, upper in self.color_ranges_hsv[color_name]:
                mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
                hsv_mask = cv2.bitwise_or(hsv_mask, mask)
            
            # RGBベースの検出（補助）
            rgb_range = self.color_ranges_rgb[color_name]
            rgb_mask = cv2.inRange(img, 
                np.array([rgb_range["b_min"], rgb_range["g_min"], rgb_range["r_min"]]),
                np.array([rgb_range["b_max"], rgb_range["g_max"], rgb_range["r_max"]])
            )
            
            # マスクの結合（HSVを主、RGBを補助として使用）
            combined_mask = cv2.bitwise_or(hsv_mask, cv2.bitwise_and(hsv_mask, rgb_mask))
            
            # ノイズ除去
            kernel = np.ones((3, 3), np.uint8)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
            
            # グラフ領域（中央部）での検出を重視
            center_x = w // 2
            center_region = combined_mask[:, center_x-100:center_x+100]
            
            # スコア計算（中央部の重みを高く）
            total_pixels = np.sum(combined_mask > 0)
            center_pixels = np.sum(center_region > 0)
            score = total_pixels + center_pixels * 2  # 中央部は2倍の重み
            
            color_scores[color_name] = score
            color_masks[color_name] = combined_mask
        
        # 最高スコアの色を選択
        detected_color = max(color_scores, key=color_scores.get)
        detected_mask = color_masks[detected_color]
        
        # 青の場合は追加の細線強調処理
        if detected_color == "blue":
            # 細い線を強調
            kernel_line = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
            detected_mask = cv2.dilate(detected_mask, kernel_line, iterations=1)
        
        return detected_mask, detected_color, color_scores
    
    def analyze_image(self, img_path):
        """画像の色を分析"""
        img = cv2.imread(img_path)
        if img is None:
            return None
        
        # グラフ領域の切り出し（おおよその領域）
        h, w = img.shape[:2]
        graph_region = img[int(h*0.1):int(h*0.9), int(w*0.1):int(w*0.9)]
        
        # 色検出
        mask, color, scores = self.detect_color_multi_method(graph_region)
        
        # 検出結果の統計
        pixels_detected = np.sum(mask > 0)
        total_pixels = mask.shape[0] * mask.shape[1]
        detection_rate = pixels_detected / total_pixels * 100
        
        return {
            'image': os.path.basename(img_path),
            'detected_color': color,
            'detection_rate': detection_rate,
            'scores': scores,
            'mask': mask
        }
    
    def test_all_images(self, image_dir):
        """すべての画像をテスト"""
        results = []
        
        # 画像ファイルを取得
        image_files = [f for f in os.listdir(image_dir) 
                      if f.endswith(('.png', '.jpg')) and 'optimal' in f]
        
        print("色検出テスト結果")
        print("=" * 80)
        print(f"{'画像':25} {'検出色':10} {'検出率':>10} {'ピンク':>10} {'青':>10} {'紫':>10}")
        print("-" * 80)
        
        for img_file in sorted(image_files):
            img_path = os.path.join(image_dir, img_file)
            result = self.analyze_image(img_path)
            
            if result:
                results.append(result)
                print(f"{result['image']:25} {result['detected_color']:10} "
                      f"{result['detection_rate']:>9.1f}% "
                      f"{result['scores']['pink']:>10} "
                      f"{result['scores']['blue']:>10} "
                      f"{result['scores']['purple']:>10}")
        
        return results
    
    def visualize_detection(self, results, output_dir='graphs/color_detection_test'):
        """検出結果を視覚化"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 色別の検出率統計
        color_stats = {'pink': [], 'blue': [], 'purple': []}
        for r in results:
            color_stats[r['detected_color']].append(r['detection_rate'])
        
        # 可視化
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # 1. 色別検出数
        colors = list(color_stats.keys())
        counts = [len(color_stats[c]) for c in colors]
        bars = ax1.bar(colors, counts, color=['pink', 'lightblue', 'lavender'])
        ax1.set_title('色別検出数')
        ax1.set_ylabel('画像数')
        
        # 数値を表示
        for bar, count in zip(bars, counts):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    str(count), ha='center', va='bottom')
        
        # 2. 検出率分布
        for color, rates in color_stats.items():
            if rates:
                ax2.hist(rates, bins=10, alpha=0.5, label=f'{color} (n={len(rates)})')
        
        ax2.set_title('色別検出率分布')
        ax2.set_xlabel('検出率 (%)')
        ax2.set_ylabel('頻度')
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'color_detection_summary.png'))
        plt.close()
        
        # 個別画像の検出結果も保存
        for i, result in enumerate(results[:6]):  # 最初の6枚
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
            
            # 元画像
            img_path = os.path.join('graphs/cropped', result['image'])
            if os.path.exists(img_path):
                img = cv2.imread(img_path)
                ax1.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                ax1.set_title(f"{result['image']}\n検出色: {result['detected_color']}")
                ax1.axis('off')
                
                # マスク
                ax2.imshow(result['mask'], cmap='hot')
                ax2.set_title(f"検出率: {result['detection_rate']:.1f}%")
                ax2.axis('off')
                
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, f'detection_{i}_{result["detected_color"]}.png'))
                plt.close()

def main():
    """メイン処理"""
    detector = ImprovedColorDetector()
    
    # テスト実行
    results = detector.test_all_images('graphs/cropped')
    
    # 結果を視覚化
    detector.visualize_detection(results)
    
    # 統計サマリー
    print("\n" + "=" * 80)
    print("統計サマリー")
    print("-" * 80)
    
    color_counts = {'pink': 0, 'blue': 0, 'purple': 0}
    for r in results:
        color_counts[r['detected_color']] += 1
    
    total = sum(color_counts.values())
    for color, count in color_counts.items():
        print(f"{color}: {count}枚 ({count/total*100:.1f}%)")
    
    print("\n✓ 色検出テスト完了")
    print("  結果は graphs/color_detection_test/ に保存されました")

if __name__ == "__main__":
    main()