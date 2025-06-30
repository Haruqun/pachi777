#!/usr/bin/env python3
"""
完全な抽出フローのテスト
元画像 → クロップ → データ抽出 → 精度検証
"""

import os
import shutil
from improved_graph_data_extractor import ImprovedGraphDataExtractor
from accuracy_checker import AccuracyChecker

def test_full_extraction():
    """完全な抽出フローをテスト"""
    
    print("🎯 完全抽出フローテスト開始")
    print("="*80)
    
    # テスト用ディレクトリを作成
    test_dir = "test_extraction"
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(f"{test_dir}/extracted_data", exist_ok=True)
    
    # テスト画像を選択（様々な特徴を持つ画像）
    test_images = [
        "S__78209160",  # 最高精度99.9%の画像
        "S__78209132",  # 最大値が大きい画像
        "S__78209170",  # 最低精度97.1%の画像
    ]
    
    print("📋 テスト画像:")
    for img in test_images:
        print(f"  - {img}")
    
    # 抽出器を初期化
    extractor = ImprovedGraphDataExtractor()
    
    # 各画像を処理
    results = []
    for image_name in test_images:
        print(f"\n{'='*60}")
        print(f"処理中: {image_name}")
        print("="*60)
        
        # クロップ済み画像のパス
        cropped_path = f"graphs/cropped/{image_name}_optimal.png"
        
        if not os.path.exists(cropped_path):
            print(f"❌ クロップ済み画像が見つかりません: {cropped_path}")
            continue
        
        # データ抽出
        result = extractor.extract_graph_data(cropped_path)
        
        if "error" in result:
            print(f"❌ エラー: {result['error']}")
            continue
        
        # 結果を保存
        base_name = os.path.basename(cropped_path).replace('.png', '')
        
        # CSV保存
        csv_path = os.path.join(test_dir, "extracted_data", f"{base_name}_data.csv")
        extractor.save_to_csv(result, csv_path)
        
        # 可視化
        vis_path = os.path.join(test_dir, "extracted_data", f"{base_name}_visualization.png")
        extractor.create_visualization(cropped_path, result, vis_path)
        
        # グラフプロット
        plot_path = os.path.join(test_dir, "extracted_data", f"{base_name}_plot.png")
        extractor.create_graph_plot(result, plot_path)
        
        # 結果を記録
        results.append({
            'image': image_name,
            'points': result.get('points', 0),
            'color': result.get('color_type', 'N/A'),
            'max_rotation': result.get('max_rotation', 0),
            'quality': result.get('quality', {}).get('message', 'N/A')
        })
        
        # 実際の値と比較（results.txtから）
        print("\n📊 抽出結果:")
        if result.get('data'):
            values = [d['value'] for d in result['data']]
            print(f"  最大値: {max(values):.0f}")
            print(f"  最終値: {values[-1]:.0f}")
            print(f"  品質: {result['quality']['message']}")
    
    # 結果サマリー
    print(f"\n{'='*80}")
    print("📊 テスト結果サマリー")
    print("="*80)
    
    for r in results:
        print(f"\n{r['image']}:")
        print(f"  検出点数: {r['points']}")
        print(f"  グラフ色: {r['color']}")
        print(f"  最大回転数: {r['max_rotation']}")
        print(f"  品質評価: {r['quality']}")
    
    # 精度検証
    print(f"\n{'='*80}")
    print("🔍 精度検証")
    print("="*80)
    
    # テスト用の精度チェッカーを作成
    # （既存のimproved_extracted_dataの代わりにtest_extractionを使用）
    original_dir = "graphs/improved_extracted_data"
    test_extracted_dir = f"{test_dir}/extracted_data"
    
    # 一時的にディレクトリを入れ替え
    temp_dir = f"{original_dir}_temp"
    if os.path.exists(original_dir):
        shutil.move(original_dir, temp_dir)
    
    shutil.copytree(test_extracted_dir, original_dir)
    
    try:
        # 精度チェック
        checker = AccuracyChecker()
        
        # テスト画像のみの精度を表示
        for image_name in test_images:
            if image_name in checker.results_data:
                actual_data = checker.results_data[image_name]
                extracted_max, extracted_final = checker.load_extracted_data(image_name)
                
                if extracted_final is not None:
                    final_accuracy = checker.calculate_accuracy(
                        actual_data['実際の最終差玉'],
                        extracted_final
                    )
                    
                    print(f"\n{image_name}:")
                    print(f"  実際の最終値: {actual_data['実際の最終差玉']:.0f}")
                    print(f"  抽出した最終値: {extracted_final:.0f}")
                    print(f"  誤差: {final_accuracy['error']:.0f}玉")
                    print(f"  精度: {final_accuracy['accuracy']:.1f}%")
    
    finally:
        # ディレクトリを元に戻す
        shutil.rmtree(original_dir)
        if os.path.exists(temp_dir):
            shutil.move(temp_dir, original_dir)
    
    print(f"\n✅ テスト完了！")
    print(f"結果は {test_dir}/ に保存されました")

if __name__ == "__main__":
    test_full_extraction()