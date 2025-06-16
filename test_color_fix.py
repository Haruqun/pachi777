#!/usr/bin/env python3
"""
色検出修正のテスト
"""

import sys
import os
sys.path.append('/Users/haruqun/Work/pachi777')

from perfect_data_extractor import PerfectDataExtractor

def main():
    """メイン処理"""
    test_image = "graphs/cropped_auto/S__78209088_cropped.png"
    
    if not os.path.exists(test_image):
        print(f"❌ {test_image} が見つかりません")
        return
    
    print(f"🔧 色検出修正テスト: {test_image}")
    
    # データ抽出器を初期化
    extractor = PerfectDataExtractor(debug_mode=True)
    
    try:
        # データ抽出を実行
        result = extractor.extract_perfect_data(test_image)
        
        if result:
            print(f"✅ 最終差玉: {result.get('final_difference', 'N/A')}円")
            print(f"📊 ライン検出: {result.get('line_detection_success', False)}")
            
            # 詳細情報
            for key, value in result.items():
                if key not in ['final_difference', 'line_detection_success']:
                    print(f"   {key}: {value}")
        else:
            print("❌ データ抽出に失敗しました")
            
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()