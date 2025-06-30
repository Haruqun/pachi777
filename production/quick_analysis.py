#!/usr/bin/env python3
"""
クイック分析スクリプト
既に切り抜き済みの画像から分析・レポート・ZIP作成のみを実行
"""

import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from professional_graph_report import ProfessionalGraphReport
from web_package_creator import create_web_package

def quick_analysis():
    """切り抜き済み画像から分析を実行"""
    print("🚀 クイック分析開始（切り抜き済み画像使用）")
    print("=" * 60)
    
    # 分析実行
    analyzer = ProfessionalGraphReport()
    results = analyzer.process_all_images()
    
    if not results:
        print("❌ エラー: 分析に失敗しました")
        return None
    
    print(f"✅ 分析完了: {len(results)}枚")
    
    # レポート生成
    report_file = analyzer.generate_ultimate_professional_report()
    print(f"✅ レポート生成: {report_file}")
    
    # ZIP作成
    zip_file = create_web_package()
    
    if zip_file:
        print(f"✅ ZIPパッケージ: {zip_file}")
        return zip_file
    else:
        print("❌ エラー: ZIP作成に失敗しました")
        return None

if __name__ == "__main__":
    zip_file = quick_analysis()
    if zip_file:
        print("\n🎉 処理完了！")
        print(f"📦 最終成果物: {zip_file}")
    else:
        print("\n❌ 処理中にエラーが発生しました")