"""
完全版OCR領域定義 - 赤枠で示された全領域を含む
画像サイズ: 1179 x 2556px (リサイズ後)
"""

# 赤枠で示された全領域の座標定義
COMPLETE_REGIONS = {
    # ========== 上部メイン数値 ==========
    'big_hit': {
        'name': '大当り回数',
        'bbox': (55, 360, 200, 460),  # 赤色の大きな「25」
        'color': 'red',
        'expected': '25'
    },
    'big_hit_rate': {
        'name': '大当り確率',
        'bbox': (55, 460, 200, 495),  # (1/148)
        'color': 'red',
        'expected': '(1/148)'
    },
    'first_hit': {
        'name': '初当り回数',
        'bbox': (290, 360, 435, 460),  # 青色の大きな「4」
        'color': 'blue',
        'expected': '4'
    },
    'first_hit_rate': {
        'name': '初当り確率',
        'bbox': (290, 460, 435, 495),  # (1/469)
        'color': 'blue',
        'expected': '(1/469)'
    },
    'total_start': {
        'name': '累計スタート',
        'bbox': (532, 390, 658, 435),  # 3721
        'color': 'white',
        'expected': '3721'
    },
    'normal_count': {
        'name': '通常',
        'bbox': (472, 460, 580, 495),  # 1877
        'color': 'white',
        'expected': '1877'
    },
    'chance_count': {
        'name': 'チャンス中',
        'bbox': (600, 460, 718, 495),  # 1844
        'color': 'white',
        'expected': '1844'
    },
    
    # ========== 超中小 ==========
    'ultra': {
        'name': '超',
        'bbox': (55, 540, 105, 590),  # 21
        'color': 'red',
        'expected': '21'
    },
    'middle': {
        'name': '中',
        'bbox': (110, 540, 150, 590),  # 0
        'color': 'red',
        'expected': '0'
    },
    'small': {
        'name': '小',
        'bbox': (160, 540, 200, 590),  # 4
        'color': 'red',
        'expected': '4'
    },
    
    # ========== 中段データ ==========
    'start': {
        'name': 'スタート',
        'bbox': (310, 540, 415, 590),  # 369
        'color': 'white',
        'expected': '369'
    },
    'max_payout': {
        'name': '最高出玉',
        'bbox': (510, 540, 680, 590),  # 26830
        'color': 'white',
        'expected': '26830'
    },
    
    # ========== 下段第1行 ==========
    'max_hit': {
        'name': '最高一撃獲得',
        'bbox': (20, 650, 145, 690),  # 25760
        'color': 'white',
        'expected': '25760'
    },
    'chance_hits': {
        'name': 'チャンス中大当り',
        'bbox': (162, 650, 288, 690),  # 21
        'color': 'white',
        'expected': '21'
    },
    'chance_rate': {
        'name': 'チャンス中確率',
        'bbox': (305, 650, 430, 690),  # 1/87
        'color': 'white',
        'expected': '1/87'
    },
    'low_chance_hits': {
        'name': '低確中大当り',
        'bbox': (447, 650, 573, 690),  # --
        'color': 'white',
        'expected': '--'
    },
    'low_chance_rate': {
        'name': '低確中確率',
        'bbox': (590, 650, 715, 690),  # --
        'color': 'white',
        'expected': '--'
    },
    
    # ========== 下段第2行 ==========
    'initial_start': {
        'name': '初回特賞スタート',
        'bbox': (20, 725, 145, 760),  # 220
        'color': 'white',
        'expected': '220'
    },
    'prev_final': {
        'name': '前日最終スタート',
        'bbox': (162, 725, 288, 760),  # 107
        'color': 'white',
        'expected': '107'
    },
    'break_count': {
        'name': '突時回数',
        'bbox': (305, 725, 430, 760),  # --
        'color': 'white',
        'expected': '--'
    },
    'low_start': {
        'name': '低確スタート',
        'bbox': (447, 725, 573, 760),  # --
        'color': 'white',
        'expected': '--'
    },
    'play_time': {
        'name': '遊タイム',
        'bbox': (590, 725, 715, 760),  # --
        'color': 'white',
        'expected': '--'
    },
    
    # ========== 累計テーブル（8/6） ==========
    'date_86': {
        'name': '日付8/6',
        'bbox': (30, 815, 95, 850),  # 8/6
        'color': 'green',
        'expected': '8/6'
    },
    'total_86': {
        'name': '累計8/6',
        'bbox': (125, 815, 230, 850),  # 3772
        'color': 'white',
        'expected': '3772'
    },
    'first_rate_86': {
        'name': '初当り確率8/6',
        'bbox': (260, 815, 390, 850),  # 1/277
        'color': 'white',
        'expected': '1/277'
    },
    'chance_rate_86': {
        'name': 'チャンス中確率8/6',
        'bbox': (420, 815, 550, 850),  # 1/166
        'color': 'green',
        'expected': '1/166'
    },
    'payout_86': {
        'name': '最高出玉8/6',
        'bbox': (580, 815, 710, 850),  # 14670
        'color': 'green',
        'expected': '14670'
    },
    
    # ========== 累計テーブル（8/5） ==========
    'date_85': {
        'name': '日付8/5',
        'bbox': (30, 855, 95, 890),  # 8/5
        'color': 'green',
        'expected': '8/5'
    },
    'total_85': {
        'name': '累計8/5',
        'bbox': (125, 855, 230, 890),  # 3213
        'color': 'white',
        'expected': '3213'
    },
    'first_rate_85': {
        'name': '初当り確率8/5',
        'bbox': (260, 855, 390, 890),  # 1/324
        'color': 'white',
        'expected': '1/324'
    },
    'chance_rate_85': {
        'name': 'チャンス中確率8/5',
        'bbox': (420, 855, 550, 890),  # 1/79
        'color': 'green',
        'expected': '1/79'
    },
    'payout_85': {
        'name': '最高出玉8/5',
        'bbox': (580, 855, 710, 890),  # 22100
        'color': 'green',
        'expected': '22100'
    },
    
    # ========== 下部バー統計（最下部） ==========
    'bottom_stats': {
        'start_bottom': {
            'name': 'スタート（下部）',
            'bbox': (20, 1250, 80, 1280),  # 369
            'color': 'white',
            'expected': '369'
        },
        'stat_1': {
            'name': '統計1',
            'bbox': (90, 1250, 140, 1280),  # 23
            'color': 'white',
            'expected': '23'
        },
        'stat_2': {
            'name': '統計2',
            'bbox': (150, 1250, 200, 1280),  # 49
            'color': 'white',
            'expected': '49'
        },
        'stat_3': {
            'name': '統計3',
            'bbox': (210, 1250, 280, 1280),  # 121
            'color': 'white',
            'expected': '121'
        },
        'stat_4': {
            'name': '統計4',
            'bbox': (290, 1250, 340, 1280),  # 96
            'color': 'white',
            'expected': '96'
        },
        'stat_5': {
            'name': '統計5',
            'bbox': (350, 1250, 400, 1280),  # 22
            'color': 'white',
            'expected': '22'
        },
        'stat_6': {
            'name': '統計6',
            'bbox': (410, 1250, 470, 1280),  # 117
            'color': 'white',
            'expected': '117'
        },
        'stat_7': {
            'name': '統計7',
            'bbox': (480, 1250, 530, 1280),  # 11
            'color': 'white',
            'expected': '11'
        },
        'stat_8': {
            'name': '統計8',
            'bbox': (540, 1250, 590, 1280),  # 28
            'color': 'white',
            'expected': '28'
        },
        'stat_9': {
            'name': '統計9',
            'bbox': (600, 1250, 650, 1280),  # 38
            'color': 'white',
            'expected': '38'
        }
    }
}

# カテゴリ別に整理
REGIONS_BY_CATEGORY = {
    '上部メイン': ['big_hit', 'big_hit_rate', 'first_hit', 'first_hit_rate', 
                  'total_start', 'normal_count', 'chance_count'],
    '超中小': ['ultra', 'middle', 'small'],
    '中段': ['start', 'max_payout'],
    '下段1行目': ['max_hit', 'chance_hits', 'chance_rate', 'low_chance_hits', 'low_chance_rate'],
    '下段2行目': ['initial_start', 'prev_final', 'break_count', 'low_start', 'play_time'],
    '累計8/6': ['date_86', 'total_86', 'first_rate_86', 'chance_rate_86', 'payout_86'],
    '累計8/5': ['date_85', 'total_85', 'first_rate_85', 'chance_rate_85', 'payout_85'],
    '下部統計': ['start_bottom', 'stat_1', 'stat_2', 'stat_3', 'stat_4', 
                'stat_5', 'stat_6', 'stat_7', 'stat_8', 'stat_9']
}

# 色別分類
REGIONS_BY_COLOR = {
    'red': ['big_hit', 'big_hit_rate', 'ultra', 'middle', 'small'],
    'blue': ['first_hit', 'first_hit_rate'],
    'white': ['total_start', 'normal_count', 'chance_count', 'start', 'max_payout',
             'max_hit', 'chance_hits', 'chance_rate', 'low_chance_hits', 'low_chance_rate',
             'initial_start', 'prev_final', 'break_count', 'low_start', 'play_time',
             'total_86', 'first_rate_86', 'total_85', 'first_rate_85'],
    'green': ['date_86', 'chance_rate_86', 'payout_86', 'date_85', 'chance_rate_85', 'payout_85']
}

def get_all_regions():
    """すべての領域を取得"""
    all_regions = {}
    for key, value in COMPLETE_REGIONS.items():
        if key == 'bottom_stats':
            # 下部統計は個別に展開
            for stat_key, stat_value in value.items():
                all_regions[stat_key] = stat_value
        else:
            all_regions[key] = value
    return all_regions

def get_regions_by_category(category):
    """カテゴリ別に領域を取得"""
    if category == '下部統計':
        return COMPLETE_REGIONS['bottom_stats']
    
    region_keys = REGIONS_BY_CATEGORY.get(category, [])
    return {k: COMPLETE_REGIONS[k] for k in region_keys if k in COMPLETE_REGIONS}

def get_regions_by_color(color):
    """色別に領域を取得"""
    region_keys = REGIONS_BY_COLOR.get(color, [])
    result = {}
    for k in region_keys:
        if k in COMPLETE_REGIONS:
            result[k] = COMPLETE_REGIONS[k]
        elif k in COMPLETE_REGIONS.get('bottom_stats', {}):
            result[k] = COMPLETE_REGIONS['bottom_stats'][k]
    return result