#!/usr/bin/env python3
"""
最新の分析結果を統合してHTMLレポートを生成
"""

import os
import json
from datetime import datetime
from pathlib import Path
import numpy as np

def generate_comprehensive_report():
    """包括的な分析レポートを生成"""
    
    # ゼロライン検出結果を集計
    zero_detection_results = []
    detection_dir = Path("zero_detection_results")
    if detection_dir.exists():
        for img_path in detection_dir.glob("*_detection.png"):
            zero_detection_results.append(img_path.name)
    
    # 最新のゼロライン検出統計（advanced_zero_line_detector.pyの実行結果より）
    zero_line_stats = {
        "mean": 249.5,
        "std": 0.7,
        "min": 249,
        "max": 251,
        "confidence": 0.65,
        "agreement": 0.96,
        "sample_count": 27
    }
    
    # HTML生成
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>パチンコグラフ分析 - 最新レポート</title>
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
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin: 30px 0;
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .summary-item {{
            background: rgba(255,255,255,0.2);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .summary-label {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        .summary-value {{
            font-size: 32px;
            font-weight: bold;
        }}
        .section {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .status-badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
            margin: 5px;
        }}
        .status-complete {{
            background: #28a745;
            color: white;
        }}
        .status-improved {{
            background: #17a2b8;
            color: white;
        }}
        .status-new {{
            background: #ffc107;
            color: #333;
        }}
        .improvement-box {{
            background: #e8f5e9;
            border-left: 4px solid #4caf50;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .tool-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .tool-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #e9ecef;
        }}
        .tool-card h3 {{
            color: #007bff;
            margin-top: 0;
        }}
        .code-block {{
            background: #f4f4f4;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            margin: 10px 0;
            font-family: monospace;
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .timestamp {{
            text-align: center;
            color: #666;
            margin-top: 50px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <h1>🎯 パチンコグラフ分析プロジェクト - 最新レポート</h1>
    
    <div class="summary-card">
        <h2>📊 プロジェクト進捗サマリー</h2>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-label">処理済み画像数</div>
                <div class="summary-value">{zero_line_stats['sample_count']}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">ゼロライン平均</div>
                <div class="summary-value">Y={zero_line_stats['mean']:.1f}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">検出精度</div>
                <div class="summary-value">{zero_line_stats['confidence']*100:.0f}%</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">手法間一致度</div>
                <div class="summary-value">{zero_line_stats['agreement']*100:.0f}%</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>🔄 最新の改善点</h2>
        
        <div class="improvement-box">
            <h3>✅ ゼロライン検出精度の大幅改善</h3>
            <p>
                <span class="status-badge status-improved">改善</span>
                従来のY=260固定値から、高精度な自動検出システムに移行しました。
            </p>
            <ul>
                <li>5つの異なる検出手法を組み合わせた高精度検出</li>
                <li>検出結果: Y={zero_line_stats['min']}-{zero_line_stats['max']}（平均Y={zero_line_stats['mean']:.1f}、標準偏差{zero_line_stats['std']:.1f}）</li>
                <li>全27画像で安定した検出結果を達成</li>
            </ul>
        </div>
        
        <div class="improvement-box">
            <h3>🖼️ インタラクティブな分析ツール</h3>
            <p>
                <span class="status-badge status-new">新機能</span>
                3つの新しいツールを実装しました。
            </p>
            <ul>
                <li><strong>advanced_zero_line_detector.py</strong> - 複数手法による高精度検出</li>
                <li><strong>multi_image_comparison_viewer.py</strong> - 複数画像の一括比較表示</li>
                <li><strong>interactive_graph_analyzer.html</strong> - ドラッグ操作可能な分析ツール</li>
            </ul>
        </div>
    </div>

    <div class="section">
        <h2>📈 ゼロライン検出の詳細統計</h2>
        <table>
            <tr>
                <th>統計項目</th>
                <th>値</th>
                <th>説明</th>
            </tr>
            <tr>
                <td>平均Y座標</td>
                <td>{zero_line_stats['mean']:.1f}</td>
                <td>27画像の平均ゼロライン位置</td>
            </tr>
            <tr>
                <td>標準偏差</td>
                <td>{zero_line_stats['std']:.1f}</td>
                <td>検出位置のばらつき（小さいほど安定）</td>
            </tr>
            <tr>
                <td>最小値</td>
                <td>{zero_line_stats['min']}</td>
                <td>検出された最も上のゼロライン</td>
            </tr>
            <tr>
                <td>最大値</td>
                <td>{zero_line_stats['max']}</td>
                <td>検出された最も下のゼロライン</td>
            </tr>
            <tr>
                <td>信頼度</td>
                <td>{zero_line_stats['confidence']*100:.0f}%</td>
                <td>各手法の平均信頼度</td>
            </tr>
            <tr>
                <td>一致度</td>
                <td>{zero_line_stats['agreement']*100:.0f}%</td>
                <td>異なる手法間の結果の一致度</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <h2>🛠️ 利用可能なツール</h2>
        <div class="tool-grid">
            <div class="tool-card">
                <h3>1. 高精度ゼロライン検出</h3>
                <p>複数の画像処理手法を組み合わせて、ゼロラインを自動検出します。</p>
                <div class="code-block">python advanced_zero_line_detector.py</div>
                <p>出力: zero_detection_results/フォルダに検出結果画像</p>
            </div>
            
            <div class="tool-card">
                <h3>2. 複数画像比較ビューワー</h3>
                <p>検出結果やスケールテスト結果を一括で比較表示します。</p>
                <div class="code-block">python multi_image_comparison_viewer.py</div>
                <p>出力: zero_line_comparison/index.html</p>
            </div>
            
            <div class="tool-card">
                <h3>3. インタラクティブ分析ツール</h3>
                <p>ブラウザ上でグラフを分析し、ラインをドラッグで調整できます。</p>
                <div class="code-block">open interactive_graph_analyzer.html</div>
                <p>機能: 自動検出、手動調整、リアルタイム分析</p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>🎯 今後の課題</h2>
        <ul>
            <li>スケール（1ピクセルあたりの値）の自動検出精度向上</li>
            <li>グラフの種類（機種）別の最適化</li>
            <li>バッチ処理の高速化</li>
            <li>エラー処理とログ機能の強化</li>
        </ul>
    </div>

    <div class="timestamp">
        <p>レポート生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        <p>パチンコグラフ分析プロジェクト v2.0</p>
    </div>
</body>
</html>"""
    
    # レポート保存
    with open("latest_report.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("最新レポートを生成しました: latest_report.html")
    
    # 自動で開く
    os.system("open latest_report.html")

if __name__ == "__main__":
    generate_comprehensive_report()