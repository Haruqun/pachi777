#!/usr/bin/env python3
"""
精密なグラフ境界検出ツール
ゼロライン検出をベースに、正確なグラフ境界を特定
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os
import json
from datetime import datetime

class PreciseGraphBoundaryDetector:
    """精密なグラフ境界検出クラス"""
    
    def __init__(self, input_dir="graphs/original", output_dir="graphs/precise_boundaries"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.overlay_dir = os.path.join(output_dir, "overlays")
        self.cropped_dir = os.path.join(output_dir, "cropped")
        
        # 出力ディレクトリを作成
        for dir_path in [self.output_dir, self.overlay_dir, self.cropped_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def detect_zero_line(self, img):
        """ゼロライン検出（前回の成功アルゴリズム）"""
        height, width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # グラフエリアを推定
        top_margin = int(height * 0.2)
        bottom_margin = int(height * 0.8)
        left_margin = int(width * 0.1)
        right_margin = int(width * 0.9)
        
        graph_region = gray[top_margin:bottom_margin, left_margin:right_margin]
        graph_height, graph_width = graph_region.shape
        
        # 水平線の候補を検出
        best_score = -1
        best_y = 0
        
        for y in range(graph_height):
            row = graph_region[y, :]
            
            # スコア計算
            darkness = 1.0 - (np.mean(row) / 255.0)
            uniformity = 1.0 - (np.std(row) / 128.0)
            uniformity = max(0, uniformity)
            min_darkness = 1.0 - (np.min(row) / 255.0)
            
            # 連続性
            dark_pixels = (row < 100).astype(int)
            max_run = 0
            current_run = 0
            for pixel in dark_pixels:
                if pixel:
                    current_run += 1
                    max_run = max(max_run, current_run)
                else:
                    current_run = 0
            continuity = max_run / graph_width
            
            total_score = (
                darkness * 0.25 +
                uniformity * 0.20 +
                min_darkness * 0.25 +
                continuity * 0.30
            )
            
            if total_score > best_score:
                best_score = total_score
                best_y = y + top_margin  # 元の画像座標
        
        return best_y, best_score
    
    def detect_graph_boundaries(self, img, zero_line_y):
        """ゼロラインを基準にグラフ境界を検出"""
        height, width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        print(f"ゼロライン位置: Y={zero_line_y}")
        
        # 1. 左右の境界を検出（より正確に）
        # ゼロライン付近でY軸ラベル「30,000」「-30,000」の終端を探す
        sample_height = 50
        sample_start = max(0, zero_line_y - sample_height)
        sample_end = min(height, zero_line_y + sample_height)
        sample_region = gray[sample_start:sample_end, :]
        
        # 各列のエッジ強度を計算
        edges = cv2.Sobel(sample_region, cv2.CV_64F, 1, 0, ksize=3)
        col_edge_strength = np.mean(np.abs(edges), axis=0)
        
        # 左境界：Y軸ラベルの右端を探す
        # 左から右へスキャンして、エッジが安定し始める点
        left_boundary = 0
        edge_threshold = np.percentile(col_edge_strength, 30)
        
        # 左側の1/3から探索開始
        for x in range(width//3):
            if x > 50 and col_edge_strength[x] < edge_threshold:
                # エッジが弱くなった = Y軸ラベルが終わった
                left_boundary = x + 10  # 少し余裕を持たせる
                break
        
        # 右境界：右側の数値軸の左端を探す
        right_boundary = width
        # 右側の1/3から探索開始
        for x in range(width - width//3, width):
            if x < width - 50 and col_edge_strength[x] < edge_threshold:
                # エッジが弱くなった = 数値軸が始まる前
                right_boundary = x - 10  # 少し余裕を持たせる
                break
        
        # 2. 上境界を検出（グラフ開始位置）
        # オレンジバーの下端を探す
        orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
        
        # オレンジバーの最下端を見つける
        orange_bottom = 0
        for y in range(height//2):  # 上半分のみ探索
            if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
                orange_bottom = y
        
        # グラフの実際の開始位置（30,000ライン）
        # オレンジバーの少し下から探索
        top_boundary = orange_bottom + 10
        
        # Y軸ラベル「30,000」を探す
        for y in range(orange_bottom + 10, zero_line_y - 50):
            row_region = gray[y:y+30, left_boundary-50:left_boundary]
            if row_region.shape[0] > 0 and row_region.shape[1] > 0:
                # テキストがある領域は分散が高い
                if np.var(row_region) > 500:
                    top_boundary = y + 30  # テキストの下
                    break
        
        # 3. 下境界を検出（グラフ終了位置）
        # -30,000ラインを探す、または「最大値」テキストの上
        bottom_boundary = zero_line_y
        
        # 「最大値」テキストを探す（ゼロラインより下）
        for y in range(zero_line_y + 50, min(height, zero_line_y + 500)):
            row_region = gray[y:y+30, left_boundary:right_boundary]
            if row_region.shape[0] > 0:
                # テキスト領域の特徴
                row_mean = np.mean(row_region)
                row_var = np.var(row_region)
                # 明るい背景に暗いテキスト
                if row_mean > 180 and row_var > 800:
                    bottom_boundary = y - 10  # テキストの上
                    break
        
        # 4. ゼロラインからの比率で微調整
        # グラフは通常、ゼロラインが中央付近にある
        zero_to_top = zero_line_y - top_boundary
        zero_to_bottom = bottom_boundary - zero_line_y
        
        # 上下の比率が極端に偏っている場合は調整
        if zero_to_top > zero_to_bottom * 1.5:
            # 上が広すぎる
            top_boundary = zero_line_y - int(zero_to_bottom * 1.2)
        elif zero_to_bottom > zero_to_top * 1.5:
            # 下が広すぎる  
            bottom_boundary = zero_line_y + int(zero_to_top * 1.2)
        
        return {
            'left': left_boundary,
            'right': right_boundary,
            'top': top_boundary,
            'bottom': bottom_boundary,
            'zero_line': zero_line_y,
            'width': right_boundary - left_boundary,
            'height': bottom_boundary - top_boundary
        }
    
    def create_overlay(self, img, boundaries):
        """境界検出結果をオーバーレイ"""
        overlay = img.copy()
        height, width = img.shape[:2]
        
        # 1. ゼロライン（赤色、太線）
        cv2.line(overlay, (0, boundaries['zero_line']), (width, boundaries['zero_line']), 
                (0, 0, 255), 3)
        cv2.putText(overlay, "Zero Line (0)", 
                   (10, boundaries['zero_line'] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # 2. グラフ境界（緑色）
        cv2.rectangle(overlay, 
                     (boundaries['left'], boundaries['top']), 
                     (boundaries['right'], boundaries['bottom']), 
                     (0, 255, 0), 2)
        
        # 3. 境界ラベル
        # 左境界
        cv2.line(overlay, (boundaries['left'], 0), (boundaries['left'], height), 
                (0, 255, 0), 2)
        cv2.putText(overlay, "Left", 
                   (boundaries['left'] + 5, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 右境界
        cv2.line(overlay, (boundaries['right'], 0), (boundaries['right'], height), 
                (0, 255, 0), 2)
        cv2.putText(overlay, "Right", 
                   (boundaries['right'] - 50, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 上境界（30,000）
        cv2.line(overlay, (boundaries['left'], boundaries['top']), 
                (boundaries['right'], boundaries['top']), 
                (0, 255, 0), 2)
        cv2.putText(overlay, "30,000", 
                   (boundaries['left'] + 10, boundaries['top'] + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 下境界（-30,000）
        cv2.line(overlay, (boundaries['left'], boundaries['bottom']), 
                (boundaries['right'], boundaries['bottom']), 
                (0, 255, 0), 2)
        cv2.putText(overlay, "-30,000", 
                   (boundaries['left'] + 10, boundaries['bottom'] - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 4. サイズ情報
        info_text = f"Graph Size: {boundaries['width']}x{boundaries['height']}px"
        cv2.putText(overlay, info_text, 
                   (width - 300, height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return overlay
    
    def crop_graph(self, img, boundaries):
        """検出された境界でグラフを切り抜き"""
        cropped = img[boundaries['top']:boundaries['bottom'], 
                     boundaries['left']:boundaries['right']]
        return cropped
    
    def process_image(self, image_path):
        """単一画像を処理"""
        print(f"\n{'='*60}")
        print(f"精密境界検出: {os.path.basename(image_path)}")
        print(f"{'='*60}")
        
        img = cv2.imread(image_path)
        if img is None:
            print(f"エラー: 画像を読み込めません: {image_path}")
            return None
        
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # 1. ゼロライン検出
        zero_line_y, zero_score = self.detect_zero_line(img)
        print(f"ゼロライン検出: Y={zero_line_y}, スコア={zero_score:.3f}")
        
        # 2. グラフ境界検出
        boundaries = self.detect_graph_boundaries(img, zero_line_y)
        print(f"グラフ境界: ")
        print(f"  左: {boundaries['left']}")
        print(f"  右: {boundaries['right']}")
        print(f"  上: {boundaries['top']} (30,000)")
        print(f"  下: {boundaries['bottom']} (-30,000)")
        print(f"  サイズ: {boundaries['width']}x{boundaries['height']}")
        
        # 3. オーバーレイ画像作成
        overlay_img = self.create_overlay(img, boundaries)
        overlay_path = os.path.join(self.overlay_dir, f"{base_name}_boundaries.png")
        cv2.imwrite(overlay_path, overlay_img)
        print(f"オーバーレイ保存: {overlay_path}")
        
        # 4. グラフ切り抜き
        cropped_img = self.crop_graph(img, boundaries)
        cropped_path = os.path.join(self.cropped_dir, f"{base_name}_graph.png")
        cv2.imwrite(cropped_path, cropped_img)
        print(f"切り抜き保存: {cropped_path}")
        
        # 結果データ
        result = {
            'file_name': base_name,
            'image_size': img.shape[:2][::-1],  # (width, height)
            'zero_line': {
                'y_position': zero_line_y,
                'score': float(zero_score)
            },
            'boundaries': boundaries,
            'cropped_size': (boundaries['width'], boundaries['height'])
        }
        
        return result
    
    def process_all(self):
        """全画像を処理"""
        print(f"\n{'='*80}")
        print("精密境界検出パイプライン開始")
        print(f"{'='*80}")
        
        # 画像ファイルを取得
        import glob
        image_files = glob.glob(os.path.join(self.input_dir, "*.jpg"))
        image_files.sort()
        
        print(f"処理対象: {len(image_files)}枚")
        
        results = []
        
        # まず5枚をテスト
        for image_path in image_files[:5]:
            result = self.process_image(image_path)
            if result:
                results.append(result)
        
        # サマリーレポート
        self.generate_summary(results)
        
        return results
    
    def generate_summary(self, results):
        """サマリーレポートを生成"""
        print(f"\n{'='*80}")
        print("精密境界検出完了サマリー")
        print(f"{'='*80}")
        
        if results:
            print(f"\n処理完了: {len(results)}枚")
            
            # 境界サイズの統計
            widths = [r['boundaries']['width'] for r in results]
            heights = [r['boundaries']['height'] for r in results]
            
            print(f"\nグラフサイズ:")
            print(f"  幅: 平均 {np.mean(widths):.0f}px, 範囲 {min(widths)}-{max(widths)}px")
            print(f"  高さ: 平均 {np.mean(heights):.0f}px, 範囲 {min(heights)}-{max(heights)}px")
            
            # ゼロライン位置
            zero_positions = [r['zero_line']['y_position'] for r in results]
            print(f"\nゼロライン位置:")
            print(f"  平均: {np.mean(zero_positions):.0f}")
            print(f"  範囲: {min(zero_positions)}-{max(zero_positions)}")
            
            # 個別結果
            print(f"\n個別結果:")
            for result in results:
                print(f"  {result['file_name']}: {result['boundaries']['width']}x{result['boundaries']['height']}px")
        
        # レポート保存
        report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_processed': len(results),
            'results': results
        }
        
        report_path = os.path.join(self.output_dir, f"boundary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\nレポート保存: {report_path}")

def main():
    """メイン処理"""
    detector = PreciseGraphBoundaryDetector()
    results = detector.process_all()

if __name__ == "__main__":
    main()