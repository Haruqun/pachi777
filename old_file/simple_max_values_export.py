#!/usr/bin/env python3
"""
画像名と最大値のみをシンプルに出力
"""

import json
import csv
from pathlib import Path
from datetime import datetime

def extract_simple_max_values():
    """統合結果から画像名と最大値のみを抽出"""
    
    # 統合結果のJSONファイルを読み込み
    try:
        with open('integrated_results.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("integrated_results.json が見つかりません")
        return
    
    # 画像名と最大値のリスト
    max_values_data = []
    
    for result in data['results']:
        file_name = Path(result['image_path']).stem.replace('_graph_only', '')
        
        # データポイントがある場合のみ最大値を取得
        if result['data_points_count'] > 0:
            max_value = result['graph_statistics']['max_value']
            max_values_data.append({
                'image_name': file_name,
                'max_value': int(max_value)
            })
        else:
            max_values_data.append({
                'image_name': file_name,
                'max_value': None
            })
    
    # CSVファイルに出力
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = f"max_values_{timestamp}.csv"
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['画像名', '最大値'])
        
        for item in max_values_data:
            max_val = item['max_value'] if item['max_value'] is not None else 'なし'
            writer.writerow([item['image_name'], max_val])
    
    # テキストファイルにも出力（見やすい形式）
    txt_file = f"max_values_{timestamp}.txt"
    
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("画像名と最大値一覧\n")
        f.write("=" * 40 + "\n")
        f.write(f"生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")
        
        for item in max_values_data:
            if item['max_value'] is not None:
                f.write(f"{item['image_name']}: +{item['max_value']:,}\n")
            else:
                f.write(f"{item['image_name']}: なし\n")
    
    # 簡単な統計
    valid_values = [item['max_value'] for item in max_values_data if item['max_value'] is not None]
    
    print(f"📊 画像名と最大値の抽出完了")
    print(f"総画像数: {len(max_values_data)}")
    print(f"最大値検出数: {len(valid_values)}")
    print(f"検出失敗数: {len(max_values_data) - len(valid_values)}")
    
    if valid_values:
        print(f"全体最高値: +{max(valid_values):,}")
        print(f"平均最大値: +{int(sum(valid_values)/len(valid_values)):,}")
    
    print(f"📄 CSV出力: {csv_file}")
    print(f"📄 TXT出力: {txt_file}")
    
    # 画面に一覧表示
    print("\n【最大値一覧】")
    print("-" * 30)
    for item in max_values_data:
        if item['max_value'] is not None:
            print(f"{item['image_name']}: +{item['max_value']:,}")
        else:
            print(f"{item['image_name']}: なし")

if __name__ == "__main__":
    extract_simple_max_values()