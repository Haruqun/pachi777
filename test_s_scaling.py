#!/usr/bin/env python3
"""
S_画像のスケーリング修正テスト
"""

import os
from perfect_data_extractor import PerfectDataExtractor

def test_s_image_scaling():
    """S_画像のスケーリングをテスト"""
    extractor = PerfectDataExtractor()
    
    # S_画像をテスト
    test_image = "graphs/cropped_auto/S__78209136_cropped.png"
    
    if os.path.exists(test_image):
        print(f"🔍 テスト対象: {test_image}")
        
        # データ抽出
        df = extractor.extract_perfect_data(test_image)
        
        if df is not None:
            print(f"✅ 抽出成功!")
            print(f"   データ点数: {len(df)}")
            print(f"   Y値範囲: {df['y_value'].min():.0f} 〜 {df['y_value'].max():.0f}")
            print(f"   最終差玉: {df['y_value'].iloc[-1]:.0f}円")
            
            # 最終10%の平均
            end_section = df.tail(int(len(df) * 0.1))
            final_avg = end_section['y_value'].mean()
            print(f"   最終10%平均: {final_avg:.0f}円")
        else:
            print("❌ 抽出失敗")
    else:
        print(f"❌ ファイルが見つかりません: {test_image}")

if __name__ == "__main__":
    test_s_image_scaling()