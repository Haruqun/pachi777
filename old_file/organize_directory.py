#!/usr/bin/env python3
"""
ディレクトリ自動整理ツール
ファイルを適切なディレクトリに整理
"""

import os
import shutil
import glob
from datetime import datetime
from pathlib import Path

class DirectoryOrganizer:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.moves = []
        self.errors = []
        
    def create_directory_structure(self):
        """新しいディレクトリ構造を作成"""
        directories = [
            'production',
            'docs',
            'dev/test_scripts',
            'dev/analyzers',
            'dev/detectors',
            'dev/experiments',
            'legacy',
            'output/reports',
            'output/packages',
            'output/analysis_images',
            'data/json',
            'data/csv',
            'data/txt',
            'backup'
        ]
        
        if not self.dry_run:
            for dir_path in directories:
                os.makedirs(dir_path, exist_ok=True)
                print(f"✅ ディレクトリ作成: {dir_path}")
        else:
            print("📁 作成予定のディレクトリ:")
            for dir_path in directories:
                print(f"   - {dir_path}")
        
        return directories
    
    def plan_moves(self):
        """ファイル移動計画を作成"""
        
        # 本番用ファイル
        production_files = [
            'complete_pipeline.py',
            'quick_analysis.py',
            'manual_graph_cropper.py',
            'professional_graph_report.py',
            'web_package_creator.py'
        ]
        
        # ドキュメント
        doc_files = [
            'CLAUDE.md',
            'README_PIPELINE.md'
        ]
        
        # レガシーファイル
        legacy_patterns = [
            'perfect_*.py',
            'refined_*.py',
            'stable_*.py',
            'comprehensive_*.py',
            'ultimate_*.py',
            'final_*.py'
        ]
        
        # 移動計画作成
        # 本番用
        for file in production_files:
            if os.path.exists(file):
                self.moves.append((file, f'production/{file}'))
        
        # ドキュメント
        for file in doc_files:
            if os.path.exists(file):
                self.moves.append((file, f'docs/{file}'))
        
        # レガシー
        for pattern in legacy_patterns:
            for file in glob.glob(pattern):
                if file not in production_files:  # 本番用は除外
                    self.moves.append((file, f'legacy/{file}'))
        
        # テストスクリプト
        test_patterns = ['test_*.py', 'debug_*.py', 'draw_*.py', 'measure_*.py']
        for pattern in test_patterns:
            for file in glob.glob(pattern):
                self.moves.append((file, f'dev/test_scripts/{file}'))
        
        # 分析ツール
        analyzer_patterns = ['*_analyzer.py', '*_extractor.py', '*_detector.py', '*_reader.py']
        for pattern in analyzer_patterns:
            for file in glob.glob(pattern):
                if file not in [m[0] for m in self.moves]:  # 既に計画済みは除外
                    self.moves.append((file, f'dev/analyzers/{file}'))
        
        # HTMLレポート
        html_reports = glob.glob('*_report_*.html') + glob.glob('*_analysis_report.html')
        for file in html_reports:
            self.moves.append((file, f'output/reports/{file}'))
        
        # ZIPパッケージ
        for file in glob.glob('*.zip'):
            self.moves.append((file, f'output/packages/{file}'))
        
        # 分析画像
        analysis_images = glob.glob('*_analysis_*.png') + glob.glob('*_overlay_*.png')
        for file in analysis_images:
            self.moves.append((file, f'output/analysis_images/{file}'))
        
        # データファイル
        for file in glob.glob('*.json'):
            self.moves.append((file, f'data/json/{file}'))
        
        for file in glob.glob('*.csv'):
            self.moves.append((file, f'data/csv/{file}'))
        
        for file in glob.glob('*.txt'):
            if file not in ['requirements.txt']:  # 特殊ファイルは除外
                self.moves.append((file, f'data/txt/{file}'))
        
        return self.moves
    
    def execute_moves(self):
        """ファイル移動を実行"""
        print(f"\n📦 移動計画: {len(self.moves)}個のファイル")
        print("-" * 60)
        
        for src, dst in self.moves:
            try:
                if self.dry_run:
                    print(f"   {src:50} → {dst}")
                else:
                    # 実際の移動
                    dst_dir = os.path.dirname(dst)
                    os.makedirs(dst_dir, exist_ok=True)
                    
                    # 既存ファイルがある場合はバックアップ
                    if os.path.exists(dst):
                        backup_dst = f"backup/{os.path.basename(dst)}.{self.timestamp}"
                        shutil.move(dst, backup_dst)
                        print(f"   ⚠️  既存ファイルをバックアップ: {backup_dst}")
                    
                    shutil.move(src, dst)
                    print(f"   ✅ {src} → {dst}")
                    
            except Exception as e:
                self.errors.append((src, dst, str(e)))
                print(f"   ❌ エラー: {src} - {e}")
    
    def cleanup_empty_dirs(self):
        """空のディレクトリを削除"""
        if not self.dry_run:
            # graphs/ と backup/ は除外
            for root, dirs, files in os.walk('.', topdown=False):
                if root.startswith('./graphs') or root.startswith('./backup'):
                    continue
                    
                if not dirs and not files and root != '.':
                    try:
                        os.rmdir(root)
                        print(f"   🗑️  空ディレクトリ削除: {root}")
                    except:
                        pass
    
    def generate_report(self):
        """整理レポートを生成"""
        report = f"""
ディレクトリ整理レポート
========================
実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
モード: {'実行' if not self.dry_run else 'ドライラン'}

移動ファイル数: {len(self.moves)}
エラー数: {len(self.errors)}

エラー詳細:
"""
        for src, dst, error in self.errors:
            report += f"  - {src} → {dst}: {error}\n"
        
        if not self.dry_run:
            with open(f'backup/organize_report_{self.timestamp}.txt', 'w') as f:
                f.write(report)
        
        return report

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ディレクトリ自動整理ツール')
    parser.add_argument('--execute', action='store_true', 
                       help='実際にファイルを移動（デフォルトはドライラン）')
    parser.add_argument('--skip-images', action='store_true',
                       help='画像ファイルの移動をスキップ')
    
    args = parser.parse_args()
    
    print("🧹 ディレクトリ整理ツール")
    print("=" * 60)
    
    organizer = DirectoryOrganizer(dry_run=not args.execute)
    
    # 1. ディレクトリ構造作成
    print("\n1️⃣ ディレクトリ構造の作成")
    organizer.create_directory_structure()
    
    # 2. 移動計画
    print("\n2️⃣ ファイル移動計画")
    moves = organizer.plan_moves()
    
    # 画像をスキップする場合
    if args.skip_images:
        organizer.moves = [(s, d) for s, d in moves if not s.endswith(('.png', '.jpg'))]
        print(f"   画像ファイルをスキップ: {len(moves) - len(organizer.moves)}個")
    
    # 3. 実行
    print("\n3️⃣ ファイル移動")
    organizer.execute_moves()
    
    # 4. クリーンアップ
    if not organizer.dry_run:
        print("\n4️⃣ 空ディレクトリのクリーンアップ")
        organizer.cleanup_empty_dirs()
    
    # 5. レポート
    print("\n5️⃣ 整理レポート")
    report = organizer.generate_report()
    print(report)
    
    if organizer.dry_run:
        print("\n💡 実際に移動を実行するには --execute オプションを付けてください")
        print("   python organize_directory.py --execute")
        print("\n💡 画像ファイルをスキップするには --skip-images を追加")
        print("   python organize_directory.py --execute --skip-images")

if __name__ == "__main__":
    main()