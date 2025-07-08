#!/usr/bin/env python3
"""
Streamlitアプリの統合テスト
実際の画像を使用してデータ出力フォームまでの動作を確認
"""

import requests
import json
import time

def test_streamlit_health():
    """Streamlitアプリのヘルスチェック"""
    try:
        response = requests.get("http://localhost:8501", timeout=5)
        if response.status_code == 200:
            print("✓ Streamlitアプリが起動しています")
            return True
        else:
            print(f"✗ ステータスコード: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ 接続エラー: {e}")
        return False

def main():
    print("=== Streamlitアプリの統合テスト ===\n")
    
    # 1. ヘルスチェック
    if not test_streamlit_health():
        print("\nStreamlitアプリが起動していません。")
        print("以下のコマンドでアプリを起動してください:")
        print("streamlit run web_app/streamlit_app_full.py")
        return
    
    # 2. テスト手順の表示
    print("\n=== 手動テスト手順 ===")
    print("\n1. ブラウザで http://localhost:8501 を開く")
    print("\n2. 画像アップロード:")
    print("   - 「画像を選択」ボタンをクリック")
    print("   - test_images/IMG_0321.PNGなどをアップロード")
    print("\n3. 解析実行:")
    print("   - 「🚀 解析開始」ボタンをクリック")
    print("\n4. データ出力フォームの確認:")
    print("   - 画面下部の「📝 データ出力フォーム」セクション")
    print("   - 「📋 データ出力（pachikeisan用）」を展開")
    print("\n5. 確認ポイント:")
    print("   - 台番号: 画像名（拡張子なし）が表示されるか")
    print("   - 初当たり回転数: システムの計算値が表示されるか")
    print("   - 通常回転数: システムの計算値が表示されるか")
    print("   - 獲得数: 総獲得球数が表示されるか")
    print("\n6. 出力フォーマット:")
    print("   - 1行目: 台番号#初当たり回転数#初当たり玉数#0")
    print("   - 2行目: 通常回転数#使用玉数#獲得数#現在値")
    print("\n7. エラーケース:")
    print("   - 初当たりがない画像でもエラーが出ないか")
    print("   - 複数画像でも正常に動作するか")
    
    print("\n=== テスト項目チェックリスト ===")
    checklist = [
        "画像アップロードが正常に動作する",
        "解析が正常に完了する",
        "データ出力フォームが表示される",
        "台番号に画像名が自動入力される",
        "初当たり球数がNoneでもエラーが出ない",
        "回転率が「計算不可」でも処理される",
        "出力フォーマットが正しい（1台2行）",
        "複数画像で一括処理できる",
        "コピー用データが正しく生成される"
    ]
    
    for item in checklist:
        print(f"□ {item}")

if __name__ == "__main__":
    main()