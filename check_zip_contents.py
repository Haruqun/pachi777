#!/usr/bin/env python3
"""
ZIPファイルの内容を確認
"""

import zipfile
import os
import tempfile
import shutil

def check_zip_contents(zip_path):
    """ZIPファイルの内容を確認"""
    print(f"🔍 Checking ZIP file: {zip_path}")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # ZIP解凍
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        # ファイル構造を表示
        print("📁 File structure:")
        for root, dirs, files in os.walk(temp_dir):
            level = root.replace(temp_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                size = os.path.getsize(os.path.join(root, file))
                print(f"{subindent}{file} ({size/1024:.1f} KB)")
        
        # HTMLファイルを確認
        html_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.html'):
                    html_files.append(os.path.join(root, file))
        
        print(f"\n📝 Found {len(html_files)} HTML files")
        
        # HTMLの画像参照を確認
        for html_file in html_files:
            print(f"\n🔍 Checking {os.path.basename(html_file)}:")
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 画像参照を抽出
            import re
            img_refs = re.findall(r'<img[^>]+src="([^"]+)"', content)
            print(f"  Found {len(img_refs)} image references")
            
            # 各画像の存在確認
            missing = 0
            for img_ref in img_refs[:5]:  # 最初の5つだけ表示
                img_path = os.path.join(os.path.dirname(html_file), img_ref)
                exists = os.path.exists(img_path)
                status = "✅" if exists else "❌"
                print(f"  {status} {img_ref}")
                if not exists:
                    missing += 1
            
            if missing > 0:
                print(f"  ⚠️  {missing} images are missing!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        check_zip_contents(sys.argv[1])
    else:
        # デフォルトでデスクトップのファイルをチェック
        zip_path = "/Users/haruqun/Desktop/complete_package_20250630_134206.zip"
        if os.path.exists(zip_path):
            check_zip_contents(zip_path)
        else:
            print("❌ Please provide a ZIP file path")