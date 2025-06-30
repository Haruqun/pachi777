#!/usr/bin/env python3
"""
改良版カラー検出 - 複数の色とグラフパターンに対応
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import glob

class ImprovedColorDetector:
    def __init__(self):
        # 複数の色パターンを定義
        self.color_ranges = {
            'pink': {
                'lower': np.array([140, 50, 50]),
                'upper': np.array([170, 255, 255]),
                'name': 'ピンク'
            },
            'magenta': {
                'lower': np.array([130, 100, 100]),
                'upper': np.array([160, 255, 255]),
                'name': 'マゼンタ'
            },
            'red': {
                'lower': np.array([0, 100, 100]),
                'upper': np.array([10, 255, 255]),
                'name': '赤'
            },
            'red_high': {
                'lower': np.array([170, 100, 100]),
                'upper': np.array([180, 255, 255]),
                'name': '赤（高域）'
            },
            'blue': {
                'lower': np.array([100, 100, 100]),
                'upper': np.array([130, 255, 255]),
                'name': '青'
            },
            'green': {
                'lower': np.array([40, 100, 100]),
                'upper': np.array([80, 255, 255]),
                'name': '緑'
            },
            'cyan': {
                'lower': np.array([80, 100, 100]),
                'upper': np.array([100, 255, 255]),
                'name': 'シアン'
            },
            'yellow': {
                'lower': np.array([20, 100, 100]),
                'upper': np.array([40, 255, 255]),
                'name': '黄'
            },
            'orange': {
                'lower': np.array([10, 100, 100]),
                'upper': np.array([25, 255, 255]),
                'name': 'オレンジ'
            },
            'purple': {
                'lower': np.array([120, 100, 100]),
                'upper': np.array([140, 255, 255]),
                'name': '紫'
            }
        }
    
    def analyze_image_colors(self, img_path):
        """画像の色分布を分析"""
        img = cv2.imread(img_path)
        if img is None:
            return None
            
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        height, width = img.shape[:2]
        
        # 各色の検出結果
        color_results = {}
        
        for color_name, color_info in self.color_ranges.items():
            mask = cv2.inRange(hsv, color_info['lower'], color_info['upper'])
            pixel_count = np.sum(mask > 0)
            percentage = (pixel_count / (height * width)) * 100
            
            color_results[color_name] = {
                'pixel_count': pixel_count,
                'percentage': percentage,
                'mask': mask,
                'name': color_info['name']
            }
        
        return color_results
    
    def extract_graph_data_multi_color(self, img_path):
        """複数色対応のグラフデータ抽出"""
        img = cv2.imread(img_path)
        if img is None:
            return [], "画像読み込み失敗"
            
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        height, width = img.shape[:2]
        
        # 各色での検出を試行
        best_result = []
        best_color = "なし"
        max_points = 0
        
        for color_name, color_info in self.color_ranges.items():
            mask = cv2.inRange(hsv, color_info['lower'], color_info['upper'])
            
            # グラフデータポイントを抽出
            data_points = []
            
            for x in range(0, width, 2):
                col_mask = mask[:, x]
                colored_pixels = np.where(col_mask > 0)[0]
                
                if len(colored_pixels) > 0:
                    # 最も下のピクセル（グラフ線の位置）を使用
                    graph_y = np.max(colored_pixels)
                    data_points.append((x, graph_y))
            
            # 最も多くのデータポイントが取れた色を選択
            if len(data_points) > max_points:
                max_points = len(data_points)
                best_result = data_points
                best_color = color_info['name']
        
        return best_result, best_color
    
    def create_color_detection_report(self, image_pattern, output_file="color_detection_report.html"):
        """色検出レポートを生成"""
        image_files = glob.glob(image_pattern)
        
        print(f"色検出分析対象: {len(image_files)}個の画像")
        
        analysis_results = []
        
        for img_file in image_files:
            print(f"色分析中: {img_file}")
            
            # 色分布分析
            color_results = self.analyze_image_colors(img_file)
            
            # マルチカラー抽出
            data_points, detected_color = self.extract_graph_data_multi_color(img_file)
            
            result = {
                'image_path': img_file,
                'file_name': Path(img_file).stem,
                'color_analysis': color_results,
                'data_points_count': len(data_points),
                'detected_color': detected_color,
                'success': len(data_points) > 50  # 50ポイント以上で成功とみなす
            }
            
            analysis_results.append(result)
            print(f"  -> データポイント数: {len(data_points)} ({detected_color})")
        
        # HTMLレポート生成
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>色検出分析レポート</title>
    <style>
        body {{
            font-family: 'Hiragino Sans', 'Meiryo', sans-serif;
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: #ecf0f1;
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
            background: linear-gradient(45deg, #e74c3c, #c0392b);
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
            padding: 15px;
            font-weight: bold;
            font-size: 1.1em;
        }}
        
        .success {{ background: linear-gradient(45deg, #27ae60, #2ecc71); }}
        .failure {{ background: linear-gradient(45deg, #e74c3c, #c0392b); }}
        
        .analysis-content {{
            padding: 20px;
        }}
        
        .original-image {{
            width: 100%;
            max-height: 300px;
            object-fit: contain;
            border-radius: 10px;
            margin-bottom: 15px;
        }}
        
        .color-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }}
        
        .color-item {{
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            font-size: 0.9em;
        }}
        
        .detection-result {{
            background: rgba(52, 152, 219, 0.2);
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            border-left: 4px solid #3498db;
        }}
        
        .high {{ color: #e74c3c; font-weight: bold; }}
        .medium {{ color: #f39c12; font-weight: bold; }}
        .low {{ color: #95a5a6; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 色検出分析レポート</h1>
            <p>グラフ線の色パターン解析結果</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>分析画像数</h3>
                <div style="font-size: 2em; font-weight: bold;">{len(analysis_results)}</div>
            </div>
            <div class="summary-card">
                <h3>検出成功数</h3>
                <div style="font-size: 2em; font-weight: bold;">{len([r for r in analysis_results if r['success']])}</div>
            </div>
            <div class="summary-card">
                <h3>成功率</h3>
                <div style="font-size: 2em; font-weight: bold;">{len([r for r in analysis_results if r['success']])/len(analysis_results)*100:.1f}%</div>
            </div>
            <div class="summary-card">
                <h3>失敗数</h3>
                <div style="font-size: 2em; font-weight: bold;">{len([r for r in analysis_results if not r['success']])}</div>
            </div>
        </div>
        
        <div class="analysis-grid">
"""
        
        # 各画像の分析結果
        for i, result in enumerate(analysis_results):
            file_name = result['file_name']
            success_class = "success" if result['success'] else "failure"
            status_text = "成功" if result['success'] else "失敗"
            
            html_content += f"""
            <div class="analysis-item">
                <div class="analysis-header {success_class}">
                    #{i+1}: {file_name} - {status_text}
                </div>
                <div class="analysis-content">
                    <img src="{result['image_path']}" alt="元画像" class="original-image">
                    
                    <div class="detection-result">
                        <strong>検出結果:</strong> {result['data_points_count']}ポイント ({result['detected_color']})
                    </div>
                    
                    <h4>色分布分析:</h4>
                    <div class="color-grid">
"""
            
            # 色分布情報を表示（パーセンテージでソート）
            sorted_colors = sorted(result['color_analysis'].items(), 
                                 key=lambda x: x[1]['percentage'], reverse=True)
            
            for color_name, color_data in sorted_colors[:8]:  # 上位8色のみ表示
                percentage = color_data['percentage']
                if percentage > 1.0:
                    intensity_class = "high"
                elif percentage > 0.1:
                    intensity_class = "medium"
                else:
                    intensity_class = "low"
                
                html_content += f"""
                        <div class="color-item">
                            <div>{color_data['name']}</div>
                            <div class="{intensity_class}">{percentage:.2f}%</div>
                        </div>"""
            
            html_content += """
                    </div>
                </div>
            </div>
"""
        
        html_content += """
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"色検出レポートを生成: {output_file}")
        
        # サマリー表示
        successful = [r for r in analysis_results if r['success']]
        failed = [r for r in analysis_results if not r['success']]
        
        print(f"\n=== 色検出分析結果 ===")
        print(f"総画像数: {len(analysis_results)}")
        print(f"検出成功: {len(successful)} ({len(successful)/len(analysis_results)*100:.1f}%)")
        print(f"検出失敗: {len(failed)} ({len(failed)/len(analysis_results)*100:.1f}%)")
        
        if successful:
            # 成功画像で最も多い色を特定
            color_counts = {}
            for result in successful:
                color = result['detected_color']
                color_counts[color] = color_counts.get(color, 0) + 1
            
            most_common_color = max(color_counts.items(), key=lambda x: x[1])
            print(f"最も成功率の高い色: {most_common_color[0]} ({most_common_color[1]}回)")
        
        return analysis_results

if __name__ == "__main__":
    detector = ImprovedColorDetector()
    
    # 色検出分析実行
    image_pattern = "graphs/manual_crop/cropped/*_graph_only.png"
    results = detector.create_color_detection_report(image_pattern)
    
    print(f"\n詳細な色分布分析完了。HTMLレポートで確認してください。")