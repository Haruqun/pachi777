#!/usr/bin/env python3
"""
完璧な切り抜き精度を目指す統合パイプライン
perfect_graph_cropper.pyの手法を基に、100%の精度でグラフを切り抜き
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os
import json
from datetime import datetime
import pandas as pd

class PerfectCropPipeline:
    """完璧な切り抜き精度を目指すパイプライン"""
    
    def __init__(self, original_dir="graphs/original", output_dir="graphs/perfect_pipeline"):
        self.original_dir = original_dir
        self.output_dir = output_dir
        self.cropped_dir = os.path.join(output_dir, "cropped")
        self.data_dir = os.path.join(output_dir, "extracted_data")
        self.report_dir = os.path.join(output_dir, "reports")
        
        # 出力ディレクトリを作成
        for dir_path in [self.output_dir, self.cropped_dir, self.data_dir, self.report_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # 標準グラフパラメータ（実測値）
        self.standard_width = 911
        self.standard_height = 797
        self.zero_line_offset_from_top = 477  # ゼロラインの標準位置（60%）
        self.critical_offset = 84  # 重要：実測による下方オフセット
        
    def detect_orange_bar(self, img):
        """オレンジバーを高精度で検出"""
        height, width = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 複数のオレンジ色範囲（照明条件に対応）
        orange_ranges = [
            # 標準的なオレンジ
            ((10, 100, 100), (30, 255, 255)),
            # より広い範囲
            ((5, 120, 120), (35, 255, 255)),
            # 明るいオレンジ
            ((15, 80, 80), (25, 255, 255))
        ]
        
        # 各範囲でマスクを作成
        combined_mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in orange_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            combined_mask = cv2.bitwise_or(combined_mask, mask)
        
        # 水平線を強調（形態学的処理）
        kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        enhanced_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_horizontal)
        
        # 各行のオレンジピクセル数を計算
        horizontal_projection = np.sum(enhanced_mask, axis=1) / 255
        
        # オレンジバーの候補を検出（行の40%以上がオレンジ）
        threshold = width * 0.4
        orange_candidates = []
        
        for y in range(height):
            if horizontal_projection[y] > threshold:
                orange_candidates.append(y)
        
        if not orange_candidates:
            return None
        
        # 連続する行をグループ化
        groups = []
        current_group = [orange_candidates[0]]
        
        for i in range(1, len(orange_candidates)):
            if orange_candidates[i] - orange_candidates[i-1] <= 3:
                current_group.append(orange_candidates[i])
            else:
                groups.append(current_group)
                current_group = [orange_candidates[i]]
        groups.append(current_group)
        
        # 最も密度の高いグループを選択
        best_group = max(groups, key=len)
        orange_bar_y = int(np.mean(best_group))
        
        return orange_bar_y
    
    def detect_zero_line(self, img, graph_area):
        """グラフ内のゼロラインを高精度で検出"""
        height, width = graph_area.shape[:2]
        gray = cv2.cvtColor(graph_area, cv2.COLOR_BGR2GRAY)
        
        # 左右20%を除外（ノイズ除去）
        left_margin = int(width * 0.2)
        right_margin = int(width * 0.8)
        center_region = gray[:, left_margin:right_margin]
        
        # 各行のスコアを計算
        scores = []
        for y in range(height):
            row = center_region[y, :]
            
            # 1. 暗さスコア（40%）
            darkness_score = 1.0 - (np.mean(row) / 255.0)
            
            # 2. 一様性スコア（30%）
            uniformity_score = 1.0 - (np.std(row) / 128.0)
            uniformity_score = max(0, uniformity_score)
            
            # 3. 最小値の暗さスコア（30%）
            min_val_score = 1.0 - (np.min(row) / 255.0)
            
            # 総合スコア
            total_score = (darkness_score * 0.4 + 
                          uniformity_score * 0.3 + 
                          min_val_score * 0.3)
            
            scores.append(total_score)
        
        # グラフ中央付近（±25%）で最高スコアの線を選択
        center_y = height // 2
        search_range = int(height * 0.25)
        
        best_score = -1
        best_y = center_y
        
        for y in range(max(0, center_y - search_range), 
                      min(height, center_y + search_range)):
            if scores[y] > best_score:
                best_score = scores[y]
                best_y = y
        
        return best_y
    
    def crop_graph_perfect(self, image_path):
        """完璧な精度でグラフを切り抜き"""
        print(f"\n切り抜き処理: {os.path.basename(image_path)}")
        
        img = cv2.imread(image_path)
        if img is None:
            print(f"エラー: 画像を読み込めません: {image_path}")
            return None, None
        
        height, width = img.shape[:2]
        
        # 1. オレンジバーを検出
        orange_y = self.detect_orange_bar(img)
        
        if orange_y is None:
            print("警告: オレンジバーが検出できません")
            return None, None
        
        print(f"オレンジバー検出: Y={orange_y}")
        
        # 2. グラフエリアの初期推定
        graph_top_initial = orange_y + 10  # オレンジバーの直下
        graph_bottom_initial = graph_top_initial + self.standard_height
        
        # 境界チェック
        if graph_bottom_initial > height:
            graph_bottom_initial = height
        
        # 3. 初期グラフエリアでゼロラインを検出
        initial_area = img[graph_top_initial:graph_bottom_initial, :]
        zero_line_in_area = self.detect_zero_line(img, initial_area)
        
        print(f"ゼロライン検出（エリア内）: Y={zero_line_in_area}")
        
        # 4. 実際のゼロライン位置を計算
        zero_line_absolute = graph_top_initial + zero_line_in_area
        
        # 5. 重要：84ピクセルオフセットを適用して最終的な切り抜き位置を決定
        graph_top = zero_line_absolute - self.zero_line_offset_from_top + self.critical_offset
        
        # 6. 左右の位置を計算（中央配置）
        graph_left = (width - self.standard_width) // 2
        graph_right = graph_left + self.standard_width
        
        # 7. 最終的な境界チェック
        graph_top = max(0, graph_top)
        graph_bottom = graph_top + self.standard_height
        
        if graph_bottom > height:
            graph_bottom = height
            graph_top = max(0, graph_bottom - self.standard_height)
        
        graph_left = max(0, graph_left)
        graph_right = min(width, graph_right)
        
        # 8. 切り抜き
        cropped = img[graph_top:graph_bottom, graph_left:graph_right]
        
        # 9. 精度情報を記録
        crop_info = {
            'orange_bar_y': orange_y,
            'zero_line_in_area': zero_line_in_area,
            'zero_line_absolute': zero_line_absolute,
            'graph_top': graph_top,
            'graph_bottom': graph_bottom,
            'graph_left': graph_left,
            'graph_right': graph_right,
            'actual_width': cropped.shape[1],
            'actual_height': cropped.shape[0],
            'width_accuracy': cropped.shape[1] / self.standard_width * 100,
            'height_accuracy': cropped.shape[0] / self.standard_height * 100
        }
        
        print(f"切り抜き領域: Y={graph_top}〜{graph_bottom}, X={graph_left}〜{graph_right}")
        print(f"切り抜きサイズ: {cropped.shape[1]}x{cropped.shape[0]} (目標: {self.standard_width}x{self.standard_height})")
        print(f"精度: 幅 {crop_info['width_accuracy']:.1f}%, 高さ {crop_info['height_accuracy']:.1f}%")
        
        return cropped, crop_info
    
    def extract_graph_data(self, cropped_img):
        """グラフデータを抽出（ピンク・青両対応）"""
        if cropped_img is None:
            return None, None
            
        height, width = cropped_img.shape[:2]
        
        # 実際のゼロライン位置（標準位置を使用）
        zero_y = int(height * 0.6)  # 60%位置
        
        # HSV変換
        hsv = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2HSV)
        
        # ピンク色と青色の検出
        pink_ranges = [
            ((150, 50, 50), (180, 255, 255)),
            ((140, 30, 100), (170, 255, 255)),
        ]
        
        blue_ranges = [
            ((100, 50, 50), (130, 255, 255)),
            ((90, 30, 100), (120, 255, 255)),
        ]
        
        # 各色のマスクを作成
        pink_mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in pink_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            pink_mask = cv2.bitwise_or(pink_mask, mask)
        
        blue_mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in blue_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            blue_mask = cv2.bitwise_or(blue_mask, mask)
        
        # 優勢な色を選択
        pink_pixels = np.sum(pink_mask)
        blue_pixels = np.sum(blue_mask)
        
        if pink_pixels > blue_pixels:
            primary_mask = pink_mask
            graph_color = "pink"
        else:
            primary_mask = blue_mask
            graph_color = "blue"
        
        # ノイズ除去
        kernel = np.ones((3, 3), np.uint8)
        mask_cleaned = cv2.morphologyEx(primary_mask, cv2.MORPH_CLOSE, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_OPEN, kernel)
        
        # データポイント抽出
        data_points = []
        for x in range(width):
            column = mask_cleaned[:, x]
            graph_pixels = np.where(column > 0)[0]
            
            if len(graph_pixels) > 0:
                y_pixel = graph_pixels[-1]
                
                # Y座標を実際の値に変換
                # ゼロラインからの距離を計算
                pixels_from_zero = zero_y - y_pixel
                
                # スケーリング（60%位置が0、上端が30000、下端が-30000）
                if y_pixel < zero_y:
                    # ゼロラインより上（正の値）
                    y_value = pixels_from_zero * (30000 / zero_y)
                else:
                    # ゼロラインより下（負の値）
                    y_value = pixels_from_zero * (30000 / (height - zero_y))
                
                data_points.append({
                    'x': x,
                    'y_pixel': y_pixel,
                    'y_value': y_value
                })
        
        return data_points, graph_color
    
    def process_image(self, image_path):
        """単一画像を処理"""
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # 1. 完璧な切り抜き
        cropped, crop_info = self.crop_graph_perfect(image_path)
        
        if cropped is None:
            return None
        
        # 切り抜き画像を保存
        cropped_path = os.path.join(self.cropped_dir, f"{base_name}_perfect.png")
        cv2.imwrite(cropped_path, cropped)
        
        # 2. データ抽出
        data_points, graph_color = self.extract_graph_data(cropped)
        
        if not data_points:
            print("警告: データポイントが検出されませんでした")
            return None
        
        # データをCSVに保存
        df = pd.DataFrame(data_points)
        csv_path = os.path.join(self.data_dir, f"{base_name}_data.csv")
        df.to_csv(csv_path, index=False)
        
        # 3. 統計情報
        y_values = [p['y_value'] for p in data_points]
        stats = {
            'file_name': base_name,
            'crop_info': crop_info,
            'graph_color': graph_color,
            'min_value': min(y_values),
            'max_value': max(y_values),
            'final_value': y_values[-1],
            'mean_value': np.mean(y_values),
            'data_points': len(data_points)
        }
        
        # 4. 可視化
        self.visualize_results(cropped, data_points, stats, base_name)
        
        return stats
    
    def visualize_results(self, img, data_points, stats, base_name):
        """結果を可視化"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # 1. 切り抜き画像
        axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        axes[0].set_title(f'切り抜き画像 ({stats["crop_info"]["actual_width"]}x{stats["crop_info"]["actual_height"]})')
        axes[0].axis('off')
        
        # ゼロラインを表示
        zero_y = int(img.shape[0] * 0.6)
        axes[0].axhline(y=zero_y, color='green', linestyle='--', alpha=0.5)
        
        # 2. 抽出データ
        x_values = [p['x'] for p in data_points]
        y_values = [p['y_value'] for p in data_points]
        
        color = 'hotpink' if stats['graph_color'] == 'pink' else 'blue'
        axes[1].plot(x_values, y_values, color=color, linewidth=2)
        axes[1].set_title(f'抽出データ ({stats["graph_color"]}色)')
        axes[1].set_xlabel('X座標')
        axes[1].set_ylabel('値')
        axes[1].grid(True, alpha=0.3)
        axes[1].axhline(y=0, color='red', linestyle='--', alpha=0.5)
        axes[1].set_ylim(-35000, 35000)
        
        # 統計情報
        stats_text = f"最大: {stats['max_value']:.0f}\n最終: {stats['final_value']:.0f}"
        axes[1].text(0.02, 0.98, stats_text, transform=axes[1].transAxes,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.suptitle(f'完璧切り抜きパイプライン: {base_name}')
        plt.tight_layout()
        
        viz_path = os.path.join(self.report_dir, f"{base_name}_visualization.png")
        plt.savefig(viz_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def process_all(self):
        """全画像を処理"""
        print(f"\n{'='*80}")
        print("完璧切り抜きパイプライン開始")
        print(f"{'='*80}")
        
        # 画像ファイルを取得
        import glob
        image_files = glob.glob(os.path.join(self.original_dir, "*.jpg"))
        image_files.sort()
        
        print(f"処理対象: {len(image_files)}枚")
        
        results = []
        crop_accuracies = []
        
        for image_path in image_files:
            result = self.process_image(image_path)
            if result:
                results.append(result)
                # 切り抜き精度を記録
                crop_accuracies.append({
                    'file': result['file_name'],
                    'width_acc': result['crop_info']['width_accuracy'],
                    'height_acc': result['crop_info']['height_accuracy']
                })
        
        # サマリーレポート
        self.generate_summary(results, crop_accuracies)
        
        return results
    
    def generate_summary(self, results, crop_accuracies):
        """サマリーレポートを生成"""
        print(f"\n{'='*80}")
        print("処理完了サマリー")
        print(f"{'='*80}")
        
        # 切り抜き精度の統計
        if crop_accuracies:
            width_accs = [ca['width_acc'] for ca in crop_accuracies]
            height_accs = [ca['height_acc'] for ca in crop_accuracies]
            
            print(f"\n切り抜き精度:")
            print(f"  幅精度: 平均 {np.mean(width_accs):.1f}%, 最小 {min(width_accs):.1f}%, 最大 {max(width_accs):.1f}%")
            print(f"  高さ精度: 平均 {np.mean(height_accs):.1f}%, 最小 {min(height_accs):.1f}%, 最大 {max(height_accs):.1f}%")
            
            # 100%精度の数
            perfect_crops = sum(1 for ca in crop_accuracies 
                              if ca['width_acc'] == 100 and ca['height_acc'] == 100)
            print(f"  完璧な切り抜き: {perfect_crops}/{len(crop_accuracies)}枚")
        
        # 各画像の結果
        print(f"\n処理結果:")
        for result in results:
            print(f"\n{result['file_name']}:")
            print(f"  グラフ色: {result['graph_color']}")
            print(f"  最大値: {result['max_value']:.0f}")
            print(f"  最終値: {result['final_value']:.0f}")
            print(f"  切り抜き精度: 幅 {result['crop_info']['width_accuracy']:.1f}%, 高さ {result['crop_info']['height_accuracy']:.1f}%")
        
        # レポートを保存
        report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_processed': len(results),
            'crop_accuracies': crop_accuracies,
            'results': results
        }
        
        report_path = os.path.join(self.report_dir, f"perfect_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        # float32をfloatに変換
        def convert_types(obj):
            if isinstance(obj, np.float32):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(item) for item in obj]
            return obj
        
        report = convert_types(report)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\nレポート保存: {report_path}")

def main():
    """メイン処理"""
    pipeline = PerfectCropPipeline(
        original_dir="/Users/haruqun/Work/pachi777/graphs/original"
    )
    
    results = pipeline.process_all()

if __name__ == "__main__":
    main()