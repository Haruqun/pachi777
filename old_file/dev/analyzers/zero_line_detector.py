#!/usr/bin/env python3
"""
ゼロライン検出とオーバーレイ表示ツール
グラフ画像からゼロラインを正確に検出し、視覚化する
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os
import json
from datetime import datetime

class ZeroLineDetector:
    """ゼロライン検出クラス"""
    
    def __init__(self, input_dir="graphs/original", output_dir="graphs/zero_line_detection"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.overlay_dir = os.path.join(output_dir, "overlays")
        self.analysis_dir = os.path.join(output_dir, "analysis")
        
        # 出力ディレクトリを作成
        for dir_path in [self.output_dir, self.overlay_dir, self.analysis_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def detect_zero_line_advanced(self, img):
        """高度なゼロライン検出"""
        height, width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        print(f"画像サイズ: {width}x{height}")
        
        # 1. グラフエリアを推定（画像の中央部分）
        # 上下20%を除外してグラフエリアを特定
        top_margin = int(height * 0.2)
        bottom_margin = int(height * 0.8)
        left_margin = int(width * 0.1)
        right_margin = int(width * 0.9)
        
        graph_region = gray[top_margin:bottom_margin, left_margin:right_margin]
        graph_height, graph_width = graph_region.shape
        
        print(f"グラフ領域: {graph_width}x{graph_height}")
        
        # 2. 水平線の候補を検出
        candidates = []
        
        for y in range(graph_height):
            row = graph_region[y, :]
            
            # 複数の指標でスコアリング
            scores = {}
            
            # A. 暗さスコア（黒い線）
            darkness = 1.0 - (np.mean(row) / 255.0)
            scores['darkness'] = darkness
            
            # B. 一様性スコア（水平線の特徴）
            uniformity = 1.0 - (np.std(row) / 128.0)
            uniformity = max(0, uniformity)
            scores['uniformity'] = uniformity
            
            # C. エッジ強度（水平線の境界）
            edges = cv2.Sobel(row.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
            edge_strength = np.mean(np.abs(edges))
            scores['edge_strength'] = edge_strength / 100.0  # 正規化
            
            # D. 最小値の暗さ（線の最も暗い部分）
            min_darkness = 1.0 - (np.min(row) / 255.0)
            scores['min_darkness'] = min_darkness
            
            # E. 連続性スコア（水平線の長さ）
            dark_pixels = (row < 100).astype(int)  # 暗いピクセル
            # 連続する暗いピクセルの最大長
            max_run = 0
            current_run = 0
            for pixel in dark_pixels:
                if pixel:
                    current_run += 1
                    max_run = max(max_run, current_run)
                else:
                    current_run = 0
            continuity = max_run / graph_width
            scores['continuity'] = continuity
            
            # 総合スコア計算
            total_score = (
                scores['darkness'] * 0.25 +
                scores['uniformity'] * 0.20 +
                scores['min_darkness'] * 0.25 +
                scores['continuity'] * 0.30
            )
            
            candidates.append({
                'y': y + top_margin,  # 元の画像座標
                'y_relative': y,      # グラフ領域内座標
                'total_score': total_score,
                'scores': scores,
                'row_data': row
            })
        
        # スコア順にソート
        candidates.sort(key=lambda x: x['total_score'], reverse=True)
        
        print(f"上位5候補:")
        for i, candidate in enumerate(candidates[:5]):
            print(f"  {i+1}. Y={candidate['y']}, スコア={candidate['total_score']:.3f}")
            for key, value in candidate['scores'].items():
                print(f"     {key}: {value:.3f}")
        
        # 最高スコアの候補を選択
        best_candidate = candidates[0]
        
        return best_candidate, candidates[:10]  # 上位10候補を返す
    
    def create_overlay(self, img, zero_line_candidate, all_candidates):
        """ゼロライン検出結果をオーバーレイ"""
        overlay = img.copy()
        height, width = img.shape[:2]
        
        # 1. 検出されたゼロライン（赤色、太線）
        y_best = zero_line_candidate['y']
        cv2.line(overlay, (0, y_best), (width, y_best), (0, 0, 255), 3)
        
        # ラベル
        cv2.putText(overlay, f"Zero Line (Score: {zero_line_candidate['total_score']:.3f})", 
                   (10, y_best - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # 2. 他の候補（黄色、細線）
        for i, candidate in enumerate(all_candidates[1:5]):  # 2-5位
            y_candidate = candidate['y']
            cv2.line(overlay, (0, y_candidate), (width, y_candidate), (0, 255, 255), 1)
            cv2.putText(overlay, f"#{i+2} ({candidate['total_score']:.3f})", 
                       (width - 150, y_candidate + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # 3. グラフ領域の境界（緑色）
        top_margin = int(height * 0.2)
        bottom_margin = int(height * 0.8)
        left_margin = int(width * 0.1)
        right_margin = int(width * 0.9)
        
        cv2.rectangle(overlay, (left_margin, top_margin), (right_margin, bottom_margin), (0, 255, 0), 2)
        cv2.putText(overlay, "Graph Region", (left_margin, top_margin - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return overlay
    
    def analyze_row_profiles(self, img, zero_line_candidate, all_candidates):
        """行プロファイル分析の可視化"""
        height, width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # グラフ領域を設定
        top_margin = int(height * 0.2)
        bottom_margin = int(height * 0.8)
        left_margin = int(width * 0.1)
        right_margin = int(width * 0.9)
        
        graph_region = gray[top_margin:bottom_margin, left_margin:right_margin]
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. スコア分布
        y_coords = [c['y'] - top_margin for c in all_candidates]
        scores = [c['total_score'] for c in all_candidates]
        
        axes[0, 0].plot(y_coords, scores, 'b-', linewidth=2)
        axes[0, 0].scatter([zero_line_candidate['y'] - top_margin], [zero_line_candidate['total_score']], 
                          color='red', s=100, zorder=5)
        axes[0, 0].set_title('Zero Line Detection Scores')
        axes[0, 0].set_xlabel('Y Position (relative to graph region)')
        axes[0, 0].set_ylabel('Score')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 上位候補の行プロファイル
        for i, candidate in enumerate(all_candidates[:3]):
            y_rel = candidate['y_relative']
            row_data = candidate['row_data']
            x_coords = range(len(row_data))
            
            color = 'red' if i == 0 else f'C{i}'
            label = f"Best (Score: {candidate['total_score']:.3f})" if i == 0 else f"#{i+1} ({candidate['total_score']:.3f})"
            
            axes[0, 1].plot(x_coords, row_data, color=color, linewidth=2 if i == 0 else 1, 
                           label=label, alpha=0.8)
        
        axes[0, 1].set_title('Row Intensity Profiles (Top 3 Candidates)')
        axes[0, 1].set_xlabel('X Position')
        axes[0, 1].set_ylabel('Pixel Intensity')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 個別スコア成分
        best = zero_line_candidate
        score_components = best['scores']
        component_names = list(score_components.keys())
        component_values = list(score_components.values())
        
        bars = axes[1, 0].bar(component_names, component_values, color=['skyblue', 'lightgreen', 'orange', 'pink', 'gold'])
        axes[1, 0].set_title(f'Score Components for Best Candidate (Y={best["y"]})')
        axes[1, 0].set_ylabel('Score Value')
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 値をバーの上に表示
        for bar, value in zip(bars, component_values):
            axes[1, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                           f'{value:.3f}', ha='center', va='bottom')
        
        # 4. グラフ領域の画像
        axes[1, 1].imshow(graph_region, cmap='gray')
        
        # ゼロライン候補をオーバーレイ
        y_best_rel = zero_line_candidate['y_relative']
        axes[1, 1].axhline(y=y_best_rel, color='red', linewidth=3, label='Detected Zero Line')
        
        for i, candidate in enumerate(all_candidates[1:5]):
            y_rel = candidate['y_relative']
            axes[1, 1].axhline(y=y_rel, color='yellow', linewidth=1, alpha=0.7)
        
        axes[1, 1].set_title('Graph Region with Detected Lines')
        axes[1, 1].set_xlabel('X Position')
        axes[1, 1].set_ylabel('Y Position')
        axes[1, 1].legend()
        
        plt.tight_layout()
        return fig
    
    def process_image(self, image_path):
        """単一画像を処理"""
        print(f"\n{'='*60}")
        print(f"ゼロライン検出: {os.path.basename(image_path)}")
        print(f"{'='*60}")
        
        img = cv2.imread(image_path)
        if img is None:
            print(f"エラー: 画像を読み込めません: {image_path}")
            return None
        
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # ゼロライン検出
        zero_line_candidate, all_candidates = self.detect_zero_line_advanced(img)
        
        # オーバーレイ画像作成
        overlay_img = self.create_overlay(img, zero_line_candidate, all_candidates)
        
        # オーバーレイ保存
        overlay_path = os.path.join(self.overlay_dir, f"{base_name}_zero_line_overlay.png")
        cv2.imwrite(overlay_path, overlay_img)
        print(f"オーバーレイ保存: {overlay_path}")
        
        # 分析図作成
        analysis_fig = self.analyze_row_profiles(img, zero_line_candidate, all_candidates)
        analysis_path = os.path.join(self.analysis_dir, f"{base_name}_analysis.png")
        analysis_fig.savefig(analysis_path, dpi=150, bbox_inches='tight')
        plt.close(analysis_fig)
        print(f"分析図保存: {analysis_path}")
        
        # 結果データ
        result = {
            'file_name': base_name,
            'image_size': img.shape[:2][::-1],  # (width, height)
            'detected_zero_line': {
                'y_position': zero_line_candidate['y'],
                'score': zero_line_candidate['total_score'],
                'score_components': zero_line_candidate['scores']
            },
            'all_candidates': [
                {
                    'y_position': c['y'],
                    'score': c['total_score'],
                    'rank': i + 1
                }
                for i, c in enumerate(all_candidates)
            ]
        }
        
        return result
    
    def process_all(self):
        """全画像を処理"""
        print(f"\n{'='*80}")
        print("ゼロライン検出パイプライン開始")
        print(f"{'='*80}")
        
        # 画像ファイルを取得
        import glob
        image_files = glob.glob(os.path.join(self.input_dir, "*.jpg"))
        image_files.sort()
        
        print(f"処理対象: {len(image_files)}枚")
        
        results = []
        
        for image_path in image_files[:5]:  # まず5枚をテスト
            result = self.process_image(image_path)
            if result:
                results.append(result)
        
        # サマリーレポート
        self.generate_summary(results)
        
        return results
    
    def generate_summary(self, results):
        """サマリーレポートを生成"""
        print(f"\n{'='*80}")
        print("ゼロライン検出完了サマリー")
        print(f"{'='*80}")
        
        if results:
            print(f"\n処理完了: {len(results)}枚")
            
            # ゼロライン位置の統計
            zero_y_positions = [r['detected_zero_line']['y_position'] for r in results]
            scores = [r['detected_zero_line']['score'] for r in results]
            
            print(f"\nゼロライン位置:")
            print(f"  平均Y座標: {np.mean(zero_y_positions):.1f}")
            print(f"  範囲: {min(zero_y_positions)} - {max(zero_y_positions)}")
            
            print(f"\n検出スコア:")
            print(f"  平均スコア: {np.mean(scores):.3f}")
            print(f"  最高スコア: {max(scores):.3f}")
            print(f"  最低スコア: {min(scores):.3f}")
            
            # 各画像の結果
            print(f"\n個別結果:")
            for result in results:
                zero_line = result['detected_zero_line']
                print(f"  {result['file_name']}: Y={zero_line['y_position']}, Score={zero_line['score']:.3f}")
        
        # レポート保存
        report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_processed': len(results),
            'results': results
        }
        
        report_path = os.path.join(self.output_dir, f"zero_line_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\nレポート保存: {report_path}")

def main():
    """メイン処理"""
    detector = ZeroLineDetector()
    results = detector.process_all()

if __name__ == "__main__":
    main()