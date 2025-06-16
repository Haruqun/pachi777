#!/usr/bin/env python3
"""
境界線整合性テスト - 上限・下限線との整合性確認
"""

import sys
import os
sys.path.append('/Users/haruqun/Work/pachi777')

from perfect_data_extractor import PerfectDataExtractor
import pandas as pd
import numpy as np
from PIL import Image

def analyze_boundary_alignment(image_path):
    """境界線整合性分析"""
    print(f"\n" + "="*60)
    print(f"🎯 境界線整合性分析: {os.path.basename(image_path)}")
    print("="*60)
    
    # 画像を読み込んで実際のサイズを確認
    img = Image.open(image_path)
    actual_width, actual_height = img.size
    print(f"📐 実際の画像サイズ: {actual_width} × {actual_height}")
    
    # データ抽出器を初期化
    extractor = PerfectDataExtractor(debug_mode=True)
    
    try:
        # 0ライン検出
        zero_line_y = extractor.detect_zero_line_precise(image_path)
        print(f"🎯 0ライン位置: Y={zero_line_y}")
        
        # 現在の変換係数
        if "S__" in os.path.basename(image_path):
            current_factor = 0.007701  # 校正済み係数
            expected_range = 244.7  # 理論値（下側のみ）
            scale_type = "S_画像(校正済み)"
        else:
            current_factor = 333 / 30000
            expected_range = 333
            scale_type = "IMG画像"
        
        print(f"📊 現在の変換係数: {current_factor:.6f}")
        print(f"📏 期待ピクセル範囲: {expected_range}px")
        
        # 境界線位置の計算（現在の係数）
        upper_boundary_y = zero_line_y - (30000 * current_factor)
        lower_boundary_y = zero_line_y + (30000 * current_factor)
        
        print(f"🔴 上限線位置 (+30000円): Y={upper_boundary_y:.1f}")
        print(f"🔵 下限線位置 (-30000円): Y={lower_boundary_y:.1f}")
        
        # 実際の画像境界との比較
        theoretical_upper = 0  # 画像上端
        theoretical_lower = actual_height  # 画像下端
        
        upper_gap = upper_boundary_y - theoretical_upper
        lower_gap = theoretical_lower - lower_boundary_y
        
        print(f"\n📏 境界ギャップ分析:")
        print(f"   上端ギャップ: {upper_gap:.1f}px ({'✅' if abs(upper_gap) < 50 else '⚠️'})")
        print(f"   下端ギャップ: {lower_gap:.1f}px ({'✅' if abs(lower_gap) < 50 else '⚠️'})")
        
        # データ抽出して実際の範囲を確認
        result = extractor.extract_perfect_data(image_path)
        
        if result is not None and len(result) > 0:
            actual_min = result['y_value'].min()
            actual_max = result['y_value'].max()
            
            print(f"\n📊 実際のデータ範囲:")
            print(f"   最小値: {actual_min:.0f}円")
            print(f"   最大値: {actual_max:.0f}円")
            print(f"   範囲幅: {actual_max - actual_min:.0f}円")
            
            # 理論値との比較
            expected_min = -30000
            expected_max = 30000
            
            min_error = abs(actual_min - expected_min)
            max_error = abs(actual_max - expected_max)
            
            print(f"\n🎯 理論値との誤差:")
            print(f"   下限誤差: {min_error:.0f}円 ({'✅' if min_error < 2000 else '⚠️'})")
            print(f"   上限誤差: {max_error:.0f}円 ({'✅' if max_error < 2000 else '⚠️'})")
            
            # 改善された変換係数の提案
            if actual_height > 0 and zero_line_y > 0:
                # 実際の画像サイズに基づく係数
                available_upper = zero_line_y
                available_lower = actual_height - zero_line_y
                
                # より保守的な係数（境界から少し余裕を持つ）
                safe_upper = available_upper * 0.9  # 10%余裕
                safe_lower = available_lower * 0.9  # 10%余裕
                
                improved_factor_upper = safe_upper / 30000
                improved_factor_lower = safe_lower / 30000
                improved_factor = min(improved_factor_upper, improved_factor_lower)
                
                print(f"\n💡 改善提案:")
                print(f"   利用可能上側: {available_upper:.1f}px")
                print(f"   利用可能下側: {available_lower:.1f}px") 
                print(f"   安全上側: {safe_upper:.1f}px")
                print(f"   安全下側: {safe_lower:.1f}px")
                print(f"   改善係数: {improved_factor:.6f}")
                print(f"   現在係数: {current_factor:.6f}")
                print(f"   改善率: {(improved_factor/current_factor - 1)*100:+.1f}%")
                
                return {
                    'current_factor': current_factor,
                    'improved_factor': improved_factor,
                    'actual_min': actual_min,
                    'actual_max': actual_max,
                    'upper_gap': upper_gap,
                    'lower_gap': lower_gap
                }
        
        return None
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None

def main():
    """境界線整合性テスト実行"""
    print("🎯 境界線整合性テスト")
    
    # テスト画像
    test_images = [
        "graphs/cropped_auto/S__78209088_cropped.png",  # 基準画像
        "graphs/cropped_auto/S__78209132_cropped.png",  # 極値画像
        "graphs/cropped_auto/S__78209160_cropped.png",  # 変動画像
    ]
    
    results = []
    
    for image_path in test_images:
        if os.path.exists(image_path):
            result = analyze_boundary_alignment(image_path)
            if result:
                results.append((os.path.basename(image_path), result))
        else:
            print(f"⚠️ {image_path} が見つかりません")
    
    # 総合評価
    print(f"\n" + "="*80)
    print(f"📊 境界線整合性総合評価")
    print("="*80)
    
    if results:
        current_factors = [r[1]['current_factor'] for r in results]
        improved_factors = [r[1]['improved_factor'] for r in results]
        
        avg_current = np.mean(current_factors)
        avg_improved = np.mean(improved_factors)
        
        print(f"平均現在係数: {avg_current:.6f}")
        print(f"平均改善係数: {avg_improved:.6f}")
        print(f"平均改善率: {(avg_improved/avg_current - 1)*100:+.1f}%")
        
        print(f"\n🏆 推奨改善係数: {avg_improved:.6f}")

if __name__ == "__main__":
    main()