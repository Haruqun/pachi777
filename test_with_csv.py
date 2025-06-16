#!/usr/bin/env python3
"""
CSVデータ付きでテスト
"""

import sys
import os
sys.path.append('/Users/haruqun/Work/pachi777')

from perfect_data_extractor import PerfectDataExtractor

def main():
    """CSV付きでデータ抽出"""
    test_image = "graphs/cropped_auto/S__78209088_cropped.png"
    csv_path = "graphs/extracted_data/S__78209088_cropped.csv"
    
    print(f"🔧 CSV付きデータ抽出: {test_image}")
    
    # データ抽出器を初期化
    extractor = PerfectDataExtractor(debug_mode=False)
    
    # データ抽出を実行（CSV保存）
    result = extractor.extract_perfect_data(test_image, csv_path)
    
    if result is not None and len(result) > 0:
        print(f"✅ データ抽出成功: {len(result)}点")
        print(f"📁 CSV保存: {csv_path}")
        
        # 最終値の情報
        final_value = result['y_value'].iloc[-1]
        print(f"🎯 最終値: {final_value:.0f}")
        
        return True
    else:
        print("❌ データ抽出に失敗")
        return False

if __name__ == "__main__":
    main()