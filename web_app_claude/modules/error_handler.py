"""エラーハンドリングとログ機能"""
import streamlit as st
import json
import os
import traceback
from datetime import datetime


def log_error(error_type, error_message, error_details=None):
    """エラーログを記録する"""
    error_log = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'type': error_type,
        'message': error_message,
        'details': error_details,
        'traceback': traceback.format_exc()
    }
    
    if 'error_logs' not in st.session_state:
        st.session_state.error_logs = []
    
    st.session_state.error_logs.append(error_log)
    
    # ログファイルにも保存（オプション）
    try:
        log_dir = "error_logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_filename = os.path.join(log_dir, f"error_log_{datetime.now().strftime('%Y%m%d')}.json")
        
        # 既存のログを読み込む
        existing_logs = []
        if os.path.exists(log_filename):
            try:
                with open(log_filename, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
            except:
                existing_logs = []
        
        # 新しいログを追加
        existing_logs.append(error_log)
        
        # ファイルに保存
        with open(log_filename, 'w', encoding='utf-8') as f:
            json.dump(existing_logs, f, ensure_ascii=False, indent=2)
    except:
        pass  # ファイル保存のエラーは無視


def get_error_logs():
    """エラーログを取得する"""
    if 'error_logs' not in st.session_state:
        return []
    return st.session_state.error_logs


def clear_error_logs():
    """エラーログをクリアする"""
    if 'error_logs' in st.session_state:
        st.session_state.error_logs = []