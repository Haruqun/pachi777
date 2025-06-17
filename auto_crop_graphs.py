#!/usr/bin/env python3
"""
グラフ自動切り取りスクリプト
- perfect_graph_cropper.pyのバッチ処理を自動実行
"""

import os
from perfect_graph_cropper import PerfectGraphCropper

def main():
    print("🎯 グラフ自動切り取り開始")
    
    # 入出力フォルダ設定
    input_folder = "graphs"
    output_folder = "graphs/cropped_perfect"
    
    # 出力フォルダ作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 画像ファイルを取得
    image_files = [f for f in os.listdir(input_folder) 
                   if f.lower().endswith(('.jpg', '.jpeg', '.png')) 
                   and not f.startswith('.')]
    
    if not image_files:
        print("❌ 画像ファイルが見つかりません")
        return
    
    print(f"📁 {len(image_files)}個の画像を処理します")
    
    # PerfectGraphCropperインスタンス作成
    cropper = PerfectGraphCropper(debug_mode=False)
    
    # 結果統計
    success_count = 0
    failed_files = []
    
    # 各画像を処理
    for i, file in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] 処理中: {file}")
        
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, 
                                   f"{os.path.splitext(file)[0]}_perfect.png")
        
        success, output_file, details = cropper.crop_perfect_graph(input_path, output_path)
        
        if success:
            success_count += 1
            print(f"✅ 成功 - 精度: {details['overall_accuracy']:.1f}%")
        else:
            failed_files.append(file)
            print(f"❌ 失敗")
    
    # 結果サマリー
    print("\n" + "="*60)
    print(f"✨ 処理完了")
    print(f"📊 成功: {success_count}/{len(image_files)}")
    
    if failed_files:
        print(f"\n❌ 失敗したファイル:")
        for file in failed_files:
            print(f"   - {file}")

if __name__ == "__main__":
    main()