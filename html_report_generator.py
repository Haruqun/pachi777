#!/usr/bin/env python3
"""
HTMLレポート生成・更新システム
テスト結果を自動的にHTMLレポートに追加
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

class HTMLReportGenerator:
    """HTMLレポート生成クラス"""
    
    def __init__(self, report_path="report.html"):
        self.report_path = report_path
        self.test_results_dir = "test_results"
        os.makedirs(self.test_results_dir, exist_ok=True)
        
        # テスト結果を保存するJSON
        self.results_json = os.path.join(self.test_results_dir, "all_results.json")
        self.load_results()
    
    def load_results(self):
        """既存の結果を読み込み"""
        if os.path.exists(self.results_json):
            with open(self.results_json, 'r', encoding='utf-8') as f:
                self.all_results = json.load(f)
        else:
            self.all_results = {
                "tests": [],
                "current_best": {
                    "zero_line": 260,
                    "scale": 120,
                    "accuracy": 0
                }
            }
    
    def save_results(self):
        """結果を保存"""
        with open(self.results_json, 'w', encoding='utf-8') as f:
            json.dump(self.all_results, f, ensure_ascii=False, indent=2)
    
    def add_test_result(self, test_name, test_data, images=None):
        """テスト結果を追加"""
        test_id = f"test_{len(self.all_results['tests']) + 1}"
        
        # 画像をコピー
        if images:
            test_images_dir = os.path.join(self.test_results_dir, test_id)
            os.makedirs(test_images_dir, exist_ok=True)
            
            copied_images = []
            for img_path in images:
                if os.path.exists(img_path):
                    dest_name = os.path.basename(img_path)
                    dest_path = os.path.join(test_images_dir, dest_name)
                    shutil.copy2(img_path, dest_path)
                    copied_images.append(os.path.join(test_id, dest_name))
            
            test_data['images'] = copied_images
        
        # テスト結果を追加
        test_result = {
            "id": test_id,
            "name": test_name,
            "timestamp": datetime.now().isoformat(),
            "data": test_data
        }
        
        self.all_results['tests'].append(test_result)
        
        # 最良の結果を更新
        if 'accuracy' in test_data and test_data['accuracy'] > self.all_results['current_best']['accuracy']:
            self.all_results['current_best'] = {
                "zero_line": test_data.get('zero_line', 260),
                "scale": test_data.get('scale', 120),
                "accuracy": test_data['accuracy'],
                "test_id": test_id
            }
        
        self.save_results()
        self.generate_html()
        
        return test_id
    
    def generate_html(self):
        """HTMLレポートを生成"""
        html_template = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>パチンコグラフ分析 - テスト結果レポート</title>
    <style>
        body {{
            font-family: 'Hiragino Sans', 'Meiryo', sans-serif;
            line-height: 1.6;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1, h2, h3 {{
            color: #333;
        }}
        h1 {{
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        .current-best {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin: 30px 0;
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }}
        .current-best h2 {{
            color: white;
            border: none;
            margin-top: 0;
        }}
        .best-values {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .best-value {{
            background: rgba(255,255,255,0.2);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .best-value .label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .best-value .value {{
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .test-card {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .test-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }}
        .test-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .test-number {{
            background: #007bff;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }}
        .test-images {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .test-image {{
            position: relative;
            overflow: hidden;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .test-image img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .test-image-label {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 8px;
            font-size: 12px;
        }}
        .test-data {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
        }}
        .test-data table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .test-data td {{
            padding: 8px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .test-data td:first-child {{
            font-weight: bold;
            color: #666;
            width: 150px;
        }}
        .accuracy-high {{
            color: #28a745;
            font-weight: bold;
        }}
        .accuracy-medium {{
            color: #ffc107;
            font-weight: bold;
        }}
        .accuracy-low {{
            color: #dc3545;
            font-weight: bold;
        }}
        .timestamp {{
            color: #666;
            font-size: 14px;
        }}
        .no-tests {{
            text-align: center;
            padding: 60px;
            color: #999;
        }}
    </style>
</head>
<body>
    <h1>🎯 パチンコグラフ分析 - テスト結果レポート</h1>
    
    <div class="current-best">
        <h2>🏆 現在の最良設定</h2>
        <div class="best-values">
            <div class="best-value">
                <div class="label">ゼロライン位置</div>
                <div class="value">Y = {zero_line}</div>
            </div>
            <div class="best-value">
                <div class="label">スケール</div>
                <div class="value">1px = {scale}</div>
            </div>
            <div class="best-value">
                <div class="label">精度</div>
                <div class="value">{accuracy}%</div>
            </div>
        </div>
    </div>
    
    <h2>📊 テスト履歴</h2>
    {test_results}
    
    <footer style="text-align: center; margin-top: 50px; padding: 20px; color: #666;">
        <p>最終更新: {last_update} | パチンコグラフ分析プロジェクト</p>
    </footer>
</body>
</html>"""
        
        # テスト結果のHTML生成
        if self.all_results['tests']:
            test_html = ""
            for i, test in enumerate(reversed(self.all_results['tests'])):
                test_num = len(self.all_results['tests']) - i
                
                # 画像HTML
                images_html = ""
                if 'images' in test['data']:
                    for img_path in test['data']['images']:
                        full_path = os.path.join(self.test_results_dir, img_path)
                        img_name = os.path.basename(img_path)
                        images_html += f'''
                        <div class="test-image">
                            <img src="{full_path}" alt="{img_name}">
                            <div class="test-image-label">{img_name}</div>
                        </div>'''
                
                # データテーブル
                data_rows = ""
                for key, value in test['data'].items():
                    if key != 'images':
                        if key == 'accuracy':
                            accuracy_class = 'accuracy-high' if value > 90 else 'accuracy-medium' if value > 70 else 'accuracy-low'
                            value_str = f'<span class="{accuracy_class}">{value}%</span>'
                        else:
                            value_str = str(value)
                        data_rows += f'<tr><td>{key}</td><td>{value_str}</td></tr>'
                
                test_html += f'''
                <div class="test-card">
                    <div class="test-header">
                        <h3>{test['name']}</h3>
                        <div>
                            <span class="test-number">Test #{test_num}</span>
                            <span class="timestamp">{test['timestamp'][:19].replace('T', ' ')}</span>
                        </div>
                    </div>
                    {f'<div class="test-images">{images_html}</div>' if images_html else ''}
                    <div class="test-data">
                        <table>{data_rows}</table>
                    </div>
                </div>'''
            
            test_results_html = test_html
        else:
            test_results_html = '<div class="no-tests">まだテスト結果がありません</div>'
        
        # HTML生成
        html = html_template.format(
            zero_line=self.all_results['current_best']['zero_line'],
            scale=self.all_results['current_best']['scale'],
            accuracy=self.all_results['current_best']['accuracy'],
            test_results=test_results_html,
            last_update=datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
        )
        
        with open(self.report_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"HTMLレポート更新: {self.report_path}")

# 使用例
def test_scale_detection():
    """スケール検出テストの例"""
    generator = HTMLReportGenerator()
    
    # テスト結果を追加
    test_data = {
        "zero_line": 260,
        "scale": 120.24,
        "accuracy": 85.5,
        "method": "手動測定",
        "10000_position_error": "±2px",
        "20000_position_error": "±3px"
    }
    
    # 関連画像
    images = [
        "graphs/scale_corrected_S__78209138_graph_only.png",
        "graphs/zero_line_test/test_y260.png"
    ]
    
    # テスト結果を追加
    test_id = generator.add_test_result(
        "スケール精密測定テスト",
        test_data,
        images
    )
    
    print(f"テスト結果を追加しました: {test_id}")
    print(f"ブラウザでレポートを確認してください: {generator.report_path}")

if __name__ == "__main__":
    # 初期レポート生成
    generator = HTMLReportGenerator()
    generator.generate_html()
    print("HTMLレポートシステムを初期化しました")