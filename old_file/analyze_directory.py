#!/usr/bin/env python3
"""
ディレクトリ構造分析ツール
試験的ファイルと本番用ファイルを分類
"""

import os
import glob
from datetime import datetime
from collections import defaultdict

def analyze_files():
    """ファイルを分類"""
    
    categories = {
        'production': {
            'description': '本番用・メインシステム',
            'patterns': [
                'complete_pipeline.py',
                'quick_analysis.py',
                'manual_graph_cropper.py',
                'professional_graph_report.py',
                'web_package_creator.py',
                'CLAUDE.md',
                'README_PIPELINE.md'
            ],
            'files': []
        },
        'test_scripts': {
            'description': 'テスト・実験用スクリプト',
            'patterns': [
                'test_*.py',
                'debug_*.py',
                'draw_*.py',
                'measure_*.py',
                'simple_*.py',
                'improved_*.py',
                'accurate_*.py',
                'advanced_*.py'
            ],
            'files': []
        },
        'analysis_tools': {
            'description': '分析・抽出ツール（開発中）',
            'patterns': [
                '*_extractor.py',
                '*_detector.py',
                '*_analyzer.py',
                '*_reader.py',
                '*_enhancer.py'
            ],
            'files': []
        },
        'report_generators': {
            'description': 'レポート生成ツール',
            'patterns': [
                '*_report_generator.py',
                'create_*.py',
                'generate_*.py',
                'html_*.py'
            ],
            'files': []
        },
        'legacy': {
            'description': '旧バージョン・非推奨',
            'patterns': [
                'perfect_*.py',
                'refined_*.py',
                'stable_*.py',
                'comprehensive_*.py',
                'ultimate_*.py',
                'final_*.py'
            ],
            'files': []
        },
        'data_files': {
            'description': 'データファイル',
            'patterns': [
                '*.json',
                '*.csv',
                '*.txt',
                '*.html',
                '*.zip'
            ],
            'files': []
        },
        'images': {
            'description': '画像ファイル',
            'patterns': [
                '*.png',
                '*.jpg',
                '*.jpeg'
            ],
            'files': []
        }
    }
    
    # 全ファイルを取得
    all_files = []
    for pattern in ['*.py', '*.json', '*.csv', '*.txt', '*.html', '*.zip', '*.png', '*.jpg']:
        all_files.extend(glob.glob(pattern))
    
    # ファイルを分類
    categorized = set()
    
    for category, info in categories.items():
        for pattern in info['patterns']:
            matching_files = glob.glob(pattern)
            for file in matching_files:
                if file not in categorized:
                    info['files'].append(file)
                    categorized.add(file)
    
    # 未分類ファイル
    uncategorized = [f for f in all_files if f not in categorized]
    
    return categories, uncategorized

def print_analysis():
    """分析結果を表示"""
    categories, uncategorized = analyze_files()
    
    print("=" * 80)
    print("📁 ディレクトリ分析レポート")
    print("=" * 80)
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # カテゴリ別に表示
    for category, info in categories.items():
        if info['files']:
            print(f"\n📂 {category.upper()} - {info['description']}")
            print(f"   ファイル数: {len(info['files'])}")
            print("-" * 60)
            for file in sorted(info['files']):
                size = os.path.getsize(file) / 1024  # KB
                print(f"   - {file:50} ({size:>8.1f} KB)")
    
    # 未分類ファイル
    if uncategorized:
        print(f"\n❓ 未分類ファイル: {len(uncategorized)}個")
        print("-" * 60)
        for file in sorted(uncategorized):
            size = os.path.getsize(file) / 1024
            print(f"   - {file:50} ({size:>8.1f} KB)")
    
    # サマリー
    total_files = sum(len(info['files']) for info in categories.values()) + len(uncategorized)
    print(f"\n📊 サマリー")
    print("-" * 60)
    print(f"総ファイル数: {total_files}")
    print(f"本番用: {len(categories['production']['files'])}")
    print(f"テスト用: {len(categories['test_scripts']['files'])}")
    print(f"レガシー: {len(categories['legacy']['files'])}")
    print(f"データ: {len(categories['data_files']['files'])}")
    print(f"画像: {len(categories['images']['files'])}")

def suggest_structure():
    """推奨ディレクトリ構造を提案"""
    print("\n" + "=" * 80)
    print("🏗️  推奨ディレクトリ構造")
    print("=" * 80)
    
    structure = """
pachi777/
│
├── 📁 production/              # 本番用システム
│   ├── complete_pipeline.py
│   ├── quick_analysis.py
│   ├── manual_graph_cropper.py
│   ├── professional_graph_report.py
│   └── web_package_creator.py
│
├── 📁 docs/                    # ドキュメント
│   ├── CLAUDE.md
│   └── README_PIPELINE.md
│
├── 📁 dev/                     # 開発・実験用
│   ├── test_scripts/          # テストスクリプト
│   ├── analyzers/             # 分析ツール
│   ├── detectors/             # 検出ツール
│   └── experiments/           # 実験的コード
│
├── 📁 legacy/                  # 旧バージョン
│   └── (perfect_*, final_* など)
│
├── 📁 output/                  # 出力ファイル
│   ├── reports/               # HTMLレポート
│   ├── packages/              # ZIPパッケージ
│   └── analysis_images/       # 分析画像
│
├── 📁 data/                    # データファイル
│   ├── json/
│   ├── csv/
│   └── txt/
│
├── 📁 graphs/                  # 画像データ（既存）
│   ├── original/
│   ├── manual_crop/
│   └── extracted_data/
│
└── 📁 backup/                  # バックアップ
    └── backup_YYYYMMDD_HHMMSS/
"""
    print(structure)

if __name__ == "__main__":
    print_analysis()
    suggest_structure()
    
    print("\n💡 次のステップ:")
    print("1. organize_directory.py を実行して自動整理")
    print("2. または手動で必要なファイルを移動")
    print("3. 不要なファイルをbackupまたは削除")