#!/usr/bin/env python3
"""
AI Graph Analysis Report - Professional Edition
高精度データ抽出・解析システム
"""

import streamlit as st
from datetime import datetime
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
import logging
from web_analyzer import WebCompatibleAnalyzer
from modules.image_processor import detect_orange_bar, detect_zero_line, crop_graph_area
from modules.claude_api import analyze_with_claude
from modules.error_handler import log_error, get_error_logs, clear_error_logs
from modules.ocr_processor import preprocess_detail_image, enhance_image_for_ocr, extract_site7_data, extract_machine_number_from_orange_bar
from modules.config_manager import (
    DEFAULT_SETTINGS, DEFAULT_IMAGE_WIDTH,
    init_settings, get_settings, update_settings, reset_settings,
    get_game_type, get_exchange_rate,
    init_preset_system, load_preset, save_preset, delete_preset
)
from modules.database_manager import (
    init_database, load_presets_from_db, save_preset_to_db, 
    delete_preset_from_db, save_api_key, load_api_key, delete_api_key
)
from modules.graph_analyzer import (
    calculate_black_ratio, detect_and_draw_black_frames,
    get_graph_limit, get_unit, get_unit_per_1000yen,
    detect_first_hit
)
from modules.machine_data import (
    get_machine_payouts, MACHINE_PAYOUT_DATA
)
from modules.utils import (
    normalize_machine_number, get_prioritized_data,
    generate_image_hash, settings_to_hash,
    format_number_with_unit, calculate_rotation_rate,
    calculate_investment_from_balls
)
import platform
import pytesseract
import re
import json
import pandas as pd
import time
import hashlib
import secrets
import sqlite3
import concurrent.futures
from functools import lru_cache
import traceback
import os

# サーバーログ出力用ヘルパー関数
def log(message):
    """Streamlit Cloud Logsに出力するためのログ関数"""
    os.write(2, f"{message}\n".encode('utf-8'))

# ページ設定
st.set_page_config(
    page_title="AI Graph Analysis Report",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# リロード検出ログ
# log(f"[Reload] Streamlit app script execution started")

# セッション状態の初期化を確実に行う
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    # 基本的なセッション状態の初期化
    st.session_state.uploaded_file_names = []
    st.session_state.start_analysis = False
    st.session_state.analysis_done = False
    # アナライザーインスタンスをキャッシュ
    st.session_state.analyzer_instance = None
    # エラーログ
    st.session_state.error_logs = []
    
# グローバル変数でパスワードを管理（アプリ再起動まで有効）
if 'GLOBAL_USER_PASSWORD' not in st.session_state:
    # アプリ全体で共有されるグローバル変数を初期化
    if not hasattr(st, '_global_passwords'):
        st._global_passwords = {
            'user': '059',
            'admin': 'admin777'
        }
    st.session_state.GLOBAL_USER_PASSWORD = st._global_passwords['user']
    st.session_state.GLOBAL_ADMIN_PASSWORD = st._global_passwords['admin']

# ========== 出玉詳細画像処理用の関数群 ==========
# デフォルト画像幅（標準サイズ）












# デフォルト値
# 設定を初期化
init_settings()

# プリセットシステムの初期化
init_preset_system()

if 'show_adjustment' not in st.session_state:
    st.session_state.show_adjustment = False

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'current_preset_name' not in st.session_state:
    st.session_state.current_preset_name = 'デフォルト'

if 'uploaded_file_names' not in st.session_state:
    st.session_state.uploaded_file_names = []

# CSV表示項目の設定を初期化
if 'csv_columns' not in st.session_state:
    # デフォルト表示項目
    st.session_state.csv_columns = [
        '台番号',
        '現在値',
        '初当たり球数',
        '初当たり回転数',
        '総獲得球数',
        '回転率①',
        '回転率②',
        '通常回転数',
        '超回数',
        '中回数',
        '小回数'
    ]

# 遊技種別の初期化
if 'game_type' not in st.session_state:
    st.session_state.game_type = 'パチンコ'  # デフォルトはパチンコ

# エラーメッセージの初期化
if 'claude_errors' not in st.session_state:
    st.session_state.claude_errors = []

# 解析開始時にエラーをクリア（重複防止）
if 'analysis_started' not in st.session_state:
    st.session_state.analysis_started = False

# 画像分類キャッシュの初期化
if 'classification_cache' not in st.session_state:
    st.session_state.classification_cache = {}

# Claude APIキーの初期化（専用データベースから読み込み）
if 'claude_api_key' not in st.session_state:
    try:
        conn = sqlite3.connect('apikey.db')
        cursor = conn.cursor()
        
        # APIキーを読み込み
        cursor.execute('''
            SELECT api_key, model FROM api_keys
            WHERE key_name = 'claude_api'
            ORDER BY created_at DESC
            LIMIT 1
        ''')
        result = cursor.fetchone()

        if result:
            st.session_state.claude_api_key = result[0]
            st.session_state.claude_model = result[1] if result[1] else 'claude-3-5-haiku-20241022'
        
        conn.close()
    except Exception:
        # エラーが発生しても続行（初回起動時など）
        pass


# URLパラメータによる自動ログインチェック
query_params = st.query_params
if 'auth' in query_params and not st.session_state.authenticated:
    auth_token = query_params['auth']
    # トークンの検証（簡易的なハッシュチェック）
    user_token = hashlib.sha256(f"user_{st._global_passwords['user']}_pachi777".encode()).hexdigest()[:16]
    admin_token = hashlib.sha256(f"admin_{st._global_passwords['admin']}_pachi777".encode()).hexdigest()[:16]
    
    if auth_token == user_token:
        st.session_state.authenticated = True
        st.session_state.is_admin = False
        st.rerun()
    elif auth_token == admin_token:
        st.session_state.authenticated = True
        st.session_state.is_admin = True
        st.rerun()

# パスワード認証
if not st.session_state.authenticated:
    # モダンなログイン画面のスタイル
    st.markdown("""
    <style>
    /* メインコンテナを中央配置 */
    .main > div {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* ログインカード */
    .login-card {
        background: transparent;
        padding: 48px;
        max-width: 400px;
        margin: 0 auto;
        text-align: center;
    }
    
    /* タイトル */
    .login-title {
        font-size: 28px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 8px;
        line-height: 1.2;
    }
    
    /* サブタイトル */
    .login-subtitle {
        font-size: 16px;
        color: #cccccc;
        margin-bottom: 32px;
        line-height: 1.5;
    }
    
    /* フォームスタイル */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        padding: 12px 16px;
        font-size: 16px;
        transition: border-color 0.3s;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        outline: none;
    }
    
    /* ボタンスタイル */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 600;
        transition: transform 0.2s, box-shadow 0.2s;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* エラーメッセージ */
    .stAlert {
        border-radius: 8px;
        margin-top: 16px;
    }
    
    /* フッター */
    .login-footer {
        margin-top: 48px;
        padding-top: 24px;
        border-top: 1px solid #444;
        color: #aaa;
        font-size: 14px;
        line-height: 1.8;
        text-align: center;
    }
    
    .login-footer a {
        color: #8899ff;
        text-decoration: none;
    }
    
    .login-footer a:hover {
        text-decoration: underline;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # スペーサー
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # ログインカード
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="login-card">
            <h1 class="login-title">AI Graph Analysis Report</h1>
            <p class="login-subtitle">Professional Edition - 認証が必要です</p>
        </div>
        """, unsafe_allow_html=True)
        
        # スペース
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ログイン処理を関数化
        def handle_login():
            # グローバルパスワードを取得
            user_password = st._global_passwords['user']
            admin_password = st._global_passwords['admin']
            
            # パスワードチェック
            if st.session_state.password_input == user_password:
                st.session_state.authenticated = True
                st.session_state.is_admin = False
                st.session_state.login_success = True
                # 自動ログインが有効な場合、URLパラメータを設定
                if st.session_state.get('remember_me', False):
                    token = hashlib.sha256(f"user_{user_password}_pachi777".encode()).hexdigest()[:16]
                    st.query_params['auth'] = token
            elif st.session_state.password_input == admin_password:
                st.session_state.authenticated = True
                st.session_state.is_admin = True
                st.session_state.login_success = True
                # 自動ログインが有効な場合、URLパラメータを設定
                if st.session_state.get('remember_me', False):
                    token = hashlib.sha256(f"admin_{admin_password}_pachi777".encode()).hexdigest()[:16]
                    st.query_params['auth'] = token
            else:
                st.session_state.login_error = True
        
        # パスワード入力（Enterキーでログイン可能）
        # ラベルを上に表示
        st.markdown('<p style="margin-bottom: 5px; color: #ffffff;">パスワード</p>', unsafe_allow_html=True)
        password = st.text_input(
            label="password_field",  # 内部用のラベル
            type="password",
            placeholder="パスワードを入力してください",
            label_visibility="collapsed",  # hiddenではなくcollapsedを使用
            key="password_input",
            on_change=handle_login
        )
        
        # 次回から自動ログインのチェックボックス
        st.checkbox("次回から自動ログイン", key="remember_me", help="チェックを入れてログインすると、URLに認証情報が追加されます。そのURLをブックマークすることで、次回から自動的にログインできます。")
        
        # ログインボタン
        if st.button("ログイン", type="primary", use_container_width=True):
            handle_login()
        
        # ログイン成功時の処理
        if st.session_state.get('login_success', False):
            st.success("✅ ログインしました")
            # 自動ログインが有効な場合の説明
            if st.session_state.get('remember_me', False):
                st.info("🔖 自動ログインが有効になりました。現在のURL（上部のアドレスバー）をブックマークしてください。次回からブックマークを開くだけで自動的にログインされます。")
            st.session_state.login_success = False
            time.sleep(0.3)
            st.rerun()
        
        # ログインエラー時の処理
        if st.session_state.get('login_error', False):
            st.error("❌ パスワードが違います")
            st.session_state.login_error = False
        
        # 自動ログインの説明
        with st.expander("💡 自動ログインの使い方", expanded=False):
            st.markdown("""
            ### 🔐 自動ログイン機能について
            
            毎回パスワードを入力する手間を省くことができます。
            
            **使い方：**
            1. 「次回から自動ログイン」にチェックを入れる
            2. パスワードを入力してログイン
            3. ログイン後、ブラウザのアドレスバーのURLをコピー
            4. ブックマークに登録
            
            **次回から：**
            - ブックマークをクリックするだけでログイン完了！
            - パスワード入力不要
            
            **注意事項：**
            - URLに認証情報が含まれるため、他人と共有しないでください
            - パスワードが変更されると自動ログインは無効になります
            - ログアウトすると自動ログインは解除されます
            """)
        
        # フッター
        st.markdown(f"""
        <div class="login-footer">
            AI Graph Analysis Report v2.5<br>
            更新日: {datetime.now().strftime('%Y/%m/%d')}<br>
            Produced by <a href="https://pp-town.com/" target="_blank">PPタウン</a><br>
            Created by <a href="https://fivenine-design.com" target="_blank">fivenine-design.com</a>
        </div>
        """, unsafe_allow_html=True)
    
    # 認証されていない場合はここで処理を終了
    st.stop()

# SQLiteデータベースの設定
import os

# データベースファイルのパスを設定
# Streamlit Cloudでは書き込み可能な一時ディレクトリを使用
if os.environ.get('STREAMLIT_SHARING_MODE'):
    # Streamlit Cloud環境
    db_path = '/tmp/presets.db'
else:
    # ローカル環境
    db_dir = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir)
        except:
            db_dir = os.path.dirname(__file__)
    db_path = os.path.join(db_dir, 'presets.db')

# データベースを初期化
init_database()

# セッションステートにプリセットを読み込み
# リロード時も常に最新のプリセットを読み込む
if 'saved_presets' not in st.session_state or st.session_state.get('force_reload_presets', False):
    st.session_state.saved_presets = load_presets_from_db()
    st.session_state.force_reload_presets = False

# 本番解析セクション
st.markdown("---")
st.markdown("## 🎰 AI Graph Analysis Report")
st.caption("""高精度データ抽出・解析システム - Professional Edition

本システムは、パチンコ・パチスロ台のグラフ画像をAI技術で自動解析する専門ツールです。
OCR技術による台番号・回転数の自動読み取り、画像処理によるグラフデータの精密抽出、
独自アルゴリズムによる統計解析を実現。複数画像の一括処理にも対応し、
解析結果はCSV形式でダウンロード可能。プリセット機能により、
異なる端末や表示形式にも柔軟に対応できる高精度な解析システムです。""")

# 遊技種別選択
st.markdown("### 🎯 遊技種別を選択")
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    game_type = st.radio(
        "遊技種別",
        ["パチンコ", "パチスロ"],
        index=0 if st.session_state.game_type == "パチンコ" else 1,
        key="game_type_selector",
        horizontal=True
    )
    if game_type != st.session_state.game_type:
        st.session_state.game_type = game_type
        # 遊技種別に応じてデフォルト値を変更
        if game_type == "パチンコ":
            update_settings('exchange_rate', 3.57145)  # 28玉交換
        else:
            update_settings('exchange_rate', 17.86)  # 5.6枚交換
        st.rerun()

with col2:
    # 単位表示
    unit = "玉" if st.session_state.game_type == "パチンコ" else "枚"
    st.info(f"🎲 単位: {unit}")

with col3:
    # 交換レート表示
    rate = get_exchange_rate()
    st.info(f"💱 交換レート: {rate:.2f}円/{unit}")

# 使い方ガイド
show_analysis_help = st.checkbox("📖 解析の使い方を表示", value=False, key="show_analysis_help")
if show_analysis_help:
    st.info("""
    **🎯 解析の流れ**
    
    1️⃣ **画像をアップロード**
    - site7のグラフ画像を選択
    - 複数枚まとめて処理可能
    
    2️⃣ **プリセットを選択**
    - 調整設定で保存したプリセットを選択
    - 初回はデフォルトでOK
    
    3️⃣ **解析開始**
    - 解析ボタンをクリック
    - 自動的に全データを抽出
    
    💡 **ポイント**
    - 端末に合わせたプリセットを使用すると精度が向上します
    - 解析結果はCSVダウンロード可能です
    """)

# ========== サイドバー：管理者機能 ==========
with st.sidebar:
    st.markdown("### ⚙️ 管理者機能")
    
    # ログイン状態を確認
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    
    if not st.session_state.is_admin:
        # ログインフォーム
        with st.form("admin_login"):
            password = st.text_input("管理者パスワード", type="password")
            submit = st.form_submit_button("ログイン")
            
            if submit:
                if password == st.session_state.GLOBAL_ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.success("✅ 管理者としてログインしました")
                    st.rerun()
                else:
                    st.error("❌ パスワードが正しくありません")
    else:
        # 管理者としてログイン済み
        st.success("🔐 管理者モード")
        
        # Claude API設定
        st.markdown("#### 🤖 Claude API設定")
        
        # APIキー入力
        api_key = st.text_input(
            "Claude APIキー",
            value=st.session_state.get('claude_api_key', ''),
            type="password",
            help="Anthropic社のClaude APIキーを入力してください（sk-ant-で始まる文字列）"
        )
        
        # APIキーの形式をチェック
        if api_key and not api_key.startswith('sk-ant-'):
            st.warning("⚠️ APIキーは通常 'sk-ant-' で始まります。形式を確認してください。")
        
        # モデル選択
        model = st.selectbox(
            "使用モデル",
            ["claude-3-5-haiku-20241022", "claude-3-haiku-20240307", "claude-3-5-sonnet-20241022"],
            index=0,
            help="使用するClaudeモデルを選択（Haiku 3.5が最も高速・安価）"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("APIキーを保存", type="primary", use_container_width=True):
                if api_key:
                    st.session_state.claude_api_key = api_key
                    st.session_state.claude_model = model
                    
                    # 専用のデータベースに保存
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

                        # APIキーを保存または更新
                        cursor.execute('''
                            INSERT OR REPLACE INTO api_keys (key_name, api_key, model)
                            VALUES (?, ?, ?)
                        ''', ('claude_api', api_key, model))

                        conn.commit()
                        conn.close()

                        st.success("✅ APIキーを保存しました")
                    except Exception as e:
                        st.error(f"❌ 保存エラー: {str(e)}")
                else:
                    st.error("❌ APIキーを入力してください")
        
        with col2:
            if st.button("🧪 APIキーをテスト", type="secondary", use_container_width=True):
                if api_key:
                    with st.spinner("APIキーをテスト中..."):
                        try:
                            # HTTP APIを使ってテスト
                            import requests
                            test_url = "https://api.anthropic.com/v1/messages"
                            test_headers = {
                                "x-api-key": api_key,
                                "anthropic-version": "2023-06-01",
                                "content-type": "application/json"
                            }
                            test_data = {
                                "model": model,
                                "max_tokens": 10,
                                "messages": [{"role": "user", "content": "Hi"}]
                            }
                            
                            response = requests.post(test_url, headers=test_headers, json=test_data)
                            
                            if response.status_code == 200:
                                st.success("✅ APIキーは有効です！")
                            elif response.status_code == 401:
                                st.error("❌ APIキーが無効です。正しいキーを入力してください。")
                                st.info("💡 ヒント: APIキーは 'sk-ant-' で始まる文字列です。")
                            else:
                                st.error(f"❌ エラー ({response.status_code}): {response.text}")
                        except Exception as e:
                            st.error(f"❌ エラー: {str(e)}")
                else:
                    st.error("❌ APIキーを入力してください")
        
        # 現在の設定状況
        if st.session_state.get('claude_api_key'):
            st.info(f"📝 APIキー設定済み: {st.session_state.claude_api_key[:10]}...")
            st.info(f"🤖 使用モデル: {st.session_state.get('claude_model', 'claude-3-5-haiku-20241022')}")
            
            # APIキー削除ボタン
            if st.button("🗑️ APIキーを削除", type="secondary"):
                try:
                    # セッションステートから削除
                    if 'claude_api_key' in st.session_state:
                        del st.session_state.claude_api_key
                    if 'claude_model' in st.session_state:
                        del st.session_state.claude_model
                    
                    # データベースから削除
                    conn = sqlite3.connect('apikey.db')
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM api_keys WHERE key_name = 'claude_api'")
                    conn.commit()
                    conn.close()
                    
                    st.success("✅ APIキーを削除しました")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 削除エラー: {str(e)}")
        
        # ログアウト
        if st.button("ログアウト", type="secondary"):
            st.session_state.is_admin = False
            st.rerun()
    
    # Claude API利用状況の表示
    st.markdown("---")
    if st.session_state.get('claude_api_key'):
        st.markdown("### 🎯 Claude API")
        st.success("✅ 利用可能")
        st.caption("出玉詳細画像から詳細データを抽出できます")
    else:
        st.markdown("### 🎯 Claude API")
        st.warning("⚠️ 未設定")
        st.caption("管理者ログイン後、APIキーを設定してください")
    
        
        # ペアリング方法の選択
        st.markdown("### 🔗 ペアリング設定")
        pairing_method = st.radio(
            "グラフと出玉詳細画像のペアリング方法",
            ["machine_total_match", "jackpot_match", "machine_number", "order"],
            format_func=lambda x: {
                "machine_total_match": "台番号＋累計スタート（最も正確）",
                "jackpot_match": "大当たり回数マッチング",
                "machine_number": "台番号マッチング",
                "order": "アップロード順"
            }.get(x, x),
            index=0,  # デフォルトは台番号＋累計スタート
            help="台番号＋累計スタート：台番号と累計スタートが両方一致する画像をペアリング（最も正確）\n大当たり回数マッチング：大当たり回数や初当たり回数が一致する画像をペアリング\n台番号マッチング：台番号が一致する画像をペアリング\nアップロード順：同じ順番でアップロードした場合"
        )
        
        if pairing_method != st.session_state.get('pairing_method', 'machine_total_match'):
            st.session_state.pairing_method = pairing_method
            if pairing_method == 'machine_total_match':
                st.success("✅ 台番号＋累計スタートでペアリング（最も正確）")
            elif pairing_method == 'jackpot_match':
                st.info("🎯 大当たり回数でペアリング")
            elif pairing_method == 'machine_number':
                st.info("🔢 台番号でペアリング")
            else:
                st.warning("📋 アップロード順でペアリング")
        
        # OCRデバッグモード
        show_ocr_debug = st.checkbox(
            "詳細デバッグ情報を表示",
            value=st.session_state.get('show_ocr_debug', False),
            help="OCR処理や計算の詳細情報を表示します"
        )
        
        if show_ocr_debug != st.session_state.get('show_ocr_debug', False):
            st.session_state.show_ocr_debug = show_ocr_debug
        
        # エラーログセクション
        st.markdown("---")
        st.markdown("### 📋 エラーログ")
        
        error_logs = get_error_logs()
        if error_logs:
            st.warning(f"🚨 {len(error_logs)}件のエラーが記録されています")
            
            # エラーログ表示
            if st.checkbox("エラーログを表示", value=False):
                for i, error in enumerate(reversed(error_logs[-10:])):  # 最新10件を表示
                    with st.expander(f"[{error['timestamp']}] {error['type']}", expanded=False):
                        st.error(f"**エラーメッセージ:** {error['message']}")
                        if error.get('details'):
                            st.info(f"**詳細情報:** {error['details']}")
                        if st.checkbox(f"トレースバックを表示 (#{i})", value=False, key=f"trace_{i}"):
                            st.code(error['traceback'], language="python")
            
            # エラーログクリアボタン
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ ログをクリア", type="secondary"):
                    clear_error_logs()
                    st.success("✅ エラーログをクリアしました")
                    st.rerun()
            
            with col2:
                # エラーログダウンロードボタン
                if st.button("💾 ログをダウンロード"):
                    log_data = json.dumps(error_logs, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="📥 JSONファイルをダウンロード",
                        data=log_data,
                        file_name=f"error_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
        else:
            st.success("✅ エラーログはありません")
    

    if st.session_state.get('is_admin', False):
        st.markdown("---")
        st.markdown("### 🔍 デバッグ: 画像分類闾値")
        
        # 闾値設定
        black_threshold = st.slider(
            "黒色判定の闾値（画素値）",
            min_value=20,
            max_value=100,
            value=50,
            help="この値以下の画素値を黒色と判定します"
        )
        
        detail_threshold = st.slider(
            "出玉詳細画像判定の闾値（黒色割合）",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.05,
            format="%.2f",
            help="黒色割合がこの値以上の場合、出玉詳細画像と判定します"
        )
        
        st.session_state['black_pixel_threshold'] = black_threshold
        st.session_state['detail_image_threshold'] = detail_threshold

# STEP 1: ファイルアップロード（統合版）
st.markdown("### 📤 STEP 1: 画像をアップロード")
st.caption("グラフ画像と出玉詳細画像を自動的に分類します")

uploaded_files = st.file_uploader(
    "画像を選択（グラフ画像・出玉詳細画像の両方可）",
    type=['jpg', 'jpeg', 'png'],
    accept_multiple_files=True,
    help="複数の画像を一度にアップロードできます。黒色の割合で自動的に分類されます。",
    key="unified_uploader"
)

# アップロードされた画像を分類
graph_files = []
detail_files = []

if uploaded_files:
    # log(f"[Upload] {len(uploaded_files)} files uploaded")

    # 黒色割合で画像を分類
    detail_threshold = st.session_state.get('detail_image_threshold', 0.3)


    debug_data = []

    # 黒色判定の閾値を取得
    black_pixel_threshold = st.session_state.get('black_pixel_threshold', 50)

    for file in uploaded_files:
        try:
            # ファイルのハッシュ値を計算してキャッシュキーとする
            file.seek(0)
            file_content = file.read()
            file_hash = hashlib.md5(file_content).hexdigest()

            # キャッシュに分類結果があるかチェック
            cache_key = f"{file.name}_{file_hash}_{black_pixel_threshold}_{detail_threshold}"

            if cache_key in st.session_state.classification_cache:
                # キャッシュから取得（ログ出力なし）
                cached_result = st.session_state.classification_cache[cache_key]
                black_ratio = cached_result['black_ratio']
                file_type = cached_result['file_type']
            else:
                # 新規に分類を実行
                file.seek(0)
                img = Image.open(file)
                black_ratio = calculate_black_ratio(img, black_threshold=black_pixel_threshold)
                file_type = 'Detail' if black_ratio >= detail_threshold else 'Graph'

                # キャッシュに保存
                st.session_state.classification_cache[cache_key] = {
                    'black_ratio': black_ratio,
                    'file_type': file_type
                }
                # log(f"[Classification] {file.name}: black_ratio={black_ratio:.3f}, type={file_type}")

            debug_data.append({
                'name': file.name,
                'ratio': black_ratio,
                'type': '出玉詳細' if black_ratio >= detail_threshold else 'グラフ'
            })

            # 分類
            file.seek(0)  # ファイルポインタをリセット
            if black_ratio >= detail_threshold:
                detail_files.append(file)
            else:
                graph_files.append(file)
        except Exception as e:
            # log(f"[Classification] ERROR: {file.name} - {str(e)}")
            st.error(f"⚠️ {file.name} の処理中にエラー: {str(e)}")
            continue

    # log(f"[Classification] Result: {len(graph_files)} graph files, {len(detail_files)} detail files")

    # 出玉詳細画像から先に機種名を検出して自動設定
    # NOTE: アップロード時のClaude API呼び出しを無効化（プリセット変更の度に再実行されて重いため）
    # 機種名検出は解析ボタン押下後に実行されるので問題なし
    # if detail_files and st.session_state.game_type == "パチンコ" and not st.session_state.get('payout_manually_changed', False):
    #     # 最初の出玉詳細画像から機種名を取得
    #     if st.session_state.get('claude_api_key'):
    #         for detail_file in detail_files[:1]:  # 最初の1枚だけチェック
    #             try:
    #                 detail_file.seek(0)
    #                 detail_img = Image.open(detail_file)
    #                 processed_detail = preprocess_detail_image(detail_img)
    #
    #                 # 機種名検出のための簡易解析
    #                 try:
    #                     if not st.session_state.get('claude_api_key'):
    #                         st.warning("⚠️ APIキーが設定されていません。Claude設定タブでAPIキーを設定してください。")
    #                         api_result = None
    #                     else:
    #                         api_result = analyze_with_claude(
    #                             processed_detail,
    #                             st.session_state.claude_api_key,
    #                             st.session_state.get('claude_model', 'claude-3-5-haiku-20241022')
    #                         )
    #
    #                         # エラーがある場合は表示
    #                         if api_result and not api_result.get('success'):
    #                             error_msg = api_result.get('error', 'Unknown error')
    #                             file_name = uploaded_files[idx].name if idx < len(uploaded_files) else 'unknown'
    #                             full_error_msg = f"❌ {file_name}: {error_msg}"
    #                             st.error(full_error_msg)
    #                             # エラーをセッションステートに保存（重複チェックを改善）
    #                             # 同じファイルのエラーを更新
    #                             st.session_state.claude_errors = [e for e in st.session_state.claude_errors if not e.startswith(f"❌ {file_name}:")]
    #                             st.session_state.claude_errors.append(full_error_msg)
    #                             # エラーログ出力
    #                             from modules.error_handler import log_error
    #                             log_error('Claude API Error at upload', error_msg, {
    #                                 'has_api_key': bool(st.session_state.get('claude_api_key')),
    #                                 'model': st.session_state.get('claude_model', 'claude-3-5-haiku-20241022'),
    #                                 'file': uploaded_files[idx].name if idx < len(uploaded_files) else 'unknown'
    #                             })
    #                 except Exception as e:
    #                     file_name = uploaded_files[idx].name if idx < len(uploaded_files) else 'unknown'
    #                     full_error_msg = f"❌ {file_name}: AI分析エラー - {str(e)}"
    #                     st.error(full_error_msg)
    #                     # エラーをセッションステートに保存（重複チェックを改善）
    #                     # 同じファイルのエラーを更新
    #                     st.session_state.claude_errors = [e for e in st.session_state.claude_errors if not e.startswith(f"❌ {file_name}:")]
    #                     st.session_state.claude_errors.append(full_error_msg)
    #                     from modules.error_handler import log_error
    #                     log_error('Exception during Claude analysis', str(e), {
    #                         'location': 'file_upload_section',
    #                         'file': uploaded_files[idx].name if idx < len(uploaded_files) else 'unknown'
    #                     })
    #                     api_result = None
    #
    #                 if api_result and api_result.get('success'):
    #                     claude_data = api_result.get('data', {})
    #                     machine_name = claude_data.get('machine_name')
    #
    #                     # 機種別払い出し球数の自動設定機能を削除
    #
    #                 detail_file.seek(0)  # ファイルポインタをリセット
    #                 break
    #             except:
    #                 pass  # エラーは無視して続行
    
    # 分類結果を表示
    col1, col2 = st.columns(2)
    with col1:
        if graph_files:
            st.success(f"📊 グラフ画像: {len(graph_files)}枚")
    with col2:
        if detail_files:
            st.success(f"📋 出玉詳細画像: {len(detail_files)}枚")
    

    if st.session_state.get('is_admin', False) and st.checkbox("🔍 デバッグ: 黒色割合を表示", key="show_debug"):
        st.markdown("#### 画像別黒色割合")
        for data in debug_data:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.text(data['name'])
            with col2:
                # プログレスバーで黒色割合を表示
                st.progress(data['ratio'], text=f"{data['ratio']:.1%}")
            with col3:
                if data['type'] == '出玉詳細':
                    st.markdown("📋 **出玉詳細**")
                else:
                    st.markdown("📊 グラフ")
        
        st.caption(f"闾値: {detail_threshold:.1%} 以上を出玉詳細画像と判定")

# 以前のdetail_files向けの処理を維持
if detail_files:
    st.success(f"✅ {len(detail_files)}枚の出玉詳細画像がアップロードされました")
    
    # プレビューオプション
    if st.checkbox("出玉詳細画像の前処理プレビューを表示", key="preview_detail"):
        for idx, detail_file in enumerate(detail_files[:3]):  # 最初の3枚まで表示
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"元画像 - {detail_file.name}")
                original_img = Image.open(detail_file)
                st.image(original_img, use_column_width=True)
            with col2:
                st.caption("前処理後（黒枠検出＋overlay＋50%切り抜き）")
                processed_img = preprocess_detail_image(original_img)
                st.image(processed_img, use_column_width=True)
            
            if idx >= 2:  # 3枚表示したら終了
                if len(detail_files) > 3:
                    st.info(f"他に{len(detail_files) - 3}枚の画像があります")
                break

# 交換レートと超中小設定（画像アップロード前でも表示）
st.markdown("### ⚙️ 解析設定")

# 交換レート設定
unit = get_unit(st.session_state.get('game_type', 'パチンコ'))
default_rate = 3.57145 if st.session_state.game_type == "パチンコ" else 17.86
help_text = "1玉あたりの交換レート（円）。28玉交換の場合は3.57145円/玉" if st.session_state.game_type == "パチンコ" else "1枚あたりの交換レート（円）。5.6枚交換の場合は17.86円/枚"

exchange_rate = st.number_input(
    f"💱 交換レート（円/{unit}）",
    min_value=0.1,
    max_value=20.0,
    value=get_settings().get('exchange_rate', default_rate),
    step=0.01,
    format="%.5f",
    help=help_text
)
update_settings('exchange_rate', exchange_rate)

# パチンコの場合のみ超中小の払い出し球数設定を表示
if st.session_state.game_type == "パチンコ":
    st.markdown("##### 🎰 大当たり払い出し球数")
    col1, col2, col3 = st.columns(3)
    
    # ユーザーが手動で変更したかを追跡するキーを初期化
    if 'payout_manually_changed' not in st.session_state:
        st.session_state.payout_manually_changed = False
    
    with col1:
        big_balls = st.number_input(
            "超（大）",
            min_value=100,
            max_value=3000,
            value=get_settings().get('big_jackpot_balls', 1500),
            step=50,
            help="超（大）の1回あたりの払い出し球数",
            key="big_jackpot_input",
            on_change=lambda: setattr(st.session_state, 'payout_manually_changed', True)
        )
        update_settings('big_jackpot_balls', big_balls)
    
    with col2:
        middle_balls = st.number_input(
            "中",
            min_value=100,
            max_value=2000,
            value=get_settings().get('middle_jackpot_balls', 750),
            step=50,
            help="中の1回あたりの払い出し球数",
            key="middle_jackpot_input",
            on_change=lambda: setattr(st.session_state, 'payout_manually_changed', True)
        )
        update_settings('middle_jackpot_balls', middle_balls)
    
    with col3:
        small_balls = st.number_input(
            "小",
            min_value=100,
            max_value=1000,
            value=get_settings().get('small_jackpot_balls', 450),
            step=50,
            help="小の1回あたりの払い出し球数",
            key="small_jackpot_input",
            on_change=lambda: setattr(st.session_state, 'payout_manually_changed', True)
        )
        update_settings('small_jackpot_balls', small_balls)
    
    # デフォルトに戻すボタン
    if st.button("🔄 デフォルト値に戻す", use_container_width=False):
        update_settings('big_jackpot_balls', 1500)
        update_settings('middle_jackpot_balls', 750)
        update_settings('small_jackpot_balls', 450)
        st.session_state['big_jackpot_input'] = 1500
        st.session_state['middle_jackpot_input'] = 750
        st.session_state['small_jackpot_input'] = 450
        st.session_state.payout_manually_changed = False
        # auto_payout_appliedのリセットを削除
        st.rerun()

if graph_files or detail_files:
    # すべてのファイルを統合してから重複チェック
    all_files = graph_files + detail_files
    
    # 重複チェック
    seen_names = {}
    unique_graph_files = []
    unique_detail_files = []
    duplicate_names = []
    
    for file in graph_files:
        if file.name not in seen_names:
            seen_names[file.name] = 1
            unique_graph_files.append(file)
        else:
            seen_names[file.name] += 1
            if seen_names[file.name] == 2:  # 初めての重複
                duplicate_names.append(file.name)
    
    for file in detail_files:
        if file.name not in seen_names:
            seen_names[file.name] = 1
            unique_detail_files.append(file)
        else:
            seen_names[file.name] += 1
            if seen_names[file.name] == 2:  # 初めての重複
                duplicate_names.append(file.name)
    
    # アップロード結果を表示
    duplicate_count = sum(count - 1 for count in seen_names.values() if count > 1)
    if duplicate_count > 0:
        total_unique = len(unique_graph_files) + len(unique_detail_files)
        st.success(f"✅ {total_unique}枚の画像がアップロードされました")
        with st.expander(f"ℹ️ {duplicate_count}枚の重複ファイルをスキップしました", expanded=False):
            for name in duplicate_names:
                count = seen_names[name]
                st.caption(f"• {name} ({count}回アップロード、1枚のみ使用)")
    
    # 以降はunique_filesを使用
    graph_files = unique_graph_files
    detail_files = unique_detail_files
    
    # ファイル名をセッションステートに保存
    st.session_state.uploaded_file_names = [f.name for f in graph_files + detail_files]
    
    # STEP 2: プリセット選択
    st.markdown("### 📋 STEP 2: 解析設定を選択")
    st.caption("保存されたプリセットを選択するか、デフォルト設定を使用します")
    
    # プリセットに関する説明を追加
    with st.expander("ℹ️ プリセットの精度について", expanded=False):
        st.info("""
        📱 **端末による差異について**
        
        プリセットは特定の端末・環境で最適化された設定です。
        同じ機種でも以下の要因により微調整が必要な場合があります：
        
        • **端末の機種** - iPhone/Android、画面サイズの違い
        • **OSバージョン** - システムのレンダリング方法の差異
        • **ブラウザ** - Safari/Chrome等による表示の違い
        • **画面の明るさ・色温度** - スクリーンショットの色調への影響
        
        💡 **推奨される使い方**
        1. 似た端末のプリセットを選択して試す
        2. 必要に応じてSTEP 3で微調整を行う
        3. 調整後は新しいプリセットとして保存
        """)
    

    if st.checkbox("🐛 デバッグ情報を表示", value=False):
        st.write(f"saved_presets の内容: {st.session_state.get('saved_presets', {})}")
        st.write(f"データベースパス: {db_path}")
        import os
        st.write(f"データベースファイル存在: {os.path.exists(db_path)}")
        
        # データベースから直接読み込み
        try:
            fresh_presets = load_presets_from_db()
            st.write(f"データベースから直接読み込んだプリセット: {list(fresh_presets.keys())}")
        except Exception as e:
            st.write(f"データベース読み込みエラー: {str(e)}")
    
    # プリセット一覧
    preset_names = ["デフォルト"] + list(st.session_state.get('saved_presets', {}).keys())
    
    # プリセットボタンを横に並べる（調整セクションと同じスタイル）
    if len(preset_names) <= 4:
        preset_cols = st.columns(len(preset_names))
        for i, preset_name in enumerate(preset_names):
            with preset_cols[i]:
                button_type = "primary" if preset_name == st.session_state.get('current_preset_name', 'デフォルト') else "secondary"
                if st.button(f"📥 {preset_name}", use_container_width=True, key=f"analysis_preset_{preset_name}", type=button_type):
                    # log(f"[Button] Preset button clicked: '{preset_name}'")
                    if preset_name == "デフォルト":
                        reset_settings()
                    else:
                        # 現在の遊技種別を保持
                        current_game_type = st.session_state.get('game_type', 'パチンコ')
                        load_preset(preset_name)
                        # プリセットに遊技種別情報がある場合でも、現在選択されている遊技種別を優先
                        st.session_state.game_type = current_game_type

                    # 現在のプリセット名を保存
                    st.session_state.current_preset_name = preset_name

                    st.success(f"✅ '{preset_name}' の設定を適用しました")
                    st.rerun()
    else:
        # 5個以上の場合は複数行に分ける
        num_rows = (len(preset_names) + 3) // 4  # 4列で何行必要か
        for row in range(num_rows):
            cols = st.columns(4)
            for col in range(4):
                idx = row * 4 + col
                if idx < len(preset_names):
                    preset_name = preset_names[idx]
                    with cols[col]:
                        button_type = "primary" if preset_name == st.session_state.get('current_preset_name', 'デフォルト') else "secondary"
                        if st.button(f"📥 {preset_name}", use_container_width=True, key=f"analysis_preset_{preset_name}", type=button_type):
                            # log(f"[Button] Preset button clicked: '{preset_name}'")
                            if preset_name == "デフォルト":
                                reset_settings()
                            else:
                                # 現在の遊技種別を保持
                                current_game_type = st.session_state.get('game_type', 'パチンコ')
                                load_preset(preset_name)
                                # プリセットに遊技種別情報がある場合でも、現在選択されている遊技種別を優先
                                st.session_state.game_type = current_game_type
                            
                            # 現在のプリセット名を保存
                            st.session_state.current_preset_name = preset_name
                            
                            st.success(f"✅ '{preset_name}' の設定を適用しました")
                            st.rerun()
    
    # 調整設定の案内テキスト
    st.info("⚙️ 詳細な調整設定は、ページ下部の「画像解析の調整設定」セクションにあります。")
    
    # STEP 3: 解析オプションと開始
    st.markdown("### 🚀 STEP 3: 解析オプションと開始")
    
    # 解析オプション
    col_opt1, col_opt2 = st.columns([1, 1])
    with col_opt1:
        skip_ocr = st.checkbox(
            "⚡ OCRをスキップ（高速モード）", 
            value=False,
            help="台番号や累計スタートなどのテキスト情報を読み取らず、グラフ解析のみ実行します。処理が高速になります。"
        )
    with col_opt2:
        show_ocr_debug = st.checkbox(
            "🔍 OCRデバッグ情報を表示", 
            value=False,
            help="OCRで読み取ったテキストを確認できます。台番号が認識されない場合のトラブルシューティングに使用してください。"
        )
    
    
    st.caption("設定を確認したら、解析ボタンをクリックしてください")
    
    if st.button("🚀 解析を開始", type="primary", use_container_width=True):
        # log(f"[Button] Analysis button clicked - skip_ocr={skip_ocr}, show_ocr_debug={show_ocr_debug}")
        # 解析開始時にエラーをクリア
        st.session_state.claude_errors = []
        st.session_state.analysis_started = True
        try:
            st.session_state.start_analysis = True
            st.session_state.skip_ocr = skip_ocr
            st.session_state.show_ocr_debug = show_ocr_debug
            # データエディタのセッションステートをリセット
            if 'edited_df' in st.session_state:
                del st.session_state.edited_df
            # セッション状態が確実に保存されるよう小さな遅延を追加
            time.sleep(0.1)
            st.rerun()
        except Exception as e:
            # log(f"[Button] ERROR: Analysis start failed - {str(e)}")
            st.error(f"⚠️ 解析開始時にエラーが発生しました: {str(e)}")
            # エラーが発生しても続行できるようにする
            st.session_state.start_analysis = True
    
    # プログレスバー（解析中のみ表示）
    if st.session_state.get('start_analysis', False) and uploaded_files:
        progress_bar = st.progress(0)
        status_text = st.empty()
        detail_text = st.empty()
        
        # プログレスバーをセッションステートに保存
        st.session_state.progress_bar = progress_bar
        st.session_state.status_text = status_text
        st.session_state.detail_text = detail_text
        
        st.markdown("---")

# ファイルがアップロードされたことがある場合、解析ボタンを常に表示
elif st.session_state.uploaded_file_names:
    st.info(f"💾 保存されたファイル: {', '.join(st.session_state.uploaded_file_names)}")
    st.warning("⚠️ 設定を変更した後は、画像を再度アップロードしてください")
    
    # クリアボタン
    if st.button("🗑️ ファイル情報をクリア", use_container_width=True):
        # log(f"[Button] Clear files button clicked - clearing session state")
        # ファイル名をクリア
        st.session_state.uploaded_file_names = []
        # 編集中のデータフレームもクリア
        if 'edited_df' in st.session_state:
            del st.session_state.edited_df
        if 'temp_df' in st.session_state:
            del st.session_state.temp_df
        # 解析結果もクリア
        if 'analysis_results' in st.session_state:
            del st.session_state.analysis_results
        if 'detail_analysis_results' in st.session_state:
            del st.session_state.detail_analysis_results
        if 'paired_results' in st.session_state:
            del st.session_state.paired_results
        if 'unpaired_graphs' in st.session_state:
            del st.session_state.unpaired_graphs
        if 'unpaired_details' in st.session_state:
            del st.session_state.unpaired_details
        # 追加: ペアリング情報もクリア
        if 'machine_payout_data' in st.session_state:
            del st.session_state.machine_payout_data
        if 'display_normal_balls' in st.session_state:
            del st.session_state.display_normal_balls
        # 台番号入力フィールドのクリア
        for key in list(st.session_state.keys()):
            if key.startswith('machine_input_'):
                del st.session_state[key]
        # 画像分類キャッシュもクリア
        if 'classification_cache' in st.session_state:
            st.session_state.classification_cache = {}
        # 解析状態をリセット
        st.session_state.start_analysis = False
        # log(f"[Button] Session state cleared successfully")
        # セッション状態が確実に更新されるよう小さな遅延を追加
        time.sleep(0.1)
        st.rerun()

# 解析を実行
if graph_files and st.session_state.get('start_analysis', False):
    # 解析結果セクション
    st.markdown("### 🎯 解析結果")
    
    # 現在使用中のプリセットを表示
    current_preset_name = st.session_state.get('current_preset_name', 'デフォルト')
    
    st.info(f"📋 使用プリセット: **{current_preset_name}**")
    
    # 現在の設定値を表示
    with st.expander("🔧 使用中の設定値", expanded=False):
        current_settings = get_settings()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**切り抜き設定**")
            st.text(f"上方向: {current_settings.get('crop_top', 246)}px")
            st.text(f"下方向: {current_settings.get('crop_bottom', 247)}px")
            st.text(f"左余白: {current_settings.get('left_margin', 125)}px")
            st.text(f"右余白: {current_settings.get('right_margin', 125)}px")
        
        with col2:
            st.markdown("**検索範囲**")
            st.text(f"開始位置: +{current_settings.get('search_start_offset', 50)}px")
            st.text(f"終了位置: +{current_settings.get('search_end_offset', 500)}px")
        
        with col3:
            st.markdown("**グリッドライン調整**")
            st.text(f"距離: {current_settings.get('grid_distance', 327)}px")
    
    # セッションステートからプログレスバーを取得（既に上部で作成済み）
    progress_bar = st.session_state.get('progress_bar')
    status_text = st.session_state.get('status_text')
    detail_text = st.session_state.get('detail_text')
    
    # プログレスバーが存在しない場合（通常はない）
    if not progress_bar:
        st.error("プログレスバーの初期化エラー")
        st.stop()
    
    # 初期メッセージを表示
    status_text.text('🚀 解析を開始します...')
    # log(f"[Analysis] Starting analysis for {len(graph_files)} graph files")
    time.sleep(0.5)  # 少し待機してメッセージを見やすくする

    # 解析結果を格納
    analysis_results = []

    # 各画像を処理
    for idx, uploaded_file in enumerate(graph_files):
        log(f"[Graph {idx+1}/{len(graph_files)}] Processing: {uploaded_file.name}")

        # 進捗更新（開始時）
        progress_start = idx / len(graph_files)
        progress_bar.progress(progress_start)
        status_text.text(f'処理中... ({idx + 1}/{len(graph_files)})')

        # 画像を読み込み
        image = Image.open(uploaded_file)
        img_array = np.array(image)
        height, width = img_array.shape[:2]
        log(f"[Graph {idx+1}/{len(graph_files)}] Image loaded: {width}x{height}px")

        # OCRでデータ抽出を試みる（スキップ設定を確認）
        if not st.session_state.get('skip_ocr', False):
            log(f"[Graph {idx+1}/{len(graph_files)}] Starting OCR analysis...")
            ocr_start_time = time.time()
            ocr_data = extract_site7_data(img_array)
            ocr_end_time = time.time()
            log(f"[Graph {idx+1}/{len(graph_files)}] OCR complete: {ocr_end_time - ocr_start_time:.1f}s")
        else:
            log(f"[Graph {idx+1}/{len(graph_files)}] OCR skipped (fast mode)")
            ocr_data = None

        # Pattern3: Zero Line Based の自動検出
        
        # オレンジバーの検出（共通関数使用）
        orange_bottom = detect_orange_bar(img_array)
        
        # ゼロライン検出
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 設定値を使用（セッションステートから取得）
        settings = get_settings()
        
        # ゼロラインを検出（共通関数使用）
        zero_line_y = detect_zero_line(
            gray, 
            orange_bottom, 
            settings['search_start_offset'],
            settings['search_end_offset']
        )
        
        # ゼロライン調整値を適用
        zero_line_adjustment = settings.get('zero_line_adjustment', 0)
        zero_line_y += zero_line_adjustment
        
        # グラフ領域を切り抜き（共通関数使用）
        crop_settings = {
            'crop_top': settings['crop_top'],
            'crop_bottom': settings['crop_bottom'],
            'left_margin': settings['left_margin'],
            'right_margin': settings['right_margin']
        }
        cropped_img, top, bottom, left, right = crop_graph_area(img_array, zero_line_y, crop_settings)
        
        # 出玉詳細画像の処理（注：詳細画像の処理は後でまとめて実行されるため、ここでは行わない）
        detail_image_processed = None
        claude_analysis_result = None
        
        # グリッドラインを追加
        # 切り抜き画像の高さは493px（246+247）
        # 最上部が+30000、最下部が-30000なので、60000の範囲を493pxで表現
        # 1pxあたり約121.7玉
        crop_height = cropped_img.shape[0]
        zero_line_in_crop = zero_line_y - top  # 切り抜き画像内での0ライン位置
        
        # スケール計算（調整されたグリッドラインに基づく）
        # 注意：この変数はグリッドライン描画にのみ使用され、実際の解析には使用されない
        scale = 30000 / 246  # グリッドライン描画用のデフォルト値
        
        # グラフの上下限値を取得
        graph_limit = get_graph_limit(st.session_state.get('game_type', 'パチンコ'))
        
        # グリッドライン描画（設定値を使用）
        # ゼロラインからの距離を取得
        grid_distance = settings.get('grid_distance', 327)

        # +上限ライン（ゼロラインから上にgrid_distance）
        y_30k = zero_line_in_crop - grid_distance
        if 0 <= y_30k < crop_height:
            cv2.line(cropped_img, (0, int(y_30k)), (cropped_img.shape[1], int(y_30k)), (128, 128, 128), 2)
            cv2.putText(cropped_img, f'+{graph_limit}', (10, max(20, int(y_30k) + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)

        # -下限ライン（ゼロラインから下にgrid_distance）
        y_minus_30k = zero_line_in_crop + grid_distance
        y_minus_30k = min(max(0, y_minus_30k), crop_height - 1)  # 画像範囲内に制限
        cv2.line(cropped_img, (0, int(y_minus_30k)), (cropped_img.shape[1], int(y_minus_30k)), (128, 128, 128), 2)
        cv2.putText(cropped_img, f'-{graph_limit}', (10, max(10, int(y_minus_30k) - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)


        # ゼロラインから上下限ラインまでの距離（上下対称なのでgrid_distance）
        distance_to_plus_30k = grid_distance
        distance_to_minus_30k = grid_distance
        
        # 0ライン
        y_0 = int(zero_line_in_crop)  # 調整なし
        if 0 < y_0 < crop_height:
            cv2.line(cropped_img, (0, y_0), (cropped_img.shape[1], y_0), (255, 0, 0), 2)
            cv2.putText(cropped_img, '0', (10, y_0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)
        
        # 元画像にもグリッドラインを追加
        img_with_grid = img_array.copy()
        
        # 元画像での座標に変換（切り抜き前の座標系）
        # +上限ライン（元画像座標）
        y_30k_orig = int(top + y_30k)
        if 0 <= y_30k_orig < height:
            cv2.line(img_with_grid, (0, y_30k_orig), (width, y_30k_orig), (128, 128, 128), 2)
            cv2.putText(img_with_grid, f'+{graph_limit}', (10, max(20, y_30k_orig + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
        
        # -下限ライン（元画像座標）
        y_minus_30k_orig = int(top + y_minus_30k)
        if 0 <= y_minus_30k_orig < height:
            cv2.line(img_with_grid, (0, y_minus_30k_orig), (width, y_minus_30k_orig), (128, 128, 128), 2)
            cv2.putText(img_with_grid, f'-{graph_limit}', (10, max(10, y_minus_30k_orig - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
        
        # 0ライン（元画像座標）
        if 0 <= zero_line_y < height:
            cv2.line(img_with_grid, (0, zero_line_y), (width, zero_line_y), (255, 0, 0), 2)
            cv2.putText(img_with_grid, '0', (10, zero_line_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        
        # 切り抜き範囲を示す枠線を追加（オプション）
        cv2.rectangle(img_with_grid, (int(left), int(top)), (int(right), int(bottom)), (0, 255, 0), 2)

        # 解析を自動実行
        log(f"[Graph {idx+1}/{len(graph_files)}] Analyzing graph data...")

        # アナライザーのインスタンスを再利用
        try:
            if 'analyzer_instance' not in st.session_state:
                st.session_state.analyzer_instance = WebCompatibleAnalyzer()
            elif st.session_state.analyzer_instance is None:
                st.session_state.analyzer_instance = WebCompatibleAnalyzer()
            analyzer = st.session_state.analyzer_instance
        except Exception as e:
            log_error('Analyzer Initialization Error', str(e), {'function': 'main_process', 'stage': 'analyzer_init'})
            detail_col.error(f"⚠️ アナライザーの初期化に失敗しました: {str(e)}")
            continue
        
        # グリッドラインなしの画像を使用
        analysis_img = img_array[int(top):int(bottom), int(left):int(right)].copy()
        
        # 0ラインの位置を設定
        analyzer.zero_y = zero_line_in_crop
        # ゼロラインから±30,000ラインまでの距離を取得
        grid_distance = settings.get('grid_distance', 327)

        # ±30,000ラインの位置（ゼロラインからの距離で指定）
        y_30k_adjusted = zero_line_in_crop - grid_distance  # ゼロラインから上に grid_distance px
        y_minus_30k_adjusted = zero_line_in_crop + grid_distance  # ゼロラインから下に grid_distance px

        # ゼロラインから±30,000ラインまでの距離（上下対称）
        distance_to_plus_30k_adjusted = grid_distance
        distance_to_minus_30k_adjusted = grid_distance
        
        # グラフの上下限値を取得
        graph_limit = get_graph_limit(st.session_state.get('game_type', 'パチンコ'))
        
        # 線形スケール計算（ゼロラインから±30,000ラインまでの距離を使用）
        if distance_to_plus_30k_adjusted > 0 and distance_to_minus_30k_adjusted > 0:
            # 上下対称なので平均 = grid_distance
            avg_distance_adjusted = (distance_to_plus_30k_adjusted + distance_to_minus_30k_adjusted) / 2
            analyzer.scale = graph_limit / avg_distance_adjusted
        else:
            # フォールバック（距離が不正な場合はデフォルト値を使用）
            default_distance = 327
            analyzer.scale = graph_limit / default_distance
        
        # グラフデータを抽出
        graph_data_points, dominant_color, _, graph_info = analyzer.extract_graph_data(analysis_img)
        

        # if uploaded_file.name in ["IMG_0165.PNG", "IMG_0174.PNG", "IMG_0177.PNG"]:
        #     st.write(f"🔍 デバッグ情報 - {uploaded_file.name}")
        #     st.write(f"- ゼロライン位置（切り抜き内）: {zero_line_in_crop}px")
        #     st.write(f"- 切り抜き画像の高さ: {crop_height}px")
        #     st.write(f"- 調整された+30000ライン位置: {y_30k_adjusted}px (ゼロラインから: {settings.get('grid_distance', 327)}px)")
        #     st.write(f"- 調整された-30000ライン位置: {y_minus_30k_adjusted}px (ゼロラインから: {settings.get('grid_distance', 327)}px)")
        #     st.write(f"- ゼロから+30000までの距離: {distance_to_plus_30k_adjusted}px")
        #     st.write(f"- ゼロから-30000までの距離: {distance_to_minus_30k_adjusted}px")
        #     st.write(f"- スケール: {analyzer.scale:.2f} 玉/ピクセル")
        #     st.write(f"- 検出された色: {dominant_color}")
        #     st.write(f"- データポイント数: {len(graph_data_points) if graph_data_points else 0}")
        #     if graph_data_points:
        #         sample_points = graph_data_points[::100][:10]  # 10点をサンプル表示
        #         st.write("- サンプルデータ (x, 値):")
        #         for x, val in sample_points:
        #             y_pixel = zero_line_in_crop - (val / analyzer.scale)
        #             st.write(f"  X={int(x)}, 値={int(val)}玉, Y座標={int(y_pixel)}px")

        if graph_data_points:
            # graph_data_pointsの最初の要素のX座標を確認
            first_x = graph_data_points[0][0]
            log(f"[Graph Data Points] First point: x={first_x}px, value={graph_data_points[0][1]:.1f}玉")
            log(f"[Graph Data Points] Total points: {len(graph_data_points)}")
            log(f"[DEBUG 1] About to process graph values, ocr_data exists: {ocr_data is not None}")

            # データポイントから値のみを抽出
            graph_values = [value for x, value in graph_data_points]
            # 補正前の値を保存
            graph_values_original = graph_values.copy()

            # START地点（graph_values[0]）を0として全体を補正
            start_offset = graph_values[0]
            graph_values = [v - start_offset for v in graph_values]
            # log(f"[Graph Values] Offset correction: start_offset={start_offset:.1f}玉 (graph_values[0]を0に補正)")
            # log(f"[Graph Values] After correction: graph_values[0]={graph_values[0]:.1f}玉 (should be 0)")

            # 非線形補正を全体に適用（modules/correction.py）
            try:
                from modules.correction import apply_correction
                graph_values_before_correction = graph_values.copy()
                graph_values = [apply_correction(v) for v in graph_values]
                log(f"[Correction] Applied non-linear correction to {len(graph_values)} graph values")

                # graph_data_pointsも補正された値で更新（回転率計算用）
                graph_data_points = [(x, corrected_val) for (x, _), corrected_val in zip(graph_data_points, graph_values)]
                log(f"[Correction] Updated graph_data_points with corrected values")
            except ImportError as e:
                log(f"[Correction Error] Failed to import correction module: {e}")

            # グラフデータを全て出力（デバッグ用 - 1台目のみ）
            if idx == 0:
                graph_start_x_val = graph_info.get('start_x', 0) if graph_info else 0
                log(f"[Graph Values] Total points: {len(graph_values)}, graph_start_x: {graph_start_x_val}px")
                log(f"[Graph Values] All values (graph_values[i] = x={graph_start_x_val} + i*2):")
                for i in range(0, len(graph_values), 10):
                    chunk = graph_values[i:i+10]
                    x_start = graph_start_x_val + i*2
                    x_end = graph_start_x_val + (i+len(chunk)-1)*2
                    log(f"  index {i:3d}-{i+len(chunk)-1:3d} (x={x_start:3d}-{x_end:3d}px): {[round(v, 1) for v in chunk]}")

            # 統計情報を計算（既に補正済みのgraph_valuesから）
            max_val = max(graph_values)
            min_val = min(graph_values)

            # 現在値を複数の方法で検証して精度向上
            if len(graph_values) >= 5:
                # 最後の5点の中央値（外れ値除去）
                current_val = np.median(graph_values[-5:])
            else:
                current_val = graph_values[-1] if graph_values else 0

            # インデックスを保存
            max_idx = graph_values.index(max_val)
            min_idx = graph_values.index(min_val)

            # グラフの上下限値でクリップ
            graph_limit = get_graph_limit(st.session_state.get('game_type', 'パチンコ'))
            
            # 最大値が上限を超える場合は上限にクリップ
            if max_val > graph_limit:
                max_val = graph_limit
            
            # 最小値が下限を下回る場合は下限にクリップ
            if min_val < -graph_limit:
                min_val = -graph_limit

            # MAXがマイナスの場合は0を表示
            if max_val < 0:
                max_val = 0

            # 初当たり値を探す（改善版）
            game_type = st.session_state.get('game_type', 'パチンコ')
            small_jackpot_balls = get_settings().get('small_jackpot_balls', 450)
            
            # モジュールの関数を使用して初当たりを検出
            first_hit_result = detect_first_hit(graph_values, game_type, small_jackpot_balls)
            first_hit_val = first_hit_result['first_hit_val']
            first_hit_x = first_hit_result['first_hit_x']
            first_hit_debug_info = first_hit_result['debug_info']
            
            # スケール情報を追加（1pxあたりの回転数と玉数）
            if 'analyzer' in locals() and hasattr(analyzer, 'scale'):
                first_hit_debug_info['scale_info'] = {
                    'balls_per_pixel': analyzer.scale,
                    'spins_per_pixel': None  # 後で計算
                }
            else:
                first_hit_debug_info['scale_info'] = {
                    'balls_per_pixel': None,
                    'spins_per_pixel': None
                }
            
            # 初当たりまでの使用球数を計算
            first_hit_used_balls = 0
            if first_hit_x is not None and first_hit_val < 0:
                # 初当たりまでの最低値（最も球を使った時点）を探す
                min_val_before_first = 0
                # 初当たり位置を少し広げて探索（検出誤差を考慮）
                search_end = min(first_hit_x + 5, len(graph_values) - 1)
                for i in range(search_end + 1):
                    if graph_values[i] < min_val_before_first:
                        min_val_before_first = graph_values[i]
                # 使用球数は最低値の絶対値
                first_hit_used_balls = abs(min_val_before_first)

            # 総獲得球数の計算
            # Claude APIで超中小の回数が取得できている場合は、それを優先
            total_jackpot_balls = 0
            total_jackpot_balls_from_ai = None  # AI計算による総獲得球数
            
            # Claude APIデータがある場合、超中小の回数から計算
            if claude_analysis_result and claude_analysis_result.get('success') and st.session_state.game_type == 'パチンコ':
                claude_data = claude_analysis_result.get('data', {})
                
                if claude_data and all(k in claude_data for k in ['big_jackpots', 'medium_jackpots', 'small_jackpots']):
                    # 超中小の回数が全て取得できている場合
                    big_count = claude_data.get('big_jackpots', 0) or 0
                    middle_count = claude_data.get('medium_jackpots', 0) or 0
                    small_count = claude_data.get('small_jackpots', 0) or 0
                    
                    # 異常値チェック（1日の大当たり回数として現実的な範囲）
                    total_jackpots = big_count + middle_count + small_count
                    if total_jackpots > 50:  # 1日50回以上は異常
                        # 異常値の場合はグラフから推定
                        print(f"警告: 異常な大当たり回数を検出 (超:{big_count}, 中:{middle_count}, 小:{small_count})")
                        big_count = 0
                        middle_count = 0
                        small_count = 0
                    
                    # 常にユーザー設定を使用
                    big_balls = get_settings().get('big_jackpot_balls', 1500)
                    middle_balls = get_settings().get('middle_jackpot_balls', 750)
                    small_balls = get_settings().get('small_jackpot_balls', 450)
                    
                    # AI計算による総獲得球数
                    total_jackpot_balls_from_ai = (
                        big_count * big_balls +
                        middle_count * middle_balls +
                        small_count * small_balls
                    )
            
            # グラフから総獲得球数を計算（従来の方法）
            jackpot_count = 0  # 大当り回数をカウント
            jackpot_details = []  # 各大当りの詳細情報
            total_decline_balls = 0  # 通常時の使用球数（下降部分の累積）
            # 遊技種別に応じた閾値
            increase_threshold = 100 if st.session_state.game_type == 'パチンコ' else 20  # パチスロは20枚以上
            
            i = 0
            while i < len(graph_values) - 1:
                # 急激な増加を検出
                increase = graph_values[i+1] - graph_values[i]
                if increase >= increase_threshold:
                    # 大当りの開始点
                    start_val = graph_values[i]
                    start_idx = i
                    # 大当りの終了点を探す（最大値まで継続）
                    j = i + 1
                    max_val_in_jackpot = graph_values[j]
                    
                    while j < len(graph_values) - 1:
                        if graph_values[j+1] > max_val_in_jackpot:
                            max_val_in_jackpot = graph_values[j+1]
                            j += 1
                        elif graph_values[j+1] < graph_values[j] - (50 if st.session_state.game_type == 'パチンコ' else 10):  # 下降で大当り終了（パチスロは10枚）
                            break
                        else:
                            j += 1
                    
                    # この大当りでの獲得球数（開始点から最大値まで）
                    jackpot_balls = max_val_in_jackpot - start_val
                    if jackpot_balls > 0:
                        total_jackpot_balls += jackpot_balls
                        jackpot_count += 1
                        jackpot_details.append({
                            'number': jackpot_count,
                            'start_idx': start_idx,
                            'end_idx': j,
                            'balls': jackpot_balls,
                            'start_val': start_val,
                            'peak_val': max_val_in_jackpot
                        })
                    
                    # 次の検出開始点を更新
                    i = j
                # 下降区間の検出（通常時の使用球数）
                elif graph_values[i+1] < graph_values[i] - 10:  # 10玉以上の下降
                    # この区間での使用球数
                    balls_used = graph_values[i] - graph_values[i+1]
                    total_decline_balls += balls_used
                    i += 1
                else:
                    i += 1
            
            # グラフから計算した総獲得玉数を保持
            total_jackpot_balls_graph = total_jackpot_balls
                
            # 平均獲得球数を計算
            avg_jackpot_balls = total_jackpot_balls / jackpot_count if jackpot_count > 0 else 0

            # オーバーレイ画像を作成
            overlay_img = cropped_img.copy()

            # 検出されたグラフラインを描画
            prev_x = None
            prev_y = None
            prev_value = None

            # 色の定義
            color_up = (0, 255, 0)      # 上昇中：緑色
            color_down = (255, 0, 0)    # 下降中：赤色
            color_flat = (255, 255, 0)  # 横ばい：黄色

            # グラフポイントを描画
            for i, (x, value) in enumerate(graph_data_points):
                # Y座標を計算（線形スケール）
                y = int(zero_line_in_crop - (value / analyzer.scale))

                # 画像範囲内かチェック
                if y is not None and 0 <= y < overlay_img.shape[0] and 0 <= x < overlay_img.shape[1]:
                    # 前の値との比較で色を決定
                    if prev_value is not None:
                        if value > prev_value + 10:  # 10玉以上の上昇
                            draw_color = color_up
                        elif value < prev_value - 10:  # 10玉以上の下降
                            draw_color = color_down
                        else:  # 横ばい
                            draw_color = color_flat
                    else:
                        draw_color = color_flat  # 最初の点

                    # 点を描画（より見やすくするため）
                    cv2.circle(overlay_img, (int(x), y), 2, draw_color, -1)

                    # 線で接続
                    if prev_x is not None and prev_y is not None:
                        cv2.line(overlay_img, (int(prev_x), int(prev_y)), (int(x), y), draw_color, 2)

                    prev_x = x
                    prev_y = y
                    prev_value = value

            # 最高値、最低値、初当たりの位置を見つける
            # インデックスは既に上で取得済み

            # Y座標計算用の関数（線形スケール）
            def calculate_y_from_value(val):
                return int(zero_line_in_crop - (val / analyzer.scale))
            
            # 横線を描画（最低値、最高値、現在値、初当たり値）
            # 最高値ライン（端から端まで）
            max_y = calculate_y_from_value(max_val)
            if 0 <= max_y < overlay_img.shape[0]:
                # 端から端まで線を引く
                cv2.line(overlay_img, (0, max_y), (overlay_img.shape[1], max_y), (0, 255, 255), 2)
                # 最高値の点に大きめの円を描画
                max_x = graph_data_points[max_idx][0]
                cv2.circle(overlay_img, (int(max_x), max_y), 4, (0, 255, 255), -1)
                cv2.circle(overlay_img, (int(max_x), max_y), 5, (0, 200, 200), 2)
                # 背景付きテキスト（白背景、濃い黄色文字）右端に表示
                text = f'MAX: {int(max_val):,}'
                text_width = 140
                text_y = max_y if max_y > 20 else max_y + 20  # 上端で見切れないように調整
                cv2.rectangle(overlay_img, (overlay_img.shape[1] - text_width - 15, text_y - 15), 
                             (overlay_img.shape[1] - 10, text_y + 5), (255, 255, 255), -1)
                cv2.putText(overlay_img, text, (overlay_img.shape[1] - text_width - 10, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 150), 1, cv2.LINE_AA)

            # 最低値ライン（端から端まで）
            min_y = calculate_y_from_value(min_val)
            if 0 <= min_y < overlay_img.shape[0]:
                # 端から端まで線を引く
                cv2.line(overlay_img, (0, min_y), (overlay_img.shape[1], min_y), (255, 0, 255), 2)
                # 最低値の点に大きめの円を描画
                min_x = graph_data_points[min_idx][0]
                cv2.circle(overlay_img, (int(min_x), min_y), 4, (255, 0, 255), -1)
                cv2.circle(overlay_img, (int(min_x), min_y), 5, (200, 0, 200), 2)
                # 背景付きテキスト（白背景、濃いマゼンタ文字）右端に表示
                text = f'MIN: {int(min_val):,}'
                text_width = 140
                text_y = min_y if (min_y > 20 and min_y < overlay_img.shape[0] - 20) else (20 if min_y <= 20 else overlay_img.shape[0] - 20)
                cv2.rectangle(overlay_img, (overlay_img.shape[1] - text_width - 15, text_y - 15), 
                             (overlay_img.shape[1] - 10, text_y + 5), (255, 255, 255), -1)
                cv2.putText(overlay_img, text, (overlay_img.shape[1] - text_width - 10, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 0, 150), 1, cv2.LINE_AA)

            # 現在値ライン（端から端まで）
            current_y = calculate_y_from_value(current_val)
            if 0 <= current_y < overlay_img.shape[0]:
                cv2.line(overlay_img, (0, current_y), (overlay_img.shape[1], current_y), (255, 255, 0), 2)
                # 現在値の点に大きめの円を描画（グラフ上）
                if len(graph_data_points) > 0:
                    current_x = graph_data_points[-1][0]  # 最後のデータポイントのX座標
                    cv2.circle(overlay_img, (int(current_x), current_y), 4, (255, 255, 0), -1)
                    cv2.circle(overlay_img, (int(current_x), current_y), 5, (200, 200, 0), 2)
                # 背景付きテキスト（白背景、濃いシアン文字）右端に表示
                text = f'CURRENT: {int(current_val):,}'
                text_width = 160
                text_y = current_y - 10 if current_y > 30 else current_y + 15
                cv2.rectangle(overlay_img, (overlay_img.shape[1] - text_width - 15, text_y - 15), 
                             (overlay_img.shape[1] - 10, text_y + 5), (255, 255, 255), -1)
                cv2.putText(overlay_img, text, (overlay_img.shape[1] - text_width - 10, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 0), 1, cv2.LINE_AA)

            # 初当たり値ライン（端から端まで）
            first_hit_pixel_x = None  # 初当たりの実際のピクセル位置を保存
            if first_hit_x is not None and first_hit_val != 0:  # 初当たりがある場合
                first_hit_y = calculate_y_from_value(first_hit_val)
                if 0 <= first_hit_y < overlay_img.shape[0]:
                    # 端から端まで線を引く
                    cv2.line(overlay_img, (0, first_hit_y), (overlay_img.shape[1], first_hit_y), (155, 48, 255), 2)
                    # 初当たりの点に大きめの円を描画
                    first_hit_graph_x = graph_data_points[first_hit_x][0]
                    first_hit_pixel_x = first_hit_graph_x  # 実際のピクセル位置を保存
                    cv2.circle(overlay_img, (int(first_hit_graph_x), first_hit_y), 4, (155, 48, 255), -1)
                    cv2.circle(overlay_img, (int(first_hit_graph_x), first_hit_y), 5, (120, 30, 200), 2)
                    # 背景付きテキスト（白背景、紫文字）右端に表示
                    text = f'FIRST HIT: {int(first_hit_val):,}'
                    text_width = 150
                    text_y = first_hit_y if (first_hit_y > 20 and first_hit_y < overlay_img.shape[0] - 20) else (20 if first_hit_y <= 20 else overlay_img.shape[0] - 20)
                    cv2.rectangle(overlay_img, (overlay_img.shape[1] - text_width - 15, text_y - 15), 
                                 (overlay_img.shape[1] - 10, text_y + 5), (255, 255, 255), -1)
                    cv2.putText(overlay_img, text, (overlay_img.shape[1] - text_width - 10, text_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 0, 150), 1, cv2.LINE_AA)
            
            # グラフの開始点と現在地のマーカーを追加（ゼロライン上）
            if graph_info and len(graph_data_points) > 0:
                # ゼロラインのY座標
                zero_y = zero_line_in_crop
                
                # 開始点（緑の点）- ゼロライン上
                if graph_info.get('start_x') is not None:
                    start_x = graph_info['start_x']
                    cv2.circle(overlay_img, (int(start_x), zero_y), 5, (0, 255, 0), -1)
                    cv2.circle(overlay_img, (int(start_x), zero_y), 6, (0, 200, 0), 2)
                    # ラベル
                    cv2.putText(overlay_img, 'START', (int(start_x) - 20, zero_y - 15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 0), 1, cv2.LINE_AA)
                

            # 結果を保存
            # 回転率計算（OCRデータがある場合のみ）
            rotation_metrics = None
            log(f"[DEBUG rotation_metrics] ocr_data={ocr_data is not None}, has_total_start={ocr_data.get('total_start') if ocr_data else 'N/A'}, skip_ocr={st.session_state.get('skip_ocr', False)}")
            if ocr_data and ocr_data.get('total_start') and not st.session_state.get('skip_ocr', False):
                # グラフの実効幅（左右マージンを除外）
                graph_width = right - left
                # analyze_values形式のデータを作成
                analysis_data = {
                    'max_value': int(max_val),
                    'max_index': max_idx,
                    'min_value': int(min_val),
                    'min_index': min_idx,
                    'first_hit_index': first_hit_x if first_hit_x is not None else -1,
                    'first_hit_value': int(first_hit_val) if first_hit_x is not None else 0,
                    'final_value': int(current_val)
                }
                rotation_metrics = analyzer.calculate_rotation_metrics(
                    graph_data_points, 
                    analysis_data, 
                    ocr_data['total_start'],
                    graph_width,
                    graph_info,
                    ocr_data,  # OCRデータを追加
                    st.session_state.get('game_type', 'パチンコ')  # 遊技種別を追加
                )
                # スケール情報を更新
                if rotation_metrics and 'spins_per_pixel' in rotation_metrics:
                    first_hit_debug_info['scale_info']['spins_per_pixel'] = rotation_metrics['spins_per_pixel']
                # グラフ情報も追加
                first_hit_debug_info['graph_info'] = {
                    'graph_width': graph_width,
                    'total_spins': int(ocr_data['total_start']) if ocr_data.get('total_start') else None,
                    'graph_start_x': graph_info.get('start_x') if graph_info else None,
                    'graph_end_x': graph_info.get('end_x') if graph_info else None
                }

            log(f"[DEBUG 2] About to save result, rotation_metrics={rotation_metrics is not None}, ocr_data={ocr_data is not None}")
            if rotation_metrics:
                log(f"[DEBUG 2] rotation_metrics keys: {list(rotation_metrics.keys())}, spins_per_pixel={rotation_metrics.get('spins_per_pixel', 'N/A')}")
            analysis_results.append({
                'name': uploaded_file.name,
                'original_image': img_with_grid,  # グリッド付き元画像を保存
                'cropped_image': cropped_img,  # 切り抜き画像
                'overlay_image': overlay_img,  # オーバーレイ画像
                'detail_image_processed': detail_image_processed,  # 処理済み出玉詳細画像
                'claude_analysis': claude_analysis_result,  # Claude API解析結果
                'success': True,
                'max_val': int(max_val),
                'min_val': int(min_val),
                'current_val': int(current_val),
                'first_hit_index': int(first_hit_x) if first_hit_x is not None else -1,  # 初当たりインデックス（AI基準計算用）
                'first_hit_val': int(first_hit_val) if first_hit_x is not None else None,
                'first_hit_pixel_x': int(first_hit_pixel_x) if first_hit_pixel_x is not None else None,  # 初当たりの実際のピクセル位置
                'first_hit_used_balls': int(first_hit_used_balls),  # 初当たりまでの使用球数
                'total_jackpot_balls': int(total_jackpot_balls),  # 総獲得球数（AI優先）
                'total_jackpot_balls_from_ai': int(total_jackpot_balls_from_ai) if total_jackpot_balls_from_ai is not None else None,  # AI計算による総獲得球数
                'total_jackpot_balls_graph': int(total_jackpot_balls_graph) if 'total_jackpot_balls_graph' in locals() else int(total_jackpot_balls),  # グラフから計算した総獲得球数
                'total_decline_balls': int(total_decline_balls) if 'total_decline_balls' in locals() else 0,  # 通常時使用球数（下降部分の累積）
                'jackpot_count': jackpot_count,  # 大当り回数（グラフから検出）
                'avg_jackpot_balls': int(avg_jackpot_balls),  # 平均獲得球数
                'jackpot_details': jackpot_details,  # 各大当りの詳細
                'dominant_color': dominant_color,
                'ocr_data': ocr_data,  # OCRデータを追加
                'ocr_text': ocr_data.get('ocr_text') if ocr_data else None,  # OCRテキストを追加
                'rotation_metrics': rotation_metrics,  # 回転率データを追加
                'first_hit_debug': first_hit_debug_info,  # 初当たり検出デバッグ情報を追加
                'graph_values': graph_values,  # グラフの生データを追加（回転率①計算用）
                'zero_line_y': zero_line_in_crop,  # ゼロライン位置を追加（Claude AIマーカー用）
                'graph_data_points': graph_data_points,  # グラフデータポイントを追加（AI基準計算用）
                'graph_info': graph_info,  # グラフ情報を追加（AI基準計算用）
                'graph_width': graph_width  # グラフ幅を追加（AI基準計算用）
            })
        else:
            # 解析失敗時
            analysis_results.append({
                'name': uploaded_file.name,
                'original_image': img_with_grid,  # グリッド付き元画像を保存
                'cropped_image': cropped_img,
                'overlay_image': cropped_img,  # 解析失敗時は切り抜き画像を使用
                'success': False,
                'ocr_data': ocr_data  # OCRデータを追加
            })
        
        # 各画像の処理完了時に進捗を更新
        progress_end = (idx + 1) / len(graph_files)
        progress_bar.progress(progress_end)
    
    # 出玉詳細画像の処理
    detail_analysis_results = []
    machine_payout_data = None  # 機種別払い出し球数を一度だけ取得
    detected_machine_name = None  # 検出した機種名を保存

    if detail_files:
        status_text.text(f'出玉詳細画像を処理中...')
        # log(f"[Detail] Starting detail image analysis for {len(detail_files)} files")

        # APIキーチェック（最初に1回だけ）
        if not st.session_state.get('claude_api_key') and detail_files:
            # log(f"[Detail] WARNING: Claude API key not set, skipping analysis")
            st.warning("⚠️ Claude APIキーが設定されていません。出玉詳細の自動解析はスキップされます。")

        for idx, detail_file in enumerate(detail_files):
            log(f"[Detail {idx+1}/{len(detail_files)}] Processing: {detail_file.name}")
            detail_file.seek(0)

            # Claude APIで解析（APIキーがある場合）
            claude_result = None
            if st.session_state.get('claude_api_key'):
                try:
                    # 画像読み込み
                    detail_img = Image.open(detail_file)
                    log(f"[Detail {idx+1}/{len(detail_files)}] Image loaded: {detail_img.width}x{detail_img.height}px")

                    # 前処理を適用
                    import time
                    preprocess_start = time.time()
                    processed_detail = preprocess_detail_image(detail_img)
                    preprocess_time = time.time() - preprocess_start
                    log(f"[Detail {idx+1}/{len(detail_files)}] Preprocessing complete: {preprocess_time:.1f}s")

                    # Claude APIで解析
                    log(f"[Detail {idx+1}/{len(detail_files)}] Starting Claude API analysis...")
                    api_start = time.time()
                    api_result = analyze_with_claude(
                        processed_detail,
                        st.session_state.claude_api_key,
                        st.session_state.get('claude_model', 'claude-3-5-haiku-20241022')
                    )
                    api_time = time.time() - api_start
                    log(f"[Detail {idx+1}/{len(detail_files)}] Claude API complete: {api_time:.1f}s")
                    # log(f"[Timing] {detail_file.name} - Preprocess: {preprocess_time:.1f}s, API: {api_time:.1f}s")
                    
                    if api_result and api_result.get('success'):
                        claude_result = api_result.get('data', {})
                        # 台番号を正規化
                        if claude_result.get('machine_number'):
                            claude_result['normalized_machine_number'] = normalize_machine_number(claude_result['machine_number'])
                        
                        # 機種名が取得でき、まだ機種データを取得していない場合のみ処理
                        if claude_result.get('machine_name'):
                            machine_name = claude_result['machine_name']
                            
                            # 最初の1回だけ機種データを設定
                            if machine_payout_data is None:
                                # log(f"[Machine Detection] 機種名検出: 「{machine_name}」")
                                detected_machine_name = machine_name
                                
                                # 手動設定された値を使用
                                machine_payout_data = {
                                    'big_jackpot_balls': get_settings().get('big_jackpot_balls', 1500),
                                    'middle_jackpot_balls': get_settings().get('middle_jackpot_balls', 750),
                                    'small_jackpot_balls': get_settings().get('small_jackpot_balls', 450)
                                }

                            # 機種データをClaude結果に追加
                            if machine_payout_data:
                                claude_result['machine_payouts'] = machine_payout_data
                except Exception as e:
                    error_msg = str(e)
                    if "401" in error_msg or "Unauthorized" in error_msg:
                        st.error(f"❌ APIキーエラー: APIキーが無効または期限切れです。設定を確認してください。")
                    elif "429" in error_msg:
                        st.warning(f"⚠️ APIレート制限: しばらく待ってから再試行してください。")
                    else:
                        st.warning(f"⚠️ {detail_file.name} のClaude解析でエラー: {error_msg}")
            
            detail_analysis_results.append({
                'name': detail_file.name,
                'claude_data': claude_result
            })
    
    # ペアリング処理
    pairing_method = st.session_state.get('pairing_method', 'machine_total_match')  # デフォルトは台番号＋累計スタート
    paired_results = []
    unpaired_graphs = []
    unpaired_details = []
    
    if pairing_method == 'machine_total_match':
        # 台番号＋累計スタートでペアリング
        # 使用済みフラグをクリア
        for detail in detail_analysis_results:
            detail['used'] = False
        
        for result in analysis_results:
            # グラフから台番号と累計スタートを取得
            graph_machine_num = None
            graph_total_start = None
            
            if result.get('ocr_data'):
                graph_machine_num = result['ocr_data'].get('machine_number')
                graph_total_start = result['ocr_data'].get('total_start')
            
            # 最適なペアを探す
            best_match = None
            
            for detail in detail_analysis_results:
                if not detail.get('used', False) and detail.get('claude_data'):
                    claude_data = detail['claude_data']
                    detail_machine_num = claude_data.get('machine_number')
                    detail_total_start = claude_data.get('total_rotations')
                    
                    # デバッグ情報を表示
                    if st.session_state.get('show_ocr_debug', False):
                        st.write(f"🔍 ペアリングチェック - {result['name']} vs {detail['name']}")
                        st.write(f"  - グラフ台番号: {graph_machine_num} → 正規化: {normalize_machine_number(str(graph_machine_num))}")
                        st.write(f"  - 詳細台番号: {detail_machine_num} → 正規化: {normalize_machine_number(str(detail_machine_num))}")
                        st.write(f"  - グラフ累計スタート: {graph_total_start}")
                        st.write(f"  - 詳細累計スタート: {detail_total_start}")
                    
                    # 台番号と累計スタートが両方一致する場合
                    # 累計スタートを数値として比較
                    graph_total_int = None
                    detail_total_int = None
                    try:
                        graph_total_int = int(graph_total_start)
                        detail_total_int = int(detail_total_start)
                    except:
                        pass
                    
                    if (graph_machine_num and detail_machine_num and 
                        graph_total_int is not None and detail_total_int is not None and
                        normalize_machine_number(str(graph_machine_num)) == normalize_machine_number(str(detail_machine_num)) and
                        graph_total_int == detail_total_int):
                        if st.session_state.get('show_ocr_debug', False):
                            st.success(f"✅ ペアリング成立！")
                        best_match = detail
                        break
            
            # ペアリング実行
            if best_match:
                machine_num = normalize_machine_number(str(graph_machine_num))
                paired_results.append({
                    'graph': result,
                    'detail': best_match,
                    'machine_number': machine_num,
                    'match_type': 'perfect_match',  # 完全一致
                    'match_info': f'台番号: {machine_num}, 累計スタート: {graph_total_start}'
                })
                best_match['used'] = True

                # ペアリング成功後、AI基準の回転率を再計算
                if result.get('rotation_metrics') and best_match.get('claude_data'):
                    claude_data = best_match['claude_data']
                    # OCRデータにClaude APIのデータを追加
                    enhanced_ocr_data = result.get('ocr_data', {}).copy() if result.get('ocr_data') else {}
                    enhanced_ocr_data['initial_ball_starts'] = claude_data.get('initial_ball_starts')

                    # rotation_metricsを再計算
                    analyzer = WebCompatibleAnalyzer()
                    graph_data_points = result.get('graph_data_points', [])
                    analysis_data = {
                        'max_value': result.get('max_val', 0),
                        'max_index': 0,  # 不要だが形式上必要
                        'min_value': result.get('min_val', 0),
                        'min_index': 0,
                        'first_hit_index': result.get('first_hit_index', -1),
                        'first_hit_value': result.get('first_hit_val', 0),
                        'final_value': result.get('current_val', 0)
                    }

                    # デバッグ: 再計算前の値を確認
                    log(f"[Pairing Recalc Debug] first_hit_index={analysis_data.get('first_hit_index')}, initial_ball_starts={enhanced_ocr_data.get('initial_ball_starts')}, data_points_len={len(graph_data_points)}")

                    if enhanced_ocr_data.get('total_start') and graph_data_points:
                        recalculated_metrics = analyzer.calculate_rotation_metrics(
                            graph_data_points,
                            analysis_data,
                            enhanced_ocr_data['total_start'],
                            result.get('graph_width', 939),
                            result.get('graph_info'),
                            enhanced_ocr_data,  # Claude APIのデータを含む
                            st.session_state.get('game_type', 'パチンコ')
                        )

                        # rotation_metricsを更新
                        if recalculated_metrics:
                            result['rotation_metrics'] = recalculated_metrics
                            log(f"[Pairing] Recalculated rotation_metrics with AI data: ai_spp={recalculated_metrics.get('ai_based_spins_per_pixel', 0)}, ai_total={recalculated_metrics.get('ai_based_cumulative_total_spins', 0)}")

                # デバッグ情報
                if st.session_state.get('show_ocr_debug', False):
                    st.success(f"✅ ペアリング成功: {result['name']} ⟷ {best_match['name']}")
                    st.caption(f"  台番号: {machine_num}, 累計スタート: {graph_total_start}")
            else:
                unpaired_graphs.append(result)
                
                # デバッグ情報
                if st.session_state.get('show_ocr_debug', False):
                    st.warning(f"⚠️ ペアリング失敗: {result['name']}")
                    st.caption(f"  グラフ - 台番号: {graph_machine_num or '未検出'}, 累計スタート: {graph_total_start or '未検出'}")
                    # 詳細画像側のデータも表示
                    for detail in detail_analysis_results:
                        if detail.get('claude_data'):
                            detail_machine = detail['claude_data'].get('machine_number')
                            detail_total = detail['claude_data'].get('total_rotations')
                            st.caption(f"  詳細画像 {detail['name']} - 台番号: {detail_machine or '未検出'}, 累計スタート: {detail_total or '未検出'}")
        
        # 使用されなかった詳細画像
        unpaired_details = [d for d in detail_analysis_results if not d.get('used', False)]
        
    elif pairing_method == 'jackpot_match':
        # 大当たり回数でペアリング
        # 使用済みフラグをクリア
        for detail in detail_analysis_results:
            detail['used'] = False
        
        for result in analysis_results:
            # グラフから大当たり回数を取得（整数に変換）
            try:
                graph_jackpot_count = int(result.get('jackpot_count', 0) or 0)
            except (ValueError, TypeError):
                graph_jackpot_count = 0
                
            # OCRから初当たり回数を取得（整数に変換）
            try:
                graph_first_hit = int((result.get('ocr_data') or {}).get('first_hit_count', 0) or 0)
            except (ValueError, TypeError):
                graph_first_hit = 0
            
            # 最適なペアを探す
            best_match = None
            best_score = 0
            
            for detail in detail_analysis_results:
                if not detail.get('used', False) and detail.get('claude_data'):
                    # 詳細画像の大当たり回数（文字列の可能性があるので整数に変換）
                    try:
                        detail_total = int(detail['claude_data'].get('total_jackpots', 0) or 0)
                    except (ValueError, TypeError):
                        detail_total = 0
                    
                    try:
                        detail_first = int(detail['claude_data'].get('first_jackpots', 0) or 0)
                    except (ValueError, TypeError):
                        detail_first = 0
                    
                    # スコア計算（完全一致を優先）
                    score = 0
                    if graph_jackpot_count > 0 and graph_jackpot_count == detail_total:
                        score += 100  # 大当たり回数が一致
                    if graph_first_hit > 0 and graph_first_hit == detail_first:
                        score += 50   # 初当たり回数が一致
                    
                    # 近似値もスコアリング（差が小さいほど高得点）
                    if score == 0 and graph_jackpot_count > 0 and detail_total > 0:
                        diff = abs(graph_jackpot_count - detail_total)
                        if diff <= 2:  # 差が2以内なら候補
                            score = 20 - diff * 5
                    
                    if score > best_score:
                        best_score = score
                        best_match = detail
            
            # ペアリング実行
            if best_match and best_score >= 20:  # 閾値以上のスコアでペア成立
                # 台番号の取得（表示用）
                machine_num = None
                if best_match.get('claude_data') and best_match['claude_data'].get('machine_number'):
                    machine_num = normalize_machine_number(best_match['claude_data']['machine_number'])
                elif result.get('ocr_data') and result['ocr_data'].get('machine_number'):
                    machine_num = normalize_machine_number(result['ocr_data']['machine_number'])
                
                paired_results.append({
                    'graph': result,
                    'detail': best_match,
                    'machine_number': machine_num or f"台{len(paired_results)+1}",
                    'match_score': best_score
                })
                best_match['used'] = True  # 使用済みフラグを設定
            else:
                unpaired_graphs.append(result)
        
        # 使用されなかった詳細画像
        unpaired_details = [d for d in detail_analysis_results if not d.get('used', False)]
        
    elif pairing_method == 'order':
        # アップロード順でペアリング
        for idx, result in enumerate(analysis_results):
            if idx < len(detail_analysis_results):
                detail = detail_analysis_results[idx]
                
                # 台番号の取得（表示用）
                machine_num = None
                # 詳細画像の台番号を優先（より正確）
                if detail.get('claude_data') and detail['claude_data'].get('machine_number'):
                    machine_num = normalize_machine_number(detail['claude_data']['machine_number'])
                # 詳細画像から台番号が取れない場合はグラフから
                elif result.get('ocr_data') and result['ocr_data'].get('machine_number'):
                    machine_num = normalize_machine_number(result['ocr_data']['machine_number'])
                # どちらからも取れない場合はインデックスベース
                if not machine_num:
                    machine_num = f"台{idx+1}"
                
                paired_results.append({
                    'graph': result,
                    'detail': detail,
                    'machine_number': machine_num
                })
                detail['paired'] = True
            else:
                unpaired_graphs.append(result)
        
        # ペアリングされなかった詳細画像（グラフより詳細画像が多い場合）
        for idx in range(len(analysis_results), len(detail_analysis_results)):
            unpaired_details.append(detail_analysis_results[idx])
    
    else:
        # 台番号でペアリング（従来の方法）
        # グラフ結果に正規化した台番号を追加
        for result in analysis_results:
            machine_num = None
            # OCRから台番号を取得
            if result.get('ocr_data') and result['ocr_data'].get('machine_number'):
                machine_num = normalize_machine_number(result['ocr_data']['machine_number'])
            result['normalized_machine_number'] = machine_num
            
            # ペアを探す
            paired = False
            for detail in detail_analysis_results:
                # detailが辞書であることを確認
                if isinstance(detail, dict):
                    claude_data = detail.get('claude_data', {})
                    if isinstance(claude_data, dict):
                        detail_machine_num = claude_data.get('normalized_machine_number')
                        if not detail_machine_num and claude_data.get('machine_number'):
                            detail_machine_num = normalize_machine_number(claude_data['machine_number'])
                    else:
                        detail_machine_num = None
                else:
                    detail_machine_num = None
                
                if machine_num and detail_machine_num and machine_num == detail_machine_num:
                    # ペアリング成功
                    paired_results.append({
                        'graph': result,
                        'detail': detail,
                        'machine_number': machine_num
                    })
                    paired = True
                    detail['paired'] = True  # 使用済みフラグ
                    break
            
            if not paired:
                unpaired_graphs.append(result)
        
        # ペアリングされなかった詳細画像
        for detail in detail_analysis_results:
            if not detail.get('paired'):
                unpaired_details.append(detail)
    
    # プログレスバーを完了
    progress_bar.progress(1.0)
    status_text.text('✅ 全ての画像の処理が完了しました！')
    detail_text.empty()
    time.sleep(1.0)  # 完了メッセージを表示する時間
    
    # 結果を保存（ペアリング情報も含めて）
    st.session_state.analysis_results = analysis_results
    st.session_state.detail_analysis_results = detail_analysis_results
    st.session_state.paired_results = paired_results
    st.session_state.unpaired_graphs = unpaired_graphs
    st.session_state.unpaired_details = unpaired_details
    
    # Reset analysis state
    st.session_state.start_analysis = False
    st.rerun()

    # 使い方
    with st.expander("💡 使い方"):
        st.markdown("""
            1. **「Browse files」ボタン**をクリック
            2. **グラフ画像を選択**（複数選択可）
            3. **自動的に切り抜きと解析が実行されます**
            
            対応フォーマット:
            - JPG/JPEG
            - PNG
            """)

# 機能紹介
st.markdown("---")
st.markdown("### 🚀 主な機能")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("#### 📈 AIグラフ解析")
    st.markdown("AIがグラフを自動認識し、正確なデータを抽出")
with col2:
    st.markdown("#### ✂️ 自動切り抜き")
    st.markdown("グラフ領域を自動検出して最適化")
with col3:
    st.markdown("#### 💡 統計分析")
    st.markdown("最高値、最低値、初当たり等を瞬時に計算")

# 操作マニュアル
st.markdown("---")
st.markdown("### 📖 操作マニュアル")
with st.expander("使い方と注意事項を確認する"):
    st.markdown("""
    #### 🎯 本ツールについて
    このツールは **[site7](https://m.site777.jp/)のグラフデータ専用** の解析ツールです。  
    それ以外のサイトのグラフには対応していません。
    
    #### 📋 使い方
    1. **画像をアップロード**
       - 「Browse files」ボタンをクリック
       - site7のグラフ画像を選択（複数選択可）
       - 対応形式：JPG/JPEG、PNG
    
    2. **自動解析**
       - アップロード後、自動的に解析が開始されます
       - グラフの0ラインを検出し、適切な範囲で切り抜きます
       - グラフデータを抽出し、統計情報を計算します
    
    3. **結果の確認**
       - 解析結果は2列で表示されます（モバイルでは1列）
       - 各結果には以下が含まれます：
         - 解析済みグラフ画像（緑色のライン）
         - 統計情報（最高値、最低値、現在値、初当たり）
         - 元画像（折りたたみ可能）
    
    #### ⚠️ 注意事項
    - **site7専用**：他のサイトのグラフは正しく解析できません
    - **画像品質**：鮮明な画像ほど精度が向上します
    - **グラフ全体**：グラフの上下が切れていない画像を使用してください
    - **初当たり検出**：マイナス値からの100玉以上の急上昇を検出します
    
    #### 🔧 技術仕様
    - 0ライン基準：上246px、下280px（±30,000玉相当）
    - スケール：約120玉/ピクセル
    - 左右余白：120px除外
    
    #### 🆕 回転率計算機能
    - **回転率①**：初当たりまでの1000円あたり回転数
    - **回転率②**：通常時全体の1000円あたり回転数
    - OCRで読み取った累計スタートを使用して精密計算
    - 初当たりが検出されない場合は回転率①は表示されません
    """)

# エラーメッセージを表示（常に表示される場所）
if st.session_state.get('claude_errors'):
    st.markdown("### ⚠️ Claude APIエラー")
    error_container = st.container()
    with error_container:
        for error_msg in st.session_state.claude_errors:
            st.error(error_msg)

        # エラーログのダウンロードと管理ボタン
        col1, col2 = st.columns(2)
        with col1:
            # エラーログをダウンロード
            if st.button("💾 エラーログを保存", key="save_error_log"):
                import json
                from datetime import datetime

                # エラーログとセッション中のログを取得
                from modules.error_handler import get_error_logs
                session_logs = get_error_logs()

                error_data = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'display_errors': st.session_state.claude_errors,
                    'detailed_logs': session_logs
                }

                # JSONファイルとしてダウンロード
                error_json = json.dumps(error_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📥 エラーログをダウンロード",
                    data=error_json,
                    file_name=f"error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    key="download_error_log"
                )

        with col2:
            # エラーをクリアするボタン
            if st.button("🗑️ エラーをクリア", key="clear_claude_errors"):
                st.session_state.claude_errors = []
                from modules.error_handler import clear_error_logs
                clear_error_logs()
                st.rerun()

# 解析結果を表示
if 'analysis_results' in st.session_state:
    # ペアリングされた結果と個別結果を取得
    paired_results = st.session_state.get('paired_results', [])
    unpaired_graphs = st.session_state.get('unpaired_graphs', [])
    unpaired_details = st.session_state.get('unpaired_details', [])
    
    # 結果をグリッド表示
    st.markdown("### 📊 解析結果一覧")
    
    # ペアリング状況を表示
    if paired_results or unpaired_graphs:
        col1, col2, col3 = st.columns(3)
        with col1:
            if paired_results:
                st.success(f"🔗 ペアリング成功: {len(paired_results)}組")
        with col2:
            if unpaired_graphs:
                st.info(f"📊 グラフのみ: {len(unpaired_graphs)}枚")
        with col3:
            # ペアリングされなかった詳細画像は表示しない（お客様要望）
            if unpaired_details and st.session_state.get('show_unpaired_details', False):
                st.info(f"📋 単独詳細: {len(unpaired_details)}枚（非表示）")
    
    # すべての結果を統合して表示用リストを作成
    all_results = []
    
    # ペアリングされた結果を先に追加
    for paired in paired_results:
        result = paired['graph'].copy()  # グラフデータをコピー
        detail = paired['detail']
        detail_data = detail.get('claude_data', {}) if detail else {}
        
        # 出玉詳細画像データを追加
        if detail and detail.get('name'):
            # 詳細画像ファイルを探して処理済み画像を作成
            for detail_file in detail_files:
                if detail_file.name == detail['name']:
                    try:
                        detail_file.seek(0)
                        detail_img = Image.open(detail_file)
                        result['detail_image_processed'] = preprocess_detail_image(detail_img)
                        break
                    except:
                        pass
        
        # 既存のClaude分析データを上書き（ペアリングされた詳細データで）
        if detail_data:
            # 機種別の払い出し球数データも含める
            if detail_data.get('machine_payouts'):
                # すでに払い出し球数データがある場合はそのまま使用
                result['claude_analysis'] = {'success': True, 'data': detail_data}
            else:
                # 機種別払い出し球数の自動設定を削除
                result['claude_analysis'] = {'success': True, 'data': detail_data}
        result['is_paired'] = True  # ペアリングフラグを追加
        # マッチング情報を追加
        if paired.get('match_score'):
            result['match_score'] = paired['match_score']
        if paired.get('match_type'):
            result['match_type'] = paired['match_type']
        if paired.get('match_info'):
            result['match_info'] = paired['match_info']
        all_results.append(result)
    
    # 単独のグラフ結果を追加
    for graph in unpaired_graphs:
        result = graph.copy()
        result['is_paired'] = False
        all_results.append(result)
    
    # analysis_resultsを更新して既存のコードで表示
    analysis_results = all_results
    

    if not analysis_results:
        st.warning("⚠️ 表示する解析結果がありません")
        st.info(f"デバッグ情報: paired={len(paired_results)}, unpaired_graphs={len(unpaired_graphs)}, unpaired_details={len(unpaired_details)}")
    
    # 既存の解析結果を3列で表示（行ごとに処理）
    for row_idx in range(0, len(analysis_results), 3):
        cols = st.columns(3)
        
        # 各行の3つの結果を処理
        for col_idx in range(3):
            idx = row_idx + col_idx
            if idx < len(analysis_results):
                result = analysis_results[idx]
                
                with cols[col_idx]:
                    # ペアリング状態を表示
                    if result.get('is_paired'):
                        st.success("🔗 ペアリング済み", icon="✅")
                    
                    # 台番号を常に編集可能なテキストフォームで表示
                    col_num, col_input = st.columns([1, 4])
                    with col_num:
                        st.markdown(f"#### {idx + 1}.")
                    with col_input:
                        # 手動入力用のセッションステートキー
                        input_key = f"machine_input_{idx}"
                        
                        # 初期値の設定（input_keyをセッションステートのキーとして使用）
                        if input_key not in st.session_state:
                            # 初期値の決定：OCRで読み取れた場合はその値、なければファイル名
                            if result.get('ocr_data') and result['ocr_data'].get('machine_number'):
                                initial_value = result['ocr_data']['machine_number']
                            else:
                                initial_value = result['name'].rsplit('.', 1)[0]
                            st.session_state[input_key] = initial_value
                        
                        # on_changeコールバック関数（ダミー関数で再実行をトリガー）
                        def trigger_update():
                            pass  # 何もしない（Streamlitが自動的に再実行される）
                        
                        # テキスト入力フィールド（keyパラメータでセッションステートに直接保存）
                        manual_machine = st.text_input(
                            "台番号を入力",
                            key=input_key,
                            label_visibility="collapsed",
                            placeholder="台番号を入力してください",
                            on_change=trigger_update
                        )

                    # Claude AI回転マーカーを追加
                    display_img = result['overlay_image'].copy()

                    log(f"[Claude AI Marker] result keys: {list(result.keys())}")
                    log(f"[Claude AI Marker] has rotation_metrics: {result.get('rotation_metrics') is not None}")
                    log(f"[Claude AI Marker] has claude_analysis: {result.get('claude_analysis') is not None}")

                    # Claude AIの初当たり回転数がある場合、マーカーを追加
                    if result.get('rotation_metrics') and result.get('claude_analysis'):
                        rotation_metrics = result['rotation_metrics']
                        claude_analysis = result['claude_analysis']
                        spins_per_pixel = rotation_metrics.get('spins_per_pixel', 0)

                        # claude_analysisの構造: {'success': True, 'data': {...}}
                        claude_data = claude_analysis.get('data', {}) if claude_analysis.get('success') else {}
                        initial_ball_starts = claude_data.get('initial_ball_starts')

                        log(f"[Claude AI Marker] claude_data keys: {list(claude_data.keys()) if claude_data else 'None'}")
                        log(f"[Claude AI Marker] spins_per_pixel={spins_per_pixel}, initial_ball_starts={initial_ball_starts}")

                        # 必要なデータが揃っている場合のみ描画
                        if initial_ball_starts:
                            try:
                                # 初当たり回転数を整数に変換
                                initial_ball_starts = int(initial_ball_starts)

                                # ゼロラインの位置を取得（STARTマーカーと同じY座標）
                                zero_y = result.get('zero_line_y', display_img.shape[0] // 2)

                                # グラフ開始位置を取得（累計スタートマーカーでも使用）
                                first_hit_debug = result.get('first_hit_debug', {})
                                graph_info = first_hit_debug.get('graph_info', {})
                                graph_start_x = graph_info.get('graph_start_x', 0)

                                # Claude AIの初当たり回転数をピクセル位置に変換
                                # グラフ解析の位置とは独立して計算
                                if spins_per_pixel > 0:
                                    claude_x = graph_start_x + (initial_ball_starts / spins_per_pixel)
                                    log(f"[Claude AI Marker] Calculated position: claude_x={claude_x:.1f}px (start={graph_start_x}px, spins={initial_ball_starts}, scale={spins_per_pixel:.4f})")
                                else:
                                    claude_x = None
                                    log(f"[Claude AI Marker] Cannot calculate: spins_per_pixel={spins_per_pixel}")

                                if claude_x is None:
                                    raise ValueError("Could not determine marker position")

                                log(f"[Claude AI Marker] claude_x={claude_x}, zero_y={zero_y}, img_size={display_img.shape}")

                                # 画像範囲内かチェック
                                if 0 <= claude_x < display_img.shape[1] and 0 <= zero_y < display_img.shape[0]:
                                    log(f"[Claude AI Marker] Drawing marker at ({int(claude_x)}, {zero_y})")
                                    # マーカーを描画（赤色）
                                    cv2.circle(display_img, (int(claude_x), zero_y), 5, (0, 0, 255), -1)  # 塗りつぶし
                                    cv2.circle(display_img, (int(claude_x), zero_y), 6, (0, 0, 200), 2)   # 外枠

                                    # ラベルを描画
                                    label_text = f'AI HIT: {initial_ball_starts}'
                                    # ラベルの背景（白）
                                    label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                                    label_x = int(claude_x) - label_size[0] // 2
                                    label_y = zero_y - 20
                                    cv2.rectangle(display_img,
                                                (label_x - 2, label_y - label_size[1] - 2),
                                                (label_x + label_size[0] + 2, label_y + 2),
                                                (255, 255, 255), -1)
                                    # テキスト（赤）
                                    cv2.putText(display_img, label_text,
                                              (label_x, label_y),
                                              cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1, cv2.LINE_AA)
                                else:
                                    log(f"[Claude AI Marker] Out of bounds - not drawing")

                                # Claude AIの累計スタート回数（グラフ最後の位置）のマーカーを追加
                                total_rotations = claude_data.get('total_rotations', 0)
                                if total_rotations > 0:
                                    # 累計スタート回数の位置を計算
                                    total_rotations_x = graph_start_x + (total_rotations / spins_per_pixel)

                                    log(f"[Total Rotations Marker] total_rotations={total_rotations}, total_rotations_x={total_rotations_x}")

                                    if 0 <= total_rotations_x < display_img.shape[1] and 0 <= zero_y < display_img.shape[0]:
                                        log(f"[Total Rotations Marker] Drawing marker at ({int(total_rotations_x)}, {zero_y})")
                                        # マーカーを描画（緑色）
                                        cv2.circle(display_img, (int(total_rotations_x), zero_y), 5, (0, 255, 0), -1)  # 塗りつぶし
                                        cv2.circle(display_img, (int(total_rotations_x), zero_y), 6, (0, 200, 0), 2)   # 外枠

                                        # ラベルを描画
                                        total_label_text = f'OCR LAST: {total_rotations}'
                                        # ラベルの背景（白）
                                        total_label_size = cv2.getTextSize(total_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                                        total_label_x = int(total_rotations_x) - total_label_size[0] // 2
                                        total_label_y = zero_y + 35  # 初当ラベルの下に配置
                                        cv2.rectangle(display_img,
                                                    (total_label_x - 2, total_label_y - total_label_size[1] - 2),
                                                    (total_label_x + total_label_size[0] + 2, total_label_y + 2),
                                                    (255, 255, 255), -1)
                                        # テキスト（緑）
                                        cv2.putText(display_img, total_label_text,
                                                  (total_label_x, total_label_y),
                                                  cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 150, 0), 1, cv2.LINE_AA)
                                    else:
                                        log(f"[Total Rotations Marker] Out of bounds - not drawing")

                                # AI基準のグラフ終点マーカーを追加
                                rotation_metrics = result.get('rotation_metrics', {})
                                ai_based_spins_per_pixel = rotation_metrics.get('ai_based_spins_per_pixel', 0)
                                ai_based_cumulative_total_spins = rotation_metrics.get('ai_based_cumulative_total_spins', 0)

                                if ai_based_cumulative_total_spins > 0 and ai_based_spins_per_pixel > 0 and total_rotations > 0:
                                    # AI基準のスケールでOCR累計回転数がどこに到達するかを計算
                                    ai_total_x = graph_start_x + (total_rotations / ai_based_spins_per_pixel)

                                    log(f"[AI Total Rotations Marker] ocr_total={total_rotations}, ai_spp={ai_based_spins_per_pixel:.4f}, ai_total_x={ai_total_x}")

                                    if 0 <= ai_total_x < display_img.shape[1] and 0 <= zero_y < display_img.shape[0]:
                                        log(f"[AI Total Rotations Marker] Drawing marker at ({int(ai_total_x)}, {zero_y})")
                                        # マーカーを描画（青色）
                                        cv2.circle(display_img, (int(ai_total_x), zero_y), 5, (255, 100, 0), -1)  # 塗りつぶし
                                        cv2.circle(display_img, (int(ai_total_x), zero_y), 6, (200, 80, 0), 2)   # 外枠

                                        # ラベルを描画
                                        ai_label_text = f'AI LAST: {total_rotations} (spp:{ai_based_spins_per_pixel:.2f})'
                                        # ラベルの背景（白）
                                        ai_label_size = cv2.getTextSize(ai_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                                        ai_label_x = int(ai_total_x) - ai_label_size[0] // 2
                                        ai_label_y = zero_y + 60  # OCR基準ラベルの下に配置
                                        cv2.rectangle(display_img,
                                                    (ai_label_x - 2, ai_label_y - ai_label_size[1] - 2),
                                                    (ai_label_x + ai_label_size[0] + 2, ai_label_y + 2),
                                                    (255, 255, 255), -1)
                                        # テキスト（青）
                                        cv2.putText(display_img, ai_label_text,
                                                  (ai_label_x, ai_label_y),
                                                  cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 80, 0), 1, cv2.LINE_AA)
                                    else:
                                        log(f"[AI Total Rotations Marker] Out of bounds - not drawing")

                                # 全ての大当たり（谷）のマーカーを描画
                                all_jackpots = result.get('all_jackpots', [])
                                if all_jackpots and len(all_jackpots) > 0:
                                    log(f"[All Jackpots Markers] Drawing {len(all_jackpots)} markers")

                                    # マーカーの色（異なる色で区別）
                                    marker_colors = [
                                        (255, 0, 255),  # マゼンタ（1回目）
                                        (255, 128, 0),  # オレンジ（2回目）
                                        (0, 255, 255)   # シアン（3回目）
                                    ]

                                    for idx, jackpot in enumerate(all_jackpots):
                                        jackpot_index = jackpot.get('index', -1)
                                        jackpot_value = jackpot.get('value', 0)

                                        if jackpot_index >= 0:
                                            # 回転数を計算
                                            jackpot_x_px = jackpot.get('x', jackpot_index * 2 + 48)
                                            relative_x = jackpot_x_px - graph_start_x
                                            jackpot_spins = int(relative_x * spins_per_pixel)

                                            # マーカーの色を選択
                                            color = marker_colors[idx % len(marker_colors)]

                                            if 0 <= jackpot_x_px < display_img.shape[1] and 0 <= zero_y < display_img.shape[0]:
                                                log(f"[All Jackpots Markers] {idx+1}回目: x={jackpot_x_px}px, spins={jackpot_spins}, value={jackpot_value:.1f}玉")

                                                # マーカーを描画
                                                cv2.circle(display_img, (int(jackpot_x_px), zero_y), 6, color, -1)  # 塗りつぶし
                                                cv2.circle(display_img, (int(jackpot_x_px), zero_y), 7, tuple([c//2 for c in color]), 2)  # 外枠（暗い色）

                                                # ラベルを描画
                                                if idx == 0:
                                                    label_text = f'FIRST HIT: {jackpot_spins}'
                                                else:
                                                    label_text = f'{idx+1}: {jackpot_spins}'
                                                label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                                                label_x = int(jackpot_x_px) - label_size[0] // 2
                                                label_y = zero_y - 40 - (idx % 2) * 20  # 交互に配置

                                                # ラベルの背景（白）
                                                cv2.rectangle(display_img,
                                                            (label_x - 2, label_y - label_size[1] - 2),
                                                            (label_x + label_size[0] + 2, label_y + 2),
                                                            (255, 255, 255), -1)
                                                # テキスト
                                                cv2.putText(display_img, label_text,
                                                          (label_x, label_y),
                                                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

                                # AI基準の全ての大当たりマーカーを描画
                                if all_jackpots and len(all_jackpots) > 0 and ai_based_spins_per_pixel > 0:
                                    log(f"[AI Jackpots Markers] Drawing {len(all_jackpots)} AI-based markers")

                                    # マーカーの色（薄い青系の色で区別）
                                    ai_marker_colors = [
                                        (255, 200, 150),  # ライトブルー（1回目）
                                        (255, 180, 100),  # ライトシアン（2回目）
                                        (255, 220, 180)   # ペールブルー（3回目）
                                    ]

                                    for idx, jackpot in enumerate(all_jackpots):
                                        jackpot_index = jackpot.get('index', -1)
                                        jackpot_value = jackpot.get('value', 0)

                                        if jackpot_index >= 0:
                                            # AI基準で回転数を計算
                                            jackpot_x_px = jackpot.get('x', jackpot_index * 2 + 48)
                                            relative_x = jackpot_x_px - graph_start_x
                                            ai_jackpot_spins = int(relative_x * ai_based_spins_per_pixel)

                                            # マーカーの色を選択
                                            color = ai_marker_colors[idx % len(ai_marker_colors)]

                                            if 0 <= jackpot_x_px < display_img.shape[1] and 0 <= zero_y < display_img.shape[0]:
                                                log(f"[AI Jackpots Markers] {idx+1}回目: x={jackpot_x_px}px, ai_spins={ai_jackpot_spins}, value={jackpot_value:.1f}玉")

                                                # マーカーを描画（小さい円で区別）
                                                cv2.circle(display_img, (int(jackpot_x_px), zero_y), 4, color, -1)  # 塗りつぶし（小さめ）
                                                cv2.circle(display_img, (int(jackpot_x_px), zero_y), 5, tuple([c//2 for c in color]), 1)  # 外枠（細め）

                                                # ラベルを描画（下側に配置してOCR基準と区別）
                                                label_text = f'{idx+1}(AI): {ai_jackpot_spins}'
                                                label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                                                label_x = int(jackpot_x_px) - label_size[0] // 2
                                                label_y = zero_y + 45 + (idx % 2) * 15  # 下側に配置

                                                # ラベルの背景（白）
                                                cv2.rectangle(display_img,
                                                            (label_x - 2, label_y - label_size[1] - 2),
                                                            (label_x + label_size[0] + 2, label_y + 2),
                                                            (255, 255, 255), -1)
                                                # テキスト（小さめ）
                                                cv2.putText(display_img, label_text,
                                                          (label_x, label_y),
                                                          cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)

                            except (ValueError, TypeError) as e:
                                # エラーが発生した場合は元の画像を使用
                                log(f"[Claude AI Marker] マーカー描画エラー: {str(e)}")
                                pass

                    # マーカー描画後のdisplay_imgをoverlay_imageに保存（ZIPダウンロード用）
                    result['overlay_image'] = display_img

                    # 解析結果画像
                    st.image(display_img, use_column_width=True)

                    # 出玉詳細画像（ペアリング済みの場合表示）
                    if result.get('detail_image_processed') is not None:
                        with st.expander("📊 ペアリングされた出玉詳細画像", expanded=False):
                            st.image(result['detail_image_processed'], use_column_width=True)
                            if result.get('is_paired'):
                                st.caption("✅ この詳細画像のデータを使用して計算しています")
                                # デバッグモードでマッチング情報を表示
                                if st.session_state.get('show_ocr_debug', False):
                                    if result.get('match_type') == 'perfect_match':
                                        st.caption(f"✅ 完全一致ペアリング: {result.get('match_info', '')}")
                                    elif result.get('match_score'):
                                        st.caption(f"🎯 マッチングスコア: {result['match_score']}点")
                            else:
                                st.caption("黒枠検出 + overlay.png + 50%切り抜き適用済み")
                    
                    # 元画像を折りたたみ可能に
                    with st.expander("📷 元画像を表示"):
                        st.image(result['original_image'], use_column_width=True)
                    
                    # 成功時は統計情報を表示（解析結果の下に縦に並べる）
                    if result['success']:
                        # Claude API解析結果の表示（統計情報の上に配置）
                        if result.get('claude_analysis'):
                            if result['claude_analysis'] and result['claude_analysis']['success']:
                                claude_data = result['claude_analysis'].get('data')
                                if claude_data:
                                    # カード風のHTMLスタイル
                                    html_content = '<div class="stat-card">'
                                    html_content += '<div class="ocr-title">🤖 Claude AI解析結果</div>'
                                
                                # 機種名と日付をカード内に含める
                                if claude_data.get('machine_name'):
                                    html_content += f'''
                                    <div class="stat-item">
                                        <span class="stat-label">🎰 機種名</span>
                                        <span class="stat-value" style="font-size: 1.1em;">{claude_data['machine_name']}</span>
                                    </div>'''
                                
                                if claude_data.get('date'):
                                    html_content += f'''
                                    <div class="stat-item">
                                        <span class="stat-label">📅 日付</span>
                                        <span class="stat-value">{claude_data['date']}</span>
                                    </div>'''
                                
                                # 台番号
                                if claude_data.get('machine_number'):
                                    html_content += f'''
                                    <div class="stat-item">
                                        <span class="stat-label">🎯 台番号</span>
                                        <span class="stat-value">{claude_data['machine_number']}</span>
                                    </div>'''
                                
                                # 大当たり情報（確率表示なし）
                                if claude_data.get('total_jackpots') is not None:
                                    html_content += f'''
                                    <div class="stat-item">
                                        <span class="stat-label">🎯 大当り回数</span>
                                        <span class="stat-value positive">{claude_data['total_jackpots']}回</span>
                                    </div>'''
                                
                                if claude_data.get('first_jackpots') is not None:
                                    html_content += f'''
                                    <div class="stat-item">
                                        <span class="stat-label">🎯 初当り回数</span>
                                        <span class="stat-value positive">{claude_data['first_jackpots']}回</span>
                                    </div>'''
                                    
                                # 機種別の払い出し球数を取得
                                machine_payouts = None
                                

                                if st.session_state.get('show_ocr_debug', False):
                                    st.write("🔍 **払い出し球数デバッグ情報:**")
                                    st.write(f"  - machine_payouts: {claude_data.get('machine_payouts')}")
                                
                                # claude_dataに保存されているものを確認
                                if claude_data.get('machine_payouts'):
                                    machine_payouts = claude_data['machine_payouts']
                                # 機種名から取得を試みる
                                # 常にユーザー設定を使用
                                big_balls = get_settings().get('big_jackpot_balls', 1500)
                                middle_balls = get_settings().get('middle_jackpot_balls', 750)
                                small_balls = get_settings().get('small_jackpot_balls', 450)
                                    
                                # 大当たり内訳（出玉数も表示） - 常に表示
                                # 超中小の内訳がない場合、total_jackpotsから推定
                                if (claude_data.get('big_jackpots') is None and 
                                    claude_data.get('medium_jackpots') is None and 
                                    claude_data.get('small_jackpots') is None):
                                    # total_jackpotsがある場合、すべて超として扱う
                                    total_jackpots = claude_data.get('total_jackpots', 0)
                                    big_j = total_jackpots
                                    medium_j = 0
                                    small_j = 0
                                else:
                                    # 個別の値が取得できている場合はそれを使用
                                    big_j = claude_data.get('big_jackpots') if claude_data.get('big_jackpots') is not None else 0
                                    medium_j = claude_data.get('medium_jackpots') if claude_data.get('medium_jackpots') is not None else 0
                                    small_j = claude_data.get('small_jackpots') if claude_data.get('small_jackpots') is not None else 0
                                    
                                # 超・中・小（1行表示）
                                html_content += f'''
                                <div class="stat-item">
                                    <span class="stat-label">大当り内訳</span>
                                    <span class="stat-value">超{big_j} 中{medium_j} 小{small_j}</span>
                                </div>'''
                                    

                                if st.session_state.get('show_ocr_debug', False):
                                    if (claude_data.get('big_jackpots') is None and 
                                        claude_data.get('medium_jackpots') is None and 
                                        claude_data.get('small_jackpots') is None):
                                        html_content += f'''
                                        <div class="stat-item" style="font-size: 0.85em; color: #ff6b6b;">
                                            <span>⚠️ 超中小データ未取得</span>
                                        </div>'''
                                    
                                # 回転数情報
                                if claude_data.get('total_rotations') is not None:
                                    html_content += f'''
                                    <div class="stat-item">
                                        <span class="stat-label">📊 累計スタート</span>
                                        <span class="stat-value">{claude_data['total_rotations']:,}回</span>
                                    </div>'''
                                
                                if claude_data.get('normal_rotations') is not None:
                                    # 数値に変換してフォーマット
                                    try:
                                        normal_rot = int(claude_data['normal_rotations'])
                                        html_content += f'''
                                        <div class="stat-item">
                                            <span class="stat-label">🔄 通常回転数</span>
                                            <span class="stat-value">{normal_rot:,}回</span>
                                        </div>'''
                                    except (ValueError, TypeError):
                                        # 数値変換できない場合はそのまま表示
                                        html_content += f'''
                                        <div class="stat-item">
                                            <span class="stat-label">🔄 通常回転数</span>
                                            <span class="stat-value">{claude_data['normal_rotations']}回</span>
                                        </div>'''
                                
                                # 回転数情報
                                if claude_data.get('spin_count') is not None:
                                    try:
                                        spin_cnt = int(claude_data['spin_count'])
                                        html_content += f'''
                                        <div class="stat-item">
                                            <span class="stat-label">🎲 累計スタート</span>
                                            <span class="stat-value">{spin_cnt:,}回</span>
                                        </div>'''
                                    except (ValueError, TypeError):
                                        html_content += f'''
                                        <div class="stat-item">
                                            <span class="stat-label">🎲 累計スタート</span>
                                            <span class="stat-value">{claude_data['spin_count']}回</span>
                                        </div>'''

                                if claude_data.get('normal_spins') is not None:
                                    try:
                                        normal_spn = int(claude_data['normal_spins'])
                                        html_content += f'''
                                        <div class="stat-item">
                                            <span class="stat-label">🔄 通常回転数</span>
                                            <span class="stat-value">{normal_spn:,}回</span>
                                        </div>'''
                                    except (ValueError, TypeError):
                                        html_content += f'''
                                        <div class="stat-item">
                                            <span class="stat-label">🔄 通常回転数</span>
                                            <span class="stat-value">{claude_data['normal_spins']}回</span>
                                        </div>'''

                                # 現在回転数はマスクで隠れているため削除
                                    
                                # その他情報
                                if claude_data.get('max_balls') is not None:
                                    try:
                                        max_b = int(claude_data['max_balls'])
                                        html_content += f'''
                                        <div class="stat-item">
                                            <span class="stat-label">💰 最高出玉</span>
                                            <span class="stat-value positive">{max_b:,}玉</span>
                                        </div>'''
                                    except (ValueError, TypeError):
                                        html_content += f'''
                                        <div class="stat-item">
                                            <span class="stat-label">💰 最高出玉</span>
                                            <span class="stat-value positive">{claude_data['max_balls']}玉</span>
                                        </div>'''

                                if claude_data.get('initial_ball_starts') is not None:
                                    try:
                                        init_starts = int(claude_data['initial_ball_starts'])
                                        html_content += f'''
                                        <div class="stat-item">
                                            <span class="stat-label">🎱 初回特賞スタート</span>
                                            <span class="stat-value">{init_starts:,}回</span>
                                        </div>'''
                                    except (ValueError, TypeError):
                                        html_content += f'''
                                        <div class="stat-item">
                                            <span class="stat-label">🎱 初回特賞スタート</span>
                                            <span class="stat-value">{claude_data['initial_ball_starts']}回</span>
                                        </div>'''
                                    
                                # 総払い出し球数をAIから計算
                                total_payout_from_ai = 0
                                # 超中小の内訳を使用した計算（上記で設定したbig_j, medium_j, small_jを使用）
                                total_payout_from_ai = big_j * big_balls + medium_j * middle_balls + small_j * small_balls

                                if total_payout_from_ai > 0:
                                    html_content += f'''
                                    <div class="stat-item">
                                        <span class="stat-label">💰 総払い出し球数（AI計算）</span>
                                        <span class="stat-value">{total_payout_from_ai:,}玉</span>
                                    </div>'''

                                html_content += '</div>'

                                # HTMLを表示
                                st.markdown(html_content, unsafe_allow_html=True)
                            else:
                                # APIエラーの場合
                                if result['claude_analysis']:
                                    with st.expander("🤖 Claude AI解析結果（エラー）", expanded=False):
                                        st.error(f"解析エラー: {result['claude_analysis'].get('error', '不明なエラー')}")
                        elif result and result.get('detail_image_processed') and not st.session_state.get('claude_api_key'):
                            # APIキーが設定されていない場合のメッセージ
                            with st.expander("🤖 Claude AI解析"):
                                st.info("Claude APIキーが設定されていません。管理者ログインしてAPIキーを設定してください。")
                        # 統計情報をカード風に表示（site7データと同じデザイン）
                        st.markdown("""
                <style>
                .stat-card {
                    background-color: #e8f4f8;
                    padding: 15px;
                    border-radius: 10px;
                    margin-top: 10px;
                    border: 1px solid #bee5eb;
                }
                .stat-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 5px 0;
                    border-bottom: 1px solid #d1ecf1;
                }
                .stat-item:last-child {
                    border-bottom: none;
                }
                .stat-label {
                    color: #0c5460;
                    font-weight: 500;
                }
                .stat-value {
                    font-weight: bold;
                    color: #0c5460;
                }
                .stat-value.positive {
                    color: #28a745;
                }
                .stat-value.negative {
                    color: #dc3545;
                }
                .stat-value.zero {
                    color: #6c757d;
                }
                </style>
                """, unsafe_allow_html=True)

                    # 値に応じて色分けするためのクラスを決定
                    def get_value_class(val):
                        if val > 0:
                            return "positive"
                        elif val < 0:
                            return "negative"
                        else:
                            return "zero"

                    unit = get_unit(st.session_state.get('game_type', 'パチンコ'))
                    first_hit_text = f"{result['first_hit_val']:,}{unit}" if result['first_hit_val'] is not None else "なし"
                    first_hit_class = get_value_class(result['first_hit_val']) if result['first_hit_val'] is not None else ""

                    # 補正係数の表示を準備（非表示にする）
                    correction_info = ""
                    
                    # 回転率データの準備（パチンコのみ）
                    rotation_html = ""
                    rotation_detail = ""
                    normal_usage_html = ""  # 通常時使用球数の表示用
                    # デフォルト値をセット
                    result['display_rotation_rate_1'] = '-'
                    result['display_rotation_rate_2'] = '-'
                    result['display_normal_balls'] = 0
                    if st.session_state.game_type == 'パチンコ':
                        # 優先度に基づいてデータを取得
                        prioritized_data = get_prioritized_data(result)
                        
                        # 回転率①の計算（グラフ解析のみ）
                        rotation_rate_1_calculated = False
                        rotation_metrics = result.get('rotation_metrics', {})
                        graph_first_hit_spins = rotation_metrics.get('first_hit_spins', 0)
                        graph_first_hit_balls = rotation_metrics.get('first_hit_balls', 0)

                        if graph_first_hit_spins > 0 and graph_first_hit_balls > 0:
                            rotation_rate_1 = (graph_first_hit_spins / graph_first_hit_balls) * 250
                            warning = " ⚠️" if rotation_rate_1 < 10 or rotation_rate_1 > 35 else ""
                            rotation_html += f'<div class="stat-item"><span class="stat-label">📊 回転率①</span><span class="stat-value positive">{rotation_rate_1:.1f}回/千円{warning}</span></div>'

                            rotation_detail += f'<div style="font-size: 0.8em; color: #666; margin-left: 20px;">→ 初当たりまで: {graph_first_hit_spins}回転 ÷ {int(graph_first_hit_balls):,}{unit}使用</div>'

                            rotation_rate_1_calculated = True
                            result['display_rotation_rate_1'] = f"{rotation_rate_1:.1f}{warning}"
                        else:
                            rotation_html += f'<div class="stat-item"><span class="stat-label">📊 回転率①</span><span class="stat-value">-</span></div>'
                            result['display_rotation_rate_1'] = '-'
                            
                        # 回転率②の計算
                        rotation_rate_2_calculated = False

                        # 優先順位: 1. Claude AIデータ, 2. rotation_metricsの通常時回転数
                        normal_rotations = prioritized_data.get('normal_rotations')
                        if not normal_rotations or normal_rotations == 0:
                            # rotation_metricsから通常時回転数を取得（累計 - 大当たり中）
                            rotation_metrics = result.get('rotation_metrics', {})
                            normal_decline_spins = rotation_metrics.get('normal_decline_spins', 0)
                            # 文字列の場合は整数に変換
                            try:
                                normal_rotations = int(normal_decline_spins) if normal_decline_spins else 0
                            except (ValueError, TypeError):
                                normal_rotations = 0

                        # 型を確実に整数にする
                        try:
                            normal_rotations = int(normal_rotations) if normal_rotations else 0
                        except (ValueError, TypeError):
                            normal_rotations = 0

                        if normal_rotations > 0:
                            # 総払い出し球数を計算
                            total_payout = 0
                            
                            # 機種別の払い出し球数を取得
                            if prioritized_data.get('machine_payouts'):
                                machine_payouts = prioritized_data['machine_payouts']
                                big_balls = machine_payouts.get('big_jackpot_balls', 1500)
                                middle_balls = machine_payouts.get('middle_jackpot_balls', 750)
                                small_balls = machine_payouts.get('small_jackpot_balls', 450)
                            else:
                                # デフォルト値を使用
                                big_balls = get_settings().get('big_jackpot_balls', 1500)
                                middle_balls = get_settings().get('middle_jackpot_balls', 750)
                                small_balls = get_settings().get('small_jackpot_balls', 450)
                            
                            # 通常時使用球数の計算
                            # 優先順位: 1. グラフ下降累積, 2. 初当たり使用球数
                            normal_balls = result.get('total_decline_balls', 0)
                            if normal_balls == 0:
                                # フォールバック: 初当たり使用球数を使用
                                normal_balls = result.get('first_hit_used_balls', 0)

                            if normal_balls > 0:
                                rotation_rate_2 = (normal_rotations / normal_balls) * 250
                                warning = " ⚠️" if rotation_rate_2 < 10 or rotation_rate_2 > 30 else ""
                                rotation_html += f'<div class="stat-item"><span class="stat-label">📊 回転率②</span><span class="stat-value positive">{rotation_rate_2:.1f}回/千円{warning}</span></div>'
                                rotation_detail += f'<div style="font-size: 0.8em; color: #666; margin-left: 20px;">→ 通常時: {normal_rotations}回転 ÷ {int(normal_balls):,}{unit}使用</div>'
                                rotation_rate_2_calculated = True
                                # 結果に保存
                                result['display_rotation_rate_2'] = f"{rotation_rate_2:.1f}{warning}"
                                result['display_normal_balls'] = int(normal_balls)
                                
                                # 通常時使用球数のHTML準備
                                normal_usage_html = f'''<div class="stat-item">
                                    <span class="stat-label">🎮 通常時使用球数</span>
                                    <span class="stat-value">{int(normal_balls):,}{unit}</span>
                                </div>'''
                                

                                if st.session_state.get('show_ocr_debug', False) and normal_balls > 0:
                                    normal_usage_html += f'''
                                    <div style="font-size: 0.85em; color: #666; margin-left: 20px;">
                                        <span>📊 グラフ下降累積により計算</span>
                                    </div>'''
                        
                        if not rotation_rate_2_calculated:
                            rotation_html += f'<div class="stat-item"><span class="stat-label">📊 回転率②</span><span class="stat-value">-</span></div>'
                            result['display_rotation_rate_2'] = '-'
                        
                    
                    # 初当たり関連のHTMLを条件分岐で生成
                    first_hit_html = ""
                    if st.session_state.game_type == 'パチンコ':
                        # グラフ解析から計算された初当たり回転数と累計スタート数を使用
                        rotation_metrics = result.get('rotation_metrics') or {}
                        first_hit_spins = rotation_metrics.get('first_hit_spins', 0)
                        cumulative_total_spins = rotation_metrics.get('cumulative_total_spins', 0)

                        # グラフ解析結果をそのまま使用（Claude AI値での上書きはしない）
                        first_hit_html = f'<div class="stat-item"><span class="stat-label">🎰 初当たり{unit}数</span><span class="stat-value {first_hit_class}">{first_hit_text}</span></div>'
                        first_hit_html += f'<div class="stat-item"><span class="stat-label">🎲 初当たり回転数</span><span class="stat-value">{first_hit_spins:,}回</span></div>'
                        first_hit_html += f'<div class="stat-item"><span class="stat-label">📊 累計スタート（グラフ）</span><span class="stat-value">{cumulative_total_spins:,}回</span></div>'
                    
                    # 大当り回数の計算（グラフから検出した回数を使用）
                    if st.session_state.game_type == 'パチンコ':
                        # グラフから検出した大当たり回数を使用
                        jackpot_count = result.get('jackpot_count', 0)
                        jackpot_label = "大当り回数（グラフ）"
                    else:
                        # パチスロの場合もグラフから検出
                        jackpot_count = result.get('jackpot_count', 0)
                        jackpot_label = "大当り回数"
                    
                    # HTMLコンテンツを組み立て
                    # 解析精度を取得して表示
                    pixel_step = get_settings().get('pixel_step', 2)
                    precision_label = f"[{pixel_step}px間隔]"

                    html_content = f"""
                    <div class="stat-card">
                        <div style="font-size: 1.1em; font-weight: bold; color: #17a2b8; margin-bottom: 10px;">
                            📊 グラフ解析結果 {precision_label}
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">🎯 現在値</span>
                            <span class="stat-value {get_value_class(result['current_val'])}">{result['current_val']:,}{unit}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">📈 最高値</span>
                            <span class="stat-value {get_value_class(result['max_val'])}">{result['max_val']:,}{unit}</span>
                        </div>"""
                    
                    # OCR最大値とのギャップを表示
                    ocr_max_value = None
                    if result.get('ocr_data') and result['ocr_data'].get('max_value'):
                        try:
                            ocr_max_value = int(result['ocr_data']['max_value'])
                            gap = result['max_val'] - ocr_max_value
                            gap_percent = (gap / ocr_max_value * 100) if ocr_max_value != 0 else 0
                            gap_class = "positive" if gap >= 0 else "negative"
                            
                            html_content += f"""
                        <div class="stat-item" style="background-color: #f0f0f0;">
                            <span class="stat-label">📊 最大値ギャップ</span>
                            <span class="stat-value {gap_class}">{gap:+,}{unit} ({gap_percent:+.1f}%)</span>
                        </div>"""
                        except (ValueError, TypeError):
                            pass
                    
                    html_content += f"""
                        <div class="stat-item">
                            <span class="stat-label">📉 最低値</span>
                            <span class="stat-value {get_value_class(result['min_val'])}">{result['min_val']:,}{unit}</span>
                        </div>
                        """
                    
                    # パチンコの場合のみ初当たり情報を追加
                    if st.session_state.game_type == 'パチンコ':
                        html_content += first_hit_html
                    
                    # 残りの統計情報を追加
                    html_content += f'<div class="stat-item"><span class="stat-label">🎯 {jackpot_label}</span><span class="stat-value positive">{jackpot_count}回</span></div>'
                    
                    # 初当たり回数（グラフ解析から取得）
                    if st.session_state.game_type == 'パチンコ':
                        first_hit_count = 0
                        # グラフ解析データから取得
                        if result.get('first_jackpot_count') is not None:
                            first_hit_count = result['first_jackpot_count']

                        if first_hit_count > 0:
                            html_content += f'<div class="stat-item"><span class="stat-label">🎰 初当たり回数</span><span class="stat-value positive">{first_hit_count}回</span></div>'

                    # 総獲得球数の計算
                    # Claude AIから総払い出し球数が取得できている場合は「総払い出し - 現在値」で計算
                    total_earned_balls = 0
                    if result.get('claude_analysis') and result['claude_analysis'].get('success'):
                        claude_data = result['claude_analysis'].get('data', {})
                        if claude_data:
                            # 総払い出し球数をAIから計算
                            big_j = claude_data.get('big_jackpots', 0) or 0
                            medium_j = claude_data.get('medium_jackpots', 0) or 0
                            small_j = claude_data.get('small_jackpots', 0) or 0

                            # 機種別の払い出し球数を取得
                            if claude_data.get('machine_payouts'):
                                big_balls = claude_data['machine_payouts'].get('big_jackpot_balls', 1500)
                                middle_balls = claude_data['machine_payouts'].get('middle_jackpot_balls', 750)
                                small_balls = claude_data['machine_payouts'].get('small_jackpot_balls', 450)
                            else:
                                big_balls = get_settings().get('big_jackpot_balls', 1500)
                                middle_balls = get_settings().get('middle_jackpot_balls', 750)
                                small_balls = get_settings().get('small_jackpot_balls', 450)

                            total_payout = big_j * big_balls + medium_j * middle_balls + small_j * small_balls

                            # 現在値を取得
                            current_value = result.get('current_value', 0)

                            # 総獲得玉数 = 総払い出し球数 - 現在値
                            if total_payout > 0:
                                total_earned_balls = total_payout - current_value

                    # Claude AIデータがない場合はグラフから計算した値を使用
                    if total_earned_balls == 0:
                        total_earned_balls = result.get("total_jackpot_balls_graph", result.get("total_jackpot_balls", 0))

                    html_content += f'<div class="stat-item"><span class="stat-label">💰 総獲得{unit}数</span><span class="stat-value positive">{total_earned_balls:,}{unit}</span></div>'
                    
                    if correction_info:
                        html_content += correction_info
                    
                    # stat-cardを閉じる
                    html_content += '</div>'
                    
                    st.markdown(html_content, unsafe_allow_html=True)
                    
                    # 回転率データを別カードで表示（パチンコのみ）
                    if st.session_state.game_type == 'パチンコ' and (rotation_html or normal_usage_html):
                        rotation_card_content = f"""
                        <div class="stat-card" style="margin-top: 10px;">
                            <div style="font-size: 1.1em; font-weight: bold; color: #28a745; margin-bottom: 10px;">
                                📊 回転率分析
                            </div>
                        """
                        
                        # 回転率データを追加
                        if rotation_html:
                            rotation_card_content += rotation_html
                        if rotation_detail:
                            rotation_card_content += rotation_detail
                        
                        # 通常時使用球数を追加
                        if normal_usage_html:
                            rotation_card_content += normal_usage_html
                        
                        rotation_card_content += '</div>'
                        st.markdown(rotation_card_content, unsafe_allow_html=True)

                    # OCRデータがある場合は表示（すべてNoneでも構造は表示）
                    if result.get('ocr_data') is not None:
                        ocr = result['ocr_data']
                        st.markdown("""
                        <style>
                        .ocr-card {
                            background-color: #e8f4f8;
                            padding: 15px;
                            border-radius: 10px;
                            margin-top: 10px;
                            border: 1px solid #bee5eb;
                        }
                        .ocr-title {
                            color: #17a2b8;
                            font-weight: bold;
                            margin-bottom: 10px;
                        }
                        .ocr-item {
                            display: flex;
                            justify-content: space-between;
                            padding: 5px 0;
                            border-bottom: 1px solid #d1ecf1;
                        }
                        .ocr-item:last-child {
                            border-bottom: none;
                        }
                        .ocr-label {
                            color: #0c5460;
                            font-weight: 500;
                        }
                        .ocr-value {
                            font-weight: bold;
                            color: #0c5460;
                        }
                        </style>
                        """, unsafe_allow_html=True)

                        ocr_html = '<div class="ocr-card"><div class="ocr-title">📱 site7データ</div>'

                        # 台番号（デバッグ情報付き）
                        if ocr.get('machine_number'):
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">🔢 台番号</span><span class="ocr-value">{ocr["machine_number"]}</span></div>'
                        else:
                            # 台番号が取得できない場合
                            ocr_html += '<div class="ocr-item"><span class="ocr-label">🔢 台番号</span><span class="ocr-value" style="color: #999;">未検出</span></div>'

                        # 遊技データ
                        if ocr.get('total_start'):
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">🎲 累計スタート</span><span class="ocr-value">{ocr["total_start"]}</span></div>'
                        if ocr.get('jackpot_count'):
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">🎊 大当り回数</span><span class="ocr-value">{ocr["jackpot_count"]}回</span></div>'
                        if ocr.get('first_hit_count'):
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">🎯 初当り回数</span><span class="ocr-value">{ocr["first_hit_count"]}回</span></div>'
                        if ocr.get('current_start'):
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">📊 スタート</span><span class="ocr-value">{ocr["current_start"]}</span></div>'
                        if ocr.get('jackpot_probability'):
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">📈 大当り確率</span><span class="ocr-value">{ocr["jackpot_probability"]}</span></div>'
                        if ocr.get('max_payout'):
                            unit_label = "玉" if st.session_state.game_type == 'パチンコ' else "枚"
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">💰 最高出{unit_label}</span><span class="ocr-value">{ocr["max_payout"]}{unit_label}</span></div>'
                        if ocr.get('max_value'):
                            unit_label = "玉" if st.session_state.game_type == 'パチンコ' else "枚"
                            ocr_html += f'<div class="ocr-item"><span class="ocr-label">📊 最大値</span><span class="ocr-value">{ocr["max_value"]}{unit_label}</span></div>'
                        
                        # パチスロ特有のデータ表示
                        if st.session_state.game_type == 'パチスロ':
                            if ocr.get('total_games'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">🎮 累計ゲーム</span><span class="ocr-value">{ocr["total_games"]}回</span></div>'
                            if ocr.get('bb_count'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">🅱️ BB回数</span><span class="ocr-value">{ocr["bb_count"]}回</span></div>'
                            if ocr.get('bb_probability'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">📊 BB確率</span><span class="ocr-value">{ocr["bb_probability"]}</span></div>'
                            if ocr.get('rb_count'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">🆁 RB回数</span><span class="ocr-value">{ocr["rb_count"]}回</span></div>'
                            if ocr.get('rb_probability'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">📊 RB確率</span><span class="ocr-value">{ocr["rb_probability"]}</span></div>'
                            if ocr.get('art_count'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">🎯 ART回数</span><span class="ocr-value">{ocr["art_count"]}回</span></div>'
                            if ocr.get('composite_probability'):
                                ocr_html += f'<div class="ocr-item"><span class="ocr-label">📈 合成確率</span><span class="ocr-value">{ocr["composite_probability"]}</span></div>'

                        # すべてのOCRデータがNoneの場合
                        basic_fields = [ocr.get('machine_number'), ocr.get('total_start'), ocr.get('jackpot_count'), 
                                       ocr.get('first_hit_count'), ocr.get('current_start'), ocr.get('jackpot_probability'), 
                                       ocr.get('max_payout')]
                        slot_fields = [ocr.get('total_games'), ocr.get('bb_count'), ocr.get('bb_probability'),
                                      ocr.get('rb_count'), ocr.get('rb_probability'), ocr.get('art_count'),
                                      ocr.get('composite_probability')] if st.session_state.game_type == 'パチスロ' else []
                        if not any(basic_fields + slot_fields):
                            ocr_html += '<div class="ocr-item"><span style="color: #856404;">⚠️ OCRデータを取得できませんでした</span></div>'

                        ocr_html += '</div>'
                        st.markdown(ocr_html, unsafe_allow_html=True)
                        
                        # OCRデバッグ情報を表示
                        if st.session_state.get('show_ocr_debug', False):
                            with st.expander("🔍 OCRデバッグ情報", expanded=True):
                                # 全体OCRテキスト結果
                                if result.get('ocr_data'):
                                    st.markdown("#### 📝 全体OCRで読み取ったテキスト")
                                    ocr_text = result['ocr_data'].get('ocr_raw_text') or result['ocr_data'].get('ocr_text', '読み取れませんでした')
                                    st.text_area("OCR結果", ocr_text, height=200, disabled=True)
                                    
                                    # 抽出されたデータ
                                    st.markdown("#### 📊 抽出されたデータ")
                                    
                                    # 台番号（取得元も表示）
                                    machine_number = result['ocr_data'].get('machine_number', '未検出')
                                    if machine_number != '未検出' and result['ocr_data'].get('machine_number_source'):
                                        source = result['ocr_data']['machine_number_source']
                                        source_labels = {
                                            'OCR_pattern_番台': 'OCRパターン「〇〇番台」',
                                            'OCR_pattern_番': 'OCRパターン「〇〇番」',
                                            'OCR_pattern_台番': 'OCRパターン「台番〇〇」',
                                            'orange_bar': 'オレンジバー領域'
                                        }
                                        source_label = source_labels.get(source, source)
                                        st.write(f"- **台番号**: {machine_number} (取得元: {source_label})")
                                    else:
                                        st.write(f"- **台番号**: {machine_number}")
                                    
                                    # その他のデータ
                                    other_data = {
                                        '累計スタート': result['ocr_data'].get('total_start', '未検出'),
                                        '大当り回数': result['ocr_data'].get('jackpot_count', '未検出'),
                                        '初当り回数': result['ocr_data'].get('first_hit_count', '未検出'),
                                        '現在スタート': result['ocr_data'].get('current_start', '未検出'),
                                        '大当り確率': result['ocr_data'].get('jackpot_probability', '未検出'),
                                        '最高出玉': result['ocr_data'].get('max_payout', '未検出')
                                    }
                                    for key, value in other_data.items():
                                        st.write(f"- **{key}**: {value}")
                                
                                # オレンジバーOCRデバッグ情報
                                if hasattr(st.session_state, 'orange_bar_ocr_debug') and st.session_state.orange_bar_ocr_debug:
                                    st.markdown("#### 🟠 オレンジバーOCR (台番号抽出)")
                                    orange_debug = st.session_state.orange_bar_ocr_debug
                                    
                                    if orange_debug.get('error'):
                                        st.error(f"エラー: {orange_debug['error']}")
                                    else:
                                        st.write(f"- **オレンジ領域検出**: {'✅ 成功' if orange_debug.get('orange_found') else '❌ 失敗'}")
                                        if orange_debug.get('orange_y_range'):
                                            st.write(f"- **オレンジ領域Y座標**: {orange_debug['orange_y_range'][0]}〜{orange_debug['orange_y_range'][1]}px")
                                        if orange_debug.get('crop_region'):
                                            crop = orange_debug['crop_region']
                                            st.write(f"- **切り出し領域**: Y: {crop['y_start']}〜{crop['y_end']}px, X: {crop['x_start']}〜{crop['x_end']}px")
                                            st.write(f"- **オレンジ中心Y**: {crop['orange_center']}px")
                                        if orange_debug.get('number_region_shape'):
                                            st.write(f"- **台番号領域サイズ**: {orange_debug['number_region_shape']}")
                                        if orange_debug.get('raw_text') is not None:
                                            st.write(f"- **OCRで読み取った文字**: `{orange_debug['raw_text']}`")
                                            if not orange_debug['raw_text'].strip():
                                                st.warning("⚠️ 台番号領域から文字が読み取れませんでした")
                                                st.info("💡 **考えられる原因**:\n"
                                                       "- オレンジバーの位置が想定と異なる\n"
                                                       "- 台番号の文字が小さすぎる/薄すぎる\n"
                                                       "- 画像の解像度が低い")
                                
                                # 処理時間情報を表示
                                if result.get('ocr_data') and result['ocr_data'].get('ocr_timings'):
                                    st.markdown("#### ⏱️ 処理時間")
                                    timing_data = result['ocr_data']['ocr_timings']
                                    for key, value in timing_data.items():
                                        st.write(f"- **{key}**: {value}")
                        
                        # 初当たり検出デバッグ情報を表示
                        if result.get('first_hit_debug'):
                            with st.expander("🔍 初当たり検出デバッグ情報"):
                                debug_info = result['first_hit_debug']
                                
                                # site7データと同じスタイル
                                st.markdown("""
                                <style>
                                .debug-card {
                                    background-color: #e8f4f8;
                                    padding: 15px;
                                    border-radius: 10px;
                                    margin-top: 10px;
                                    border: 1px solid #bee5eb;
                                }
                                .debug-title {
                                    color: #17a2b8;
                                    font-weight: bold;
                                    margin-bottom: 10px;
                                }
                                .debug-item {
                                    display: flex;
                                    justify-content: space-between;
                                    padding: 5px 0;
                                    border-bottom: 1px solid #d1ecf1;
                                }
                                .debug-item:last-child {
                                    border-bottom: none;
                                }
                                .debug-label {
                                    color: #0c5460;
                                    font-weight: 500;
                                }
                                .debug-value {
                                    font-weight: bold;
                                    color: #0c5460;
                                }
                                </style>
                                """, unsafe_allow_html=True)
                                
                                # 検出結果
                                debug_html = '<div class="debug-card"><div class="debug-title">🎯 検出結果</div>'
                                
                                if debug_info['detected_position'] is not None:
                                    debug_html += f'<div class="debug-item"><span class="debug-label">📍 検出位置</span><span class="debug-value">{debug_info["detected_position"]}点目</span></div>'
                                    debug_html += f'<div class="debug-item"><span class="debug-label">💰 検出値</span><span class="debug-value">{debug_info["detected_value"]:,.0f}玉</span></div>'
                                else:
                                    debug_html += '<div class="debug-item"><span class="debug-label">📍 検出位置</span><span class="debug-value" style="color: #999;">未検出</span></div>'
                                    debug_html += '<div class="debug-item"><span class="debug-label">💰 検出値</span><span class="debug-value" style="color: #999;">-</span></div>'
                                
                                debug_html += f'<div class="debug-item"><span class="debug-label">🔍 検出方法</span><span class="debug-value">{debug_info["detection_method"] or "なし"}</span></div>'
                                debug_html += f'<div class="debug-item"><span class="debug-label">📋 候補数</span><span class="debug-value">{len(debug_info["candidates"])}件</span></div>'
                                debug_html += '</div>'
                                
                                st.markdown(debug_html, unsafe_allow_html=True)
                                
                                # スケール情報を表示
                                if 'scale_info' in debug_info:
                                    scale_html = '<div class="debug-card"><div class="debug-title">📏 スケール情報（1pxあたりの数値）</div>'
                                    
                                    balls_per_px = debug_info['scale_info'].get('balls_per_pixel')
                                    spins_per_px = debug_info['scale_info'].get('spins_per_pixel')
                                    
                                    if balls_per_px:
                                        scale_html += f'<div class="debug-item"><span class="debug-label">🎱 玉数/px</span><span class="debug-value">{balls_per_px:.4f}玉</span></div>'
                                    else:
                                        scale_html += '<div class="debug-item"><span class="debug-label">🎱 玉数/px</span><span class="debug-value" style="color: #999;">未計算</span></div>'
                                    
                                    if spins_per_px:
                                        scale_html += f'<div class="debug-item"><span class="debug-label">🎯 回転数/px</span><span class="debug-value">{spins_per_px:.4f}回</span></div>'
                                    else:
                                        scale_html += '<div class="debug-item"><span class="debug-label">🎯 回転数/px</span><span class="debug-value" style="color: #999;">未計算</span></div>'
                                    
                                    scale_html += '</div>'
                                    st.markdown(scale_html, unsafe_allow_html=True)
                                    
                                    # グラフ情報も表示
                                    if 'graph_info' in debug_info:
                                        graph_info = debug_info['graph_info']
                                        graph_html = '<div class="debug-card"><div class="debug-title">📊 グラフ情報</div>'
                                        
                                        graph_html += f'<div class="debug-item"><span class="debug-label">📐 グラフ幅</span><span class="debug-value">{graph_info.get("graph_width", 0)}px</span></div>'
                                        graph_html += f'<div class="debug-item"><span class="debug-label">🎰 総回転数</span><span class="debug-value">{graph_info.get("total_spins", 0):,}回</span></div>'
                                        graph_html += f'<div class="debug-item"><span class="debug-label">▶️ 開始X座標</span><span class="debug-value">{graph_info.get("graph_start_x", 0)}px</span></div>'
                                        graph_html += f'<div class="debug-item"><span class="debug-label">⏸️ 終了X座標</span><span class="debug-value">{graph_info.get("graph_end_x", 0)}px</span></div>'
                                        
                                        graph_html += '</div>'
                                        st.markdown(graph_html, unsafe_allow_html=True)
                                
                                if debug_info['candidates']:
                                    candidates_html = '<div class="debug-card"><div class="debug-title">🔍 検出候補一覧</div>'
                                    
                                    for idx, candidate in enumerate(debug_info['candidates']):
                                        candidates_html += f'<div style="margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #d1ecf1;"><div style="font-weight: bold; color: #17a2b8; margin-bottom: 5px;">候補{idx+1}</div>'
                                        candidates_html += f'<div class="debug-item"><span class="debug-label">📍 位置</span><span class="debug-value">{candidate["position"]}点目</span></div>'
                                        candidates_html += f'<div class="debug-item"><span class="debug-label">💰 検出値</span><span class="debug-value">{candidate["value"]:,.0f}玉</span></div>'
                                        candidates_html += f'<div class="debug-item"><span class="debug-label">📈 上昇量</span><span class="debug-value">{candidate.get("increase", 0):,.0f}玉</span></div>'
                                        if 'slope' in candidate:
                                            candidates_html += f'<div class="debug-item"><span class="debug-label">📊 傾き</span><span class="debug-value">{candidate["slope"]:.1f}</span></div>'
                                        candidates_html += f'<div class="debug-item"><span class="debug-label">💡 検出理由</span><span class="debug-value">{candidate["reason"]}</span></div>'
                                        candidates_html += '</div>'
                                    
                                    candidates_html += '</div>'
                                    st.markdown(candidates_html, unsafe_allow_html=True)

                        # 玉推移CSVデータ
                        if result.get('graph_values'):
                            with st.expander("📊 玉推移データ (CSV)"):
                                # 回転数計算用のデータを取得
                                rotation_metrics = result.get('rotation_metrics', {})
                                spins_per_pixel = rotation_metrics.get('spins_per_pixel', 0)

                                # CSV形式でデータを作成（回転数と玉数のペア）
                                csv_lines = ["rotation,balls"]
                                for i, ball_value in enumerate(result['graph_values']):
                                    # 回転数を計算（pixel_step=1なので、i pixel = i * spins_per_pixel回転）
                                    rotation = round(i * spins_per_pixel) if spins_per_pixel > 0 else i
                                    csv_lines.append(f"{rotation},{round(ball_value, 1)}")

                                csv_str = "\n".join(csv_lines)

                                # メタ情報を表示
                                machine_number = result.get('ocr_data', {}).get('machine_number', result.get('name', '').rsplit('.', 1)[0])
                                total_spins = result.get('ocr_data', {}).get('total_start', 0)
                                st.info(f"📊 台番号: {machine_number} | 累計: {total_spins}回転 | データ数: {len(result['graph_values'])}点")

                                st.text_area(
                                    "CSV データ（コピー可）",
                                    csv_str,
                                    height=300,
                                    help="このテキストを選択してコピーできます"
                                )

                                # ダウンロードボタンも追加
                                st.download_button(
                                    label="📥 CSVファイルとしてダウンロード",
                                    data=csv_str,
                                    file_name=f"{result.get('name', 'graph').rsplit('.', 1)[0]}_transition.csv",
                                    mime="text/csv"
                                )

                    else:
                        st.warning("⚠️ グラフデータを検出できませんでした")

                    # 区切り線（各列内で）
                    if idx < len(analysis_results) - 3:
                        st.markdown("---")

    # サマリー情報
    st.markdown("### 📋 解析サマリー")

    success_count = sum(1 for r in analysis_results if r['success'])
    st.info(f"📈 総画像数: {len(analysis_results)}枚 | ✅ 成功: {success_count}枚 | ⚠️ 失敗: {len(analysis_results) - success_count}枚")

    # 切り抜き画像の一括ダウンロード
    if analysis_results:
        import zipfile
        import io
        from PIL import Image

        # ZIPファイルを作成
        zip_buffer = io.BytesIO()
        image_count = 0
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, result in enumerate(analysis_results):
                # オーバーレイ画像を優先、なければ切り抜き画像を使用
                overlay_img = result.get('overlay_image')
                cropped_img = result.get('cropped_image')

                if overlay_img is not None or cropped_img is not None:
                    # 使用する画像を決定
                    image_to_save = overlay_img if overlay_img is not None else cropped_img

                    # PIL ImageをPNGバイナリに変換
                    img_buffer = io.BytesIO()
                    Image.fromarray(image_to_save).save(img_buffer, format='PNG')
                    img_buffer.seek(0)

                    # ファイル名を生成（台番号または元ファイル名）
                    machine_number = result.get('ocr_data', {}).get('machine_number', '')
                    if machine_number:
                        filename = f"{machine_number}_overlay.png"
                    else:
                        filename = f"{result.get('name', f'graph_{i+1}')}_overlay.png"

                    # ZIPに追加
                    zip_file.writestr(filename, img_buffer.getvalue())
                    image_count += 1

        zip_buffer.seek(0)

        # ダウンロードボタン
        if image_count > 0:
            st.download_button(
                label=f"📥 オーバーレイ画像を一括ダウンロード ({image_count}枚 / ZIP)",
                data=zip_buffer,
                file_name="overlay_graphs.zip",
                mime="application/zip",
                use_container_width=True
            )

    # 結果を表形式で表示
    st.markdown("### 📊 解析結果（表形式）")

    # 統計情報を計算して表示
    if analysis_results:
        success_results = [r for r in analysis_results if r.get('success')]
        if success_results:
            # 統計情報の計算
            total_balance = sum(r['current_val'] for r in success_results)
            exchange_rate = get_settings().get('exchange_rate', 3.57145)
            total_balance_yen = int(total_balance * exchange_rate)
            avg_balance = total_balance / len(success_results)
            avg_balance_yen = int(avg_balance * exchange_rate)
            max_result = max(success_results, key=lambda x: x['current_val'])
            min_result = min(success_results, key=lambda x: x['current_val'])
            
            # 1日の総獲得球数を計算
            total_day_jackpot_balls = sum(r.get('total_jackpot_balls', 0) for r in success_results)
            
            # パチスロの場合はBB+RBの合計、パチンコは従来通り
            if st.session_state.game_type == 'パチスロ':
                total_day_jackpot_count = sum(
                    int((r.get('ocr_data') or {}).get('bb_count') or 0) + 
                    int((r.get('ocr_data') or {}).get('rb_count') or 0)
                    if (r.get('ocr_data') or {}).get('bb_count') or (r.get('ocr_data') or {}).get('rb_count')
                    else r.get('jackpot_count', 0)
                    for r in success_results
                )
            else:
                total_day_jackpot_count = sum(r.get('jackpot_count', 0) for r in success_results)
            
            avg_day_jackpot_balls = total_day_jackpot_balls / total_day_jackpot_count if total_day_jackpot_count > 0 else 0
            
            # 総投資球数を計算（各台の最低値の絶対値の合計）
            total_investment = sum(abs(min(r['min_val'], 0)) for r in success_results)
            
            # 実質収支 = 総獲得球数 - 総投資球数
            net_balance = total_day_jackpot_balls - total_investment
            net_balance_yen = int(net_balance * exchange_rate)

            # 統計情報を2列で表示（見やすさ重視）
            st.markdown("#### 📊 収支サマリー")
            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "🎯 現在の合計収支",
                    f"{total_balance_yen:+,}円",
                    f"{total_balance:+,}{get_unit(st.session_state.get('game_type', 'パチンコ'))}",
                    delta_color="normal"
                )

            with col2:
                st.metric(
                    "📊 台平均収支",
                    f"{avg_balance_yen:+,.0f}円",
                    f"{avg_balance:+,.0f}{get_unit(st.session_state.get('game_type', 'パチンコ'))}",
                    delta_color="normal"
                )
            
            # 大当り情報を別セクションに
            st.markdown("#### 🎰 大当り分析")
            col5, col6, col7 = st.columns(3)
            
            with col5:
                st.metric(
                    "総大当り回数",
                    f"{total_day_jackpot_count}回",
                    f"{len(success_results)}台合計"
                )
            
            with col6:
                unit = get_unit(st.session_state.get('game_type', 'パチンコ'))
                label = "総獲得球数" if st.session_state.game_type == "パチンコ" else "総獲得枚数"
                st.metric(
                    label,
                    f"{total_day_jackpot_balls:,}{unit}",
                    f"平均{avg_day_jackpot_balls:,.0f}{unit}/回"
                )
            
            with col7:
                st.metric(
                    "獲得金額換算",
                    f"{int(total_day_jackpot_balls * exchange_rate):,}円",
                    f"@{exchange_rate:.3f}円/{get_unit(st.session_state.get('game_type', 'パチンコ'))}"
                )

        # データフレームを作成
        df_data = []
        for result in analysis_results:
            if result['success']:
                # 台番号の決定（手動入力優先）
                if st.session_state.get('skip_ocr', False):
                    machine_number = result['name']
                else:
                    # 手動入力された台番号があればそれを優先
                    idx = analysis_results.index(result)
                    input_key = f"machine_input_{idx}"
                    if input_key in st.session_state:
                        machine_number = st.session_state[input_key]
                    else:
                        machine_number = result.get('ocr_data', {}).get('machine_number', result['name'])
                
                # 優先度に基づいてデータを取得
                prioritized_data = get_prioritized_data(result)
                
                row = {
                    '画像名': result['name'],  # 画像名を追加
                    '台番号': machine_number,
                    '最高値': prioritized_data['max_val'],
                    '最低値': prioritized_data['min_val'],
                    '現在値': prioritized_data['current_val'],
                    '初当たり球数': prioritized_data['first_hit_val'] if prioritized_data['first_hit_val'] is not None else None,
                    '初当たり回転数': result.get('rotation_metrics', {}).get('first_hit_spins', 0) if prioritized_data.get('first_hit_val') is not None else 0,
                    '収支（円）': int(prioritized_data['current_val'] * get_settings().get('exchange_rate', 3.57145)),
                    '総獲得球数': result.get('total_jackpot_balls', 0),
                    '大当り回数（グラフ）': result.get('jackpot_count', 0),  # 列名を変更
                    '色': result['dominant_color']
                }
                
                # 超中小の回数を追加（優先度に基づく）
                if (prioritized_data.get('big_jackpots') is None and 
                    prioritized_data.get('medium_jackpots') is None and 
                    prioritized_data.get('small_jackpots') is None):
                    # total_jackpotsがある場合、すべて超として扱う
                    total_jackpots = prioritized_data.get('total_jackpots', 0)
                    row['超回数'] = total_jackpots
                    row['中回数'] = 0
                    row['小回数'] = 0
                else:
                    row['超回数'] = prioritized_data.get('big_jackpots', '')
                    row['中回数'] = prioritized_data.get('medium_jackpots', '')
                    row['小回数'] = prioritized_data.get('small_jackpots', '')
                row['機種名'] = prioritized_data.get('machine_name', '')
                
                # 回転率データを追加（表示時に計算した値をそのまま使用）
                # 回転率①（表示時の値を使用）
                row['回転率①'] = result.get('display_rotation_rate_1', '-')
                
                # 回転率②（表示時の値を使用）
                row['回転率②'] = result.get('display_rotation_rate_2', '-')
                
                # 初当り使用玉
                if result.get('rotation_metrics'):
                    row['初当り使用玉'] = result['rotation_metrics']['first_hit_balls'] if result['rotation_metrics'].get('first_hit_balls', 0) > 0 else '-'
                else:
                    row['初当り使用玉'] = '-'
                
                # 通常時使用球数（表示時の値を使用）
                row['通常時使用球数'] = result.get('display_normal_balls', 0)
                
                # グラフ解析データを保持（データエディタの再計算用）
                row['_total_decline_balls'] = result.get('total_decline_balls', 0)
                
                # 通常回転数を追加（優先度に基づく）
                row['通常回転数'] = prioritized_data.get('normal_rotations', 0) or 0
                
                # OCRデータを追加（OCRスキップモードでない場合のみ）
                if not st.session_state.get('skip_ocr', False) and result.get('ocr_data'):
                    ocr = result['ocr_data']
                    # 現在回転数（OCRのcurrent_startを使用）
                    current_start = ocr.get('current_start', '')
                    
                    row.update({
                        '累計スタート': prioritized_data.get('total_rotations', '') or ocr.get('total_start', ''),
                        '大当り回数（OCR）': ocr.get('jackpot_count', ''),  # 列名を変更
                        '初当り回数': prioritized_data.get('first_jackpots', '') or ocr.get('first_hit_count', ''),
                        '現在回転数': current_start,
                        '大当り確率': ocr.get('jackpot_probability', ''),
                        '最高出玉': ocr.get('max_payout', '')
                    })
                    # パチスロ用データを追加
                    if st.session_state.game_type == 'パチスロ':
                        row.update({
                            '累計ゲーム': ocr.get('total_games', ''),
                            'BB回数': ocr.get('bb_count', ''),
                            'BB確率': ocr.get('bb_probability', ''),
                            'RB回数': ocr.get('rb_count', ''),
                            'RB確率': ocr.get('rb_probability', ''),
                            'ART回数': ocr.get('art_count', ''),
                            '合成確率': ocr.get('composite_probability', ''),
                            'BB+RB回数': int(ocr.get('bb_count') or 0) + int(ocr.get('rb_count') or 0) if (ocr.get('bb_count') or ocr.get('rb_count')) else ''
                        })
                df_data.append(row)
            else:
                # 解析失敗時も台番号の決定方法を統一
                if st.session_state.get('skip_ocr', False):
                    machine_number = result['name']
                else:
                    # 手動入力された台番号があればそれを優先
                    idx = analysis_results.index(result)
                    input_key = f"machine_input_{idx}"
                    if input_key in st.session_state:
                        machine_number = st.session_state[input_key]
                    else:
                        machine_number = result.get('ocr_data', {}).get('machine_number', result['name'])
                    
                df_data.append({
                    '画像名': result['name'],  # 画像名を追加
                    '台番号': machine_number,
                    '最高値': '解析失敗',
                    '最低値': '-',
                    '現在値': '-',
                    '初当たり球数': None,
                    '収支（円）': '-',
                    '色': '-'
                })

        if df_data:
            # 全データを含むDataFrameを作成
            df_full = pd.DataFrame(df_data)
            
            # 選択された列のみを抽出
            # csv_columnsに存在する列のみを選択
            selected_cols = [col for col in st.session_state.csv_columns if col in df_full.columns]
            df = df_full[selected_cols].copy()
            
            # データエディタで編集可能にする
            st.markdown("#### 📝 データ編集")
            
            # 並び替え機能を追加
            col_sort1, col_sort2, col_sort3 = st.columns([1, 1, 2])
            with col_sort1:
                sort_option = st.selectbox(
                    "並び順",
                    ["アップロード順", "台番号順", "回転率①順", "回転率②順"],
                    key="sort_option"
                )
            
            with col_sort2:
                # アップロード順以外の場合のみ昇順・降順を選択
                if sort_option != "アップロード順":
                    sort_order = st.selectbox(
                        "順序",
                        ["昇順", "降順"],
                        key="sort_order"
                    )
                else:
                    sort_order = "昇順"  # デフォルト
            
            st.info("""
            💡 表内のセルをクリックして直接編集できます。
            
            **編集後に「🔄 再計算」ボタンを押すと以下が計算されます：**
            - 現在値 → 収支（円）
            - 初当たり球数・回転数 → 回転率①
            - 通常回転数・総獲得球数 → 回転率②
            """)
            
            # 台番号入力フィールドの変更を反映するため、常に最新のdfを使用
            # （上記のデータフレーム作成時にセッションステートから台番号を取得済み）
            
            # セッションステートにデータフレームを保存
            # 新しいデータが追加された場合（行数が増えた場合）は更新
            if 'edited_df' not in st.session_state or len(df) > len(st.session_state.edited_df):
                st.session_state.edited_df = df.copy()
            else:
                # 既存データの台番号の更新を反映
                for idx in range(len(df)):
                    if idx < len(st.session_state.edited_df):
                        st.session_state.edited_df.at[idx, '台番号'] = df.at[idx, '台番号']
            
            # 一時的な編集用データフレーム
            if 'temp_df' not in st.session_state or len(df) > len(st.session_state.temp_df):
                st.session_state.temp_df = st.session_state.edited_df.copy()
            else:
                # 既存データの台番号の更新を反映
                for idx in range(len(df)):
                    if idx < len(st.session_state.temp_df):
                        st.session_state.temp_df.at[idx, '台番号'] = df.at[idx, '台番号']
            
            # 並び替え処理を適用
            display_df = st.session_state.temp_df.copy()
            
            if sort_option == "台番号順":
                # 台番号を数値として解釈できる場合は数値順、できない場合は文字列順
                def parse_machine_number(x):
                    if pd.isna(x) or x == '':
                        return float('inf') if sort_order == "昇順" else float('-inf')
                    # 文字列から数字部分を抽出
                    import re
                    numbers = re.findall(r'\d+', str(x))
                    if numbers:
                        return int(numbers[0])
                    return float('inf') if sort_order == "昇順" else float('-inf')
                
                try:
                    display_df['台番号_sort'] = display_df['台番号'].apply(parse_machine_number)
                    display_df = display_df.sort_values('台番号_sort', ascending=(sort_order == "昇順")).drop('台番号_sort', axis=1)
                except Exception as e:
                    st.warning(f"台番号ソートに失敗しました: {str(e)}")
                    # フォールバックとして文字列ソート
                    try:
                        display_df = display_df.sort_values('台番号', ascending=(sort_order == "昇順"))
                    except:
                        pass
            elif sort_option == "回転率①順":
                # 回転率①を数値に変換してソート（警告記号を除去）
                if '回転率①' in display_df.columns:
                    display_df['回転率①_sort'] = display_df['回転率①'].apply(
                        lambda x: float(str(x).replace(' ⚠️', '')) if str(x) != '-' and str(x) != '' else -1
                    )
                    # 回転率の場合、通常は降順（高い順）がデフォルト
                    display_df = display_df.sort_values('回転率①_sort', ascending=(sort_order == "昇順")).drop('回転率①_sort', axis=1)
            elif sort_option == "回転率②順":
                # 回転率②を数値に変換してソート（警告記号を除去）
                if '回転率②' in display_df.columns:
                    display_df['回転率②_sort'] = display_df['回転率②'].apply(
                        lambda x: float(str(x).replace(' ⚠️', '')) if str(x) != '-' and str(x) != '' else -1
                    )
                    # 回転率の場合、通常は降順（高い順）がデフォルト
                    display_df = display_df.sort_values('回転率②_sort', ascending=(sort_order == "昇順")).drop('回転率②_sort', axis=1)
            # アップロード順の場合はソートしない（元の順序を維持）
            
            edited_df = st.data_editor(
                display_df,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",  # 行の追加・削除を許可
                key="data_editor",
                column_config={
                    "台番号": st.column_config.TextColumn(
                        "台番号",
                        help="台番号を入力",
                        required=True
                    ),
                    "最高値": st.column_config.NumberColumn(
                        "最高値",
                        help="最高値（玉数）",
                        format="%d玉"
                    ),
                    "最低値": st.column_config.NumberColumn(
                        "最低値", 
                        help="最低値（玉数）",
                        format="%d玉"
                    ),
                    "現在値": st.column_config.NumberColumn(
                        "現在値",
                        help="現在値（玉数）", 
                        format="%d玉"
                    ),
                    "初当たり球数": st.column_config.NumberColumn(
                        "初当たり球数",
                        help="初当たり時の玉数",
                        format="%d玉"
                    ),
                    "初当たり回転数": st.column_config.NumberColumn(
                        "初当たり回転数",
                        help="初当たりまでの回転数",
                        format="%d回"
                    ),
                    "収支（円）": st.column_config.NumberColumn(
                        "収支（円）",
                        help="現在値×4円",
                        format="¥%d"
                    ),
                    "総獲得球数": st.column_config.NumberColumn(
                        "総獲得球数",
                        help="大当りで獲得した総球数",
                        format="%d玉"
                    ),
                    "大当り回数": st.column_config.NumberColumn(
                        "大当り回数",
                        help="大当りの回数",
                        format="%d回"
                    ),
                    "回転率①": st.column_config.TextColumn(
                        "回転率①",
                        help="初当たりまでの回転率"
                    ),
                    "回転率②": st.column_config.TextColumn(
                        "回転率②",
                        help="通常時全体の回転率"
                    ),
                    "通常回転数": st.column_config.NumberColumn(
                        "通常回転数",
                        help="大当たり中を除いた通常時の総回転数",
                        format="%d回"
                    )
                }
            )
            
            # 編集されたデータは edited_df に保持されるが、
            # セッションステートへの保存は再計算ボタンが押されるまで行わない
            # これによりカーソルのリセットを防ぐ

            # 再計算ボタンとCSVダウンロードボタン
            col1, col2, col3 = st.columns([1, 1, 3])
            
            with col1:
                if st.button("🔄 再計算", type="primary", use_container_width=True):
                    try:
                        # 現在の交換レートを取得
                        exchange_rate = get_settings().get('exchange_rate', 3.57145)
                        
                        # 編集されたデータを取得（edited_dfが最新の編集内容を持っている）
                        calc_df = edited_df.copy()
                        
                        # 各行について計算
                        for idx in range(len(calc_df)):
                            # 収支（円）を現在値から計算
                            if '現在値' in calc_df.columns and pd.notna(calc_df.at[idx, '現在値']):
                                calc_df.at[idx, '収支（円）'] = int(calc_df.at[idx, '現在値'] * exchange_rate)
                            
                            # 回転率①を計算
                            if ('初当たり回転数' in calc_df.columns and pd.notna(calc_df.at[idx, '初当たり回転数']) and
                                '初当たり球数' in calc_df.columns and pd.notna(calc_df.at[idx, '初当たり球数'])):
                                spins = calc_df.at[idx, '初当たり回転数']
                                balls = abs(calc_df.at[idx, '初当たり球数'])  # 絶対値を使用
                                if balls > 0:
                                    rate1 = round((spins / balls) * 250, 1)
                                    calc_df.at[idx, '回転率①'] = f"{rate1:.1f}"
                                else:
                                    calc_df.at[idx, '回転率①'] = '-'
                            else:
                                calc_df.at[idx, '回転率①'] = '-'
                            
                            # 回転率②を計算
                            # 通常回転数と使用球数から計算
                            if '通常回転数' in calc_df.columns and pd.notna(calc_df.at[idx, '通常回転数']):
                                normal_spins = calc_df.at[idx, '通常回転数']
                                
                                # グラフ下降累積データを使用
                                normal_balls = 0
                                if '_total_decline_balls' in calc_df.columns and pd.notna(calc_df.at[idx, '_total_decline_balls']):
                                    normal_balls = calc_df.at[idx, '_total_decline_balls']
                                
                                if normal_balls > 0 and normal_spins > 0:
                                    # パチンコの場合は250玉/千円、パチスロの場合は50枚/千円
                                    unit_per_1000yen = 250 if st.session_state.get('game_type', 'パチンコ') == 'パチンコ' else 50
                                    rate2 = round((normal_spins / normal_balls) * unit_per_1000yen, 1)
                                    calc_df.at[idx, '回転率②'] = f"{rate2:.1f}"
                                else:
                                    calc_df.at[idx, '回転率②'] = '-'
                        
                        # 計算結果をセッションステートに保存
                        st.session_state.edited_df = calc_df.copy()
                        st.session_state.temp_df = calc_df.copy()
                        st.success("✅ 再計算が完了しました")
                        # 画面を再描画
                        st.rerun()
                    except Exception as e:
                        log_error('Recalculation Error', str(e), {'function': 'recalculate_button', 'stage': 'data_recalculation'})
                        st.error(f"⚠️ 再計算中にエラーが発生しました: {str(e)}")
                        # エラーが発生しても編集したデータは保持
                        if 'edited_df' not in st.session_state:
                            st.session_state.edited_df = edited_df.copy()
            
            with col2:
                # 編集されたデータを使用
                csv_df = edited_df
                csv = csv_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 CSV保存",
                    data=csv,
                    file_name=f'pachinko_analysis_edited_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                    mime='text/csv',
                    type="secondary",
                    use_container_width=True
                )
            
            # 回転率の詳細情報を表示
            with st.expander("📊 回転率計算の詳細"):
                st.markdown("""
                ### 回転率の計算方法
                
                **回転率①（初当たりまで）**
                - 初当たりまでの回転数 ÷ (使用玉数 ÷ 250)
                - 初当たりまでの1000円あたりの回転数
                - 朝一から初当たりを引くまでの釘の状態を反映
                
                **回転率②（通常時全体）**
                - 通常時の総回転数 ÷ (総消費玉数 ÷ 250)
                - グラフの下降部分を累積して使用球数を計算（より正確）
                - 全体を通しての釘の状態を反映
                
                ※ 1000円 = 250玉として計算
                ※ グラフ下降累積により精密に計算
                """)
            
            # データ出力フォーム（簡易版）
            st.markdown("---")
            st.markdown("### 📝 データ出力")
            st.caption("pachikeisan.x0.com用のフォーマットで一括出力します")
            
            # 出力タイプの選択
            output_type = st.radio(
                "出力タイプを選択",
                ["初のみ", "全のみ", "両方"],
                index=2,  # デフォルトは「両方」
                horizontal=True,
                help="初: 初当たり関連データのみ、全: 全体データのみ、両方: 従来通り両方出力"
            )
            
            # 一括データ出力（常に表示）
            # 今日の日付を取得
            today = datetime.now().strftime("%-m/%-d")  # 例: 7/7
            
            # データ収集用のリスト
            output_lines = [today]  # 日付を最初に追加
            
            # 各解析結果に対してデータを収集（自動処理）
            for idx, row in edited_df.iterrows():
                # 台番号を取得
                machine_number = str(row.get('台番号', ''))
                if machine_number == '' or machine_number == row.get('画像名', '') or machine_number == 'None' or machine_number == '未検出':
                    # 画像名から拡張子を除去して台番号とする
                    image_name = row.get('画像名', f'台{idx + 1}')
                    machine_number = image_name.rsplit('.', 1)[0]
                
                # 初当たり回転数
                first_hit_spins_value = row.get('初当たり回転数', 0)
                if pd.isna(first_hit_spins_value) or first_hit_spins_value is None:
                    first_hit_spins = 0
                else:
                    try:
                        first_hit_spins = int(first_hit_spins_value)
                    except (ValueError, TypeError):
                        first_hit_spins = 0
                
                # 初当たり玉数（絶対値）
                first_hit_balls_value = row.get('初当たり球数', 0)
                if pd.isna(first_hit_balls_value) or first_hit_balls_value is None or first_hit_balls_value == 'なし':
                    first_hit_balls = 0
                else:
                    try:
                        first_hit_balls = abs(int(first_hit_balls_value))
                    except (ValueError, TypeError):
                        first_hit_balls = 0
                
                # 回転率①
                rotation_rate_1 = row.get('回転率①', '-')
                if rotation_rate_1 != '-':
                    if isinstance(rotation_rate_1, str):
                        rotation_rate_1 = rotation_rate_1.replace('回/千円', '').replace(' ⚠️', '')
                    else:
                        rotation_rate_1 = str(rotation_rate_1)
                else:
                    rotation_rate_1 = '0'
                
                # 通常回転数（rotation_metricsから取得）
                normal_spins = 0
                if st.session_state.analysis_results:
                    for result in st.session_state.analysis_results:
                        if result['name'] == row.get('画像名'):
                            if result.get('rotation_metrics'):
                                normal_spins = result['rotation_metrics'].get('normal_decline_spins', 0)
                            break
                
                # 総獲得球数
                total_win_value = row.get('総獲得球数', 0)
                if pd.isna(total_win_value) or total_win_value is None:
                    total_win = 0
                else:
                    try:
                        total_win = int(total_win_value)
                    except (ValueError, TypeError):
                        total_win = 0
                
                # 現在値
                current_value_raw = row.get('現在値', 0)
                if pd.isna(current_value_raw) or current_value_raw is None:
                    current_value = 0
                else:
                    try:
                        current_value = int(current_value_raw)
                    except (ValueError, TypeError):
                        current_value = 0
                
                # 回転率②
                rotation_rate_2 = row.get('回転率②', '-')
                if rotation_rate_2 != '-':
                    if isinstance(rotation_rate_2, str):
                        rotation_rate_2 = rotation_rate_2.replace('回/千円', '').replace(' ⚠️', '')
                    else:
                        rotation_rate_2 = str(rotation_rate_2)
                else:
                    rotation_rate_2 = '0'
                
                # 出力タイプに応じてデータを追加
                if output_type in ["初のみ", "両方"]:
                    # 1行目: (初) 台番#初当たり回転数#初当たり玉数(回転率①)
                    line1 = f"(初){machine_number}#{first_hit_spins}#{first_hit_balls}({rotation_rate_1})"
                    output_lines.append(line1)
                
                if output_type in ["全のみ", "両方"]:
                    # 2行目: (全) 台番#通常回転数#獲得数#現在値(回転率②)
                    line2 = f"(全){machine_number}#{normal_spins}#{total_win}#{current_value}({rotation_rate_2})"
                    output_lines.append(line2)
            
            # 全データ出力
            all_data = "\n".join(output_lines)
            st.text_area("コピー用データ", value=all_data, height=300)
            
            # 出力フォーマット説明
            if output_type == "初のみ":
                st.info("""
                📌 **出力フォーマット**
                - 1行目: 日付
                - 以降、1台につき1行で出力
                - (初)台番#初当たり回転数#初当たり玉数(回転率①)
                """)
            elif output_type == "全のみ":
                st.info("""
                📌 **出力フォーマット**
                - 1行目: 日付
                - 以降、1台につき1行で出力
                - (全)台番#通常回転数#獲得数#現在値(回転率②)
                """)
            else:
                st.info("""
                📌 **出力フォーマット**
                - 1行目: 日付
                - 以降、1台につき2行で出力
                - (初)台番#初当たり回転数#初当たり玉数(回転率①)
                - (全)台番#通常回転数#獲得数#現在値(回転率②)
                """)
            
            # 調整設定の案内
            st.markdown("---")
            st.info("""
            💡 **出力結果が期待と異なる場合は？**
            
            端末や画面サイズによってグラフの表示が異なるため、調整設定が必要な場合があります。
            ページ下部の「⚙️ 画像解析の調整設定」から、お使いの端末に合わせた設定を保存してください。
            """)

# CSV表示項目の設定セクション
with st.expander("📊 CSV表示項目の設定", expanded=False):
    st.markdown("##### CSVデータテーブルに表示する項目を選択")
    st.caption("チェックを外した項目は表示されません。表が横に長くなりすぎる場合は不要な項目を非表示にできます。")
    
    # 全項目リスト（単位を動的に変更）
    unit = get_unit(st.session_state.get('game_type', 'パチンコ'))
    all_columns = [
        '画像名', '台番号', '最高値', '最低値', '現在値',
        f'初当たり{unit}数', '初当たり回転数', '収支（円）',
        f'総獲得{unit}数', '大当り回数（グラフ）', '色', '回転率①', '回転率②',
        '通常回転数', f'初当り使用{unit}', f'通常時使用{unit}数',
        '累計スタート', '大当り回数（OCR）', '初当り回数',
        '現在回転数', '大当り確率', f'最高出{unit}',
        '機種名', '超回数', '中回数', '小回数'
    ]
    
    # パチスロ用の追加カラム
    if st.session_state.game_type == 'パチスロ':
        all_columns.extend([
            '累計ゲーム', 'BB回数', 'BB確率', 'RB回数', 'RB確率',
            'ART回数', '合成確率', 'BB+RB回数'
        ])
    
    # デフォルト表示項目
    default_columns = [
        '台番号', '現在値', f'初当たり{unit}数', '初当たり回転数',
        f'総獲得{unit}数', '回転率①', '回転率②', '通常回転数'
    ]
    
    # 初期化時にデフォルト値を設定
    if 'csv_columns' not in st.session_state or len(st.session_state.csv_columns) == 0:
        st.session_state.csv_columns = default_columns.copy()
    
    # 項目を3列で表示
    col_count = 3
    cols = st.columns(col_count)
    
    # 選択された項目を一時的に保存
    selected_columns = []
    
    for i, column in enumerate(all_columns):
        col_idx = i % col_count
        with cols[col_idx]:
            # デフォルトでチェックされているかどうか
            is_checked = column in st.session_state.csv_columns
            # インデックスを含むユニークなキーを生成
            if st.checkbox(column, value=is_checked, key=f"csv_col_{i}_{column}"):
                selected_columns.append(column)
    
    # ボタンで操作
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    
    with btn_col1:
        if st.button("デフォルトに戻す", use_container_width=True):
            st.session_state.csv_columns = default_columns.copy()
            st.success("デフォルト設定に戻しました")
            st.rerun()
    
    with btn_col2:
        if st.button("全て選択", use_container_width=True):
            st.session_state.csv_columns = all_columns.copy()
            st.success("全項目を選択しました")
            st.rerun()
    
    with btn_col3:
        if st.button("選択を適用", type="primary", use_container_width=True):
            st.session_state.csv_columns = selected_columns
            st.success(f"{len(selected_columns)}個の項目を選択しました")
            st.rerun()

# 調整機能（コラプス）
# アンカー用のHTMLを追加
st.markdown('<div id="adjustment-settings"></div>', unsafe_allow_html=True)

# スクロール処理
if st.session_state.get('scroll_to_adjustment', False):
    st.markdown("""
    <script>
    // ページ読み込み後にスクロール
    window.addEventListener('load', function() {
        setTimeout(function() {
            var element = document.getElementById('adjustment-settings');
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 500);
    });
    </script>
    """, unsafe_allow_html=True)
    st.session_state.scroll_to_adjustment = False

with st.expander("⚙️ 画像解析の調整設定", expanded=st.session_state.show_adjustment):
    st.markdown("##### 端末ごとの調整設定")
    st.caption("※ お使いの端末で撮影した画像に合わせて調整してください")
    
    # 初心者向けの使い方説明
    show_help = st.checkbox("📖 調整機能の使い方を表示", value=False, key="show_adjustment_help")
    if show_help:
        st.info("""
        **🎯 調整機能とは？**  
        site7のグラフは端末（iPhone/Android）や画面サイズによって表示が異なります。
        この機能で**お使いの端末に最適な設定**を保存できます。
        
        **📝 使い方（3ステップ）**
        
        1️⃣ **テスト画像を準備**
        - 実際の最大値がわかるグラフ画像を用意
        - 例：パチンコ「最大値が+15,000玉」、パチスロ「最大値が+2,500枚」とわかっている画像
        
        2️⃣ **自動調整を実行**
        - 画像をアップロード → 実際の最大値を入力
        - 「🔧 推奨値を自動適用」ボタンをクリック
        - 必要に応じて手動で微調整
        
        3️⃣ **設定を保存**
        - プリセット名を入力（例：iPhone15用）
        - 「💾 保存」ボタンをクリック
        
        💡 **ポイント**
        - 複数枚の画像で調整するとより正確になります
        - 一度設定すれば、次回から選ぶだけでOK
        - 端末を変えたら新しいプリセットを作成
        """)
        st.divider()
    
    # STEP 1: テスト画像のアップロード
    st.markdown("### 📸 STEP 1: テスト用画像をアップロード")
    st.caption("実際の最大値がわかるグラフ画像を用意してください")
    
    # サンプル画像の表示
    show_sample = st.checkbox("📷 調整例を表示", value=False, key="show_adjustment_sample")
    if show_sample:
        st.info("""
        **調整用画像の例**
        
        ✅ **良い例**
        - 実際の最大値が確認できる画像
        - 例：店舗の実機でパチンコ「最大+15,000玉」、パチスロ「最大+2,500枚」と確認した画像
        - グラフが明確に写っている画像
        
        ❌ **悪い例**
        - 最大値が不明な画像
        - グラフが不鮮明な画像
        - 画面が暗い・ぼやけている画像
        
        💡 **ヒント**
        - 複数枚使用するとより正確になります
        - 異なる最大値の画像を混ぜてもOK
        """)
        
        # サンプル画像が存在する場合は表示
        sample_image_path = "images/sample.png"
        if os.path.exists(sample_image_path):
            st.markdown("**📸 調整画面の見本**")
            st.image(sample_image_path, caption="各エリアの説明付きサンプル", use_column_width=True)
            st.caption("このような画像で、実際の最大値（この例では+2290玉）を入力して調整します")
    
    test_images = st.file_uploader(
        "画像を選択",
        type=['jpg', 'jpeg', 'png'],
        help="調整用の画像を複数アップロードできます。複数枚の場合は統計的に処理されます",
        key="test_images",
        accept_multiple_files=True
    )
    
    # 単一画像の場合の互換性のため
    test_image = test_images[0] if test_images else None
    
    # 画像がアップロードされた場合のみプリセット選択を表示
    if test_image:
        st.divider()
        
        # STEP 2: プリセット選択セクション
        st.markdown("### 📋 STEP 2: 設定の読み込み（任意）")
        st.caption("保存済みの設定がある場合は選択してください")
        
        # プリセットに関する説明を追加（expanderを使わずinfoボックスで表示）
        st.info("""
        ℹ️ **プリセットの互換性について**
        
        📱 **端末差による調整の必要性**
        
        保存されたプリセットは作成時の端末環境に最適化されています。
        異なる端末で使用する場合、以下の点にご注意ください：
        
        • **画面解像度の違い** - ピクセル単位の設定が影響を受ける可能性
        • **表示倍率** - ブラウザのズーム設定やデバイスの画面密度
        • **カラープロファイル** - 端末による色の表現の違い
        
        🎯 **最良の結果を得るために**
        - 同一端末・同一ブラウザでの使用が最も精度が高い
        - 異なる端末の場合は読み込み後に微調整を推奨
        - 端末ごとに専用プリセットを作成することを推奨
        """)
        
        # 保存されたプリセット一覧
        preset_names = ["デフォルト"] + list(st.session_state.get('saved_presets', {}).keys())
        
        # プリセットボタンを横に並べる
        if len(preset_names) <= 4:
            preset_cols = st.columns(len(preset_names))
            # プリセットが4個以下の場合
            for i, preset_name in enumerate(preset_names):
                with preset_cols[i]:
                    button_type = "primary" if preset_name == st.session_state.get('current_preset_name', 'デフォルト') else "secondary"
                    if st.button(f"📥 {preset_name}", use_container_width=True, key=f"load_preset_{preset_name}", type=button_type):
                        log(f"[Button] Preset button clicked (settings page): '{preset_name}'")
                        if preset_name == "デフォルト":
                            reset_settings()
                        else:
                            load_preset(preset_name)
                            # プリセットに遊技種別情報がある場合は適用
                            if 'game_type' in get_settings():
                                st.session_state.game_type = get_settings()['game_type']
                        
                        # 現在のプリセット名を保存（編集モードで使用）
                        st.session_state.current_preset_name = preset_name
                        st.session_state.editing_preset_name = preset_name
                        
                        st.success(f"✅ '{preset_name}' の設定を読み込みました")
                        time.sleep(0.5)
                        st.rerun()
        else:
            # 5個以上の場合は複数行に分ける
            num_rows = (len(preset_names) + 3) // 4  # 4列で何行必要か
            for row in range(num_rows):
                cols = st.columns(4)
                for col in range(4):
                    idx = row * 4 + col
                    if idx < len(preset_names):
                        preset_name = preset_names[idx]
                        with cols[col]:
                            button_type = "primary" if preset_name == st.session_state.get('current_preset_name', 'デフォルト') else "secondary"
                            if st.button(f"📥 {preset_name}", use_container_width=True, key=f"load_preset_{preset_name}", type=button_type):
                                log(f"[Button] Preset button clicked (settings page): '{preset_name}'")
                                if preset_name == "デフォルト":
                                    reset_settings()
                                else:
                                    load_preset(preset_name)
                                    # プリセットに遊技種別情報がある場合は適用
                                    if 'game_type' in get_settings():
                                        st.session_state.game_type = get_settings()['game_type']
                                
                                # 現在のプリセット名を保存（編雈モードで使用）
                                st.session_state.current_preset_name = preset_name
                                st.session_state.editing_preset_name = preset_name
                                
                                st.success(f"✅ '{preset_name}' の設定を読み込みました")
                                time.sleep(0.5)
                                st.rerun()
        
        st.divider()
    
    
    # 設定値の初期化
    if test_image:
        # 画像を読み込み
        img_array = np.array(Image.open(test_image).convert('RGB'))
        height, width = img_array.shape[:2]
        
        # オレンジバーを検出（共通関数使用）
        orange_bottom = detect_orange_bar(img_array)
        
        # グレースケール変換
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        st.info(f"画像サイズ: {width}x{height}px")
        
        # レイアウト用のメインカラム（画像を読み込んだ後）
        main_col1, main_col2 = st.columns([3, 2])
        
        # 画像がアップロードされている場合のみレイアウトを適用
        with main_col2:
            # STEP 3: 設定用の入力フィールド
            st.markdown("### 🔍 STEP 3: 詳細設定（通常はデフォルトでOK）")
            st.caption("必要に応じて微調整できます")
            
            st.markdown("#### ゼロライン検索設定")
            col1, col2 = st.columns(2)
    
            with col1:
                search_start_offset = st.number_input(
                    "検索開始位置（オレンジバーから）",
                    min_value=0, max_value=800, value=get_settings()['search_start_offset'],
                    step=10, help="オレンジバーから何ピクセル下から検索を開始するか"
                )
            
            with col2:
                search_end_offset = st.number_input(
                    "検索終了位置（オレンジバーから）",
                    min_value=100, max_value=1200, value=get_settings()['search_end_offset'],
                    step=50, help="オレンジバーから何ピクセル下まで検索するか"
                )
            
            st.markdown("#### ✂️ 切り抜きサイズの設定")
            col3, col4 = st.columns(2)
    
            with col3:
                crop_top = st.number_input(
                    "上方向の切り抜きサイズ",
                    min_value=100, max_value=500, value=get_settings()['crop_top'],
                    step=1, help="ゼロラインから上方向に何ピクセル切り抜くか"
                )
                crop_bottom = st.number_input(
                    "下方向の切り抜きサイズ",
                    min_value=100, max_value=500, value=get_settings()['crop_bottom'],
                    step=1, help="ゼロラインから下方向に何ピクセル切り抜くか"
                )
            
            with col4:
                left_margin = st.number_input(
                    "左側の余白",
                    min_value=0, max_value=300, value=get_settings()['left_margin'],
                    step=25, help="左側から何ピクセル除外するか"
                )
                right_margin = st.number_input(
                    "右側の余白",
                    min_value=0, max_value=300, value=get_settings()['right_margin'],
                    step=25, help="右側から何ピクセル除外するか"
                )
            
            # グリッドライン調整
            st.markdown("#### 📏 グリッドライン調整")
            st.markdown("##### ⚙️ 手動調整")
            # 遊技種別に応じた上下限値を取得
            graph_limit = get_graph_limit(st.session_state.get('game_type', 'パチンコ'))
            st.caption(f"ゼロラインから±{graph_limit:,}ラインまでの距離を調整できます（単位：ピクセル）")

            grid_distance = st.number_input(
                f"ゼロラインから±{graph_limit:,}ラインまでの距離",
                min_value=100, max_value=500, value=get_settings().get('grid_distance', 327),
                step=1, help=f"ゼロラインから上下対称に±{graph_limit:,}ラインまでの距離（デフォルト: 330px）"
            )
            
            # 中間ライン用のダミー変数を設定（他のコードで参照されるため）
            
            # ゼロライン微調整（STEP 4の直前に配置）
            st.markdown("### 🎯 ゼロライン微調整")
            st.caption("検出されたゼロラインを1ピクセル単位で調整できます")
            
            zero_line_adjustment = st.number_input(
                "ゼロライン位置調整",
                min_value=-50, max_value=50, 
                value=get_settings().get('zero_line_adjustment', 0),
                step=1, 
                help="検出されたゼロラインを上下に調整（プラス値で下方向、マイナス値で上方向）",
                key="zero_line_adjustment_main"
            )
            # セッションステートに保存
            update_settings('zero_line_adjustment', zero_line_adjustment)

            # STEP 4: 最大値アライメント機能を統合
            if test_images:
                st.markdown("### 🎯 STEP 4: 実際の最大値を入力して自動調整")
                st.caption(f"アップロードされた{len(test_images)}枚の画像から最適な設定を自動計算します")
                
                # 追加テキスト
                st.info("📝 ここに追加のテキストを表示します。このテキストはSTEP 4の後ろに表示されます。")
                
                # 複数画像の解析結果を保存
                all_detections = []
                all_max_positions = []
                
                # 現在の設定を取得（入力フィールドの値を使用）
                current_settings_align = {
                    'search_start_offset': search_start_offset,
                    'search_end_offset': search_end_offset,
                    'crop_top': crop_top,
                    'crop_bottom': crop_bottom,
                    'left_margin': left_margin,
                    'right_margin': right_margin,
                    'grid_distance': grid_distance
                }
                
                # 各画像を解析
                for img_idx, test_img in enumerate(test_images):
                    # 画像を読み込み
                    img_array_tmp = np.array(Image.open(test_img).convert('RGB'))
                    height_tmp, width_tmp = img_array_tmp.shape[:2]
                    
                    # オレンジバーを検出
                    hsv_tmp = cv2.cvtColor(img_array_tmp, cv2.COLOR_RGB2HSV)
                    orange_mask_tmp = cv2.inRange(hsv_tmp, np.array([10, 100, 100]), np.array([30, 255, 255]))
                    orange_bottom_tmp = 0
                    
                    for y in range(height_tmp//2):
                        if np.sum(orange_mask_tmp[y, :]) > width_tmp * 0.3 * 255:
                            orange_bottom_tmp = y
                    
                    if orange_bottom_tmp > 0:
                        for y in range(orange_bottom_tmp, min(orange_bottom_tmp + 100, height_tmp)):
                            if np.sum(orange_mask_tmp[y, :]) < width_tmp * 0.1 * 255:
                                orange_bottom_tmp = y
                                break
                    else:
                        orange_bottom_tmp = 150
                    
                    # グレースケール変換
                    gray_tmp = cv2.cvtColor(img_array_tmp, cv2.COLOR_RGB2GRAY)
                    
                    # 現在の画像で解析を実行
                    analyzer_align = WebCompatibleAnalyzer()
                    
                    # ゼロライン検出（最大値アライメント用）
                    align_search_start = orange_bottom_tmp + search_start_offset
                    align_search_end = min(height_tmp - 100, orange_bottom_tmp + search_end_offset)
                    
                    # ゼロライン検出
                    align_best_score = 0
                    align_zero_line_y = (align_search_start + align_search_end) // 2
                    
                    for y in range(align_search_start, align_search_end):
                        row = gray_tmp[y, 100:width_tmp-100]
                        darkness = 1.0 - (np.mean(row) / 255.0)
                        uniformity = 1.0 - (np.std(row) / 128.0)
                        score = darkness * 0.5 + uniformity * 0.5
                        
                        if score > align_best_score:
                            align_best_score = score
                            align_zero_line_y = y
                    
                    # ゼロライン調整値を適用
                    zero_line_adjustment = get_settings().get('zero_line_adjustment', 0)
                    align_zero_line_y += zero_line_adjustment
                    
                    # 切り抜き
                    align_top = max(0, align_zero_line_y - crop_top)
                    align_bottom = min(height_tmp, align_zero_line_y + crop_bottom)
                    align_left = left_margin
                    align_right = width_tmp - right_margin
                    
                    # グリッドライン調整値も適用（現在の入力値を使用）
                    align_zero_in_crop = align_zero_line_y - align_top
                    align_grid_distance = grid_distance

                    # カスタム設定で解析
                    analyzer_align.zero_y = align_zero_in_crop
                    graph_limit = get_graph_limit(st.session_state.get('game_type', 'パチンコ'))
                    analyzer_align.scale = graph_limit / align_grid_distance if align_grid_distance > 0 else 122
                    
                    # 切り抜き画像で解析
                    cropped_for_align = img_array_tmp[int(align_top):int(align_bottom), int(align_left):int(align_right)]
                    # BGRに変換（OpenCVの標準形式）
                    cropped_bgr_align = cv2.cvtColor(cropped_for_align, cv2.COLOR_RGB2BGR)
                    
                    # 解析実行（画像データを直接渡す）
                    data_points_align, color_align, detected_zero_align, graph_info_align = analyzer_align.extract_graph_data(cropped_bgr_align)
                    
                    if data_points_align:
                        analysis_align = analyzer_align.analyze_values(data_points_align, st.session_state.game_type)
                        detected_max_align = analysis_align['max_value']
                        
                        # 最大値の位置を取得
                        max_index = analysis_align['max_index']
                        if max_index < len(data_points_align):
                            max_x, max_y_value = data_points_align[max_index]
                            # 画像座標系での最大値のY座標
                            max_y_pixel = int(align_zero_in_crop - (max_y_value / analyzer_align.scale))
                            
                            all_detections.append({
                                'detected_max': detected_max_align,
                                'max_y_pixel': max_y_pixel,
                                'zero_in_crop': align_zero_in_crop,
                                'crop_height': cropped_for_align.shape[0],
                                'image_name': test_img.name
                            })
                            
                            all_max_positions.append({
                                'x': int(max_x),
                                'y': max_y_pixel,
                                'value': max_y_value
                            })
                
                if all_detections:
                    # 統計情報を計算
                    detected_maxes = [d['detected_max'] for d in all_detections]
                    avg_detected_max = int(np.mean(detected_maxes))
                    median_detected_max = int(np.median(detected_maxes))
                    
                    # 検出結果を表示
                    st.markdown("##### 📊 検出結果と実際の値の入力")
                    
                    # 各画像に対して個別に実際の値を入力
                    visual_max_values = []
                    
                    if len(all_detections) > 1:
                        # 統計情報を表示
                        unit = get_unit(st.session_state.get('game_type', 'パチンコ'))
                        detection_cols = st.columns(3)
                        with detection_cols[0]:
                            st.metric("検出平均値", f"{avg_detected_max:,}{unit}")
                        with detection_cols[1]:
                            st.metric("検出中央値", f"{median_detected_max:,}{unit}")
                        with detection_cols[2]:
                            st.metric("検出画像数", f"{len(all_detections)}/{len(test_images)}枚")
                        
                        st.markdown("---")
                        st.markdown("##### 🎯 各画像の実際の最大値を入力")
                        st.caption("各画像を確認して、実際の最大値を入力してください")
                        
                        # 各画像に対して入力フィールドを作成
                        cols_per_row = 2
                        for i, detection in enumerate(all_detections):
                            if i % cols_per_row == 0:
                                cols = st.columns(cols_per_row)
                            
                            with cols[i % cols_per_row]:
                                st.markdown(f"**{detection['image_name']}**")
                                unit = get_unit(st.session_state.get('game_type', 'パチンコ'))
                                st.caption(f"検出値: {detection['detected_max']:,}{unit}")
                                
                                # プレビューボタン
                                if st.button(f"🔍 画像を確認", key=f"preview_btn_{i}"):
                                    st.session_state['preview_image_index'] = i
                                    # 検出情報も保存
                                    st.session_state['preview_detection_info'] = detection
                                
                                # セッションステートから値を取得（なければデフォルト値を使用）
                                # ウィジェットのキーとは別のキーを使用
                                default_val = st.session_state.get(f"saved_visual_max_{i}", detection['detected_max'])
                                visual_max = st.number_input(
                                    "実際の最大値",
                                    min_value=0,
                                    max_value=50000,
                                    value=default_val,
                                    step=100,
                                    help=f"{detection['image_name']}の実際の最高値",
                                    key=f"visual_max_{i}",
                                    label_visibility="visible"
                                )
                                # 値が変更されたら保存
                                if visual_max != default_val:
                                    st.session_state[f"saved_visual_max_{i}"] = visual_max
                                visual_max_values.append(visual_max)
                    else:
                        # 単一画像の場合
                        detection = all_detections[0]
                        unit = get_unit(st.session_state.get('game_type', 'パチンコ'))
                        st.info(f"🔍 検出値: **{detection['detected_max']:,}{unit}**")
                        
                        # セッションステートから値を取得（なければデフォルト値を使用）
                        default_val = st.session_state.get("saved_visual_max_single", detection['detected_max'])
                        visual_max = st.number_input(
                            "実際の最大値を入力",
                            min_value=0,
                            max_value=50000,
                            value=default_val,
                            step=100,
                            help="グラフ画像を見て確認した最高値",
                            key="visual_max_single",
                            label_visibility="visible"
                        )
                        # 値が変更されたら保存
                        if visual_max != default_val:
                            st.session_state["saved_visual_max_single"] = visual_max
                        visual_max_values.append(visual_max)
                    
                    if any(v > 0 for v in visual_max_values):
                        # 各画像での補正率を計算
                        corrections = []
                        for i, (detection, visual_max) in enumerate(zip(all_detections, visual_max_values)):
                            if detection['detected_max'] > 0 and visual_max > 0:
                                correction_factor = visual_max / detection['detected_max']
                                actual_distance = detection['zero_in_crop'] - detection['max_y_pixel']
                                if actual_distance > 0:
                                    new_scale = visual_max / actual_distance
                                    
                                    # 新しい距離を計算（上下対称）
                                    graph_limit = get_graph_limit(st.session_state.get('game_type', 'パチンコ'))
                                    new_distance = graph_limit / new_scale
                                    current_distance = current_settings_align['grid_distance']
                                    adjustment = int(new_distance - current_distance)

                                    corrections.append({
                                        'adjustment': adjustment,
                                        'correction_factor': correction_factor
                                    })
                        
                        if corrections:
                            # 平均調整値を計算
                            avg_adjustment = int(np.mean([c['adjustment'] for c in corrections]))
                            avg_correction_factor = np.mean([c['correction_factor'] for c in corrections])

                            # セッションステートに保存
                            st.session_state.avg_correction_factor = avg_correction_factor

                            if abs(avg_correction_factor - 1.0) > 0.001:
                                # 推奨調整値を表示
                                # st.info(f"平均補正率: **{avg_correction_factor:.2f}x** （{len(corrections)}枚の画像から計算）")  # 補正率表示を非表示化

                                graph_limit = get_graph_limit(st.session_state.get('game_type', 'パチンコ'))
                                st.info(f"**ゼロラインから±{graph_limit:,}ラインまでの距離:** {grid_distance}px → {grid_distance + avg_adjustment}px (調整: {avg_adjustment:+d}px)")

                                # 自動適用ボタン
                                if st.button("🔧 推奨値を自動適用", type="secondary", key="apply_max_alignment"):
                                    # セッションステートに新しい値を設定（現在の入力値に調整を加える）
                                    update_settings('grid_distance', grid_distance + avg_adjustment)

                                    # 最初の画像の最大値位置を保存（非線形スケール用）
                                    if all_max_positions:
                                        st.session_state['max_value_position'] = all_max_positions[0]

                                    st.success("✅ 推奨値を適用しました！画面が更新されます...")
                                    time.sleep(1)
                                    st.rerun()
                            else:
                                st.success("✅ 検出値と実際の値が一致しています")
                else:
                    st.warning("グラフデータを検出できませんでした")
            
    
    
    if test_images:
        st.markdown("### 🖼️ リアルタイムプレビュー")
        
        # プレビューする画像を決定（ボタンで選択されたもの、または最初の画像）
        if 'preview_image_index' in st.session_state and st.session_state['preview_image_index'] < len(test_images):
            selected_image_idx = st.session_state['preview_image_index']
            selected_image = test_images[selected_image_idx]
            if len(test_images) > 1:
                st.info(f"📸 表示中: **{selected_image.name}**")
        else:
            selected_image = test_image
            selected_image_idx = 0
        
        # 選択された画像を読み込み
        img_array_preview = np.array(Image.open(selected_image).convert('RGB'))
        height_preview, width_preview = img_array_preview.shape[:2]
        
        # オレンジバーを検出（選択された画像用）
        hsv_preview = cv2.cvtColor(img_array_preview, cv2.COLOR_RGB2HSV)
        orange_mask_preview = cv2.inRange(hsv_preview, np.array([10, 100, 100]), np.array([30, 255, 255]))
        orange_bottom_preview = 0
        
        for y in range(height_preview//2):
            if np.sum(orange_mask_preview[y, :]) > width_preview * 0.3 * 255:
                orange_bottom_preview = y
        
        if orange_bottom_preview > 0:
            for y in range(orange_bottom_preview, min(orange_bottom_preview + 100, height_preview)):
                if np.sum(orange_mask_preview[y, :]) < width_preview * 0.1 * 255:
                    orange_bottom_preview = y
                    break
        else:
            orange_bottom_preview = 150
        
        # グレースケール変換
        gray_preview = cv2.cvtColor(img_array_preview, cv2.COLOR_RGB2GRAY)
        
        # 現在の設定で切り抜き処理を実行
        search_start = orange_bottom_preview + search_start_offset
        search_end = min(height_preview - 100, orange_bottom_preview + search_end_offset)
        
        # ゼロライン検出
        best_score = 0
        zero_line_y = (search_start + search_end) // 2
        
        for y in range(search_start, search_end):
            row = gray_preview[y, 100:width_preview-100]
            darkness = 1.0 - (np.mean(row) / 255.0)
            uniformity = 1.0 - (np.std(row) / 128.0)
            score = darkness * 0.5 + uniformity * 0.5
            
            if score > best_score:
                best_score = score
                zero_line_y = y
        
        # ゼロライン調整値を適用
        zero_line_adjustment = get_settings().get('zero_line_adjustment', 0)
        zero_line_y += zero_line_adjustment
        
        # 切り抜き
        top = max(0, zero_line_y - crop_top)
        bottom = min(height_preview, zero_line_y + crop_bottom)
        left = left_margin
        right = width_preview - right_margin
        
        # オーバーレイ画像を作成
        overlay_img = img_array_preview.copy()
        
        # 検索範囲を可視化（濃い緑の枠線）
        cv2.rectangle(overlay_img, (100, search_start), (width_preview-100, search_end), (0, 255, 0), 3)
        # 半透明の緑で塗りつぶし
        overlay = overlay_img.copy()
        cv2.rectangle(overlay, (100, search_start), (width_preview-100, search_end), (0, 255, 0), -1)
        overlay_img = cv2.addWeighted(overlay_img, 0.8, overlay, 0.2, 0)
        
        # 検索範囲の説明テキストを右上に追加
        text = 'Zero Line Search Area'
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        cv2.putText(overlay_img, text, (width_preview - text_size[0] - 110, search_start + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)
        
        text2 = f'({search_start_offset} ~ {search_end_offset}px)'
        text_size2 = cv2.getTextSize(text2, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.putText(overlay_img, text2, (width_preview - text_size2[0] - 110, search_start + 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)
        
        # 検出したゼロラインを描画（赤）
        cv2.line(overlay_img, (0, zero_line_y), (width_preview, zero_line_y), (255, 0, 0), 3)
        # 調整値がある場合は表示
        adjustment_text = f' (adj: {zero_line_adjustment:+d}px)' if zero_line_adjustment != 0 else ''
        cv2.putText(overlay_img, f'Zero Line (score: {best_score:.3f}){adjustment_text}', (10, zero_line_y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # 切り抜き範囲を描画（濃い青）
        cv2.rectangle(overlay_img, (left, int(top)), (right, int(bottom)), (0, 0, 255), 4)
        
        # 切り抜き範囲の説明テキストを右上に追加
        text3 = 'Crop Area'
        text_size3 = cv2.getTextSize(text3, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        cv2.putText(overlay_img, text3, (right - text_size3[0] - 5, int(top) + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 200), 2)
        
        text4 = f'(Top: {crop_top}px, Bottom: {crop_bottom}px)'
        text_size4 = cv2.getTextSize(text4, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.putText(overlay_img, text4, (right - text_size4[0] - 5, int(top) + 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 200), 2)
        
        # オレンジバーの位置を表示（濃いオレンジ）
        cv2.line(overlay_img, (0, orange_bottom_preview), (width_preview, orange_bottom_preview), (255, 140, 0), 3)
        cv2.putText(overlay_img, 'Orange Bar', (10, orange_bottom_preview + 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 140, 0), 2)
        
        # ゼロラインから±30000ラインまでの距離を取得
        zero_in_crop = zero_line_y - top
        grid_distance_preview = grid_distance

        # グリッドラインを元画像にも追加
        # +30000ライン（元画像座標、ゼロラインから上にgrid_distance）
        y_30k_orig = int(zero_line_y - grid_distance_preview)
        if 0 <= y_30k_orig < height_preview:
            cv2.line(overlay_img, (0, y_30k_orig), (width_preview, y_30k_orig), (128, 128, 128), 2)
            cv2.putText(overlay_img, '+30000', (10, max(20, y_30k_orig + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)

        # -30000ライン（元画像座標、ゼロラインから下にgrid_distance）
        y_minus_30k_orig = int(zero_line_y + grid_distance_preview)
        if 0 <= y_minus_30k_orig < height_preview:
            cv2.line(overlay_img, (0, y_minus_30k_orig), (width_preview, y_minus_30k_orig), (128, 128, 128), 2)
            cv2.putText(overlay_img, '-30000', (10, max(10, y_minus_30k_orig - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
        
        
        # プレビューを左カラムに表示（縦に配置）
        with main_col1:
            # 元画像（調整範囲を表示）
            st.markdown("#### 元画像（調整範囲を表示）")
            st.image(overlay_img, use_column_width=True)
            
            # 切り抜き結果（元画像の下に配置）
            st.markdown("#### 切り抜き結果")
            cropped_preview_original = img_array_preview[int(top):int(bottom), int(left):int(right)].copy()
            cropped_preview = cropped_preview_original.copy()  # 表示用のコピーを作成
            
            # グリッドラインを追加（表示用画像にのみ）
            zero_in_crop = zero_line_y - top
            cv2.line(cropped_preview, (0, int(zero_in_crop)), (cropped_preview.shape[1], int(zero_in_crop)), (255, 0, 0), 2)
            
            # グリッドラインを追加（調整値付き）
            # +30000ライン（ゼロラインから上にgrid_distance）
            y_30k = zero_in_crop - grid_distance_preview
            if 0 <= y_30k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, int(y_30k)), (cropped_preview.shape[1], int(y_30k)), (0, 150, 0), 3)
                cv2.putText(cropped_preview, '+30000', (10, max(20, int(y_30k) + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 0), 2)

            # -30000ライン（ゼロラインから下にgrid_distance）
            y_minus_30k = zero_in_crop + grid_distance_preview
            if 0 <= y_minus_30k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, int(y_minus_30k)), (cropped_preview.shape[1], int(y_minus_30k)), (150, 0, 0), 3)
                cv2.putText(cropped_preview, '-30000', (10, max(10, int(y_minus_30k) - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 0, 0), 2)


            # 選択された画像の実際の最大値を表示
            if 'preview_image_index' in st.session_state:
                preview_idx = st.session_state.get('preview_image_index', 0)

                # プレビュー用の解析を実行して最大値を検出
                analyzer_preview = WebCompatibleAnalyzer()
                analyzer_preview.zero_y = zero_in_crop

                # スケールを計算（ゼロラインからの距離を使用）
                analyzer_preview.scale = 30000 / grid_distance_preview if grid_distance_preview > 0 else 122


                # BGRに変換（グリッドラインなしの元画像を使用）
                cropped_bgr_preview = cv2.cvtColor(cropped_preview_original, cv2.COLOR_RGB2BGR)
                
                # グラフデータを抽出
                data_points_preview, color_preview, _, graph_info_preview = analyzer_preview.extract_graph_data(cropped_bgr_preview)
                
                if data_points_preview:
                    # 最大値を検出
                    values_preview = [value for x, value in data_points_preview]
                    max_val_detected = max(values_preview)
                    max_idx = values_preview.index(max_val_detected)
                    max_x, _ = data_points_preview[max_idx]
                    
                    # 入力された実際の最大値を取得
                    actual_max_value = None
                    if f'visual_max_{preview_idx}' in st.session_state:
                        actual_max_value = st.session_state[f'visual_max_{preview_idx}']
                    
                    # 実際の値が入力されている場合はそれを使用、そうでなければ検出値を使用
                    display_max_value = actual_max_value if actual_max_value is not None else max_val_detected
                    
                    # グラフ上の実際の最大値のY座標（線形スケール）
                    max_y_in_crop = int(zero_in_crop - (max_val_detected / analyzer_preview.scale))
                    
                    # 表示する値は実際の値があればそれを使用
                    if actual_max_value and max_val_detected > 0:
                        correction_factor = actual_max_value / max_val_detected
                        display_value = actual_max_value
                    else:
                        correction_factor = 1.0
                        display_value = max_val_detected
                    
                    if 0 <= max_y_in_crop < cropped_preview.shape[0]:
                        # 赤い水平線を描画（グラフの最高点の高さ）
                        cv2.line(cropped_preview, (0, max_y_in_crop), (cropped_preview.shape[1], max_y_in_crop), (0, 0, 255), 3)
                        # 最大値の点に円を描画（グラフ上の実際の位置）
                        cv2.circle(cropped_preview, (int(max_x), max_y_in_crop), 4, (0, 0, 255), -1)
                        cv2.circle(cropped_preview, (int(max_x), max_y_in_crop), 5, (0, 0, 200), 2)
                        # ラベルを追加（表示する値は実際の値）
                        label_text = f"MAX: {int(display_value):,}"
                        cv2.putText(cropped_preview, label_text, (cropped_preview.shape[1] - 180, max_y_in_crop - 5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    # 補正情報を表示
                    if actual_max_value and abs(correction_factor - 1.0) > 0.01:
                        unit = get_unit(st.session_state.get('game_type', 'パチンコ'))
                        info_text = f"🔍 検出値: {int(max_val_detected):,}{unit} → 実際の値: {int(actual_max_value):,}{unit}"
                        st.info(info_text)
            
            st.image(cropped_preview, use_column_width=True)
            
            # 情報表示
            st.caption(f"🔍 検出情報: オレンジバー位置 Y={orange_bottom}, ゼロライン Y={zero_line_y}, 検索範囲 Y={search_start}〜{search_end}")
            st.caption(f"✂️ 切り抜き範囲: 上{crop_top}px, 下{crop_bottom}px, 左{left_margin}px, 右{right_margin}px")
        
    # 設定の保存とプリセット削除を同じ配置で表示（順序を入れ替え）
    
    # 設定の保存セクション（全体で共通、保存ボタンだけ別）  
    # test_imageがある場合は変数を利用、ない場合はセッションステート利用
    if test_image:
        # test_imageがある場合、入力値から直接設定を作成
        def save_settings():
            settings = {
                'search_start_offset': search_start_offset,
                'search_end_offset': search_end_offset,
                'crop_top': crop_top,
                'crop_bottom': crop_bottom,
                'left_margin': left_margin,
                'right_margin': right_margin,
                'grid_distance': grid_distance,
                'zero_line_adjustment': get_settings().get('zero_line_adjustment', 0),  # ゼロライン調整値を追加
                'game_type': st.session_state.game_type  # 遊技種別を追加
            }
            return settings
    else:
        # test_imageがない場合、セッションステートから取得
        def save_settings():
            settings = get_settings().copy()
            settings['game_type'] = st.session_state.game_type  # 遊技種別を追加
            return settings
    
    # STEP 5: 設定の保存の見出しを適切な場所に配置（画像がある場合のみ表示）
    if test_image:
        with main_col2:
            st.markdown("### 💾 STEP 5: 設定の保存")
            st.caption("調整が完了したら、端末名をつけて保存してください")
    
    # 設定の保存の内容（test_imageの有無で配置を変更）
    def render_save_settings():
        # 既存のプリセットを編集する場合
        if st.session_state.get('saved_presets', {}):
            edit_mode = st.checkbox("既存のプリセットを編集", key="edit_preset_mode")
            
            if edit_mode:
                # 編集するプリセットを選択
                selected_preset = st.selectbox(
                    "編集するプリセットを選択",
                    ["新規作成"] + list(st.session_state.get('saved_presets', {}).keys()),
                    key="edit_preset_select",
                    help="既存のプリセットを選択して設定を更新できます"
                )
                
                if selected_preset != "新規作成":
                    # 選択されたプリセット名を入力フィールドに設定
                    preset_name = st.text_input(
                        "プリセット名",
                        value=selected_preset,
                        help="プリセット名を変更することもできます"
                    )
                else:
                    # 編集中のプリセット名がある場合はそれを使用
                    default_name = st.session_state.get('editing_preset_name', '')
                    if default_name == 'デフォルト':
                        default_name = ''
                    preset_name = st.text_input(
                        "プリセット名",
                        value=default_name,
                        placeholder="例: iPhone15用、S__シリーズ用",
                        help="保存する設定の名前を入力してください"
                    )
            else:
                # 新規作成モード（編集中のプリセット名がある場合はそれを使用）
                default_name = st.session_state.get('editing_preset_name', '')
                if default_name == 'デフォルト':
                    default_name = ''
                preset_name = st.text_input(
                    "プリセット名",
                    value=default_name,
                    placeholder="例: iPhone15用、S__シリーズ用",
                    help="保存する設定の名前を入力してください"
                )
        else:
            # プリセットがない場合は新規作成のみ（編集中のプリセット名がある場合はそれを使用）
            default_name = st.session_state.get('editing_preset_name', '')
            if default_name == 'デフォルト':
                default_name = ''
            preset_name = st.text_input(
                "プリセット名",
                value=default_name,
                placeholder="例: iPhone15用、S__シリーズ用",
                help="保存する設定の名前を入力してください"
            )
        
        # ボタン用のカラムレイアウト
        save_col1, save_col2 = st.columns([1, 1])
        
        with save_col1:
            # 編集モードかどうかでボタンのラベルを変更
            save_button_label = "💾 プリセットを更新" if (st.session_state.get('saved_presets', {}) and 
                                                         'edit_preset_mode' in st.session_state and 
                                                         st.session_state.edit_preset_mode and 
                                                         'edit_preset_select' in st.session_state and
                                                         st.session_state.edit_preset_select != "新規作成") else "💾 プリセットを保存"
            
            if st.button(save_button_label, type="primary", use_container_width=True):
                if preset_name:
                    # 現在の設定を取得
                    settings = save_settings()
                    
                    # 補正係数があれば追加
                    if 'avg_correction_factor' in st.session_state:
                        settings['correction_factor'] = st.session_state.avg_correction_factor
                    
                    # プリセットに保存
                    st.session_state.get('saved_presets', {})[preset_name] = settings.copy()
                    # 現在の設定も更新
                    # 現在の設定を更新
                    for key, value in settings.items():
                        update_settings(key, value)
                    
                    # データベースに保存
                    if save_preset_to_db(preset_name, settings):
                        # データベースから再読み込みして確実に反映
                        st.session_state.saved_presets = load_presets_from_db()
                        
                        # 編集モードかどうかでメッセージを変更
                        if (st.session_state.get('saved_presets', {}) and 
                            'edit_preset_mode' in st.session_state and 
                            st.session_state.edit_preset_mode and 
                            'edit_preset_select' in st.session_state and
                            st.session_state.edit_preset_select != "新規作成"):
                            st.success(f"✅ プリセット '{preset_name}' を更新しました")
                        else:
                            st.success(f"✅ プリセット '{preset_name}' を保存しました")
                        st.rerun()
                else:
                    st.error("プリセット名を入力してください")
        
        with save_col2:
            if st.button("🔄 デフォルトに戻す", use_container_width=True):
                reset_settings()
                st.rerun()
    
    # 設定の保存を描画（画像がある場合のみ）
    if test_image:
        with main_col2:
            render_save_settings()
    
    # プリセット削除セクション（設定の保存の直後に配置）
    if test_image:
        with main_col2:
            # プリセット削除
            if st.session_state.get('saved_presets', {}):
                st.markdown("### 🗑️ プリセットの削除")
                
                # 現在編集中のプリセットをデフォルトにする
                default_delete_preset = None
                if ('edit_preset_mode' in st.session_state and 
                    st.session_state.edit_preset_mode and 
                    'edit_preset_select' in st.session_state and
                    st.session_state.edit_preset_select != "新規作成"):
                    default_delete_preset = st.session_state.edit_preset_select
                
                # デフォルト値を見つける
                preset_list = list(st.session_state.get('saved_presets', {}).keys())
                default_index = 0
                if default_delete_preset and default_delete_preset in preset_list:
                    default_index = preset_list.index(default_delete_preset)
                
                # プリセット選択（全幅）
                preset_to_delete = st.selectbox(
                    "削除するプリセット",
                    preset_list,
                    index=default_index,
                    key="delete_preset"
                )
                
                # 削除ボタン
                if st.button("🗑️ 削除", type="secondary", use_container_width=True):
                    if preset_to_delete:
                        del st.session_state.get('saved_presets', {})[preset_to_delete]
                        
                        # データベースから削除
                        if delete_preset_from_db(preset_to_delete):
                            st.success(f"✅ プリセット '{preset_to_delete}' を削除しました")
                            st.rerun()

# フッター
st.markdown("---")

# プリセットのエクスポート/インポート機能
with st.expander("📤 プリセットのエクスポート/インポート"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📤 エクスポート")
        if st.session_state.get('saved_presets', {}):
            # プリセットデータをJSON形式で表示
            preset_data = {
                "presets": st.session_state.get('saved_presets', {}),
                "version": "2.1",
                "exported_at": datetime.now().isoformat()
            }
            preset_json = json.dumps(preset_data, ensure_ascii=False, indent=2)
            st.text_area("プリセットデータ（コピーして保存）", preset_json, height=200)
            
            # ダウンロードボタン
            st.download_button(
                label="📥 JSONファイルとしてダウンロード",
                data=preset_json,
                file_name=f"presets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        else:
            st.info("保存されたプリセットがありません")
    
    with col2:
        st.markdown("#### 📥 インポート")
        import_data = st.text_area("プリセットデータを貼り付け", height=200, placeholder="エクスポートしたJSONデータを貼り付けてください")
        
        if st.button("📥 インポート実行"):
            if import_data:
                try:
                    imported = json.loads(import_data)
                    if "presets" in imported:
                        # 既存のプリセットに追加
                        for name, preset in imported["presets"].items():
                            # zero_line_adjustmentがない場合は0を設定
                            if 'zero_line_adjustment' not in preset:
                                preset['zero_line_adjustment'] = 0
                            st.session_state.get('saved_presets', {})[name] = preset
                            # データベースにも保存
                            save_preset_to_db(name, preset)
                        st.success(f"✅ {len(imported['presets'])}個のプリセットをインポートしました")
                        st.rerun()
                    else:
                        st.error("無効なプリセットデータです")
                except json.JSONDecodeError:
                    st.error("JSONの形式が正しくありません")
                except Exception as e:
                    st.error(f"インポートエラー: {str(e)}")
            else:
                st.warning("インポートするデータを入力してください")

# フッターをカラムで配置
footer_col1, footer_col2, footer_col3 = st.columns([2, 1, 1])

with footer_col1:
    st.markdown(f"""
    🎰 パチンコグラフ解析システム v2.5.0  
    更新日: {datetime.now().strftime('%Y/%m/%d')}  
    Produced by [PPタウン](https://pp-town.com/)  
    Created by [fivenine-design.com](https://fivenine-design.com)
    """)

with footer_col2:
    # 管理者の場合はパスワード変更ボタンを表示
    if st.session_state.get('is_admin', False):
        if st.button("🔐 パスワード管理", key="password_management_button"):
            st.session_state.show_password_management = True

with footer_col3:
    if st.button("🚪 ログアウト", key="logout_button"):
        st.session_state.authenticated = False
        st.session_state.is_admin = False
        st.session_state.remember_me = False
        # URLパラメータから認証トークンを削除
        if 'auth' in st.query_params:
            del st.query_params['auth']
        time.sleep(0.3)
        st.rerun()

# パスワード管理モーダル（管理者のみ）
if st.session_state.get('show_password_management', False) and st.session_state.get('is_admin', False):
    with st.container():
        st.markdown("---")
        st.markdown("### 🔐 パスワード管理")
        
        # 現在のパスワードを表示
        st.info(f"""
        **現在のパスワード:**
        - 一般ユーザー: {st._global_passwords['user']}
        - 管理者: {st._global_passwords['admin']}
        """)
        
        # パスワード変更フォーム
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 一般ユーザーパスワード")
            new_user_password = st.text_input(
                "新しいパスワード",
                type="password",
                key="new_user_password",
                placeholder="新しいパスワードを入力"
            )
            if st.button("一般パスワードを変更", key="change_user_password"):
                if new_user_password:
                    st._global_passwords['user'] = new_user_password
                    st.success("✅ 一般ユーザーパスワードを変更しました（アプリ再起動まで有効）")
                else:
                    st.error("パスワードを入力してください")
        
        with col2:
            st.markdown("#### 管理者パスワード")
            new_admin_password = st.text_input(
                "新しいパスワード",
                type="password",
                key="new_admin_password",
                placeholder="新しいパスワードを入力"
            )
            if st.button("管理者パスワードを変更", key="change_admin_password"):
                if new_admin_password:
                    st._global_passwords['admin'] = new_admin_password
                    st.success("✅ 管理者パスワードを変更しました（アプリ再起動まで有効）")
                else:
                    st.error("パスワードを入力してください")
        
        # 閉じるボタン
        if st.button("閉じる", key="close_password_management"):
            st.session_state.show_password_management = False
            st.rerun()