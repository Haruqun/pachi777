#!/usr/bin/env python3
"""
最大数抽出専用ツール - シンプル&高速
元画像から最大値のみを効率的に抽出
"""

import cv2
import numpy as np
import glob
from pathlib import Path
import json
from datetime import datetime

class SimpleMaxExtractor:
    def __init__(self):
        # 改良された色検出範囲
        self.color_ranges = {
            'pink': {'lower': np.array([140, 50, 50]), 'upper': np.array([170, 255, 255])},
            'magenta': {'lower': np.array([130, 100, 100]), 'upper': np.array([160, 255, 255])},
            'red': {'lower': np.array([0, 100, 100]), 'upper': np.array([10, 255, 255])},
            'red_high': {'lower': np.array([170, 100, 100]), 'upper': np.array([180, 255, 255])},
            'blue': {'lower': np.array([100, 100, 100]), 'upper': np.array([130, 255, 255])},
            'green': {'lower': np.array([40, 100, 100]), 'upper': np.array([80, 255, 255])},
            'cyan': {'lower': np.array([80, 100, 100]), 'upper': np.array([100, 255, 255])},
            'yellow': {'lower': np.array([20, 100, 100]), 'upper': np.array([40, 255, 255])},
            'orange': {'lower': np.array([10, 100, 100]), 'upper': np.array([25, 255, 255])},
            'purple': {'lower': np.array([120, 100, 100]), 'upper': np.array([140, 255, 255])}
        }
        
        self.results = []
    
    def detect_zero_line(self, img):
        """ゼロライン高速検出"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # 中央部分を検索
        search_top = height // 3
        search_bottom = height * 2 // 3
        
        # 水平線の濃い部分を検出
        for y in range(search_top, search_bottom):
            row = gray[y, :]
            dark_pixels = np.sum(row < 100)
            if dark_pixels > width * 0.7:  # 70%以上が暗い場合
                return y
        
        return 250  # デフォルト値
    
    def extract_max_value_only(self, img_path):
        """最大値のみを高速抽出"""
        img = cv2.imread(img_path)
        if img is None:
            return None, "なし"
            
        height, width = img.shape[:2]
        zero_y = self.detect_zero_line(img)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # スケール計算 (30,000を画像上部Y=5に配置)
        scale = 30000 / (zero_y - 5)
        
        max_value = 0
        detected_color = "なし"
        
        # 各色での検出を試行
        for color_name, color_range in self.color_ranges.items():
            mask = cv2.inRange(hsv, color_range['lower'], color_range['upper'])
            
            # 最上部のY座標を検索（最大値に対応）
            colored_pixels = np.where(mask > 0)
            if len(colored_pixels[0]) > 0:
                min_y = np.min(colored_pixels[0])
                value = (zero_y - min_y) * scale
                
                if value > max_value:
                    max_value = value
                    detected_color = color_name
        
        return int(max_value) if max_value > 0 else None, detected_color
    
    def process_all_images(self):
        """全画像の最大値を抽出"""
        original_files = glob.glob("graphs/original/*.jpg")
        
        print(f"🚀 最大値抽出開始: {len(original_files)}枚の画像")
        print("=" * 50)
        
        for img_file in original_files:
            file_name = Path(img_file).stem
            print(f"処理中: {file_name}")
            
            max_value, detected_color = self.extract_max_value_only(img_file)
            
            result = {
                'file_name': file_name,
                'max_value': max_value,
                'detected_color': detected_color,
                'image_path': img_file
            }
            
            self.results.append(result)
            
            if max_value:
                print(f"  ✅ 最大値: +{max_value:,} ({detected_color})")
            else:
                print(f"  ❌ 検出失敗")
        
        return self.results
    
    def save_results(self):
        """結果をJSON形式で保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"max_values_report_{timestamp}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_images': len(self.results),
            'successful_extractions': len([r for r in self.results if r['max_value']]),
            'results': self.results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 結果保存: {output_file}")
        return output_file
    
    def create_simple_html_report(self):
        """シンプルなHTMLレポート生成"""
        successful_results = [r for r in self.results if r['max_value']]
        
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📈 最大値抽出レポート</title>
    <style>
        body {{
            font-family: 'Hiragino Sans', 'Meiryo', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }}
        .results-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .result-card {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .max-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #4ecdc4;
        }}
        .no-value {{
            color: #ff6b6b;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 パチンコ最大値抽出レポート</h1>
            <p>作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>総画像数</h3>
                <div style="font-size: 2em;">{len(self.results)}</div>
            </div>
            <div class="stat-card">
                <h3>抽出成功</h3>
                <div style="font-size: 2em;">{len(successful_results)}</div>
            </div>
            <div class="stat-card">
                <h3>成功率</h3>
                <div style="font-size: 2em;">{len(successful_results)/len(self.results)*100:.1f}%</div>
            </div>
            <div class="stat-card">
                <h3>最高値</h3>
                <div style="font-size: 2em;">{max([r['max_value'] for r in successful_results], default=0):,}</div>
            </div>
        </div>
        
        <h2>📊 画像別最大値一覧</h2>
        <div class="results-grid">
"""
        
        for result in self.results:
            file_name = result['file_name']
            max_value = result['max_value']
            detected_color = result['detected_color']
            
            if max_value:
                html_content += f"""
            <div class="result-card">
                <div>
                    <div style="font-weight: bold;">{file_name}</div>
                    <div style="font-size: 0.9em; opacity: 0.7;">検出色: {detected_color}</div>
                </div>
                <div class="max-value">+{max_value:,}</div>
            </div>"""
            else:
                html_content += f"""
            <div class="result-card">
                <div>
                    <div style="font-weight: bold;">{file_name}</div>
                    <div style="font-size: 0.9em; opacity: 0.7;">検出失敗</div>
                </div>
                <div class="no-value">---</div>
            </div>"""
        
        html_content += """
        </div>
    </div>
</body>
</html>"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"max_values_report_{timestamp}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 HTMLレポート保存: {output_file}")
        return output_file

if __name__ == "__main__":
    extractor = SimpleMaxExtractor()
    
    # 全画像の最大値を抽出
    results = extractor.process_all_images()
    
    # 結果サマリー
    successful = [r for r in results if r['max_value']]
    print("\n" + "=" * 50)
    print(f"✅ 抽出完了")
    print(f"📊 総画像数: {len(results)}")
    print(f"🎯 成功数: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
    
    if successful:
        max_values = [r['max_value'] for r in successful]
        print(f"📈 最高値: +{max(max_values):,}")
        print(f"📊 平均値: +{int(np.mean(max_values)):,}")
    
    # 結果を保存
    extractor.save_results()
    extractor.create_simple_html_report()
    
    print("=" * 50)