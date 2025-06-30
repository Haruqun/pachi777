#!/usr/bin/env python3
"""
Web配信用パッケージ作成ツール
HTMLレポートと関連ファイルをZIPでパッケージ化
"""

import zipfile
import glob
from pathlib import Path
import shutil
import os
from datetime import datetime
import json

def create_web_package():
    """Web配信用ZIPパッケージを作成"""
    
    print("📦 Web配信用パッケージ作成開始")
    print("=" * 60)
    
    # 最新のHTMLレポートファイルを取得
    html_files = glob.glob("reports/*/html/professional_graph_report_*.html")
    
    if not html_files:
        print("❌ professional_graph_report_*.html ファイルが見つかりません")
        return None
    
    # 最新のファイルを選択
    latest_html = max(html_files, key=lambda x: Path(x).stat().st_mtime)
    print(f"📁 メインHTMLファイル: {latest_html}")
    
    # パッケージ名生成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    package_name = f"pptown_graph_analysis_report_{timestamp}"
    temp_dir = f"temp_{package_name}"
    # 最新のHTMLファイルから日時ディレクトリを取得
    html_dir = Path(latest_html).parent.parent
    output_dir = f"{html_dir}/packages"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    zip_file = f"{output_dir}/{package_name}.zip"
    
    try:
        # 一時ディレクトリ作成
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        # メインHTMLファイルをindex.htmlとしてコピー
        shutil.copy2(latest_html, os.path.join(temp_dir, "index.html"))
        print(f"✅ メインHTML: index.html")
        
        # 分析画像ファイルを収集
        images_dir = os.path.join(temp_dir, "images")
        os.makedirs(images_dir)
        
        # professional_analysis_*.png ファイルを収集
        analysis_images = glob.glob("reports/*/images/professional_analysis_*.png")
        print(f"📸 分析画像: {len(analysis_images)}枚")
        
        for img in analysis_images:
            shutil.copy2(img, images_dir)
        
        # 元画像ファイルを収集
        original_images = glob.glob("graphs/original/*.jpg")
        print(f"📷 元画像: {len(original_images)}枚")
        
        for img in original_images:
            shutil.copy2(img, images_dir)
        
        # HTMLファイル内のパスを調整
        adjust_html_paths(os.path.join(temp_dir, "index.html"))
        
        # README.txtを作成
        create_readme(temp_dir, package_name)
        
        # package.jsonを作成（Web用メタデータ）
        create_package_json(temp_dir, package_name)
        
        # .htaccessを作成（Web配信用設定）
        create_htaccess(temp_dir)
        
        # ZIPファイル作成
        print("🗜️ ZIPファイル作成中...")
        
        # ディレクトリ作成
        Path("reports/packages").mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arc_path)
        
        # 一時ディレクトリを削除
        shutil.rmtree(temp_dir)
        
        # ZIPファイル情報表示
        zip_size = os.path.getsize(zip_file)
        print("=" * 60)
        print("✅ Web配信パッケージ作成完了")
        print(f"📦 ファイル名: {zip_file}")
        print(f"📊 ファイルサイズ: {zip_size / 1024 / 1024:.2f} MB")
        
        # ZIPファイルの内容を表示
        print("\n📋 パッケージ内容:")
        with zipfile.ZipFile(zip_file, 'r') as zipf:
            for info in zipf.infolist():
                size_kb = info.file_size / 1024
                print(f"   {info.filename} ({size_kb:.1f} KB)")
        
        return zip_file
        
    except Exception as e:
        print(f"❌ パッケージ作成エラー: {e}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return None

def adjust_html_paths(html_file):
    """HTMLファイル内の画像パスを調整"""
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # reports/YYYYMMDD/images/professional_analysis_*.png のパスを調整
    import re
    content = re.sub(r'reports/\d{8}/images/professional_analysis_([^"]+\.png)', r'images/professional_analysis_\1', content)
    # 旧パスの調整（互換性のため）
    content = re.sub(r'(?<!/)professional_analysis_([^"]+\.png)', r'images/professional_analysis_\1', content)
    
    # graphs/original/*.jpg のパスを調整  
    content = re.sub(r'graphs/original/([^"]+\.jpg)', r'images/\1', content)
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ HTMLパス調整完了")

def create_readme(temp_dir, package_name):
    """README.txtを作成"""
    readme_content = f"""
📊 PPタウン様 パチンコグラフ分析レポート
==================================================

パッケージ名: {package_name}
作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

📁 ファイル構成:
├── index.html          ... メインレポート（ブラウザで開いてください）
├── images/             ... 画像ファイル
│   ├── *.png          ... AI分析結果画像
│   └── *.jpg          ... 元画像ファイル
├── README.txt          ... このファイル
├── package.json        ... Webメタデータ
└── .htaccess          ... Web配信設定

🌐 Web配信方法:
1. このZIPファイルをWebサーバーに展開
2. ブラウザでindex.htmlにアクセス
3. モバイル・デスクトップ対応

🔧 技術仕様:
- HTML5 + CSS3 + JavaScript
- レスポンシブデザイン
- 高解像度画像対応
- 最新ブラウザ推奨

🎨 制作:
Report Design: ファイブナインデザイン - 佐藤
AI Analysis: Next-Gen ML Platform

© 2024 PPタウン様専用レポート | 機密情報取扱注意
"""
    
    with open(os.path.join(temp_dir, "README.txt"), 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("✅ README.txt作成完了")

def create_package_json(temp_dir, package_name):
    """package.jsonを作成（Web用メタデータ）"""
    package_data = {
        "name": package_name,
        "version": "1.0.0",
        "description": "PPタウン様 パチンコグラフ分析レポート - AI高精度解析システム",
        "main": "index.html",
        "keywords": ["pachinko", "graph", "analysis", "ai", "report"],
        "author": "ファイブナインデザイン - 佐藤",
        "license": "Proprietary",
        "private": True,
        "created": datetime.now().isoformat(),
        "client": "PPタウン様",
        "type": "analysis-report",
        "technologies": [
            "HTML5",
            "CSS3", 
            "JavaScript",
            "AI Machine Learning",
            "Computer Vision",
            "OCR"
        ],
        "features": [
            "10色グラフ線検出",
            "±1px精度測定", 
            "自動0ライン検出",
            "レスポンシブデザイン",
            "高解像度画像対応"
        ]
    }
    
    with open(os.path.join(temp_dir, "package.json"), 'w', encoding='utf-8') as f:
        json.dump(package_data, f, ensure_ascii=False, indent=2)
    
    print("✅ package.json作成完了")

def create_htaccess(temp_dir):
    """Web配信用.htaccessを作成"""
    htaccess_content = """
# PPタウン様 パチンコグラフ分析レポート - Web配信設定

# MIME Types
AddType text/html .html
AddType application/json .json
AddType image/png .png
AddType image/jpeg .jpg

# キャッシュ設定
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType text/html "access plus 1 hour"
    ExpiresByType image/png "access plus 1 week"
    ExpiresByType image/jpeg "access plus 1 week"
    ExpiresByType application/json "access plus 1 day"
</IfModule>

# 圧縮設定
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/html
    AddOutputFilterByType DEFLATE text/css
    AddOutputFilterByType DEFLATE application/javascript
    AddOutputFilterByType DEFLATE application/json
</IfModule>

# セキュリティヘッダー
<IfModule mod_headers.c>
    Header always set X-Content-Type-Options nosniff
    Header always set X-Frame-Options DENY
    Header always set X-XSS-Protection "1; mode=block"
</IfModule>

# DirectoryIndex
DirectoryIndex index.html

# エラーページ
ErrorDocument 404 /index.html
"""
    
    with open(os.path.join(temp_dir, ".htaccess"), 'w', encoding='utf-8') as f:
        f.write(htaccess_content)
    
    print("✅ .htaccess作成完了")

def main():
    """メイン実行"""
    print("🌐 Web配信パッケージ作成ツール")
    print("📊 PPタウン様専用レポート")
    print("=" * 60)
    
    zip_file = create_web_package()
    
    if zip_file:
        print("\n🎉 パッケージ作成成功！")
        print(f"📦 配信用ファイル: {zip_file}")
        print("\n💡 使用方法:")
        print("1. ZIPファイルをWebサーバーにアップロード")
        print("2. サーバー上で展開")
        print("3. index.htmlにブラウザでアクセス")
        print("\n🔒 機密情報取扱注意")
    else:
        print("❌ パッケージ作成に失敗しました")

if __name__ == "__main__":
    main()