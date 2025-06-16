#!/usr/bin/env python3
"""
ランダム画像テスト
"""

import sys
import os
import random
sys.path.append('/Users/haruqun/Work/pachi777')

from perfect_data_extractor import PerfectDataExtractor
import pandas as pd
import numpy as np

def test_random_image(image_path):
    """ランダム画像のテスト"""
    print(f"\n" + "="*60)
    print(f"🎲 ランダムテスト: {os.path.basename(image_path)}")
    print("="*60)
    
    # データ抽出器を初期化
    extractor = PerfectDataExtractor(debug_mode=False)
    
    try:
        # データ抽出を実行
        result = extractor.extract_perfect_data(image_path)
        
        if result is None or len(result) == 0:
            print("❌ データ抽出失敗")
            return None
        
        print(f"✅ データ抽出成功: {len(result)}点")
        
        # 基本統計
        final_value = result['y_value'].iloc[-1]
        min_val = result['y_value'].min()
        max_val = result['y_value'].max()
        avg_val = result['y_value'].mean()
        
        # 最後の10点分析
        end_points = result['y_value'].iloc[-10:]
        end_avg = end_points.mean()
        end_std = end_points.std()
        
        # 開始点分析
        start_points = result['y_value'].iloc[:10]
        start_avg = start_points.mean()
        
        print(f"\n📊 基本統計:")
        print(f"   データ範囲: {min_val:.0f} 〜 {max_val:.0f}円")
        print(f"   平均値: {avg_val:.0f}円")
        print(f"   データ点数: {len(result)}点")
        
        print(f"\n📈 開始点分析:")
        print(f"   開始値: {result['y_value'].iloc[0]:.0f}円")
        print(f"   平均10点: {start_avg:.0f}円")
        print(f"   0ライン精度: {'✅' if abs(start_avg) < 1000 else '⚠️'} ({abs(start_avg):.0f}円)")
        
        print(f"\n📉 終点分析:")
        print(f"   最終値: {final_value:.0f}円")
        print(f"   平均10点: {end_avg:.0f}円")
        print(f"   変動性: {end_std:.1f} ({'✅' if end_std < 200 else '⚠️' if end_std < 500 else '❌'})")
        
        # 特殊ケース検出
        print(f"\n🔍 特殊ケース検出:")
        
        # 上限振り切り
        if abs(max_val) >= 29000 or abs(min_val) >= 29000:
            print(f"   ⚠️ 上限振り切り: 最大={max_val:.0f}, 最小={min_val:.0f}")
        
        # 変動パターン
        if max_val - min_val > 40000:
            print(f"   📊 大変動パターン: 振幅{max_val - min_val:.0f}円")
        elif max_val - min_val < 5000:
            print(f"   📊 安定パターン: 振幅{max_val - min_val:.0f}円")
        else:
            print(f"   📊 通常パターン: 振幅{max_val - min_val:.0f}円")
        
        # データ品質評価
        quality_score = 0
        quality_notes = []
        
        # 開始点精度 (30点満点)
        start_score = max(0, 30 - abs(start_avg) / 50)
        quality_score += start_score
        if start_score >= 25:
            quality_notes.append("開始点良好")
        elif start_score >= 15:
            quality_notes.append("開始点普通")
        else:
            quality_notes.append("開始点要改善")
        
        # 終点安定性 (40点満点)
        end_score = max(0, 40 - end_std / 5)
        quality_score += end_score
        if end_score >= 35:
            quality_notes.append("終点安定")
        elif end_score >= 25:
            quality_notes.append("終点普通")
        else:
            quality_notes.append("終点不安定")
        
        # データ量 (30点満点)
        data_score = min(30, len(result) / 100)
        quality_score += data_score
        if data_score >= 25:
            quality_notes.append("データ十分")
        elif data_score >= 15:
            quality_notes.append("データ普通")
        else:
            quality_notes.append("データ不足")
        
        print(f"\n🏆 品質評価:")
        print(f"   総合スコア: {quality_score:.1f}/100")
        print(f"   評価: {', '.join(quality_notes)}")
        
        grade = "S" if quality_score >= 90 else "A" if quality_score >= 75 else "B" if quality_score >= 60 else "C"
        print(f"   グレード: {grade}")
        
        return {
            'final_value': final_value,
            'end_avg': end_avg,
            'end_std': end_std,
            'start_avg': start_avg,
            'data_points': len(result),
            'quality_score': quality_score,
            'grade': grade,
            'range': max_val - min_val
        }
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None

def main():
    """ランダムテスト実行"""
    print("🎲 ランダム画像テスト")
    
    # 利用可能な画像をリストアップ
    available_images = []
    
    # S_画像
    s_images = [
        "graphs/cropped_auto/S__78209128_cropped.png",
        "graphs/cropped_auto/S__78209130_cropped.png",
        "graphs/cropped_auto/S__78209136_cropped.png",
        "graphs/cropped_auto/S__78209138_cropped.png",
        "graphs/cropped_auto/S__78209156_cropped.png",
        "graphs/cropped_auto/S__78209158_cropped.png",
        "graphs/cropped_auto/S__78209162_cropped.png",
        "graphs/cropped_auto/S__78209164_cropped.png",
        "graphs/cropped_auto/S__78209166_cropped.png",
        "graphs/cropped_auto/S__78209168_cropped.png",
        "graphs/cropped_auto/S__78209170_cropped.png",
        "graphs/cropped_auto/S__78209174_cropped.png",
    ]
    
    # 存在する画像のみを対象にする
    for img in s_images:
        if os.path.exists(img):
            available_images.append(img)
    
    print(f"📁 利用可能画像: {len(available_images)}枚")
    
    if len(available_images) < 3:
        print("❌ テスト用画像が不足しています")
        return
    
    # ランダムに3枚選択
    test_images = random.sample(available_images, 3)
    
    print(f"\n🎯 選択された画像:")
    for i, img in enumerate(test_images, 1):
        print(f"   {i}. {os.path.basename(img)}")
    
    results = []
    
    # 各画像をテスト
    for image_path in test_images:
        result = test_random_image(image_path)
        if result:
            results.append((os.path.basename(image_path), result))
    
    # 総合評価
    if results:
        print(f"\n" + "="*80)
        print(f"📊 ランダムテスト総合評価")
        print("="*80)
        
        total_score = sum(r[1]['quality_score'] for r in results)
        avg_score = total_score / len(results)
        
        grades = [r[1]['grade'] for r in results]
        grade_counts = {g: grades.count(g) for g in ['S', 'A', 'B', 'C']}
        
        print(f"平均品質スコア: {avg_score:.1f}/100")
        print(f"グレード分布: {grade_counts}")
        
        print(f"\n📋 詳細結果:")
        for image_name, result in results:
            print(f"{image_name:30s} | {result['grade']} | {result['final_value']:6.0f}円 | std:{result['end_std']:5.1f}")
        
        # 安定性評価
        stable_count = sum(1 for r in results if r[1]['end_std'] < 200)
        print(f"\n🏆 安定画像: {stable_count}/{len(results)}枚")
        
        if avg_score >= 80:
            print("✅ 総合評価: 優秀 - 実用レベル達成")
        elif avg_score >= 65:
            print("🟡 総合評価: 良好 - 概ね実用可能")
        else:
            print("⚠️ 総合評価: 要改善 - さらなる調整が必要")

if __name__ == "__main__":
    main()