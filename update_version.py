#!/usr/bin/env python3
"""
バージョン情報を自動更新するスクリプト
"""

import subprocess
import re
from datetime import datetime

def get_git_info():
    """Gitから情報を取得"""
    # コミット数（バージョン番号として使用）
    commit_count = subprocess.check_output(['git', 'rev-list', '--count', 'HEAD']).decode().strip()
    
    # 最新のコミットハッシュ（短縮版）
    commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()
    
    # 現在の日付
    today = datetime.now().strftime('%Y-%m-%d')
    
    return commit_count, commit_hash, today

def update_file(filepath, commit_count, commit_hash, today):
    """ファイルのバージョン情報を更新"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Version行を更新
    content = re.sub(
        r'Version: \d+\.\d+\.\d+ \(Build [a-f0-9]+\)',
        f'Version: 1.0.{commit_count} (Build {commit_hash})',
        content
    )
    
    # Last Updated行を更新
    content = re.sub(
        r'Last Updated: \d{4}-\d{2}-\d{2}',
        f'Last Updated: {today}',
        content
    )
    
    # __version__変数を更新
    content = re.sub(
        r'__version__ = "[^"]*"',
        f'__version__ = "1.0.{commit_count}"',
        content
    )
    
    # __build__変数を更新
    content = re.sub(
        r'__build__ = "[^"]*"',
        f'__build__ = "{commit_hash}"',
        content
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated {filepath}")

def main():
    """メイン処理"""
    commit_count, commit_hash, today = get_git_info()
    
    print(f"Version: 1.0.{commit_count}")
    print(f"Build: {commit_hash}")
    print(f"Date: {today}")
    
    # 更新対象ファイル
    files_to_update = [
        'web_app/web_analyzer.py',
        'web_app/streamlit_app.py'
    ]
    
    for filepath in files_to_update:
        try:
            update_file(filepath, commit_count, commit_hash, today)
        except Exception as e:
            print(f"Error updating {filepath}: {e}")

if __name__ == '__main__':
    main()