#!/usr/bin/env python3
"""
残りの画像を切り抜くスクリプト
manual_graph_cropper.pyの手法を使用
"""

import sys
sys.path.append('/Users/haruqun/Work/pachi777')
from manual_graph_cropper import ManualGraphCropper
import glob
import os

# 全ての元画像
all_original = glob.glob("graphs/original/*.jpg")
print(f"元画像総数: {len(all_original)}")

# 既に切り抜き済みの画像を確認
cropped_manual = glob.glob("graphs/manual_crop/cropped/*_graph_only.png")
cropped_optimal = glob.glob("graphs/cropped/*_optimal.png")

# ベースネームを取得
manual_bases = [os.path.basename(f).replace("_graph_only.png", "") for f in cropped_manual]
optimal_bases = [os.path.basename(f).replace("_optimal.png", "") for f in cropped_optimal]
all_cropped_bases = set(manual_bases + optimal_bases)

print(f"切り抜き済み（manual_crop）: {len(manual_bases)}")
print(f"切り抜き済み（optimal）: {len(optimal_bases)}")
print(f"切り抜き済み合計: {len(all_cropped_bases)}")

# 未処理の画像を特定
unprocessed = []
for orig in all_original:
    base = os.path.splitext(os.path.basename(orig))[0]
    if base not in all_cropped_bases:
        unprocessed.append(orig)

print(f"\n未処理画像: {len(unprocessed)}")
for img in sorted(unprocessed):
    print(f"  - {os.path.basename(img)}")

# 未処理画像がある場合は処理
if unprocessed:
    print("\n切り抜き処理を開始します...")
    cropper = ManualGraphCropper()
    
    for img_path in sorted(unprocessed):
        try:
            result = cropper.process_image(img_path)
            if result:
                print(f"✅ 成功: {os.path.basename(img_path)}")
        except Exception as e:
            print(f"❌ エラー: {os.path.basename(img_path)} - {e}")
    
    print("\n処理完了！")
else:
    print("\n全ての画像が既に処理済みです。")