#!/usr/bin/env python3
"""
Web版のZIP作成プロセスをテスト
"""

import tempfile
import os
import zipfile
from datetime import datetime

def test_zip_creation():
    """ZIP作成プロセスをテスト"""
    print("🧪 Testing ZIP creation process")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Temp directory: {temp_dir}")
        
        # ディレクトリ構造を再現
        original_dir = os.path.join(temp_dir, "original")
        output_dir = os.path.join(temp_dir, "images")
        os.makedirs(original_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # テストファイルを作成
        test_files = {
            os.path.join(original_dir, "test.jpg"): "Original image",
            os.path.join(output_dir, "professional_analysis_test.png"): "Analysis image",
            os.path.join(output_dir, "cropped_test.png"): "Cropped image",
            os.path.join(temp_dir, "report.html"): "HTML report"
        }
        
        for path, content in test_files.items():
            with open(path, "w") as f:
                f.write(content)
            print(f"  Created: {path.replace(temp_dir, '.')}")
        
        # ZIPファイル作成
        zip_path = os.path.join(temp_dir, "test_package.zip")
        
        print("\n📦 Creating ZIP file...")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # HTMLレポート
            zipf.write(os.path.join(temp_dir, "report.html"), "index.html")
            
            # 画像ファイル（output_dir内）
            for img_file in os.listdir(output_dir):
                img_path = os.path.join(output_dir, img_file)
                if os.path.isfile(img_path):
                    zipf.write(img_path, f"images/{img_file}")
                    print(f"  Added: images/{img_file}")
            
            # 元画像（original_dir内）
            for img_file in os.listdir(original_dir):
                img_path = os.path.join(original_dir, img_file)
                if os.path.isfile(img_path):
                    zipf.write(img_path, f"images/{img_file}")
                    print(f"  Added: images/{img_file} (from original)")
        
        # ZIP内容を確認
        print("\n📋 ZIP contents:")
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            for info in zipf.infolist():
                print(f"  {info.filename}")

if __name__ == "__main__":
    test_zip_creation()