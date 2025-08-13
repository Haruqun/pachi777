"""
正確なOCR領域定義（実際の検出結果に基づく）
"""

# 実際に検出できた領域（白色テキスト）- これらは正確
DETECTED_REGIONS = {
    'total_start': {
        'name': '累計スタート',
        'bbox': (886, 638, 1040, 691),  # 実際の検出座標
        'color': 'white',
        'expected': '3721',
        'status': '✅ 検出成功'
    },
    'max_payout': {
        'name': '最高出玉',
        'bbox': (851, 897, 1087, 957),  # 実際の検出座標
        'color': 'white',
        'expected': '26830',
        'status': '✅ 検出成功'
    },
    'max_hit': {
        'name': '最高一撃獲得',
        'bbox': (65, 1066, 213, 1102),  # 実際の検出座標
        'color': 'white',
        'expected': '25760',
        'status': '✅ 検出成功'
    },
    'chance_rate': {
        'name': 'チャンス中確率',
        'bbox': (555, 1066, 663, 1104),  # 実際の検出座標
        'color': 'white',
        'expected': '1/87',
        'status': '✅ 検出成功'
    },
    'initial_start': {
        'name': '初回特賞スタート',
        'bbox': (96, 1184, 182, 1220),  # 実際の検出座標
        'color': 'white',
        'expected': '220',
        'status': '✅ 検出成功'
    },
    
    # 累計テーブル（8/6）
    'date_86': {
        'name': '日付8/6',
        'bbox': (50, 1326, 124, 1364),  # 実際の検出座標
        'color': 'white',
        'expected': '8/6',
        'status': '✅ 検出成功'
    },
    'total_86': {
        'name': '累計8/6',
        'bbox': (204, 1326, 322, 1362),  # 実際の検出座標
        'color': 'white',
        'expected': '3772',
        'status': '✅ 検出成功'
    },
    'chance_rate_86': {
        'name': 'チャンス中確率8/6',
        'bbox': (693, 1326, 831, 1364),  # 実際の検出座標
        'color': 'white',
        'expected': '1/166',
        'status': '✅ 検出成功'
    },
    'payout_86': {
        'name': '最高出玉8/6',
        'bbox': (953, 1326, 1099, 1362),  # 実際の検出座標
        'color': 'white',
        'expected': '14670',
        'status': '✅ 検出成功'
    },
    
    # 累計テーブル（8/5）
    'date_85': {
        'name': '日付8/5',
        'bbox': (50, 1386, 124, 1424),  # 実際の検出座標
        'color': 'white',
        'expected': '8/5',
        'status': '✅ 検出成功'
    },
    'total_85': {
        'name': '累計8/5',
        'bbox': (204, 1386, 321, 1422),  # 実際の検出座標
        'color': 'white',
        'expected': '3213',
        'status': '✅ 検出成功'
    },
    'chance_rate_85': {
        'name': 'チャンス中確率8/5',
        'bbox': (709, 1386, 815, 1424),  # 実際の検出座標
        'color': 'white',
        'expected': '1/79',
        'status': '✅ 検出成功'
    },
    'payout_85': {
        'name': '最高出玉8/5',
        'bbox': (951, 1386, 1099, 1422),  # 実際の検出座標
        'color': 'white',
        'expected': '22100',
        'status': '✅ 検出成功'
    }
}

# 検出できていない領域（推定座標）
UNDETECTED_REGIONS = {
    # 赤色テキスト（最重要）
    'big_hit': {
        'name': '大当り回数',
        'bbox': (128, 636, 287, 741),  # 推定座標（累計スタートの左側）
        'color': 'red',
        'expected': '25',
        'status': '❌ 未検出',
        'issue': '赤色の大きな数字の検出失敗'
    },
    
    # 青色テキスト
    'first_hit': {
        'name': '初当り回数',
        'bbox': (493, 636, 640, 741),  # 推定座標（大当りと累計の間）
        'color': 'blue',
        'expected': '4',
        'status': '⚠️ 部分検出',
        'issue': '青色は検出できるが座標調整必要'
    },
    
    # 超中小（赤色）
    'ultra': {
        'name': '超',
        'bbox': (106, 908, 163, 951),  # 推定座標
        'color': 'red',
        'expected': '21',
        'status': '❌ 未検出'
    },
    'middle': {
        'name': '中',
        'bbox': (208, 908, 237, 952),  # 推定座標
        'color': 'red',
        'expected': '0',
        'status': '❌ 未検出'
    },
    'small': {
        'name': '小',
        'bbox': (275, 908, 307, 951),  # 推定座標
        'color': 'red',
        'expected': '4',
        'status': '❌ 未検出'
    },
    
    # チャンス中大当り（白色だが未検出）
    'chance_hits': {
        'name': 'チャンス中大当り',
        'bbox': (395, 1066, 440, 1104),  # 推定座標（チャンス確率の左）
        'color': 'white',
        'expected': '21',
        'status': '❌ 未検出'
    },
    
    # 前日最終スタート（白色だが未検出）
    'prev_final': {
        'name': '前日最終スタート',
        'bbox': (343, 1184, 427, 1220),  # 推定座標（初回特賞の右）
        'color': 'white',
        'expected': '107',
        'status': '❌ 未検出'
    },
    
    # 初当り確率（未検出）
    'first_rate_86': {
        'name': '初当り確率8/6',
        'bbox': (432, 1326, 570, 1364),  # 推定座標（累計とチャンス確率の間）
        'color': 'white',
        'expected': '1/277',
        'status': '❌ 未検出'
    },
    'first_rate_85': {
        'name': '初当り確率8/5',
        'bbox': (432, 1386, 570, 1424),  # 推定座標
        'color': 'white',
        'expected': '1/324',
        'status': '❌ 未検出'
    }
}

# 特殊な位置の数値（下部のスタート関連）
BOTTOM_SECTION = {
    'start_main': {
        'name': 'スタート（メイン）',
        'bbox': (45, 2035, 106, 2063),  # 実際の検出座標
        'color': 'white',
        'expected': '369',
        'status': '✅ 検出成功',
        'note': '画面下部のスタート数値'
    },
    'other_stats': {
        'name': 'その他統計',
        'bbox_list': [
            (169, 2035, 210, 2063),  # 23
            (283, 2035, 324, 2063),  # 49
            (512, 2035, 552, 2063),  # 96
            (968, 2035, 1009, 2063), # 28
            (1082, 2035, 1123, 2063) # 38
        ],
        'status': '✅ 検出成功',
        'note': '下部の各種統計値'
    }
}

# 中段のスタート領域（推定）
MIDDLE_START_REGION = {
    'start_middle': {
        'name': 'スタート（中段）',
        'bbox': (520, 897, 660, 957),  # 推定座標（最高出玉の左）
        'color': 'white',
        'expected': '369',
        'status': '❓ 位置要確認',
        'note': '中段右側にもスタート表示がある可能性'
    }
}

# 全領域を統合
ALL_REGIONS = {
    **DETECTED_REGIONS,
    **UNDETECTED_REGIONS,
    **BOTTOM_SECTION,
    **MIDDLE_START_REGION
}

# 優先度別リスト
PRIORITY_REGIONS = {
    'critical': [  # 最重要
        'big_hit',     # 大当り回数（赤）
        'ultra',       # 超（赤）
        'middle',      # 中（赤）
        'small'        # 小（赤）
    ],
    'high': [      # 重要
        'first_hit',   # 初当り回数（青）
        'chance_hits', # チャンス中大当り
        'prev_final',  # 前日最終スタート
        'first_rate_86', # 初当り確率8/6
        'first_rate_85'  # 初当り確率8/5
    ],
    'normal': [    # 通常（既に検出成功）
        'total_start',
        'max_payout',
        'max_hit',
        'chance_rate',
        'initial_start'
    ]
}

def get_region_by_priority(priority='critical'):
    """優先度別に領域を取得"""
    region_keys = PRIORITY_REGIONS.get(priority, [])
    return {k: ALL_REGIONS[k] for k in region_keys if k in ALL_REGIONS}

def get_undetected_regions():
    """未検出領域のみ取得"""
    return UNDETECTED_REGIONS

def get_detected_regions():
    """検出成功領域のみ取得"""
    return DETECTED_REGIONS