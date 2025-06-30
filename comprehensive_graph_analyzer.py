#!/usr/bin/env python3
"""
包括的グラフ分析ツール - 複数画像の一括分析とHTMLレポート生成
グリッド表示 + データ抽出 + オーバーレイ表示
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import platform
import json
from datetime import datetime
import glob

# 日本語フォント設定
if platform.system() == 'Darwin':  # macOS
    plt.rcParams['font.family'] = 'Hiragino Sans'

class ComprehensiveGraphAnalyzer:
    def __init__(self):
        self.zero_y = 250
        self.target_30k_y = 5
        self.scale = 122.4
        self.results = []
        
    def detect_zero_line(self, img):
        """ゼロライン検出（複数手法）"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # 中央部分を検索範囲とする
        search_top = height // 3
        search_bottom = height * 2 // 3
        search_region = gray[search_top:search_bottom, :]
        
        # 手法1: 水平線検出（Hough変換）
        edges = cv2.Canny(search_region, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=int(width*0.3))
        
        zero_candidates = []
        
        if lines is not None:
            for rho, theta in lines[0]:
                # 水平線のみ（theta ≈ 0 or π）
                if abs(theta) < 0.1 or abs(theta - np.pi) < 0.1:
                    y = int(rho / np.sin(theta)) if abs(np.sin(theta)) > 0.1 else search_top
                    if 0 < y < search_region.shape[0]:
                        zero_candidates.append(search_top + y)
        
        # 手法2: 濃い水平線検出
        for y in range(search_top, search_bottom):
            row = gray[y, :]
            dark_pixels = np.sum(row < 100)
            if dark_pixels > width * 0.7:  # 70%以上が濃い
                zero_candidates.append(y)
        
        # 最も可能性の高い位置を選択
        if zero_candidates:
            return int(np.median(zero_candidates))
        else:
            return self.zero_y  # デフォルト値
    
    def extract_graph_data(self, img_path):
        """グラフからデータを抽出"""
        img = cv2.imread(img_path)
        if img is None:
            return [], 0
            
        height, width = img.shape[:2]
        
        # 検出されたゼロライン
        detected_zero = self.detect_zero_line(img)
        
        # HSVに変換してピンク色のグラフ線を検出
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # ピンク色の範囲（HSV）
        lower_pink = np.array([140, 50, 50])
        upper_pink = np.array([170, 255, 255])
        
        # マスクを作成
        mask = cv2.inRange(hsv, lower_pink, upper_pink)
        
        # グラフデータポイントを抽出
        data_points = []
        
        for x in range(0, width, 2):  # 2ピクセルおきにサンプリング
            col_mask = mask[:, x]
            pink_pixels = np.where(col_mask > 0)[0]
            
            if len(pink_pixels) > 0:
                # 最も下のピンクピクセル（グラフ線の位置）
                graph_y = np.max(pink_pixels)
                
                # Y座標を値に変換
                value = (detected_zero - graph_y) * self.scale
                data_points.append((x, value))
        
        return data_points, detected_zero
    
    def create_overlay_visualization(self, img_path, output_path):
        """グリッド + データ抽出オーバーレイ画像を生成"""
        img = cv2.imread(img_path)
        if img is None:
            return None
            
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        height, width = img.shape[:2]
        
        # データ抽出
        data_points, detected_zero = self.extract_graph_data(img_path)
        
        # matplotlib図を作成
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.imshow(img_rgb)
        
        # 検出されたゼロライン
        ax.axhline(y=detected_zero, color='black', linewidth=4, label=f'検出ゼロライン (Y={detected_zero})', alpha=0.8)
        
        # +30,000ライン
        ax.axhline(y=self.target_30k_y, color='#FF1493', linewidth=3, label='+30,000ライン', alpha=0.9)
        
        # -30,000ライン
        minus_30k_y = detected_zero + ((30000) / self.scale)
        if minus_30k_y <= height:
            ax.axhline(y=minus_30k_y, color='#FF1493', linewidth=3, label='-30,000ライン', alpha=0.9)
        
        # グリッドライン（主要ライン）
        grid_values = [25000, 20000, 15000, 10000, 5000]
        for value in grid_values:
            # プラス側
            plus_y = detected_zero - (value / self.scale)
            if 0 <= plus_y <= height:
                if value >= 20000:
                    ax.axhline(y=plus_y, color='#FF69B4', linewidth=1.5, linestyle='--', alpha=0.7, label=f'+{value//1000}k' if value == 25000 else '')
                elif value >= 10000:
                    ax.axhline(y=plus_y, color='#FFB6C1', linewidth=1.2, linestyle=':', alpha=0.6, label=f'+{value//1000}k' if value == 15000 else '')
                else:
                    ax.axhline(y=plus_y, color='gray', linewidth=0.8, linestyle=':', alpha=0.5, label=f'+{value//1000}k' if value == 5000 else '')
            
            # マイナス側
            minus_y = detected_zero + (value / self.scale)
            if 0 <= minus_y <= height:
                if value >= 20000:
                    ax.axhline(y=minus_y, color='#FF69B4', linewidth=1.5, linestyle='--', alpha=0.7, label=f'-{value//1000}k' if value == 25000 else '')
                elif value >= 10000:
                    ax.axhline(y=minus_y, color='#FFB6C1', linewidth=1.2, linestyle=':', alpha=0.6, label=f'-{value//1000}k' if value == 15000 else '')
                else:
                    ax.axhline(y=minus_y, color='gray', linewidth=0.8, linestyle=':', alpha=0.5, label=f'-{value//1000}k' if value == 5000 else '')
        
        # 抽出されたグラフデータを薄くオーバーレイ
        if data_points:
            x_coords = [p[0] for p in data_points]
            y_coords = [detected_zero - (p[1] / self.scale) for p in data_points]
            values = [p[1] for p in data_points]
            
            # 元のグラフ線をなぞる（薄い青）
            ax.plot(x_coords, y_coords, color='cyan', linewidth=2, alpha=0.6, label='抽出データ')
            
            # データポイント
            ax.scatter(x_coords[::10], y_coords[::10], color='yellow', s=8, alpha=0.8, label='データポイント')
            
            # 最大値、最小値、現在値の位置を特定
            max_val = max(values)
            min_val = min(values)
            current_val = values[-1]
            
            max_idx = values.index(max_val)
            min_idx = values.index(min_val)
            current_idx = len(values) - 1
            
            # 最大値線（赤）
            max_y = detected_zero - (max_val / self.scale)
            ax.axhline(y=max_y, color='red', linewidth=2, linestyle='--', alpha=0.8, label=f'最大値線 (+{max_val:,.0f})')
            ax.plot(x_coords[max_idx], max_y, 'ro', markersize=8, label='最大値位置')
            
            # 最大値の数値ラベル
            ax.text(width - 100, max_y - 15, f'+{max_val:,.0f}', 
                   fontsize=11, color='red', weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
            
            # 最小値線（青）
            min_y = detected_zero - (min_val / self.scale)
            ax.axhline(y=min_y, color='blue', linewidth=2, linestyle='--', alpha=0.8, label=f'最小値線 ({min_val:+,.0f})')
            ax.plot(x_coords[min_idx], min_y, 'bo', markersize=8, label='最小値位置')
            
            # 現在値線（緑）
            current_y = detected_zero - (current_val / self.scale)
            ax.axhline(y=current_y, color='lime', linewidth=2, linestyle=':', alpha=0.8, label=f'最終差玉 ({current_val:+,.0f})')
            ax.plot(x_coords[current_idx], current_y, 'go', markersize=8, label='最終位置')
            
            # 最終差玉の数値ラベル
            ax.text(width - 100, current_y + 15, f'{current_val:+,.0f}', 
                   fontsize=12, color='lime', weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.8))
        
        # 縦のグリッド線（時間軸）
        for x in range(100, width, 100):
            ax.axvline(x=x, color='gray', linewidth=0.3, alpha=0.4)
        
        # 統計情報
        if data_points:
            values = [p[1] for p in data_points]
            max_val = max(values)
            min_val = min(values)
            current_val = values[-1] if values else 0
            
            stats_text = f'最大: +{max_val:,.0f}\n最小: {min_val:,.0f}\n現在: {current_val:+,.0f}'
            ax.text(width - 150, 50, stats_text, 
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.9),
                   fontsize=11, verticalalignment='top')
        
        # タイトルと情報
        file_name = Path(img_path).stem
        ax.set_title(f'グラフ分析結果: {file_name}', fontsize=16, pad=20)
        
        ax.text(width//2, -30, f'検出ゼロライン: Y={detected_zero} | 設定スケール: 1px = {self.scale:.1f}', 
               ha='center', fontsize=12, color='blue')
        
        # 軸設定
        ax.set_xlim(0, width)
        ax.set_ylim(height, 0)
        ax.axis('off')
        
        # 凡例（3列に分けて見やすく）
        legend_elements = ax.get_legend_handles_labels()
        ax.legend(legend_elements[0], legend_elements[1], loc='upper left', fontsize=8, framealpha=0.9, ncol=3, bbox_to_anchor=(0, 1))
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return {
            'image_path': img_path,
            'output_path': output_path,
            'detected_zero': detected_zero,
            'data_points_count': len(data_points),
            'data_points': data_points[:100],  # 最初の100ポイントのみ保存
            'statistics': {
                'max_value': max([p[1] for p in data_points]) if data_points else 0,
                'min_value': min([p[1] for p in data_points]) if data_points else 0,
                'current_value': data_points[-1][1] if data_points else 0,
                'data_range': max([p[1] for p in data_points]) - min([p[1] for p in data_points]) if data_points else 0,
                'max_position': data_points[[p[1] for p in data_points].index(max([p[1] for p in data_points]))][0] if data_points else 0,
                'min_position': data_points[[p[1] for p in data_points].index(min([p[1] for p in data_points]))][0] if data_points else 0
            }
        }
    
    def analyze_multiple_images(self, image_pattern):
        """複数画像の一括分析"""
        image_files = glob.glob(image_pattern)
        
        print(f"分析対象: {len(image_files)}個の画像")
        
        for img_file in image_files:
            print(f"分析中: {img_file}")
            
            # 出力ファイル名
            base_name = Path(img_file).stem
            output_path = f"analysis_overlay_{base_name}.png"
            
            # 分析実行
            result = self.create_overlay_visualization(img_file, output_path)
            
            if result:
                self.results.append(result)
                print(f"  -> 保存: {output_path}")
                print(f"  -> データポイント数: {result['data_points_count']}")
                print(f"  -> 検出ゼロライン: Y={result['detected_zero']}")
        
        return self.results
    
    def generate_html_report(self, output_file="comprehensive_analysis_report.html"):
        """HTML分析レポートを生成"""
        
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>包括的グラフ分析レポート</title>
    <style>
        body {{
            font-family: 'Hiragino Sans', 'Meiryo', sans-serif;
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: #fff;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            background: linear-gradient(45deg, #4a90e2, #6bb6ff);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .summary-card {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }}
        
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #4CAF50;
        }}
        
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #fff;
        }}
        
        .analysis-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 30px;
        }}
        
        .analysis-item {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .analysis-header {{
            background: linear-gradient(45deg, #2196F3, #21CBF3);
            padding: 15px;
            font-weight: bold;
            font-size: 1.1em;
        }}
        
        .analysis-content {{
            padding: 20px;
        }}
        
        .analysis-image {{
            width: 100%;
            border-radius: 10px;
            margin-bottom: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-top: 15px;
        }}
        
        .stat-item {{
            background: rgba(255,255,255,0.08);
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            color: #ccc;
            margin-bottom: 5px;
        }}
        
        .stat-value {{
            font-size: 1.3em;
            font-weight: bold;
            color: #fff;
        }}
        
        .detection-info {{
            background: rgba(255,193,7,0.2);
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            border-left: 4px solid #FFC107;
        }}
        
        .data-quality {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            margin-top: 10px;
        }}
        
        .quality-excellent {{ background: #4CAF50; }}
        .quality-good {{ background: #FF9800; }}
        .quality-poor {{ background: #F44336; }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            color: #ccc;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>包括的グラフ分析レポート</h1>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>分析画像数</h3>
                <div class="value">{len(self.results)}</div>
            </div>
            <div class="summary-card">
                <h3>データ抽出成功</h3>
                <div class="value">{len([r for r in self.results if r['data_points_count'] > 0])}</div>
            </div>
            <div class="summary-card">
                <h3>平均最終差玉</h3>
                <div class="value">{"" if not [r for r in self.results if r['data_points_count'] > 0] else f"{int(np.mean([r['statistics']['current_value'] for r in self.results if r['data_points_count'] > 0])):+,}"}</div>
            </div>
            <div class="summary-card">
                <h3>最高最終差玉</h3>
                <div class="value">{"N/A" if not [r for r in self.results if r['data_points_count'] > 0] else f"{max([r['statistics']['current_value'] for r in self.results if r['data_points_count'] > 0]):+,.0f}"}</div>
            </div>
            <div class="summary-card">
                <h3>最低最終差玉</h3>
                <div class="value">{"N/A" if not [r for r in self.results if r['data_points_count'] > 0] else f"{min([r['statistics']['current_value'] for r in self.results if r['data_points_count'] > 0]):+,.0f}"}</div>
            </div>
            <div class="summary-card">
                <h3>使用スケール</h3>
                <div class="value">{self.scale}</div>
            </div>
        </div>
        
        <div class="analysis-grid">
"""
        
        # 各画像の分析結果
        for i, result in enumerate(self.results):
            file_name = Path(result['image_path']).stem
            stats = result['statistics']
            
            # データ品質評価
            data_count = result['data_points_count']
            if data_count > 200:
                quality_class = "quality-excellent"
                quality_text = "優秀"
            elif data_count > 100:
                quality_class = "quality-good"
                quality_text = "良好"
            else:
                quality_class = "quality-poor"
                quality_text = "要改善"
            
            html_content += f"""
            <div class="analysis-item">
                <div class="analysis-header">
                    #{i+1}: {file_name}
                </div>
                <div class="analysis-content">
                    <img src="{result['output_path']}" alt="分析結果" class="analysis-image">
                    
                    <div style="margin: 15px 0;">
                        <h4 style="margin: 5px 0; color: #ccc;">元画像:</h4>
                        <img src="graphs/original/{Path(result['image_path']).stem.replace('_graph_only', '')}.jpg" alt="元画像" style="width: 100%; border-radius: 5px; margin-bottom: 10px;">
                    </div>
                    
                    <div class="detection-info">
                        <strong>検出情報:</strong> ゼロライン Y={result['detected_zero']} 
                        (設定値からの差: {abs(result['detected_zero'] - self.zero_y)}px)
                    </div>
                    
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-label">最大値</div>
                            <div class="stat-value">+{stats['max_value']:,.0f}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">最小値</div>
                            <div class="stat-value">{stats['min_value']:+,.0f}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">最終差玉</div>
                            <div class="stat-value">{stats['current_value']:+,.0f}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">データ範囲</div>
                            <div class="stat-value">{stats['data_range']:,.0f}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">最大値位置</div>
                            <div class="stat-value">X={stats['max_position']:.0f}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">最小値位置</div>
                            <div class="stat-value">X={stats['min_position']:.0f}</div>
                        </div>
                    </div>
                    
                    <div class="data-quality {quality_class}">
                        データ品質: {quality_text} ({data_count}ポイント)
                    </div>
                </div>
            </div>
"""
        
        html_content += f"""
        </div>
        
        <div class="footer">
            <p>このレポートは包括的グラフ分析ツールによって自動生成されました</p>
            <p>分析スケール: 1px = {self.scale} | 基準ゼロライン: Y={self.zero_y}</p>
            
            <h3 style="margin-top: 20px; color: #4CAF50;">最終差玉データ一覧</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 10px; margin-top: 15px;">"""
        
        # データ抽出に成功した画像の最終差玉一覧を追加
        successful_results = [r for r in self.results if r['data_points_count'] > 0]
        for result in successful_results:
            file_name = Path(result['image_path']).stem
            final_value = result['statistics']['current_value']
            html_content += f"""
                <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 5px; font-family: monospace;">
                    <strong>{file_name}:</strong> {final_value:+,.0f}
                </div>"""
        
        html_content += """
            </div>
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTMLレポートを生成: {output_file}")
        return output_file

if __name__ == "__main__":
    analyzer = ComprehensiveGraphAnalyzer()
    
    # 複数画像の分析（全ての画像）
    image_pattern = "graphs/manual_crop/cropped/*_graph_only.png"
    results = analyzer.analyze_multiple_images(image_pattern)
    
    # HTMLレポート生成
    html_file = analyzer.generate_html_report()
    
    print(f"\n=== 分析完了 ===")
    print(f"分析画像数: {len(results)}")
    print(f"HTMLレポート: {html_file}")
    print(f"オーバーレイ画像: analysis_overlay_*.png")