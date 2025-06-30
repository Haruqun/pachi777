#!/usr/bin/env python3
"""
既に切り抜かれた画像からグラフエリアのみを抽出
不要な部分（オレンジバー、ボタン、余白）を除去
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os
import json
from datetime import datetime
import pandas as pd

class RefinedGraphCropper:
    """既存の切り抜き画像をさらに精製するクラス"""
    
    def __init__(self, input_dir="graphs/perfect_pipeline/cropped", output_dir="graphs/refined_graph"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.cropped_dir = os.path.join(output_dir, "cropped")
        self.data_dir = os.path.join(output_dir, "extracted_data")
        self.report_dir = os.path.join(output_dir, "reports")
        
        # 出力ディレクトリを作成
        for dir_path in [self.output_dir, self.cropped_dir, self.data_dir, self.report_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def refine_crop(self, image_path):
        """既存の切り抜き画像をさらに精製"""
        print(f"\n精製処理: {os.path.basename(image_path)}")
        
        img = cv2.imread(image_path)
        if img is None:
            print(f"エラー: 画像を読み込めません: {image_path}")
            return None, None
        
        height, width = img.shape[:2]
        print(f"入力サイズ: {width}x{height}")
        
        # 1. オレンジバーを除去（上部）
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # オレンジ色検出
        orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
        
        # オレンジバーの下端を見つける
        orange_bottom = 0
        horizontal_projection = np.sum(orange_mask, axis=1)
        for y in range(height):
            if horizontal_projection[y] > width * 0.5:  # 行の50%以上がオレンジ
                orange_bottom = max(orange_bottom, y)
        
        if orange_bottom > 0:
            orange_bottom += 5  # 少し余裕を持たせる
        
        # 2. ボタンエリアを除去（下部）
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 下から上に向かってボタンを探す
        button_top = height
        for y in range(height-1, height//2, -1):  # 下半分を探索
            row = gray[y, :]
            # ボタンの特徴：明るい値（200以上）が一定幅続く
            bright_pixels = np.sum(row > 200)
            if bright_pixels > width * 0.3:  # 行の30%以上が明るい
                button_top = y - 5  # 少し余裕を持たせる
                break
        
        # 「最大値」テキスト領域も除去対象
        # 下部20%エリアでテキスト領域を探す
        bottom_20_percent = int(height * 0.8)
        if button_top > bottom_20_percent:
            button_top = bottom_20_percent
        
        # 3. 左右の余白を除去
        # グラフエリア（オレンジバー下からボタン上まで）で分析
        graph_region = img[orange_bottom:button_top, :]
        
        if graph_region.shape[0] > 10:  # 十分な高さがある場合
            graph_gray = cv2.cvtColor(graph_region, cv2.COLOR_BGR2GRAY)
            
            # 各列の標準偏差を計算（グラフ線がある部分は変動が大きい）
            col_std = np.std(graph_gray, axis=0)
            
            # 閾値設定（平均の30%）
            threshold = np.mean(col_std) * 0.3
            
            # 左端を探す
            left_boundary = 0
            for x in range(width):
                if col_std[x] > threshold:
                    left_boundary = max(0, x - 5)
                    break
            
            # 右端を探す  
            right_boundary = width
            for x in range(width-1, -1, -1):
                if col_std[x] > threshold:
                    right_boundary = min(width, x + 5)
                    break
        else:
            # フォールバック：元の10%マージン
            left_boundary = int(width * 0.05)
            right_boundary = int(width * 0.95)
        
        # 4. 最終的な切り抜き実行
        final_top = max(0, orange_bottom)
        final_bottom = min(height, button_top)
        final_left = max(0, left_boundary)
        final_right = min(width, right_boundary)
        
        print(f"精製境界: top={final_top}, bottom={final_bottom}, "
              f"left={final_left}, right={final_right}")
        
        if final_bottom <= final_top or final_right <= final_left:
            print("エラー: 無効な境界")
            return None, None
        
        refined = img[final_top:final_bottom, final_left:final_right]
        
        refined_info = {
            'original_size': (width, height),
            'orange_bottom': orange_bottom,
            'button_top': button_top,
            'left_boundary': left_boundary,
            'right_boundary': right_boundary,
            'final_top': final_top,
            'final_bottom': final_bottom,
            'final_left': final_left,
            'final_right': final_right,
            'refined_size': (refined.shape[1], refined.shape[0])
        }
        
        print(f"精製後サイズ: {refined.shape[1]}x{refined.shape[0]}")
        
        return refined, refined_info
    
    def extract_graph_data(self, refined_img):
        """精製されたグラフからデータを抽出"""
        if refined_img is None:
            return None, None
            
        height, width = refined_img.shape[:2]
        
        # ゼロライン位置を推定（グラフの約60%位置）
        zero_y = int(height * 0.6)
        
        # HSV変換
        hsv = cv2.cvtColor(refined_img, cv2.COLOR_BGR2HSV)
        
        # 複数の色範囲でグラフ線を検出
        color_ranges = [
            # ピンク
            ((150, 50, 50), (180, 255, 255)),
            ((140, 30, 100), (170, 255, 255)),
            # 青
            ((100, 50, 50), (130, 255, 255)),
            ((90, 30, 100), (120, 255, 255)),
            # オレンジ/赤
            ((0, 50, 50), (20, 255, 255)),
            ((160, 50, 50), (180, 255, 255)),
        ]
        
        # 全色の統合マスク
        combined_mask = np.zeros((height, width), dtype=np.uint8)
        color_counts = {}
        
        for i, (lower, upper) in enumerate(color_ranges):
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            combined_mask = cv2.bitwise_or(combined_mask, mask)
            color_counts[i] = np.sum(mask)
        
        # 最も多い色を判定
        dominant_color_idx = max(color_counts, key=color_counts.get)
        if dominant_color_idx < 2:
            graph_color = "pink"
        elif dominant_color_idx < 4:
            graph_color = "blue"
        else:
            graph_color = "orange"
        
        # ノイズ除去
        kernel = np.ones((3, 3), np.uint8)
        mask_cleaned = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_OPEN, kernel)
        
        # データポイント抽出
        data_points = []
        for x in range(width):
            column = mask_cleaned[:, x]
            graph_pixels = np.where(column > 0)[0]
            
            if len(graph_pixels) > 0:
                # 複数のピクセルがある場合は中央値を使用
                y_pixel = int(np.median(graph_pixels))
                
                # Y座標を実際の値に変換（ゼロライン基準）
                pixels_from_zero = zero_y - y_pixel
                
                # スケーリング（±30000の範囲）
                if y_pixel < zero_y:
                    # 正の値
                    y_value = pixels_from_zero * (30000 / zero_y)
                else:
                    # 負の値
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
        # _perfectを除去
        if base_name.endswith('_perfect'):
            base_name = base_name[:-8]
        
        # 1. 精製切り抜き
        refined, refined_info = self.refine_crop(image_path)
        
        if refined is None:
            return None
        
        # 精製画像を保存
        refined_path = os.path.join(self.cropped_dir, f"{base_name}_refined.png")
        cv2.imwrite(refined_path, refined)
        
        # 2. データ抽出
        data_points, graph_color = self.extract_graph_data(refined)
        
        if not data_points:
            print("警告: データポイントが検出されませんでした")
            # それでも画像は保存する
            return {
                'file_name': base_name,
                'refined_info': refined_info,
                'graph_color': 'unknown',
                'data_points': 0
            }
        
        # データをCSVに保存
        df = pd.DataFrame(data_points)
        csv_path = os.path.join(self.data_dir, f"{base_name}_data.csv")
        df.to_csv(csv_path, index=False)
        
        # 統計情報
        y_values = [p['y_value'] for p in data_points]
        stats = {
            'file_name': base_name,
            'refined_info': refined_info,
            'graph_color': graph_color,
            'min_value': min(y_values) if y_values else 0,
            'max_value': max(y_values) if y_values else 0,
            'final_value': y_values[-1] if y_values else 0,
            'mean_value': np.mean(y_values) if y_values else 0,
            'data_points': len(data_points)
        }
        
        # 可視化
        self.visualize_results(refined, data_points, stats, base_name)
        
        return stats
    
    def visualize_results(self, img, data_points, stats, base_name):
        """結果を可視化"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # 1. 精製画像
        axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        axes[0].set_title(f'Refined Graph ({img.shape[1]}x{img.shape[0]})')
        axes[0].axis('off')
        
        # 2. 抽出データ
        if data_points:
            x_values = [p['x'] for p in data_points]
            y_values = [p['y_value'] for p in data_points]
            
            color_map = {'pink': 'hotpink', 'blue': 'blue', 'orange': 'orange', 'unknown': 'gray'}
            color = color_map.get(stats['graph_color'], 'gray')
            
            axes[1].plot(x_values, y_values, color=color, linewidth=2)
            axes[1].set_title(f'Extracted Data ({stats["graph_color"]})')
            axes[1].set_xlabel('X Position')
            axes[1].set_ylabel('Value')
            axes[1].grid(True, alpha=0.3)
            axes[1].axhline(y=0, color='red', linestyle='--', alpha=0.5)
            axes[1].set_ylim(-35000, 35000)
            
            # 統計情報
            stats_text = f"Max: {stats['max_value']:.0f}\nFinal: {stats['final_value']:.0f}"
            axes[1].text(0.02, 0.98, stats_text, transform=axes[1].transAxes,
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        else:
            axes[1].text(0.5, 0.5, 'No Data Points Detected', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=axes[1].transAxes, fontsize=16)
            axes[1].set_title('No Data Extracted')
        
        plt.suptitle(f'Refined Graph Cropper: {base_name}')
        plt.tight_layout()
        
        viz_path = os.path.join(self.report_dir, f"{base_name}_visualization.png")
        plt.savefig(viz_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def process_all(self):
        """全画像を処理"""
        print(f"\n{'='*80}")
        print("精製グラフ切り抜きパイプライン開始")
        print(f"{'='*80}")
        
        # 画像ファイルを取得
        import glob
        image_files = glob.glob(os.path.join(self.input_dir, "*.png"))
        image_files.sort()
        
        print(f"処理対象: {len(image_files)}枚")
        
        results = []
        
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
        print("精製切り抜き完了サマリー")
        print(f"{'='*80}")
        
        if results:
            # サイズの統計
            sizes = [(r['refined_info']['refined_size'][0], r['refined_info']['refined_size'][1]) 
                    for r in results if 'refined_info' in r]
            
            if sizes:
                widths = [s[0] for s in sizes]
                heights = [s[1] for s in sizes]
                
                print(f"\n精製後サイズ:")
                print(f"  幅: 平均 {np.mean(widths):.0f}px, 範囲 {min(widths)}-{max(widths)}px")
                print(f"  高さ: 平均 {np.mean(heights):.0f}px, 範囲 {min(heights)}-{max(heights)}px")
            
            # 色別統計
            color_counts = {}
            for r in results:
                color = r.get('graph_color', 'unknown')
                color_counts[color] = color_counts.get(color, 0) + 1
            
            print(f"\nグラフ色分布:")
            for color, count in color_counts.items():
                print(f"  {color}: {count}枚")
            
            # データ抽出成功数
            with_data = sum(1 for r in results if r.get('data_points', 0) > 0)
            print(f"\nデータ抽出成功: {with_data}/{len(results)}枚")
            
            print(f"処理完了: {len(results)}枚")
        
        # レポート保存
        report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_processed': len(results),
            'results': results
        }
        
        report_path = os.path.join(self.report_dir, f"refined_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        # NumPy型を変換
        def convert_types(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
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
    cropper = RefinedGraphCropper()
    results = cropper.process_all()

if __name__ == "__main__":
    main()