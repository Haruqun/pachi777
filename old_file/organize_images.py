#!/usr/bin/env python3
"""
画像ファイル整理専用ツール
ルートディレクトリの画像を適切な場所に整理
"""

import os
import shutil
import glob
from datetime import datetime
from collections import defaultdict

class ImageOrganizer:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.moves = []
        self.stats = defaultdict(int)
        
    def analyze_images(self):
        """画像ファイルを分析して分類"""
        
        # ルートディレクトリの画像ファイルを取得
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg']:
            image_files.extend(glob.glob(ext))
        
        print(f"🖼️  ルートディレクトリの画像ファイル: {len(image_files)}個")
        
        # 画像を種類別に分類
        categories = {
            'analysis_overlay': [],
            'integrated_analysis': [],
            'professional_analysis': [],
            'final_analysis': [],
            'grid_overlay': [],
            'scale_test': [],
            'zero_line': [],
            'visualization': [],
            'comparison': [],
            'workflow': [],
            'misc': []
        }
        
        for img in sorted(image_files):
            if 'analysis_overlay' in img:
                categories['analysis_overlay'].append(img)
            elif 'integrated_analysis' in img:
                categories['integrated_analysis'].append(img)
            elif 'professional_analysis' in img:
                categories['professional_analysis'].append(img)
            elif 'final_analysis' in img:
                categories['final_analysis'].append(img)
            elif 'grid_overlay' in img or 'grid_' in img:
                categories['grid_overlay'].append(img)
            elif 'scale_test' in img or 'scale_corrected' in img:
                categories['scale_test'].append(img)
            elif 'zero_line' in img or 'zero_plus' in img or 'zero_detection' in img:
                categories['zero_line'].append(img)
            elif 'visual_report' in img or 'workflow_diagram' in img:
                categories['workflow'].append(img)
            elif 'comparison' in img or 'variance' in img:
                categories['comparison'].append(img)
            else:
                categories['misc'].append(img)
        
        return categories
    
    def plan_image_moves(self, categories):
        """画像の移動計画を作成"""
        
        # カテゴリ別の移動先
        destinations = {
            'analysis_overlay': 'output/analysis_images/overlay',
            'integrated_analysis': 'output/analysis_images/integrated',
            'professional_analysis': 'output/analysis_images/professional',
            'final_analysis': 'output/analysis_images/final',
            'grid_overlay': 'output/analysis_images/grid_tests',
            'scale_test': 'output/analysis_images/scale_tests',
            'zero_line': 'output/analysis_images/zero_line_tests',
            'visualization': 'output/analysis_images/visualizations',
            'comparison': 'output/analysis_images/comparisons',
            'workflow': 'docs/images',
            'misc': 'archive/misc_images'
        }
        
        # 移動計画作成
        for category, files in categories.items():
            dest_dir = destinations[category]
            for file in files:
                self.moves.append((file, f"{dest_dir}/{file}"))
                self.stats[category] += 1
        
        return self.moves
    
    def create_directories(self):
        """必要なディレクトリを作成"""
        required_dirs = [
            'output/analysis_images/overlay',
            'output/analysis_images/integrated',
            'output/analysis_images/professional',
            'output/analysis_images/final',
            'output/analysis_images/grid_tests',
            'output/analysis_images/scale_tests',
            'output/analysis_images/zero_line_tests',
            'output/analysis_images/visualizations',
            'output/analysis_images/comparisons',
            'docs/images',
            'archive/misc_images'
        ]
        
        if not self.dry_run:
            for dir_path in required_dirs:
                os.makedirs(dir_path, exist_ok=True)
                print(f"✅ ディレクトリ作成: {dir_path}")
    
    def execute_moves(self):
        """画像ファイルの移動を実行"""
        print(f"\n📦 移動計画: {len(self.moves)}個の画像ファイル")
        print("-" * 60)
        
        for src, dst in sorted(self.moves):
            try:
                if self.dry_run:
                    print(f"   {src:50} → {dst}")
                else:
                    # 実際の移動
                    dst_dir = os.path.dirname(dst)
                    os.makedirs(dst_dir, exist_ok=True)
                    
                    # 既存ファイルがある場合はスキップ
                    if os.path.exists(dst):
                        print(f"   ⚠️  既存ファイルのためスキップ: {src}")
                        continue
                    
                    shutil.move(src, dst)
                    print(f"   ✅ {src} → {dst}")
                    
            except Exception as e:
                print(f"   ❌ エラー: {src} - {e}")
    
    def print_summary(self):
        """整理結果のサマリーを表示"""
        print("\n📊 画像整理サマリー")
        print("=" * 60)
        print(f"総画像数: {len(self.moves)}")
        print("\nカテゴリ別内訳:")
        
        category_names = {
            'analysis_overlay': '分析オーバーレイ',
            'integrated_analysis': '統合分析',
            'professional_analysis': 'プロフェッショナル分析',
            'final_analysis': '最終分析',
            'grid_overlay': 'グリッドテスト',
            'scale_test': 'スケールテスト',
            'zero_line': 'ゼロライン検出',
            'visualization': '可視化',
            'comparison': '比較',
            'workflow': 'ワークフロー図',
            'misc': 'その他'
        }
        
        for category, count in sorted(self.stats.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                print(f"  {category_names[category]:20} : {count:3}個")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='画像ファイル整理ツール')
    parser.add_argument('--execute', action='store_true', 
                       help='実際にファイルを移動（デフォルトはドライラン）')
    
    args = parser.parse_args()
    
    print("🖼️  画像ファイル整理ツール")
    print("=" * 60)
    
    organizer = ImageOrganizer(dry_run=not args.execute)
    
    # 1. 画像分析
    print("\n1️⃣ 画像ファイルの分析")
    categories = organizer.analyze_images()
    
    # 2. 移動計画
    print("\n2️⃣ 移動計画の作成")
    organizer.plan_image_moves(categories)
    
    # 3. ディレクトリ作成
    if not organizer.dry_run:
        print("\n3️⃣ ディレクトリ構造の作成")
        organizer.create_directories()
    
    # 4. 実行
    print("\n4️⃣ ファイル移動")
    organizer.execute_moves()
    
    # 5. サマリー
    organizer.print_summary()
    
    if organizer.dry_run:
        print("\n💡 実際に移動を実行するには --execute オプションを付けてください")
        print("   python organize_images.py --execute")

if __name__ == "__main__":
    main()