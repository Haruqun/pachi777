#!/usr/bin/env python3
"""
AI Graph Analysis Report - Professional Edition
高精度データ抽出・解析システム
"""

import streamlit as st
from datetime import datetime
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
from web_analyzer import WebCompatibleAnalyzer
import platform
import pytesseract
import re
import json
import pandas as pd
import time
import hashlib
import secrets
import sqlite3

# ページ設定
st.set_page_config(
    page_title="AI Graph Analysis Report",
    page_icon="🎰",
    layout="wide"
)

def extract_site7_data(image):
    """site7の画像からOCRでデータを抽出"""
    try:
        # 画像をグレースケールに変換
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # OCRの前処理
        # コントラストを上げる
        alpha = 1.5  # コントラスト制御
        beta = 0     # 明度制御
        adjusted = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)
        
        # 全体のOCR実行（日本語対応）
        text = pytesseract.image_to_string(adjusted, lang='jpn')
        
        # 抽出したいデータのパターン定義
        data = {
            'machine_number': None,
            'total_start': None,
            'jackpot_count': None,
            'first_hit_count': None,
            'current_start': None,
            'jackpot_probability': None,
            'max_payout': None
        }
        
        # 台番号の抽出
        lines = text.split('\n')
        for line in lines:
            if '番台' in line and '【' in line:
                data['machine_number'] = line.strip()
        
        # 数値データの抽出
        # 累計スタート
        start_match = re.search(r'(\d{3,4})\s*スタート', text)
        if start_match:
            data['total_start'] = start_match.group(1)
        
        # 大当り回数
        jackpot_match = re.search(r'(\d+)\s*回\s*大当り', text)
        if not jackpot_match:
            jackpot_match = re.search(r'大当り回数\s*(\d+)', text)
        if jackpot_match:
            data['jackpot_count'] = jackpot_match.group(1)
        
        # 初当り回数
        first_hit_match = re.search(r'初当り回数\s*(\d+)', text)
        if not first_hit_match:
            first_hit_match = re.search(r'(\d+)\s*回.*初当り', text)
        if first_hit_match:
            data['first_hit_count'] = first_hit_match.group(1)
        
        # 現在のスタート
        current_start_match = re.search(r'スタート\s*(\d{2,3})(?!\d)', text)
        if current_start_match:
            data['current_start'] = current_start_match.group(1)
        
        # 大当り確率
        prob_match = re.search(r'1/(\d{2,4})', text)
        if prob_match:
            data['jackpot_probability'] = f"1/{prob_match.group(1)}"
        
        # 最高出玉
        max_payout_patterns = [
            r'最高出玉\s*(\d{3,5})',
            r'(\d{3,5})\s*最高',
            r'出玉\s*(\d{3,5})'
            # 最後の手段のパターンを削除（誤検出を防ぐため）
        ]
        
        for pattern in max_payout_patterns:
            max_payout_match = re.search(pattern, text)
            if max_payout_match:
                value = int(max_payout_match.group(1))
                # 妥当な範囲の値かチェック（100-99999）
                if 100 <= value <= 99999:
                    data['max_payout'] = str(value)
                    break
        
        
        return data
    except Exception as e:
        st.warning(f"OCRエラー: {str(e)}")
        return None


# デフォルト値
default_settings = {
    'search_start_offset': 50,
    'search_end_offset': 500,
    'crop_top': 246,
    'crop_bottom': 280,
    'left_margin': 120,
    'right_margin': 120,
    # グリッドライン調整値
    'grid_30k_offset': 1,       # +30000ライン（最上部）
    'grid_minus_30k_offset': -34, # -30000ライン（最下部）
}

# セッションステートの初期化（エキスパンダーより前に行う）
if 'settings' not in st.session_state:
    st.session_state.settings = default_settings.copy()

if 'saved_presets' not in st.session_state:
    st.session_state.saved_presets = {}
    # データベースから読み込みフラグを設定
    st.session_state.force_reload_presets = True

if 'show_adjustment' not in st.session_state:
    st.session_state.show_adjustment = False

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'current_preset_name' not in st.session_state:
    st.session_state.current_preset_name = 'デフォルト'

if 'uploaded_file_names' not in st.session_state:
    st.session_state.uploaded_file_names = []

# セッショントークンの生成と検証
def generate_session_token():
    """セッショントークンを生成"""
    return secrets.token_urlsafe(32)

def verify_session_token(token):
    """セッショントークンを検証（簡易実装）"""
    # 実際の実装では、サーバー側でトークンを管理すべきですが、
    # 簡易実装として、トークンの形式チェックのみ行います
    return token and len(token) > 20

# JavaScriptでCookieを扱うヘルパー関数
def cookie_manager():
    """Cookie管理用のJavaScriptコード"""
    return """
    <script>
    // Cookieを設定
    function setCookie(name, value, days) {
        var expires = "";
        if (days) {
            var date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = "; expires=" + date.toUTCString();
        }
        document.cookie = name + "=" + (value || "") + expires + "; path=/";
    }
    
    // Cookieを取得
    function getCookie(name) {
        var nameEQ = name + "=";
        var ca = document.cookie.split(';');
        for(var i = 0; i < ca.length; i++) {
            var c = ca[i];
            while (c.charAt(0) == ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    }
    
    // Cookieを削除
    function eraseCookie(name) {
        document.cookie = name + '=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    }
    
    // Streamlitとの通信
    function sendToStreamlit(data) {
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            data: data
        }, '*');
    }
    
    // ページ読み込み時にセッショントークンをチェック
    window.addEventListener('load', function() {
        var token = getCookie('pachi777_session');
        if (token) {
            // セッショントークンが存在する場合の処理
            // 現在は特に処理なし（将来の拡張用）
        }
    });
    </script>
    """

# Cookie管理用のJavaScriptを常に挿入（ログイン・ログアウト両方で使用）
st.markdown(cookie_manager(), unsafe_allow_html=True)

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
            if st.session_state.password_input == "059":
                st.session_state.authenticated = True
                st.session_state.login_success = True
                # セッショントークンを生成
                st.session_state.session_token = generate_session_token()
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
        
        # ログインボタン
        if st.button("ログイン", type="primary", use_container_width=True):
            handle_login()
        
        # ログイン成功時の処理
        if st.session_state.get('login_success', False):
            st.success("✅ ログインしました")
            # Cookieを設定するJavaScriptを実行
            if 'session_token' in st.session_state:
                st.markdown(f"""
                <script>
                setCookie('pachi777_session', '{st.session_state.session_token}', 30);
                </script>
                """, unsafe_allow_html=True)
            st.session_state.login_success = False
            time.sleep(0.5)  # Cookieが設定されるまで少し待機
            st.rerun()
        
        # ログインエラー時の処理
        if st.session_state.get('login_error', False):
            st.error("❌ パスワードが違います")
            st.session_state.login_error = False
        
        # フッター
        st.markdown(f"""
        <div class="login-footer">
            AI Graph Analysis Report v2.0<br>
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

# データベース接続とテーブル作成
def init_database():
    """データベースを初期化"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # プリセットテーブルを作成
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS presets (
            name TEXT PRIMARY KEY,
            settings TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# データベースを初期化
init_database()

# プリセットを読み込み
def load_presets_from_db():
    """データベースからプリセットを読み込み"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name, settings FROM presets')
        rows = cursor.fetchall()
        conn.close()
        
        presets = {}
        for name, settings_json in rows:
            presets[name] = json.loads(settings_json)
        
        return presets
    except Exception as e:
        st.warning(f"プリセット読み込みエラー: {str(e)}")
        return {}

# セッションステートにプリセットを読み込み
# リロード時も常に最新のプリセットを読み込む
if 'saved_presets' not in st.session_state or st.session_state.get('force_reload_presets', False):
    st.session_state.saved_presets = load_presets_from_db()
    st.session_state.force_reload_presets = False

# プリセットを保存
def save_preset_to_db(name, settings):
    """プリセットをデータベースに保存"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        settings_json = json.dumps(settings)
        
        # UPSERT操作（存在する場合は更新、なければ挿入）
        cursor.execute('''
            INSERT OR REPLACE INTO presets (name, settings, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (name, settings_json))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"プリセットの保存に失敗しました: {str(e)}")
        return False

# プリセットを削除
def delete_preset_from_db(name):
    """プリセットをデータベースから削除"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM presets WHERE name = ?', (name,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"プリセットの削除に失敗しました: {str(e)}")
        return False

# 本番解析セクション
st.markdown("---")
st.markdown("## 🎰 AI Graph Analysis Report")
st.caption("""高精度データ抽出・解析システム - Professional Edition

本システムは、パチンコ台のグラフ画像をAI技術で自動解析する専門ツールです。
OCR技術による台番号・回転数の自動読み取り、画像処理によるグラフデータの精密抽出、
独自アルゴリズムによる統計解析を実現。複数画像の一括処理にも対応し、
解析結果はCSV形式でダウンロード可能。プリセット機能により、
異なる端末や表示形式にも柔軟に対応できる高精度な解析システムです。""")

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

# STEP 1: ファイルアップロード
st.markdown("### 📤 STEP 1: 解析したいグラフ画像をアップロード")
st.caption("site7のグラフ画像を選択してください（複数可）")

uploaded_files = st.file_uploader(
    "画像を選択",
    type=['jpg', 'jpeg', 'png'],
    accept_multiple_files=True,
    help="複数の画像を一度にアップロードできます（JPG, PNG形式）",
    key="graph_uploader"
)

if uploaded_files:
    # 重複チェック
    seen_names = {}
    unique_files = []
    duplicate_names = []
    
    for file in uploaded_files:
        if file.name not in seen_names:
            seen_names[file.name] = 1
            unique_files.append(file)
        else:
            seen_names[file.name] += 1
            if seen_names[file.name] == 2:  # 初めての重複
                duplicate_names.append(file.name)
    
    # アップロード結果を表示
    duplicate_count = sum(count - 1 for count in seen_names.values() if count > 1)
    if duplicate_count > 0:
        st.success(f"✅ {len(unique_files)}枚の画像がアップロードされました")
        with st.expander(f"ℹ️ {duplicate_count}枚の重複ファイルをスキップしました", expanded=False):
            for name in duplicate_names:
                count = seen_names[name]
                st.caption(f"• {name} ({count}回アップロード、1枚のみ使用)")
    else:
        st.success(f"✅ {len(unique_files)}枚の画像がアップロードされました")
    
    # 以降はunique_filesを使用
    uploaded_files = unique_files
    
    # ファイル名をセッションステートに保存
    st.session_state.uploaded_file_names = [f.name for f in uploaded_files]
    
    # STEP 2: プリセット選択
    st.markdown("### 📋 STEP 2: 解析設定を選択")
    st.caption("保存されたプリセットを選択するか、デフォルト設定を使用します")
    
    # デバッグ情報（一時的）
    if st.checkbox("🐛 デバッグ情報を表示", value=False):
        st.write(f"saved_presets の内容: {st.session_state.saved_presets}")
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
    preset_names = ["デフォルト"] + list(st.session_state.saved_presets.keys())
    
    # プリセットボタンを横に並べる（調整セクションと同じスタイル）
    if len(preset_names) <= 4:
        preset_cols = st.columns(len(preset_names))
        for i, preset_name in enumerate(preset_names):
            with preset_cols[i]:
                button_type = "primary" if preset_name == st.session_state.get('current_preset_name', 'デフォルト') else "secondary"
                if st.button(f"📥 {preset_name}", use_container_width=True, key=f"analysis_preset_{preset_name}", type=button_type):
                    if preset_name == "デフォルト":
                        st.session_state.settings = default_settings.copy()
                    else:
                        st.session_state.settings = st.session_state.saved_presets[preset_name].copy()
                    
                    # 現在のプリセット名を保存
                    st.session_state.current_preset_name = preset_name
                    
                    st.success(f"✅ '{preset_name}' の設定を適用しました")
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
                        if st.button(f"📥 {preset_name}", use_container_width=True, key=f"analysis_preset_{preset_name}", type=button_type):
                            if preset_name == "デフォルト":
                                st.session_state.settings = default_settings.copy()
                            else:
                                st.session_state.settings = st.session_state.saved_presets[preset_name].copy()
                            
                            # 現在のプリセット名を保存
                            st.session_state.current_preset_name = preset_name
                            
                            st.success(f"✅ '{preset_name}' の設定を適用しました")
                            time.sleep(0.5)
                            st.rerun()
    
    # 設定を調整ボタン（別行で表示）
    if st.button("⚙️ 調整設定を開く", use_container_width=True, help="設定を細かく調整したい場合はこちら"):
        st.session_state.show_adjustment = True
        st.session_state.scroll_to_adjustment = True
        st.rerun()
    
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
    
    st.caption("設定を確認したら、解析ボタンをクリックしてください")
    
    if st.button("🚀 解析を開始", type="primary", use_container_width=True):
        st.session_state.start_analysis = True
        st.session_state.skip_ocr = skip_ocr
        st.rerun()

# ファイルがアップロードされたことがある場合、解析ボタンを常に表示
elif st.session_state.uploaded_file_names:
    st.info(f"💾 保存されたファイル: {', '.join(st.session_state.uploaded_file_names)}")
    st.warning("⚠️ 設定を変更した後は、画像を再度アップロードしてください")
    
    # クリアボタン
    if st.button("🗑️ ファイル情報をクリア", use_container_width=True):
        st.session_state.uploaded_file_names = []
        st.rerun()

# 解析を実行
if uploaded_files and st.session_state.get('start_analysis', False):
    # 解析結果セクション
    st.markdown("### 🎯 解析結果")
    
    # 現在使用中のプリセットを表示
    current_preset_name = st.session_state.get('current_preset_name', 'デフォルト')
    
    st.info(f"📋 使用プリセット: **{current_preset_name}**")
    
    # 現在の設定値を表示
    with st.expander("🔧 使用中の設定値", expanded=False):
        current_settings = st.session_state.get('settings', default_settings)
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
            st.text(f"+30k: {current_settings.get('grid_30k_offset', 0):+d}px")
            st.text(f"-30k: {current_settings.get('grid_minus_30k_offset', 0):+d}px")
    
    # プログレスバー
    progress_bar = st.progress(0)
    status_text = st.empty()
    detail_text = st.empty()
    
    # 初期メッセージを表示
    status_text.text('🚀 解析を開始します...')
    time.sleep(0.5)  # 少し待機してメッセージを見やすくする
    
    # 解析結果を格納
    analysis_results = []
    
    # 各画像を処理
    for idx, uploaded_file in enumerate(uploaded_files):
        # 進捗更新（開始時）
        progress_start = idx / len(uploaded_files)
        progress_bar.progress(progress_start)
        status_text.text(f'処理中... ({idx + 1}/{len(uploaded_files)})')
        detail_text.text(f'📷 {uploaded_file.name} の画像を読み込み中...')
        time.sleep(0.1)  # 視覚的フィードバックのため少し徇機
        
        # 画像を読み込み
        image = Image.open(uploaded_file)
        img_array = np.array(image)
        height, width = img_array.shape[:2]
        
        # OCRでデータ抽出を試みる（スキップ設定を確認）
        if not st.session_state.get('skip_ocr', False):
            detail_text.text(f'🔍 {uploaded_file.name} のOCR解析を実行中...')
            time.sleep(0.1)  # 視覚的フィードバック
            ocr_data = extract_site7_data(img_array)
        else:
            detail_text.text(f'⚡ {uploaded_file.name} のOCR解析をスキップ（高速モード）')
            ocr_data = None
        
        # Pattern3: Zero Line Based の自動検出
        detail_text.text(f'📐 {uploaded_file.name} のグラフ領域を検出中...')
        time.sleep(0.1)  # 視覚的フィードバック
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
        orange_bottom = 0
        
        # オレンジバーの検出
        for y in range(height//2):
            if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
                orange_bottom = y
        
        # オレンジバーの下端を正確に見つける
        if orange_bottom > 0:
            for y in range(orange_bottom, min(orange_bottom + 100, height)):
                if np.sum(orange_mask[y, :]) < width * 0.1 * 255:
                    orange_bottom = y
                    break
        else:
            orange_bottom = 150
        
        # ゼロライン検出
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 設定値を使用（セッションステートから取得）
        settings = st.session_state.get('settings', default_settings)
        
        # 検索範囲（設定値を使用）
        search_start = orange_bottom + settings['search_start_offset']
        search_end = min(height - 100, orange_bottom + settings['search_end_offset'])
        
        # 切り抜きサイズ（±30000）
        crop_top_offset = settings['crop_top']
        crop_bottom_offset = settings['crop_bottom']
        
        best_score = 0
        zero_line_y = (search_start + search_end) // 2
        
        for y in range(search_start, search_end):
            row = gray[y, 100:width-100]
            darkness = 1.0 - (np.mean(row) / 255.0)
            uniformity = 1.0 - (np.std(row) / 128.0)
            score = darkness * 0.5 + uniformity * 0.5
            
            if score > best_score:
                best_score = score
                zero_line_y = y
        
        # 切り抜き範囲を設定（最終調整値）
        top = max(0, zero_line_y - crop_top_offset)  # 0ラインから上
        bottom = min(height, zero_line_y + crop_bottom_offset)  # 0ラインから下
        left = settings['left_margin']  # 左右の余白
        right = width - settings['right_margin']  # 左右の余白
        
        # 切り抜き実行
        cropped_img = img_array[int(top):int(bottom), int(left):int(right)].copy()
        
        # グリッドラインを追加
        # 切り抜き画像の高さは493px（246+247）
        # 最上部が+30000、最下部が-30000なので、60000の範囲を493pxで表現
        # 1pxあたり約121.7玉
        crop_height = cropped_img.shape[0]
        zero_line_in_crop = zero_line_y - top  # 切り抜き画像内での0ライン位置
        
        # スケール計算（調整されたグリッドラインに基づく）
        # 注意：この変数はグリッドライン描画にのみ使用され、実際の解析には使用されない
        scale = 30000 / 246  # グリッドライン描画用のデフォルト値
        
        # グリッドライン描画（設定値を使用）
        # +30000ライン（最上部）
        y_30k = 0 + settings.get('grid_30k_offset', 0)  # 最上部基準
        if 0 <= y_30k < crop_height:
            cv2.line(cropped_img, (0, y_30k), (cropped_img.shape[1], y_30k), (128, 128, 128), 2)
            cv2.putText(cropped_img, '+30000', (10, max(20, y_30k + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)
        
        # -30000ライン（最下部）
        y_minus_30k = crop_height - 1 + settings.get('grid_minus_30k_offset', 0)
        y_minus_30k = min(max(0, y_minus_30k), crop_height - 1)  # 画像範囲内に制限
        cv2.line(cropped_img, (0, y_minus_30k), (cropped_img.shape[1], y_minus_30k), (128, 128, 128), 2)
        cv2.putText(cropped_img, '-30000', (10, max(10, y_minus_30k - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (64, 64, 64), 1)

        
        # ゼロラインから±30000ラインまでの距離を計算
        distance_to_plus_30k = zero_line_in_crop - y_30k
        distance_to_minus_30k = y_minus_30k - zero_line_in_crop
        
        # 0ライン
        y_0 = int(zero_line_in_crop)  # 調整なし
        if 0 < y_0 < crop_height:
            cv2.line(cropped_img, (0, y_0), (cropped_img.shape[1], y_0), (255, 0, 0), 2)
            cv2.putText(cropped_img, '0', (10, y_0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)
        
        # 元画像にもグリッドラインを追加
        img_with_grid = img_array.copy()
        
        # 元画像での座標に変換（切り抜き前の座標系）
        # +30000ライン（元画像座標）
        y_30k_orig = int(top + y_30k)
        if 0 <= y_30k_orig < height:
            cv2.line(img_with_grid, (0, y_30k_orig), (width, y_30k_orig), (128, 128, 128), 2)
            cv2.putText(img_with_grid, '+30000', (10, max(20, y_30k_orig + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
        
        # -30000ライン（元画像座標）
        y_minus_30k_orig = int(top + y_minus_30k)
        if 0 <= y_minus_30k_orig < height:
            cv2.line(img_with_grid, (0, y_minus_30k_orig), (width, y_minus_30k_orig), (128, 128, 128), 2)
            cv2.putText(img_with_grid, '-30000', (10, max(10, y_minus_30k_orig - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
        
        # 0ライン（元画像座標）
        if 0 <= zero_line_y < height:
            cv2.line(img_with_grid, (0, zero_line_y), (width, zero_line_y), (255, 0, 0), 2)
            cv2.putText(img_with_grid, '0', (10, zero_line_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        
        # 切り抜き範囲を示す枠線を追加（オプション）
        cv2.rectangle(img_with_grid, (int(left), int(top)), (int(right), int(bottom)), (0, 255, 0), 2)

        # 解析を自動実行
        detail_text.text(f'📊 {uploaded_file.name} のグラフデータを解析中...')
        
        # アナライザーを初期化
        analyzer = WebCompatibleAnalyzer()
        
        # グリッドラインなしの画像を使用
        analysis_img = img_array[int(top):int(bottom), int(left):int(right)].copy()
        
        # 0ラインの位置を設定
        analyzer.zero_y = zero_line_in_crop
        # 調整されたグリッドライン位置に基づいてスケールを計算
        crop_height = analysis_img.shape[0]
        
        # 調整された±30,000ライン位置
        y_30k_adjusted = 0 + settings.get('grid_30k_offset', 0)
        y_minus_30k_adjusted = crop_height - 1 + settings.get('grid_minus_30k_offset', 0)
        
        # ゼロラインから調整された±30,000ラインまでの距離
        distance_to_plus_30k_adjusted = zero_line_in_crop - y_30k_adjusted
        distance_to_minus_30k_adjusted = y_minus_30k_adjusted - zero_line_in_crop
        
        # 通常の線形スケール計算
        if distance_to_plus_30k_adjusted > 0 and distance_to_minus_30k_adjusted > 0:
            # 上下の平均距離を使用
            avg_distance_adjusted = (distance_to_plus_30k_adjusted + distance_to_minus_30k_adjusted) / 2
            analyzer.scale = 30000 / avg_distance_adjusted
        else:
            # フォールバック（調整前の値を使用）
            distance_to_top = zero_line_in_crop
            distance_to_bottom = crop_height - zero_line_in_crop
            avg_distance = (distance_to_top + distance_to_bottom) / 2
            analyzer.scale = 30000 / avg_distance
        
        # グラフデータを抽出
        graph_data_points, dominant_color, _ = analyzer.extract_graph_data(analysis_img)
        
        # デバッグ情報を無効化（必要に応じて有効化可能）
        # if uploaded_file.name in ["IMG_0165.PNG", "IMG_0174.PNG", "IMG_0177.PNG"]:
        #     st.write(f"🔍 デバッグ情報 - {uploaded_file.name}")
        #     st.write(f"- ゼロライン位置（切り抜き内）: {zero_line_in_crop}px")
        #     st.write(f"- 切り抜き画像の高さ: {crop_height}px")
        #     st.write(f"- 調整された+30000ライン位置: {y_30k_adjusted}px (オフセット: {settings.get('grid_30k_offset', 0)})")
        #     st.write(f"- 調整された-30000ライン位置: {y_minus_30k_adjusted}px (オフセット: {settings.get('grid_minus_30k_offset', 0)})")
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
            # データポイントから値のみを抽出
            graph_values = [value for x, value in graph_data_points]

            # 統計情報を計算
            max_val_original = max(graph_values)
            min_val_original = min(graph_values)
            current_val_original = graph_values[-1] if graph_values else 0
            
            # インデックスを保存
            max_idx = graph_values.index(max_val_original)
            min_idx = graph_values.index(min_val_original)
            
            # 補正係数の計算
            correction_factor = settings.get('correction_factor', 1.0)
            
            # 補正を適用
            if correction_factor != 1.0:
                max_val = max_val_original * correction_factor
                min_val = min_val_original * correction_factor
                current_val = current_val_original * correction_factor
                # グラフ値も更新（初当たり検出用）
                graph_values = [v * correction_factor for v in graph_values]
            else:
                max_val = max_val_original
                min_val = min_val_original
                current_val = current_val_original

            # 最大値が30,000を超える場合は30,000にクリップ
            if max_val > 30000:
                max_val = 30000
            
            # 最小値が-30,000を下回る場合は-30,000にクリップ
            if min_val < -30000:
                min_val = -30000

            # MAXがマイナスの場合は0を表示
            if max_val < 0:
                max_val = 0

            # 初当たり値を探す（production版と同じロジック）
            first_hit_val = 0
            first_hit_x = None
            min_payout = 100  # 最低払い出し玉数

            # 方法1: 100玉以上の急激な増加を検出
            for i in range(1, min(len(graph_values)-2, 150)):  # 最大150点まで探索
                current_increase = graph_values[i+1] - graph_values[i]

                # 100玉以上の増加を検出
                if current_increase > min_payout:
                    # 次の点も上昇または維持していることを確認（ノイズ除外）
                    if graph_values[i+2] >= graph_values[i+1] - 50:
                        # 初当たりは必ずマイナス値から
                        if graph_values[i] < 0:
                            first_hit_val = graph_values[i]
                            first_hit_x = i
                            break

            # 方法2: 減少傾向からの急上昇を検出
            if first_hit_x is None:
                window_size = 5
                for i in range(window_size, len(graph_values)-1):
                    # 過去の傾向を計算
                    past_window = graph_values[max(0, i-window_size):i]
                    if len(past_window) >= 2:
                        avg_slope = (past_window[-1] - past_window[0]) / len(past_window)

                        # 現在の変化
                        current_change = graph_values[i+1] - graph_values[i]

                        # 減少傾向からの急上昇
                        if avg_slope <= 0 and current_change > min_payout:
                            if i + 2 < len(graph_values) and graph_values[i+2] > graph_values[i+1] - 50:
                                # 初当たりは必ずマイナス値
                                if graph_values[i] < 0:
                                    first_hit_val = graph_values[i]
                                    first_hit_x = i
                                    break

            # 初当たり値がプラスの場合は0を表示
            if first_hit_val > 0:
                first_hit_val = 0

            # オーバーレイ画像を作成
            overlay_img = cropped_img.copy()

            # 検出されたグラフラインを描画
            prev_x = None
            prev_y = None

            # 緑色で統一（見やすさ重視）
            draw_color = (0, 255, 0)  # 緑色固定

            # グラフポイントを描画
            for x, value in graph_data_points:
                # Y座標を計算（線形スケール）
                y = int(zero_line_in_crop - (value / analyzer.scale))

                # 画像範囲内かチェック
                if y is not None and 0 <= y < overlay_img.shape[0] and 0 <= x < overlay_img.shape[1]:
                    # 点を描画（より見やすくするため）
                    cv2.circle(overlay_img, (int(x), y), 2, draw_color, -1)

                    # 線で接続
                    if prev_x is not None and prev_y is not None:
                        cv2.line(overlay_img, (int(prev_x), int(prev_y)), (int(x), y), draw_color, 2)

                    prev_x = x
                    prev_y = y

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
                cv2.circle(overlay_img, (int(max_x), max_y), 8, (0, 255, 255), -1)
                cv2.circle(overlay_img, (int(max_x), max_y), 10, (0, 200, 200), 2)
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
                cv2.circle(overlay_img, (int(min_x), min_y), 8, (255, 0, 255), -1)
                cv2.circle(overlay_img, (int(min_x), min_y), 10, (200, 0, 200), 2)
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
                # 背景付きテキスト（白背景、濃いシアン文字）右端に表示
                text = f'CURRENT: {int(current_val):,}'
                text_width = 160
                text_y = current_y - 10 if current_y > 30 else current_y + 15
                cv2.rectangle(overlay_img, (overlay_img.shape[1] - text_width - 15, text_y - 15), 
                             (overlay_img.shape[1] - 10, text_y + 5), (255, 255, 255), -1)
                cv2.putText(overlay_img, text, (overlay_img.shape[1] - text_width - 10, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 0), 1, cv2.LINE_AA)

            # 初当たり値ライン（端から端まで）
            if first_hit_x is not None and first_hit_val != 0:  # 初当たりがある場合
                first_hit_y = calculate_y_from_value(first_hit_val)
                if 0 <= first_hit_y < overlay_img.shape[0]:
                    # 端から端まで線を引く
                    cv2.line(overlay_img, (0, first_hit_y), (overlay_img.shape[1], first_hit_y), (155, 48, 255), 2)
                    # 初当たりの点に大きめの円を描画
                    first_hit_graph_x = graph_data_points[first_hit_x][0]
                    cv2.circle(overlay_img, (int(first_hit_graph_x), first_hit_y), 8, (155, 48, 255), -1)
                    cv2.circle(overlay_img, (int(first_hit_graph_x), first_hit_y), 10, (120, 30, 200), 2)
                    # 背景付きテキスト（白背景、紫文字）右端に表示
                    text = f'FIRST HIT: {int(first_hit_val):,}'
                    text_width = 150
                    text_y = first_hit_y if (first_hit_y > 20 and first_hit_y < overlay_img.shape[0] - 20) else (20 if first_hit_y <= 20 else overlay_img.shape[0] - 20)
                    cv2.rectangle(overlay_img, (overlay_img.shape[1] - text_width - 15, text_y - 15), 
                                 (overlay_img.shape[1] - 10, text_y + 5), (255, 255, 255), -1)
                    cv2.putText(overlay_img, text, (overlay_img.shape[1] - text_width - 10, text_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 0, 150), 1, cv2.LINE_AA)

            # 結果を保存
            analysis_results.append({
                'name': uploaded_file.name,
                'original_image': img_with_grid,  # グリッド付き元画像を保存
                'cropped_image': cropped_img,  # 切り抜き画像
                'overlay_image': overlay_img,  # オーバーレイ画像
                'success': True,
                'max_val': int(max_val),
                'min_val': int(min_val),
                'current_val': int(current_val),
                'first_hit_val': int(first_hit_val) if first_hit_x is not None else None,
                'dominant_color': dominant_color,
                'ocr_data': ocr_data,  # OCRデータを追加
                'correction_factor': correction_factor  # 補正係数を追加
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
        progress_end = (idx + 1) / len(uploaded_files)
        progress_bar.progress(progress_end)
    
    # プログレスバーを完了
    progress_bar.progress(1.0)
    status_text.text('✅ 全ての画像の処理が完了しました！')
    detail_text.empty()
    time.sleep(1.0)  # 完了メッセージを表示する時間
    
    # 結果を保存
    st.session_state.analysis_results = analysis_results
    
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
    - 0ライン基準：上246px、下247px（±30,000玉相当）
    - スケール：120玉/ピクセル
    - 左右余白：125px除外
    """)

# 解析結果を表示
if 'analysis_results' in st.session_state and st.session_state.analysis_results:
    analysis_results = st.session_state.analysis_results
    
    # 結果をグリッド表示
    st.markdown("### 📊 解析結果一覧")

    # 解析結果を2列で表示
    cols = st.columns(2)

    for idx, result in enumerate(analysis_results):
        with cols[idx % 2]:
            # 台番号を優先表示、なければファイル名
            if result.get('ocr_data') and result['ocr_data'].get('machine_number'):
                display_name = result['ocr_data']['machine_number']
            else:
                display_name = result['name']
            st.markdown(f"#### {idx + 1}. {display_name}")

            # 解析結果画像
            st.image(result['overlay_image'], use_column_width=True)

            # 元画像を折りたたみ可能に
            with st.expander("📷 元画像を表示"):
                st.image(result['original_image'], use_column_width=True)

            # 成功時は統計情報を表示（解析結果の下に縦に並べる）
            if result['success']:
                # 統計情報をカード風に表示
                st.markdown("""
                <style>
                .stat-card {
                    background-color: #f0f2f6;
                    padding: 15px;
                    border-radius: 10px;
                    margin-top: 10px;
                }
                .stat-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 5px 0;
                    border-bottom: 1px solid #e0e0e0;
                }
                .stat-item:last-child {
                    border-bottom: none;
                }
                .stat-label {
                    color: #666;
                    font-weight: 500;
                }
                .stat-value {
                    font-weight: bold;
                    color: #333;
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

                first_hit_text = f"{result['first_hit_val']:,}玉" if result['first_hit_val'] is not None else "なし"
                first_hit_class = get_value_class(result['first_hit_val']) if result['first_hit_val'] is not None else ""

                # 補正係数の表示を準備
                correction_info = ""
                if 'correction_factor' in result and result['correction_factor'] != 1.0:
                    correction_info = f'<div style="font-size: 0.8em; color: #666; text-align: right; margin-top: 5px;">補正率: x{result["correction_factor"]:.2f}</div>'
                
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-item">
                        <span class="stat-label">📈 最高値</span>
                        <span class="stat-value {get_value_class(result['max_val'])}">{result['max_val']:,}玉</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">📉 最低値</span>
                        <span class="stat-value {get_value_class(result['min_val'])}">{result['min_val']:,}玉</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">🎯 現在値</span>
                        <span class="stat-value {get_value_class(result['current_val'])}">{result['current_val']:,}玉</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">🎰 初当たり</span>
                        <span class="stat-value {first_hit_class}">{first_hit_text}</span>
                    </div>
                    {correction_info}
                </div>
                """, unsafe_allow_html=True)

                # OCRデータがある場合は表示
                if result.get('ocr_data') and any(result['ocr_data'].values()):
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

                    # 台番号
                    if ocr.get('machine_number'):
                        ocr_html += f'<div class="ocr-item"><span class="ocr-label">🔢 台番号</span><span class="ocr-value">{ocr["machine_number"]}</span></div>'

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
                        ocr_html += f'<div class="ocr-item"><span class="ocr-label">💰 最高出玉</span><span class="ocr-value">{ocr["max_payout"]}玉</span></div>'

                    ocr_html += '</div>'
                    st.markdown(ocr_html, unsafe_allow_html=True)

            else:
                st.warning("⚠️ グラフデータを検出できませんでした")

            # 区切り線（各列内で）
            if idx < len(analysis_results) - 2:
                st.markdown("---")

    # サマリー情報
    st.markdown("### 📋 解析サマリー")

    success_count = sum(1 for r in analysis_results if r['success'])
    st.info(f"📈 総画像数: {len(analysis_results)}枚 | ✅ 成功: {success_count}枚 | ⚠️ 失敗: {len(analysis_results) - success_count}枚")


    # 結果を表形式で表示
    st.markdown("### 📊 解析結果（表形式）")

    # 統計情報を計算して表示
    if analysis_results:
        success_results = [r for r in analysis_results if r.get('success')]
        if success_results:
            # 統計情報の計算
            total_balance = sum(r['current_val'] for r in success_results)
            total_balance_yen = total_balance * 4
            avg_balance = total_balance / len(success_results)
            avg_balance_yen = avg_balance * 4
            max_result = max(success_results, key=lambda x: x['current_val'])
            min_result = min(success_results, key=lambda x: x['current_val'])

            # 統計情報を3列で表示
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "合計収支",
                    f"{total_balance_yen:+,}円",
                    f"{total_balance:+,}玉"
                )

            with col2:
                st.metric(
                    "平均収支",
                    f"{avg_balance_yen:+,.0f}円",
                    f"{avg_balance:+,.0f}玉"
                )

            with col3:
                st.metric(
                    "最高/最低",
                    f"{max_result['current_val']:+,}玉",
                    f"{min_result['current_val']:+,}玉"
                )

        # データフレームを作成
        df_data = []
        for result in analysis_results:
            if result['success']:
                # 台番号の決定（OCRスキップ時はファイル名を使用）
                if st.session_state.get('skip_ocr', False):
                    machine_number = result['name']
                else:
                    machine_number = result.get('ocr_data', {}).get('machine_number', result['name'])
                
                row = {
                    '台番号': machine_number,
                    '最高値': result['max_val'],
                    '最低値': result['min_val'],
                    '現在値': result['current_val'],
                    '初当たり': result['first_hit_val'] if result['first_hit_val'] is not None else None,
                    '収支（円）': result['current_val'] * 4,
                    '色': result['dominant_color']
                }
                # OCRデータを追加（OCRスキップモードでない場合のみ）
                if not st.session_state.get('skip_ocr', False) and result.get('ocr_data'):
                    ocr = result['ocr_data']
                    row.update({
                        '累計スタート': ocr.get('total_start', ''),
                        '大当り回数': ocr.get('jackpot_count', ''),
                        '初当り回数': ocr.get('first_hit_count', ''),
                        '現在スタート': ocr.get('current_start', ''),
                        '大当り確率': ocr.get('jackpot_probability', ''),
                        '最高出玉': ocr.get('max_payout', '')
                    })
                df_data.append(row)
            else:
                # 解析失敗時も台番号の決定方法を統一
                if st.session_state.get('skip_ocr', False):
                    machine_number = result['name']
                else:
                    machine_number = result.get('ocr_data', {}).get('machine_number', result['name'])
                    
                df_data.append({
                    '台番号': machine_number,
                    '最高値': '解析失敗',
                    '最低値': '-',
                    '現在値': '-',
                    '初当たり': None,
                    '収支（円）': '-',
                    '色': '-'
                })

        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "最高値": st.column_config.NumberColumn(format="%d玉"),
                    "最低値": st.column_config.NumberColumn(format="%d玉"),
                    "現在値": st.column_config.NumberColumn(format="%d玉"),
                    "初当たり": st.column_config.NumberColumn(format="%d玉"),
                    "収支（円）": st.column_config.NumberColumn(format="¥%d")
                }
            )

            # CSVダウンロードボタン
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 CSVダウンロード",
                data=csv,
                file_name=f'pachinko_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv'
            )
            
            # 調整設定の案内
            st.markdown("---")
            st.info("""
            💡 **出力結果が期待と異なる場合は？**
            
            端末や画面サイズによってグラフの表示が異なるため、調整設定が必要な場合があります。
            下記の「⚙️ 画像解析の調整設定」から、お使いの端末に合わせた設定を保存してください。
            
            [⚙️ 画像解析の調整設定](#画像解析の調整設定)へ移動
            """)

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
        - 例：「最大値が+15,000玉」とわかっている画像
        
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
        - 例：店舗の実機で「最大+15,000玉」と確認した画像
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
        
        # 保存されたプリセット一覧
        preset_names = ["デフォルト"] + list(st.session_state.saved_presets.keys())
        
        # プリセットボタンを横に並べる
        if len(preset_names) <= 4:
            preset_cols = st.columns(len(preset_names))
            # プリセットが4個以下の場合
            for i, preset_name in enumerate(preset_names):
                with preset_cols[i]:
                    button_type = "primary" if preset_name == st.session_state.get('current_preset_name', 'デフォルト') else "secondary"
                    if st.button(f"📥 {preset_name}", use_container_width=True, key=f"load_preset_{preset_name}", type=button_type):
                        if preset_name == "デフォルト":
                            st.session_state.settings = default_settings.copy()
                        else:
                            st.session_state.settings = st.session_state.saved_presets[preset_name].copy()
                        
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
                                if preset_name == "デフォルト":
                                    st.session_state.settings = default_settings.copy()
                                else:
                                    st.session_state.settings = st.session_state.saved_presets[preset_name].copy()
                                
                                # 現在のプリセット名を保存（編集モードで使用）
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
        
        # オレンジバーを検出
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([30, 255, 255]))
        orange_bottom = 0
        
        for y in range(height//2):
            if np.sum(orange_mask[y, :]) > width * 0.3 * 255:
                orange_bottom = y
        
        if orange_bottom > 0:
            for y in range(orange_bottom, min(orange_bottom + 100, height)):
                if np.sum(orange_mask[y, :]) < width * 0.1 * 255:
                    orange_bottom = y
                    break
        else:
            orange_bottom = 150
        
        # グレースケール変換
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        st.info(f"画像サイズ: {width}x{height}px")
        
        # レイアウト用のメインカラム（画像を読み込んだ後）
        main_col1, main_col2 = st.columns([3, 2])
    
    # 画像がアップロードされている場合のみレイアウトを適用
    if test_image:
        with main_col2:
            # STEP 3: 設定用の入力フィールド
            st.markdown("### 🔍 STEP 3: 詳細設定（通常はデフォルトでOK）")
            st.caption("必要に応じて微調整できます")
            
            st.markdown("#### ゼロライン検索設定")
            col1, col2 = st.columns(2)
    
            with col1:
                search_start_offset = st.number_input(
                    "検索開始位置（オレンジバーから）",
                    min_value=0, max_value=800, value=st.session_state.settings['search_start_offset'],
                    step=10, help="オレンジバーから何ピクセル下から検索を開始するか"
                )
            
            with col2:
                search_end_offset = st.number_input(
                    "検索終了位置（オレンジバーから）",
                    min_value=100, max_value=1200, value=st.session_state.settings['search_end_offset'],
                    step=50, help="オレンジバーから何ピクセル下まで検索するか"
                )
            
            st.markdown("#### ✂️ 切り抜きサイズの設定")
            col3, col4 = st.columns(2)
    
            with col3:
                crop_top = st.number_input(
                    "上方向の切り抜きサイズ",
                    min_value=100, max_value=500, value=st.session_state.settings['crop_top'],
                    step=1, help="ゼロラインから上方向に何ピクセル切り抜くか"
                )
                crop_bottom = st.number_input(
                    "下方向の切り抜きサイズ",
                    min_value=100, max_value=500, value=st.session_state.settings['crop_bottom'],
                    step=1, help="ゼロラインから下方向に何ピクセル切り抜くか"
                )
            
            with col4:
                left_margin = st.number_input(
                    "左側の余白",
                    min_value=0, max_value=300, value=st.session_state.settings['left_margin'],
                    step=25, help="左側から何ピクセル除外するか"
                )
                right_margin = st.number_input(
                    "右側の余白",
                    min_value=0, max_value=300, value=st.session_state.settings['right_margin'],
                    step=25, help="右側から何ピクセル除外するか"
                )
            
            # グリッドライン調整
            st.markdown("#### 📏 グリッドライン調整")
            
            # グリッドライン手動調整
            st.markdown("#### ⚙️ 手動調整")
            st.caption("±30,000ラインの位置を微調整できます（単位：ピクセル）")
            
            grid_col1, grid_col2 = st.columns(2)
            
            with grid_col1:
                grid_30k_offset = st.number_input(
                    "+30,000ライン調整",
                    min_value=-1000, max_value=1000, value=st.session_state.settings.get('grid_30k_offset', 0),
                    step=1, help="上端の+30,000ラインの位置調整"
                )
            
            with grid_col2:
                grid_minus_30k_offset = st.number_input(
                    "-30,000ライン調整",
                    min_value=-1000, max_value=1000, value=st.session_state.settings.get('grid_minus_30k_offset', 0),
                    step=1, help="下端の-30,000ラインの位置調整"
                )
            
            # 中間ライン用のダミー変数を設定（他のコードで参照されるため）
            
            # STEP 4: 最大値アライメント機能を統合
            if test_images:
                st.markdown("### 🎯 STEP 4: 実際の最大値を入力して自動調整")
                st.caption(f"アップロードされた{len(test_images)}枚の画像から最適な設定を自動計算します")
                
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
                    'grid_30k_offset': grid_30k_offset,
                    'grid_minus_30k_offset': grid_minus_30k_offset
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
                    
                    # 切り抜き
                    align_top = max(0, align_zero_line_y - crop_top)
                    align_bottom = min(height_tmp, align_zero_line_y + crop_bottom)
                    align_left = left_margin
                    align_right = width_tmp - right_margin
                    
                    # グリッドライン調整値も適用（現在の入力値を使用）
                    align_zero_in_crop = align_zero_line_y - align_top
                    align_distance_to_plus_30k = align_zero_in_crop - grid_30k_offset
                    align_distance_to_minus_30k = (align_bottom - align_top - 1 + grid_minus_30k_offset) - align_zero_in_crop
                    
                    # カスタム設定で解析
                    analyzer_align.zero_y = align_zero_in_crop
                    analyzer_align.scale = 30000 / align_distance_to_plus_30k if align_distance_to_plus_30k > 0 else 122
                    
                    # 切り抜き画像で解析
                    cropped_for_align = img_array_tmp[int(align_top):int(align_bottom), int(align_left):int(align_right)]
                    # BGRに変換（OpenCVの標準形式）
                    cropped_bgr_align = cv2.cvtColor(cropped_for_align, cv2.COLOR_RGB2BGR)
                    
                    # 解析実行（画像データを直接渡す）
                    data_points_align, color_align, detected_zero_align = analyzer_align.extract_graph_data(cropped_bgr_align)
                    
                    if data_points_align:
                        analysis_align = analyzer_align.analyze_values(data_points_align)
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
                        detection_cols = st.columns(3)
                        with detection_cols[0]:
                            st.metric("検出平均値", f"{avg_detected_max:,}玉")
                        with detection_cols[1]:
                            st.metric("検出中央値", f"{median_detected_max:,}玉")
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
                                st.caption(f"検出値: {detection['detected_max']:,}玉")
                                
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
                        st.info(f"🔍 検出値: **{detection['detected_max']:,}玉**")
                        
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
                                    
                                    # 新しい+30000ラインの位置を計算
                                    new_30k_distance = 30000 / new_scale
                                    current_30k_distance = detection['zero_in_crop'] - current_settings_align['grid_30k_offset']
                                    adjustment_30k = int(current_30k_distance - new_30k_distance)
                                    
                                    # 新しい-30000ラインの位置を計算
                                    new_minus_30k_distance = 30000 / new_scale
                                    current_minus_30k_distance = (detection['crop_height'] - 1 + current_settings_align['grid_minus_30k_offset']) - detection['zero_in_crop']
                                    adjustment_minus_30k = int(new_minus_30k_distance - current_minus_30k_distance)
                                    
                                    corrections.append({
                                        'adjustment_30k': adjustment_30k,
                                        'adjustment_minus_30k': adjustment_minus_30k,
                                        'correction_factor': correction_factor
                                    })
                        
                        if corrections:
                            # 平均調整値を計算
                            avg_adjustment_30k = int(np.mean([c['adjustment_30k'] for c in corrections]))
                            avg_adjustment_minus_30k = int(np.mean([c['adjustment_minus_30k'] for c in corrections]))
                            avg_correction_factor = np.mean([c['correction_factor'] for c in corrections])
                            
                            # セッションステートに保存
                            st.session_state.avg_correction_factor = avg_correction_factor
                            
                            if abs(avg_correction_factor - 1.0) > 0.001:
                                # 推奨調整値を表示
                                st.info(f"平均補正率: **{avg_correction_factor:.2f}x** （{len(corrections)}枚の画像から計算）")
                                
                                col_adj1, col_adj2 = st.columns(2)
                                with col_adj1:
                                    st.info(f"**+30,000ライン:** {grid_30k_offset}px → {grid_30k_offset + avg_adjustment_30k}px (調整: {avg_adjustment_30k:+d}px)")
                                with col_adj2:
                                    st.info(f"**-30,000ライン:** {grid_minus_30k_offset}px → {grid_minus_30k_offset + avg_adjustment_minus_30k}px (調整: {avg_adjustment_minus_30k:+d}px)")
                                
                                # 自動適用ボタン
                                if st.button("🔧 推奨値を自動適用", type="secondary", key="apply_max_alignment"):
                                    # セッションステートに新しい値を設定（現在の入力値に調整を加える）
                                    st.session_state.settings['grid_30k_offset'] = grid_30k_offset + avg_adjustment_30k
                                    st.session_state.settings['grid_minus_30k_offset'] = grid_minus_30k_offset + avg_adjustment_minus_30k
                                    
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
        cv2.putText(overlay_img, f'Zero Line (score: {best_score:.3f})', (10, zero_line_y - 10), 
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
        
        # ゼロラインから±30000ラインまでの距離を計算（切り抜き内での計算）
        zero_in_crop = zero_line_y - top
        distance_to_plus_30k = zero_in_crop - grid_30k_offset
        distance_to_minus_30k = (bottom - top - 1 + grid_minus_30k_offset) - zero_in_crop
        
        # グリッドラインを元画像にも追加
        # +30000ライン（元画像座標）
        y_30k_orig = int(top + grid_30k_offset)
        if 0 <= y_30k_orig < height_preview:
            cv2.line(overlay_img, (0, y_30k_orig), (width_preview, y_30k_orig), (128, 128, 128), 2)
            cv2.putText(overlay_img, '+30000', (10, max(20, y_30k_orig + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (64, 64, 64), 2)
        
        # -30000ライン（元画像座標）
        y_minus_30k_orig = int(bottom - 1 + grid_minus_30k_offset)
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
            # +30000ライン（最上部付近）
            y_30k = 0 + grid_30k_offset  # 最上部を基準に調整
            if 0 <= y_30k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_30k), (cropped_preview.shape[1], y_30k), (0, 150, 0), 3)
                cv2.putText(cropped_preview, '+30000', (10, max(20, y_30k + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 0), 2)
            
            # -30000ライン
            y_minus_30k = cropped_preview.shape[0] - 1 + grid_minus_30k_offset  # 最下部基準
            if 0 <= y_minus_30k < cropped_preview.shape[0]:
                cv2.line(cropped_preview, (0, y_minus_30k), (cropped_preview.shape[1], y_minus_30k), (150, 0, 0), 3)
                cv2.putText(cropped_preview, '-30000', (10, max(10, y_minus_30k - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 0, 0), 2)
            
            
            # 選択された画像の実際の最大値を表示
            if 'preview_image_index' in st.session_state:
                preview_idx = st.session_state.get('preview_image_index', 0)
                
                # プレビュー用の解析を実行して最大値を検出
                analyzer_preview = WebCompatibleAnalyzer()
                analyzer_preview.zero_y = zero_in_crop
                
                # 調整されたグリッドライン位置に基づいてスケールを計算
                y_30k_adjusted = 0 + grid_30k_offset
                y_minus_30k_adjusted = cropped_preview.shape[0] - 1 + grid_minus_30k_offset
                
                # 線形スケールのみ使用
                distance_to_plus_30k_adjusted = zero_in_crop - y_30k_adjusted
                distance_to_minus_30k_adjusted = y_minus_30k_adjusted - zero_in_crop
                
                if distance_to_plus_30k_adjusted > 0 and distance_to_minus_30k_adjusted > 0:
                    avg_distance_adjusted = (distance_to_plus_30k_adjusted + distance_to_minus_30k_adjusted) / 2
                    analyzer_preview.scale = 30000 / avg_distance_adjusted
                else:
                    analyzer_preview.scale = 122  # デフォルト


                # BGRに変換（グリッドラインなしの元画像を使用）
                cropped_bgr_preview = cv2.cvtColor(cropped_preview_original, cv2.COLOR_RGB2BGR)
                
                # グラフデータを抽出
                data_points_preview, color_preview, _ = analyzer_preview.extract_graph_data(cropped_bgr_preview)
                
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
                        cv2.circle(cropped_preview, (int(max_x), max_y_in_crop), 8, (0, 0, 255), -1)
                        cv2.circle(cropped_preview, (int(max_x), max_y_in_crop), 10, (0, 0, 200), 2)
                        # ラベルを追加（表示する値は実際の値）
                        label_text = f"MAX: {int(display_value):,}"
                        cv2.putText(cropped_preview, label_text, (cropped_preview.shape[1] - 180, max_y_in_crop - 5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    # 補正情報を表示
                    if actual_max_value and abs(correction_factor - 1.0) > 0.01:
                        info_text = f"🔍 検出値: {int(max_val_detected):,}玉 → 実際の値: {int(actual_max_value):,}玉 (補正率 x{correction_factor:.2f})"
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
                'grid_30k_offset': grid_30k_offset,
                'grid_minus_30k_offset': grid_minus_30k_offset
            }
            return settings
    else:
        # test_imageがない場合、セッションステートから取得
        def save_settings():
            return st.session_state.settings.copy()
    
    # STEP 5: 設定の保存の見出しを適切な場所に配置（画像がある場合のみ表示）
    if test_image:
        with main_col2:
            st.markdown("### 💾 STEP 5: 設定の保存")
            st.caption("調整が完了したら、端末名をつけて保存してください")
    
    # 設定の保存の内容（test_imageの有無で配置を変更）
    def render_save_settings():
        # 既存のプリセットを編集する場合
        if st.session_state.saved_presets:
            edit_mode = st.checkbox("既存のプリセットを編集", key="edit_preset_mode")
            
            if edit_mode:
                # 編集するプリセットを選択
                selected_preset = st.selectbox(
                    "編集するプリセットを選択",
                    ["新規作成"] + list(st.session_state.saved_presets.keys()),
                    key="edit_preset_select"
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
            save_button_label = "💾 プリセットを更新" if (st.session_state.saved_presets and 
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
                    st.session_state.saved_presets[preset_name] = settings.copy()
                    # 現在の設定も更新
                    st.session_state.settings = settings
                    
                    # データベースに保存
                    if save_preset_to_db(preset_name, settings):
                        # データベースから再読み込みして確実に反映
                        st.session_state.saved_presets = load_presets_from_db()
                        
                        # 編集モードかどうかでメッセージを変更
                        if (st.session_state.saved_presets and 
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
                st.session_state.settings = default_settings.copy()
                st.rerun()
    
    # 設定の保存を描画（画像がある場合のみ）
    if test_image:
        with main_col2:
            render_save_settings()
    
    # プリセット削除セクション（設定の保存の直後に配置）
    if test_image:
        with main_col2:
            # プリセット削除
            if st.session_state.saved_presets:
                st.markdown("### 🗑️ プリセットの削除")
                
                # 現在編集中のプリセットをデフォルトにする
                default_delete_preset = None
                if ('edit_preset_mode' in st.session_state and 
                    st.session_state.edit_preset_mode and 
                    'edit_preset_select' in st.session_state and
                    st.session_state.edit_preset_select != "新規作成"):
                    default_delete_preset = st.session_state.edit_preset_select
                
                # デフォルト値を見つける
                preset_list = list(st.session_state.saved_presets.keys())
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
                        del st.session_state.saved_presets[preset_to_delete]
                        
                        # データベースから削除
                        if delete_preset_from_db(preset_to_delete):
                            st.success(f"✅ プリセット '{preset_to_delete}' を削除しました")
                            st.rerun()

# フッター
st.markdown("---")

# フッターをカラムで配置
footer_col1, footer_col2, footer_col3 = st.columns([2, 1, 1])

with footer_col1:
    st.markdown(f"""
    🎰 パチンコグラフ解析システム v2.0  
    更新日: {datetime.now().strftime('%Y/%m/%d')}  
    Produced by [PPタウン](https://pp-town.com/)  
    Created by [fivenine-design.com](https://fivenine-design.com)
    """)

with footer_col3:
    if st.button("🚪 ログアウト", key="logout_button"):
        # Cookieを削除
        st.markdown("""
        <script>
        eraseCookie('pachi777_session');
        </script>
        """, unsafe_allow_html=True)
        st.session_state.authenticated = False
        if 'session_token' in st.session_state:
            del st.session_state.session_token
        time.sleep(0.3)
        st.rerun()