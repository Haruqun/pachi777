#!/usr/bin/env python3
"""
最終差玉表示ツール
- 全ての解析済み画像の最終差玉を表示
- グラフ抽出とOCR結果を比較
"""

import os
import json
import glob
from datetime import datetime

def load_analysis_results():
    """解析結果を読み込み"""
    results = {}
    
    # JSONファイルを検索
    json_files = glob.glob("graphs/extracted_data/*_complete_analysis.json")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # ファイル名から画像名を抽出
            base_name = os.path.basename(json_file).replace('_complete_analysis.json', '')
            results[base_name] = data
            
        except Exception as e:
            print(f"⚠️ {json_file} 読み込みエラー: {e}")
    
    return results

def display_final_differences():
    """最終差玉を表示"""
    print("=" * 80)
    print("💰 最終差玉一覧")
    print("=" * 80)
    
    results = load_analysis_results()
    
    if not results:
        print("❌ 解析結果が見つかりません。")
        print("💡 先に complete_graph_analyzer.py を実行してください。")
        return
    
    # 結果を整理
    final_diffs = []
    graph_successes = 0
    ocr_successes = 0
    
    print(f"{'画像名':<20} {'グラフ抽出':<12} {'OCR抽出':<10} {'採用値':<12} {'状態'}")
    print("-" * 80)
    
    for name, data in sorted(results.items()):
        # グラフからの最終差玉
        graph_final = data.get("final_difference_from_graph")
        
        # OCRからの最終差玉
        stats = data.get("statistics", {})
        ocr_final = stats.get("最終差玉") if stats else None
        
        # 採用値（優先順位: graph > OCR）
        best_final = data.get("final_difference_best")
        if best_final is None:
            best_final = graph_final if graph_final is not None else ocr_final
        
        # 状態判定
        if graph_final is not None and ocr_final is not None:
            diff = abs(graph_final - ocr_final)
            if diff <= 500:
                status = "✅一致"
            else:
                status = f"⚠️差{diff:,.0f}円"
        elif graph_final is not None:
            status = "📈グラフのみ"
        elif ocr_final is not None:
            status = "📋OCRのみ"
        else:
            status = "❌抽出失敗"
        
        # フォーマット表示
        graph_str = f"{graph_final:,.0f}円" if graph_final is not None else "N/A"
        ocr_str = f"{ocr_final:,.0f}円" if ocr_final is not None else "N/A"
        best_str = f"{best_final:,.0f}円" if best_final is not None else "N/A"
        
        print(f"{name:<20} {graph_str:<12} {ocr_str:<10} {best_str:<12} {status}")
        
        # 統計用
        if graph_final is not None:
            graph_successes += 1
        if ocr_final is not None:
            ocr_successes += 1
        if best_final is not None:
            final_diffs.append(best_final)
    
    # 統計表示
    print("-" * 80)
    print(f"📊 統計情報:")
    print(f"   総画像数: {len(results)}")
    print(f"   グラフ抽出成功: {graph_successes}/{len(results)} ({graph_successes/len(results)*100:.1f}%)")
    print(f"   OCR抽出成功: {ocr_successes}/{len(results)} ({ocr_successes/len(results)*100:.1f}%)")
    print(f"   最終差玉取得: {len(final_diffs)}/{len(results)} ({len(final_diffs)/len(results)*100:.1f}%)")
    
    if final_diffs:
        print(f"\n💰 最終差玉統計:")
        print(f"   平均: {sum(final_diffs)/len(final_diffs):,.0f}円")
        print(f"   最大: {max(final_diffs):,.0f}円")
        print(f"   最小: {min(final_diffs):,.0f}円")
        print(f"   プラス収支: {len([x for x in final_diffs if x > 0])}/{len(final_diffs)}")
        print(f"   マイナス収支: {len([x for x in final_diffs if x < 0])}/{len(final_diffs)}")
    
    print("=" * 80)

def show_specific_image(image_name):
    """特定画像の詳細表示"""
    results = load_analysis_results()
    
    if image_name not in results:
        print(f"❌ {image_name} の解析結果が見つかりません。")
        available = list(results.keys())
        if available:
            print(f"💡 利用可能な画像: {', '.join(available[:5])}...")
        return
    
    data = results[image_name]
    
    print("=" * 60)
    print(f"📊 {image_name} 詳細結果")
    print("=" * 60)
    
    # 基本情報
    print(f"解析時刻: {data.get('timestamp', 'N/A')}")
    print(f"元画像: {data.get('source_image', 'N/A')}")
    
    # 処理結果
    print(f"\n🔧 処理結果:")
    print(f"   画像切り抜き: {'✅' if data.get('cropping_success') else '❌'}")
    print(f"   グラフデータ抽出: {'✅' if data.get('graph_extraction_success') else '❌'}")
    print(f"   統計情報抽出: {'✅' if data.get('stats_extraction_success') else '❌'}")
    
    # 最終差玉
    print(f"\n💰 最終差玉:")
    graph_final = data.get("final_difference_from_graph")
    if graph_final is not None:
        print(f"   グラフ抽出: {graph_final:,.0f}円")
    
    stats = data.get("statistics", {})
    ocr_final = stats.get("最終差玉") if stats else None
    if ocr_final is not None:
        print(f"   OCR抽出: {ocr_final:,.0f}円")
    
    best_final = data.get("final_difference_best")
    if best_final is not None:
        print(f"   採用値: {best_final:,.0f}円")
    
    # 統計情報
    if stats:
        print(f"\n📋 統計情報:")
        for key, value in stats.items():
            if value is not None and key != "最終差玉":
                print(f"   {key}: {value:,}" if isinstance(value, (int, float)) else f"   {key}: {value}")
    
    # エラー情報
    errors = data.get("errors", [])
    if errors:
        print(f"\n⚠️ エラー:")
        for error in errors:
            print(f"   - {error}")
    
    print("=" * 60)

def main():
    """メイン処理"""
    import sys
    
    if len(sys.argv) > 1:
        # 特定画像の詳細表示
        image_name = sys.argv[1]
        show_specific_image(image_name)
    else:
        # 全体の最終差玉表示
        display_final_differences()

if __name__ == "__main__":
    main()