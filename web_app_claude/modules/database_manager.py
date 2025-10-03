"""データベース処理"""
import sqlite3
import streamlit as st
import json
import secrets


def init_database():
    """データベースを初期化"""
    try:
        conn = sqlite3.connect('apikey.db')
        cursor = conn.cursor()
        
        # テーブルが存在しない場合は作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT UNIQUE NOT NULL,
                api_key TEXT NOT NULL,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # presets テーブルも作成
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
        
    except Exception as e:
        st.error(f"データベース初期化エラー: {str(e)}")


def load_presets_from_db():
    """データベースからプリセットを読み込み"""
    try:
        conn = sqlite3.connect('apikey.db')
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
        conn = sqlite3.connect('apikey.db')
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
        conn = sqlite3.connect('apikey.db')
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
        conn = sqlite3.connect('apikey.db')
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
        conn = sqlite3.connect('apikey.db')
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
        conn = sqlite3.connect('apikey.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_keys WHERE key_name = 'claude_api'")
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False