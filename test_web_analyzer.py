#!/usr/bin/env python3
"""
Web版アナライザーのローカルテスト
"""

import sys
import os
sys.path.append('web_app')

from web_analyzer import WebCompatibleAnalyzer
import tempfile
import glob
import json
import shutil

def test_web_analyzer():
    """Web版アナライザーをテスト"""
    print("🧪 Web版アナライザーのテスト開始")
    print("=" * 60)
    
    # テスト用画像を取得
    test_images = glob.glob("graphs/original/*.jpg")[:3]  # 最初の3枚でテスト
    
    if not test_images:
        print("❌ テスト画像が見つかりません")
        return
    
    print(f"📸 テスト画像: {len(test_images)}枚")
    for img in test_images:
        print(f"  - {os.path.basename(img)}")
    
    # テスト結果用ディレクトリを作成
    test_output_dir = "test_results/web_analyzer_test"
    if os.path.exists(test_output_dir):
        shutil.rmtree(test_output_dir)
    os.makedirs(test_output_dir, exist_ok=True)
    
    # 一時ディレクトリで処理
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # アナライザー初期化
        analyzer = WebCompatibleAnalyzer(work_dir=temp_dir)
        
        print("\n📊 画像処理開始...")
        print("-" * 60)
        
        # 各画像を処理
        for img_path in test_images:
            print(f"\n🔍 処理中: {os.path.basename(img_path)}")
            
            result = analyzer.process_single_image(img_path, output_dir)
            
            if result.get('error'):
                print(f"  ❌ エラー: {result['error']}")
            else:
                print(f"  ✅ 成功")
                print(f"  📈 データポイント: {result['data_points']}点")
                print(f"  🎨 検出色: {result['detected_color']}")
                print(f"  📊 最高値: {result['analysis']['max_value']:,}玉")
                print(f"  📉 最低値: {result['analysis']['min_value']:,}玉")
                print(f"  🏁 最終値: {result['analysis']['final_value']:,}玉")
                
                if result['analysis']['first_hit_index'] >= 0:
                    print(f"  🎰 初当たり: {result['analysis']['first_hit_value']:,}玉")
                else:
                    print(f"  🎰 初当たり: なし")
        
        # 出力ファイルを確認
        print("\n📁 生成されたファイル:")
        print("-" * 60)
        for file in os.listdir(output_dir):
            file_path = os.path.join(output_dir, file)
            size = os.path.getsize(file_path) / 1024
            print(f"  - {file} ({size:.1f} KB)")
            
            # テスト結果ディレクトリにコピー
            shutil.copy2(file_path, os.path.join(test_output_dir, file))
        
        # レポート生成
        print("\n📝 HTMLレポート生成...")
        report_path = os.path.join(temp_dir, "test_report.html")
        analyzer.generate_html_report(report_path)
        
        if os.path.exists(report_path):
            size = os.path.getsize(report_path) / 1024
            print(f"  ✅ レポート生成成功: {size:.1f} KB")
        else:
            print("  ❌ レポート生成失敗")
        
        # 結果をJSON形式で保存
        results_json = os.path.join(temp_dir, "test_results.json")
        with open(results_json, 'w', encoding='utf-8') as f:
            json.dump(analyzer.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 詳細結果: {results_json}")
        
        # 結果ファイルもコピー
        shutil.copy2(results_json, os.path.join(test_output_dir, "test_results.json"))
        if os.path.exists(report_path):
            shutil.copy2(report_path, os.path.join(test_output_dir, "test_report.html"))
        
        # デバッグ情報
        print("\n🔧 デバッグ情報:")
        print(f"  - zero_y: {analyzer.zero_y}")
        print(f"  - target_30k_y: {analyzer.target_30k_y}")
        print(f"  - scale: {analyzer.scale:.2f}")
        
        print(f"\n✅ テスト結果は {test_output_dir} に保存されました")

if __name__ == "__main__":
    test_web_analyzer()