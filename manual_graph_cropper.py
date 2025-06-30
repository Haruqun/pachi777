#!/usr/bin/env python3
"""
手動観察に基づく精密なグラフ切り出しツール
観察された共通パターンを使用して正確にグラフエリアを抽出
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os
import json
from datetime import datetime

class ManualGraphCropper:
    """手動観察に基づくグラフ切り出しクラス"""
    
    def __init__(self, input_dir="graphs/original", output_dir="graphs/manual_crop"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.overlay_dir = os.path.join(output_dir, "overlays")
        self.cropped_dir = os.path.join(output_dir, "cropped")
        
        # 出力ディレクトリを作成
        for dir_path in [self.output_dir, self.overlay_dir, self.cropped_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def detect_key_elements(self, img):
        """画像の主要要素を検出"""
        height, width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 1. オレンジバーを検出
        orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
        orange_bottom = 0
        
        # オレンジバーの最下端
        for y in range(height//2):
            if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
                orange_bottom = y
        
        print(f"オレンジバー下端: Y={orange_bottom}")
        
        # 2. Y軸ラベル領域を推定
        # 「30,000」テキストを含む領域を探す
        # オレンジバーの下、左側1/3エリア
        search_area = gray[orange_bottom+20:orange_bottom+200, :width//3]
        
        # テキストらしい領域（分散が高い）を探す
        y_label_top = orange_bottom + 50  # デフォルト
        for y in range(search_area.shape[0]):
            row_variance = np.var(search_area[y, :])
            if row_variance > 500:  # テキストがある
                y_label_top = orange_bottom + 20 + y
                break
        
        print(f"Y軸ラベル上端（推定）: Y={y_label_top}")
        
        # 3. グラフの実際の境界を定義
        # 観察に基づく固定オフセット（ゼロラインから±500px版）
        boundaries = {
            'orange_bottom': orange_bottom,
            'graph_top': y_label_top + 40 + 30 - 200,      # 暫定的な上端
            'graph_left': 90 + 30 + 2,                     # Y軸ラベルの右側（固定値）+ 30px調整 + 2px右へ
            'graph_right': width - 90 + 40 - 100,          # 右側の数値の左側（固定値）+ 40px調整 - 100px（左に移動）
            'y_label_region': (y_label_top, y_label_top + 40)
        }
        
        # 4. ゼロラインを検出（グラフ内で）
        graph_region = gray[boundaries['graph_top']:boundaries['graph_top']+600, 
                           boundaries['graph_left']:boundaries['graph_right']]
        
        best_zero_y = 0
        best_score = -1
        
        for y in range(100, min(500, graph_region.shape[0]-100)):  # 中央付近を探索
            row = graph_region[y, :]
            # 暗い水平線の特徴
            darkness = 1.0 - (np.mean(row) / 255.0)
            uniformity = 1.0 - (np.std(row) / 128.0)
            
            score = darkness * 0.5 + uniformity * 0.5
            if score > best_score:
                best_score = score
                best_zero_y = y
        
        boundaries['zero_line'] = boundaries['graph_top'] + best_zero_y
        print(f"ゼロライン: Y={boundaries['zero_line']}")
        
        # 5. グラフの下端を決定
        # ゼロラインから対称的な距離、または「最大値」テキストの上
        zero_to_top = boundaries['zero_line'] - boundaries['graph_top']
        
        # 対称的な位置
        symmetric_bottom = boundaries['zero_line'] + zero_to_top
        
        # 「最大値」テキストを探す
        text_bottom = height
        for y in range(boundaries['zero_line'] + 100, min(height-100, boundaries['zero_line'] + 500)):
            row_region = gray[y:y+50, boundaries['graph_left']:boundaries['graph_right']]
            if row_region.shape[0] > 0:
                # 明るい背景に暗いテキスト
                if np.mean(row_region) > 180 and np.var(row_region) > 800:
                    text_bottom = y - 10
                    break
        
        # 5.5. ゼロラインから正確に±250pxで上下端を再設定
        boundaries['graph_top'] = boundaries['zero_line'] - 250
        boundaries['graph_bottom'] = boundaries['zero_line'] + 250
        
        # 境界チェック
        if boundaries['graph_top'] < 0:
            boundaries['graph_top'] = 0
        if boundaries['graph_bottom'] > height:
            boundaries['graph_bottom'] = height
        
        # 6. サイズ情報
        boundaries['width'] = boundaries['graph_right'] - boundaries['graph_left']
        boundaries['height'] = boundaries['graph_bottom'] - boundaries['graph_top']
        
        return boundaries
    
    def create_detailed_overlay(self, img, boundaries):
        """詳細なオーバーレイを作成"""
        overlay = img.copy()
        height, width = img.shape[:2]
        
        # 1. グラフ境界（太い緑線）
        cv2.rectangle(overlay, 
                     (boundaries['graph_left'], boundaries['graph_top']), 
                     (boundaries['graph_right'], boundaries['graph_bottom']), 
                     (0, 255, 0), 3)
        
        # 2. ゼロライン（赤線）
        cv2.line(overlay, 
                (boundaries['graph_left'], boundaries['zero_line']), 
                (boundaries['graph_right'], boundaries['zero_line']), 
                (0, 0, 255), 2)
        cv2.putText(overlay, "Zero Line", 
                   (boundaries['graph_left'] + 10, boundaries['zero_line'] - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # 2.5. ゼロラインから10pxごとの補助線を追加（数値付き）
        # 上方向（正の値）
        y = boundaries['zero_line'] - 10
        line_count = 1
        while y > boundaries['graph_top']:
            # 50px（5本）ごとに太い線と大きい数値
            if line_count % 5 == 0:
                cv2.line(overlay, 
                        (boundaries['graph_left'], y), 
                        (boundaries['graph_right'], y), 
                        (255, 100, 100), 2)  # 薄い赤色、太め
                # 右端にピクセル数を表示（大きめ）
                cv2.putText(overlay, f"+{line_count * 10}", 
                           (boundaries['graph_right'] + 5, y + 3), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                # 左端にも表示
                cv2.putText(overlay, f"+{line_count * 10}", 
                           (boundaries['graph_left'] - 40, y + 3), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            else:
                cv2.line(overlay, 
                        (boundaries['graph_left'], y), 
                        (boundaries['graph_right'], y), 
                        (200, 200, 200), 1, cv2.LINE_AA)  # 薄いグレー
                # 10px単位の小さい数値（10の倍数ごと）
                if line_count % 2 == 0:  # 20, 40, 60, 80...
                    cv2.putText(overlay, f"{line_count * 10}", 
                               (boundaries['graph_left'] + 5, y - 2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (150, 150, 150), 1)
            y -= 10
            line_count += 1
        
        # 下方向（負の値）
        y = boundaries['zero_line'] + 10
        line_count = 1
        while y < boundaries['graph_bottom']:
            # 50px（5本）ごとに太い線と大きい数値
            if line_count % 5 == 0:
                cv2.line(overlay, 
                        (boundaries['graph_left'], y), 
                        (boundaries['graph_right'], y), 
                        (100, 100, 255), 2)  # 薄い青色、太め
                # 右端にピクセル数を表示（大きめ）
                cv2.putText(overlay, f"-{line_count * 10}", 
                           (boundaries['graph_right'] + 5, y + 3), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                # 左端にも表示
                cv2.putText(overlay, f"-{line_count * 10}", 
                           (boundaries['graph_left'] - 40, y + 3), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            else:
                cv2.line(overlay, 
                        (boundaries['graph_left'], y), 
                        (boundaries['graph_right'], y), 
                        (200, 200, 200), 1, cv2.LINE_AA)  # 薄いグレー
                # 10px単位の小さい数値（10の倍数ごと）
                if line_count % 2 == 0:  # 20, 40, 60, 80...
                    cv2.putText(overlay, f"{line_count * 10}", 
                               (boundaries['graph_left'] + 5, y - 2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (150, 150, 150), 1)
            y += 10
            line_count += 1
        
        # 3. オレンジバー位置（黄線）
        cv2.line(overlay, (0, boundaries['orange_bottom']), (width, boundaries['orange_bottom']), 
                (0, 255, 255), 1)
        cv2.putText(overlay, "Orange Bar Bottom", 
                   (10, boundaries['orange_bottom'] + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # 4. Y軸ラベル領域（シアン）
        y_top, y_bottom = boundaries['y_label_region']
        cv2.rectangle(overlay, (0, y_top), (boundaries['graph_left']-5, y_bottom), 
                     (255, 255, 0), 2)
        cv2.putText(overlay, "Y-axis labels", 
                   (5, y_top - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # 5. 境界線のラベル
        # 上端
        cv2.putText(overlay, f"Top (Y={boundaries['graph_top']})", 
                   (boundaries['graph_left'] + 10, boundaries['graph_top'] + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 下端
        cv2.putText(overlay, f"Bottom (Y={boundaries['graph_bottom']})", 
                   (boundaries['graph_left'] + 10, boundaries['graph_bottom'] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 左端
        cv2.putText(overlay, f"L={boundaries['graph_left']}", 
                   (boundaries['graph_left'] - 50, height//2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
        
        # 右端
        cv2.putText(overlay, f"R={boundaries['graph_right']}", 
                   (boundaries['graph_right'] + 5, height//2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
        
        # 6. サイズ情報
        info_text = f"Graph: {boundaries['width']}x{boundaries['height']}px"
        cv2.rectangle(overlay, (width-250, height-40), (width-10, height-10), (0, 0, 0), -1)
        cv2.putText(overlay, info_text, 
                   (width-240, height-20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        return overlay
    
    def crop_graph(self, img, boundaries):
        """グラフエリアを切り出し"""
        cropped = img[boundaries['graph_top']:boundaries['graph_bottom'], 
                     boundaries['graph_left']:boundaries['graph_right']]
        return cropped
    
    def process_image(self, image_path):
        """単一画像を処理"""
        print(f"\n{'='*60}")
        print(f"手動観察ベース切り出し: {os.path.basename(image_path)}")
        print(f"{'='*60}")
        
        img = cv2.imread(image_path)
        if img is None:
            print(f"エラー: 画像を読み込めません: {image_path}")
            return None
        
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # 1. 主要要素を検出
        boundaries = self.detect_key_elements(img)
        print(f"グラフ境界: ({boundaries['graph_left']}, {boundaries['graph_top']}) - "
              f"({boundaries['graph_right']}, {boundaries['graph_bottom']})")
        print(f"サイズ: {boundaries['width']}x{boundaries['height']}")
        
        # 2. オーバーレイ画像作成
        overlay_img = self.create_detailed_overlay(img, boundaries)
        overlay_path = os.path.join(self.overlay_dir, f"{base_name}_manual_overlay.png")
        cv2.imwrite(overlay_path, overlay_img)
        print(f"オーバーレイ保存: {overlay_path}")
        
        # 3. グラフ切り抜き
        cropped_img = self.crop_graph(img, boundaries)
        cropped_path = os.path.join(self.cropped_dir, f"{base_name}_graph_only.png")
        cv2.imwrite(cropped_path, cropped_img)
        print(f"切り抜き保存: {cropped_path}")
        
        # 結果データ
        result = {
            'file_name': base_name,
            'image_size': img.shape[:2][::-1],
            'boundaries': boundaries,
            'cropped_size': (boundaries['width'], boundaries['height'])
        }
        
        return result
    
    def process_all(self):
        """全画像を処理"""
        print(f"\n{'='*80}")
        print("手動観察ベース切り出しパイプライン開始")
        print(f"{'='*80}")
        
        # 画像ファイルを取得
        import glob
        image_files = glob.glob(os.path.join(self.input_dir, "*.jpg"))
        image_files.sort()
        
        print(f"処理対象: {len(image_files)}枚")
        
        results = []
        
        # すべての画像を処理
        for image_path in image_files:
            result = self.process_image(image_path)
            if result:
                results.append(result)
        
        # サマリーレポート
        self.generate_summary(results)
        
        return results
    
    def generate_summary(self, results):
        """サマリーレポートを生成"""
        print(f"\n{'='*80}")
        print("手動観察ベース切り出し完了サマリー")
        print(f"{'='*80}")
        
        if results:
            print(f"\n処理完了: {len(results)}枚")
            
            # サイズ統計
            widths = [r['boundaries']['width'] for r in results]
            heights = [r['boundaries']['height'] for r in results]
            
            print(f"\nグラフサイズ:")
            print(f"  幅: 平均 {np.mean(widths):.0f}px, 範囲 {min(widths)}-{max(widths)}px")
            print(f"  高さ: 平均 {np.mean(heights):.0f}px, 範囲 {min(heights)}-{max(heights)}px")
            
            # 個別結果
            print(f"\n個別結果:")
            for result in results:
                print(f"  {result['file_name']}: {result['boundaries']['width']}x{result['boundaries']['height']}px")

def main():
    """メイン処理"""
    cropper = ManualGraphCropper()
    results = cropper.process_all()

if __name__ == "__main__":
    main()