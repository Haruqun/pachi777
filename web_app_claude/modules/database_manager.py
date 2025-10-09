"""データベース処理"""
import sqlite3
import streamlit as st
import json


def init_database():
    """データベースを初期化"""
    try:
        # 統一されたデータベースファイルパス
        db_path = get_db_path()
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # APIキーテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT UNIQUE NOT NULL,
                api_key TEXT NOT NULL,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # presets テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                settings TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        return db_path
        
    except Exception as e:
        st.error(f"データベース初期化エラー: {str(e)}")
        return None

def get_db_path():
    """統一されたデータベースパスを取得"""
    import os
    if 'STREAMLIT_CLOUD' in os.environ:
        return '/tmp/pptown.db'
    else:
        db_dir = os.path.expanduser('~/.pachi777')
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        return os.path.join(db_dir, 'pptown.db')


def load_presets_from_db():
    """データベースからプリセットを読み込み"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, settings FROM presets ORDER BY name")
        rows = cursor.fetchall()
        
        presets = {}
        for name, settings_json in rows:
            try:
                settings = json.loads(settings_json)
                presets[name] = settings
            except json.JSONDecodeError:
                continue
        
        conn.close()
        return presets
        
    except Exception:
        return {}


def save_preset_to_db(name, settings):
    """プリセットをデータベースに保存"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        settings_json = json.dumps(settings, ensure_ascii=False)
        
        cursor.execute('''
            INSERT OR REPLACE INTO presets (name, settings, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (name, settings_json))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"プリセット保存エラー: {str(e)}")
        return False


def delete_preset_from_db(name):
    """プリセットをデータベースから削除"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM presets WHERE name = ?", (name,))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"プリセット削除エラー: {str(e)}")
        return False


def save_api_key(api_key, model):
    """APIキーを保存"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO api_keys (key_name, api_key, model)
            VALUES ('claude_api', ?, ?)
        ''', (api_key, model))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        st.error(f"APIキー保存エラー: {str(e)}")
        return False


def load_api_key():
    """保存されたAPIキーを読み込み"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT api_key, model FROM api_keys WHERE key_name = 'claude_api'")
        result = cursor.fetchone()

        conn.close()

        if result:
            api_key, model = result
            return api_key, model

        return None, None
        
    except Exception:
        return None, None


def delete_api_key():
    """APIキーを削除"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_keys WHERE key_name = 'claude_api'")
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False