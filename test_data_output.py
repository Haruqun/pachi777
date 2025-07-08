#!/usr/bin/env python3
"""
データ出力フォームのテストスクリプト
"""

import pandas as pd
from datetime import datetime

def test_data_formatting():
    """データ出力フォーマットのテスト"""
    
    # テストデータの作成
    test_cases = [
        {
            '画像名': 'IMG_0321.PNG',
            '台番号': '',  # 空文字（画像名を使用するケース）
            '最高値': 18100,
            '最低値': -955,
            '現在値': 8004,
            '初当たり球数': -864,  # 負の値
            '初当たり回転数': 84,
            '総獲得球数': 31016,
            '回転率①': '24.3',
            '回転率②': '23.0'
        },
        {
            '画像名': 'IMG_0164.PNG',
            '台番号': '1000',  # 台番号あり
            '最高値': 0,
            '最低値': -3501,
            '現在値': -3501,
            '初当たり球数': None,  # Noneの場合
            '初当たり回転数': 0,
            '総獲得球数': 0,
            '回転率①': '-',
            '回転率②': '15.1'
        },
        {
            '画像名': 'IMG_0165.PNG',
            '台番号': '',
            '最高値': 7504,
            '最低値': -3001,
            '現在値': 7367,
            '初当たり球数': 'なし',  # 文字列の場合
            '初当たり回転数': 474,
            '総獲得球数': 10596,
            '回転率①': '計算不可',  # 計算不可の場合
            '回転率②': '計算不可'
        }
    ]
    
    print("=== データ出力フォームのテスト ===\n")
    
    for idx, row in enumerate(test_cases):
        print(f"\n--- テストケース {idx + 1}: {row['画像名']} ---")
        
        # 台番号の処理
        default_machine_number = str(row.get('台番号', ''))
        if default_machine_number == '' or default_machine_number == row.get('画像名', ''):
            image_name = row.get('画像名', f'台{idx + 1}')
            default_machine_number = image_name.rsplit('.', 1)[0]
        
        print(f"台番号: {default_machine_number}")
        
        # 初当たり玉数の処理
        first_hit_balls_value = row.get('初当たり球数', 0)
        if first_hit_balls_value is None or first_hit_balls_value == 'なし':
            first_hit_balls = 0
        else:
            try:
                first_hit_balls = abs(int(first_hit_balls_value))
            except (ValueError, TypeError):
                first_hit_balls = 0
        
        print(f"初当たり球数: {first_hit_balls_value} → {first_hit_balls}")
        
        # 回転率の処理
        rotation_rate_1 = row.get('回転率①', '-')
        if rotation_rate_1 != '-' and rotation_rate_1 != '計算不可':
            rotation_rate_1 = rotation_rate_1.replace('回/千円', '')
        else:
            rotation_rate_1 = '0'
        
        rotation_rate_2 = row.get('回転率②', '-')
        if rotation_rate_2 != '-' and rotation_rate_2 != '計算不可':
            rotation_rate_2 = rotation_rate_2.replace('回/千円', '')
        else:
            rotation_rate_2 = '0'
        
        print(f"回転率①: {row.get('回転率①')} → {rotation_rate_1}")
        print(f"回転率②: {row.get('回転率②')} → {rotation_rate_2}")
        
        # 使用玉数（最低値の絶対値）
        used_balls = abs(int(row.get('最低値', 0)))
        
        # pachikeisanツール用フォーマット
        line1 = f"{default_machine_number}#{row['初当たり回転数']}#{first_hit_balls}#0"
        line2 = f"0#{used_balls}#{row['総獲得球数']}#{row['現在値']}"  # 通常回転数は0と仮定
        
        print(f"\n出力フォーマット:")
        print(f"1行目: {line1}")
        print(f"2行目: {line2}")
        
        # 検証
        parts1 = line1.split('#')
        parts2 = line2.split('#')
        
        assert len(parts1) == 4, f"1行目のフォーマットエラー: {parts1}"
        assert len(parts2) == 4, f"2行目のフォーマットエラー: {parts2}"
        
        print("✓ フォーマット検証OK")

if __name__ == "__main__":
    test_data_formatting()
    print("\n\n=== すべてのテストが完了しました ===")