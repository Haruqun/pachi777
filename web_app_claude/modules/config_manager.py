"""設定管理とプリセット機能"""
import streamlit as st
import json
import os


# デフォルト設定値
DEFAULT_SETTINGS = {
    'search_start_offset': 50,
    'search_end_offset': 500,
    'crop_top': 350,
    'crop_bottom': 400,
    'left_margin': 120,
    'right_margin': 120,
    # グリッドライン調整値
    'grid_30k_offset': 1,       # +30000ライン（最上部）
    'grid_minus_30k_offset': -34, # -30000ライン（最下部）
    'exchange_rate': 3.57145,    # 交換レート（円/玉）デフォルトは28玉交換
    'zero_line_adjustment': 0,   # ゼロライン調整値
    # 超中小の払い出し球数
    'big_jackpot_balls': 1500,   # 超（大）の払い出し球数
    'middle_jackpot_balls': 750,  # 中の払い出し球数
    'small_jackpot_balls': 450    # 小の払い出し球数
}

# 定数
DEFAULT_IMAGE_WIDTH = 400


def init_settings():
    """設定を初期化"""
    if 'settings' not in st.session_state:
        st.session_state.settings = DEFAULT_SETTINGS.copy()


def get_settings():
    """現在の設定を取得"""
    init_settings()
    return st.session_state.settings


def update_settings(key, value):
    """設定を更新"""
    init_settings()
    st.session_state.settings[key] = value


def reset_settings():
    """設定をデフォルトに戻す"""
    st.session_state.settings = DEFAULT_SETTINGS.copy()


def get_game_type():
    """現在の遊技種別を取得"""
    return st.session_state.get('game_type', 'パチンコ')


def get_exchange_rate():
    """現在の交換レートを取得"""
    settings = get_settings()
    game_type = get_game_type()
    
    if game_type == 'パチンコ':
        return settings.get('exchange_rate', 3.57145)
    else:
        return settings.get('exchange_rate', 17.86)


def init_preset_system():
    """プリセットシステムを初期化"""
    if 'saved_presets' not in st.session_state:
        st.session_state.saved_presets = {}
        # デフォルトプリセットを読み込み（存在する場合）
        try:
            default_preset_path = os.path.join(os.path.dirname(__file__), '..', '..', 'default_presets.json')
            if os.path.exists(default_preset_path):
                with open(default_preset_path, 'r', encoding='utf-8') as f:
                    default_data = json.load(f)
                    if 'presets' in default_data:
                        st.session_state.saved_presets.update(default_data['presets'])
        except Exception:
            pass
        # データベースから読み込みフラグを設定
        st.session_state.force_reload_presets = True
    
    if 'current_preset_name' not in st.session_state:
        st.session_state.current_preset_name = 'デフォルト'


def load_preset(preset_name):
    """プリセットを読み込み"""
    init_preset_system()
    
    if preset_name in st.session_state.saved_presets:
        settings = st.session_state.saved_presets[preset_name].copy()
        st.session_state.settings = settings
        st.session_state.current_preset_name = preset_name
        return True
    return False


def save_preset(preset_name):
    """現在の設定をプリセットとして保存"""
    init_preset_system()
    
    st.session_state.saved_presets[preset_name] = st.session_state.settings.copy()
    st.session_state.current_preset_name = preset_name


def delete_preset(preset_name):
    """プリセットを削除"""
    init_preset_system()
    
    if preset_name in st.session_state.saved_presets:
        del st.session_state.saved_presets[preset_name]
        if st.session_state.current_preset_name == preset_name:
            st.session_state.current_preset_name = 'デフォルト'