#!/usr/bin/env python3
"""
パチンコグラフ解析完全パイプライン
画像切り抜き → データ抽出 → レポート生成 → ZIP作成まで一括処理
"""

import os
import sys
import glob
import shutil
from datetime import datetime
from pathlib import Path

# 各モジュールをインポート
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from manual_graph_cropper import ManualGraphCropper
from professional_graph_report import ProfessionalGraphReport
from web_package_creator import create_web_package

class CompletePipeline:
    """完全な処理パイプライン"""
    
    def __init__(self):
        self.original_dir = "graphs/original"
        self.cropped_dir = "graphs/manual_crop/cropped"
        self.report_dir = "."
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        print(f"[{level}] {message}")
        
    def backup_existing_files(self):
        """既存ファイルのバックアップ"""
        backup_dir = f"backup_{self.timestamp}"
        
        if os.path.exists(self.cropped_dir) and os.listdir(self.cropped_dir):
            self.log(f"既存の切り抜き画像をバックアップ: {backup_dir}")
            os.makedirs(backup_dir, exist_ok=True)
            shutil.copytree(self.cropped_dir, os.path.join(backup_dir, "cropped"))
            
    def step1_crop_images(self):
        """ステップ1: 画像の切り抜き"""
        self.log("=" * 80)
        self.log("ステップ1: 画像切り抜き処理")
        self.log("=" * 80)
        
        # 元画像の確認
        original_images = glob.glob(os.path.join(self.original_dir, "*.jpg"))
        if not original_images:
            self.log("エラー: 元画像が見つかりません", "ERROR")
            return False
            
        self.log(f"元画像数: {len(original_images)}枚")
        
        # 切り抜き実行
        cropper = ManualGraphCropper()
        results = cropper.process_all()
        
        self.log(f"切り抜き完了: {len(results)}枚")
        return True
        
    def step2_analyze_and_report(self):
        """ステップ2: データ分析とレポート生成"""
        self.log("=" * 80)
        self.log("ステップ2: データ分析とレポート生成")
        self.log("=" * 80)
        
        # 切り抜き画像の確認
        cropped_images = glob.glob(os.path.join(self.cropped_dir, "*_graph_only.png"))
        if not cropped_images:
            self.log("エラー: 切り抜き画像が見つかりません", "ERROR")
            return False, None
            
        self.log(f"分析対象: {len(cropped_images)}枚")
        
        # 分析実行
        analyzer = ProfessionalGraphReport()
        results = analyzer.process_all_images()
        
        # レポート生成
        report_file = analyzer.generate_ultimate_professional_report()
        self.log(f"レポート生成: {report_file}")
        
        return True, report_file
        
    def step3_create_package(self, report_file):
        """ステップ3: Web配信パッケージ作成"""
        self.log("=" * 80)
        self.log("ステップ3: Web配信パッケージ作成")
        self.log("=" * 80)
        
        if not report_file or not os.path.exists(report_file):
            self.log("エラー: レポートファイルが見つかりません", "ERROR")
            return False, None
            
        # パッケージ作成
        # web_package_creatorは最新のHTMLを自動で検出するため、
        # ここでは単に関数を呼び出す
        zip_file = create_web_package()
        
        if zip_file:
            self.log(f"ZIPパッケージ作成: {zip_file}")
            return True, zip_file
        else:
            self.log("エラー: パッケージ作成に失敗", "ERROR")
            return False, None
            
    def generate_summary_report(self, results):
        """処理サマリーレポート生成"""
        # レポートファイルから日時ディレクトリを取得
        if results['report_file']:
            report_path = Path(results['report_file'])
            output_dir = report_path.parent.parent
        else:
            # フォールバック
            date_dir = datetime.now().strftime('%Y%m%d%H%M%S')
            output_dir = f"reports/{date_dir}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        summary_file = f"{output_dir}/pipeline_summary_{self.timestamp}.txt"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("パチンコグラフ解析パイプライン実行サマリー\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")
            
            f.write("処理結果:\n")
            f.write(f"  ステップ1 (画像切り抜き): {'成功' if results['crop_success'] else '失敗'}\n")
            f.write(f"  ステップ2 (分析・レポート): {'成功' if results['report_success'] else '失敗'}\n")
            f.write(f"  ステップ3 (パッケージ作成): {'成功' if results['package_success'] else '失敗'}\n\n")
            
            f.write("生成ファイル:\n")
            if results['report_file']:
                f.write(f"  レポート: {results['report_file']}\n")
            if results['zip_file']:
                f.write(f"  ZIPパッケージ: {results['zip_file']}\n")
                
        return summary_file
        
    def run_pipeline(self, backup=True):
        """完全パイプライン実行"""
        self.log("🚀 パチンコグラフ解析完全パイプライン開始")
        self.log("=" * 80)
        
        results = {
            'crop_success': False,
            'report_success': False,
            'package_success': False,
            'report_file': None,
            'zip_file': None
        }
        
        try:
            # バックアップ（オプション）
            if backup:
                self.backup_existing_files()
            
            # ステップ1: 画像切り抜き
            results['crop_success'] = self.step1_crop_images()
            if not results['crop_success']:
                self.log("パイプライン中断: 画像切り抜きエラー", "ERROR")
                return results
                
            # ステップ2: 分析とレポート生成
            results['report_success'], results['report_file'] = self.step2_analyze_and_report()
            if not results['report_success']:
                self.log("パイプライン中断: 分析エラー", "ERROR")
                return results
                
            # ステップ3: パッケージ作成
            results['package_success'], results['zip_file'] = self.step3_create_package(results['report_file'])
            
            # サマリー生成
            summary_file = self.generate_summary_report(results)
            self.log(f"サマリーレポート: {summary_file}")
            
        except Exception as e:
            self.log(f"予期しないエラー: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            
        self.log("=" * 80)
        self.log("🏁 パイプライン処理完了")
        
        # 最終結果表示
        if results['package_success']:
            self.log("✅ 全ステップ成功！")
            self.log(f"📦 最終成果物: {results['zip_file']}")
        else:
            self.log("❌ 一部のステップでエラーが発生しました", "WARNING")
            
        return results


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='パチンコグラフ解析完全パイプライン')
    parser.add_argument('--no-backup', action='store_true', 
                       help='既存ファイルのバックアップをスキップ')
    parser.add_argument('--original-dir', type=str, default='graphs/original',
                       help='元画像ディレクトリ (デフォルト: graphs/original)')
    
    args = parser.parse_args()
    
    # パイプライン実行
    pipeline = CompletePipeline()
    
    # カスタムディレクトリ設定
    if args.original_dir:
        pipeline.original_dir = args.original_dir
    
    # 実行
    results = pipeline.run_pipeline(backup=not args.no_backup)
    
    # 終了コード
    if results['package_success']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()