"""
実際の検出結果に基づく確実なOCR領域定義
検出成功したデータのみを使用
"""

# 実際に検出成功した領域の定義
VERIFIED_REGIONS = {
    # 上部メイン領域（白色テキストのみ - 検出成功）
    'total_start': {
        'name': '累計スタート',
        'bbox': (886, 638, 1040, 691),
        'color': 'white',
        'expected': '3721',
        'detected': True
    },
    
    # 中段領域（検出成功）
    'max_payout': {
        'name': '最高出玉',
        'bbox': (851, 897, 1087, 957),
        'color': 'white',
        'expected': '26830',
        'detected': True
    },
    
    # 下段第1行（検出成功）
    'max_hit': {
        'name': '最高一撃獲得',
        'bbox': (65, 1066, 213, 1102),
        'color': 'white',
        'expected': '25760',
        'detected': True
    },
    'chance_rate': {
        'name': 'チャンス中確率',
        'bbox': (555, 1066, 663, 1104),
        'color': 'white',
        'expected': '1/87',
        'detected': True
    },
    
    # 下段第2行（検出成功）
    'initial_start': {
        'name': '初回特賞スタート',
        'bbox': (96, 1184, 182, 1220),
        'color': 'white',
        'expected': '220',
        'detected': True
    },
    
    # 累計テーブル 8/6行（検出成功）
    'date_86': {
        'name': '日付8/6',
        'bbox': (50, 1326, 124, 1364),
        'color': 'white',
        'expected': '8/6',
        'detected': True
    },
    'total_86': {
        'name': '累計8/6',
        'bbox': (204, 1326, 322, 1362),
        'color': 'white',
        'expected': '3772',
        'detected': True
    },
    'chance_rate_86': {
        'name': 'チャンス中確率8/6',
        'bbox': (693, 1326, 831, 1364),
        'color': 'white',
        'expected': '1/166',
        'detected': True
    },
    'payout_86': {
        'name': '最高出玉8/6',
        'bbox': (953, 1326, 1099, 1362),
        'color': 'white',
        'expected': '14670',
        'detected': True
    },
    
    # 累計テーブル 8/5行（検出成功）
    'date_85': {
        'name': '日付8/5',
        'bbox': (50, 1386, 124, 1424),
        'color': 'white',
        'expected': '8/5',
        'detected': True
    },
    'total_85': {
        'name': '累計8/5',
        'bbox': (204, 1386, 321, 1422),
        'color': 'white',
        'expected': '3213',
        'detected': True
    },
    'chance_rate_85': {
        'name': 'チャンス中確率8/5',
        'bbox': (709, 1386, 815, 1424),
        'color': 'white',
        'expected': '1/79',
        'detected': True
    },
    'payout_85': {
        'name': '最高出玉8/5',
        'bbox': (951, 1386, 1099, 1422),
        'color': 'white',
        'expected': '22100',
        'detected': True
    },
    
    # 下部の統計データ（y=2035の領域）
    'bottom_start': {
        'name': 'スタート（下部）',
        'bbox': (45, 2035, 106, 2063),
        'color': 'white',
        'expected': '369',
        'detected': True
    },
    'bottom_stat1': {
        'name': '下部統計1',
        'bbox': (169, 2035, 210, 2063),
        'color': 'white',
        'expected': '23',
        'detected': True
    },
    'bottom_stat2': {
        'name': '下部統計2',
        'bbox': (283, 2035, 324, 2063),
        'color': 'white',
        'expected': '49',
        'detected': True
    },
    'bottom_stat3': {
        'name': '下部統計3',
        'bbox': (512, 2035, 552, 2063),
        'color': 'white',
        'expected': '96',
        'detected': True
    },
    'bottom_stat4': {
        'name': '下部統計4',
        'bbox': (968, 2035, 1009, 2063),
        'color': 'white',
        'expected': '28',
        'detected': True
    },
    'bottom_stat5': {
        'name': '下部統計5',
        'bbox': (1082, 2035, 1123, 2063),
        'color': 'white',
        'expected': '38',
        'detected': True
    }
}

# 推定で追加すべき領域（等間隔計算）
ESTIMATED_REGIONS = {
    # 下段第1行の補完
    'chance_hits': {
        'name': 'チャンス中大当り',
        'bbox': (180, 1066, 260, 1102),  # 25760と1/87の間
        'color': 'white',
        'expected': '21',
        'detected': False
    },
    'low_chance_hits': {
        'name': '低確中大当り',
        'bbox': (457, 1066, 507, 1102),  # 等間隔配置
        'color': 'white',
        'expected': '--',
        'detected': False
    },
    'low_chance_rate': {
        'name': '低確中確率',
        'bbox': (790, 1066, 880, 1102),  # 等間隔配置
        'color': 'white',
        'expected': '--',
        'detected': False
    },
    
    # 下段第2行の補完
    'prev_final': {
        'name': '前日最終スタート',
        'bbox': (210, 1184, 295, 1220),  # 220の右側
        'color': 'white',
        'expected': '107',
        'detected': False
    },
    'break_count': {
        'name': '突時回数',
        'bbox': (338, 1184, 388, 1220),  # 等間隔配置
        'color': 'white',
        'expected': '--',
        'detected': False
    },
    'low_start': {
        'name': '低確スタート',
        'bbox': (457, 1184, 525, 1220),  # 等間隔配置
        'color': 'white',
        'expected': '--',
        'detected': False
    },
    'play_time': {
        'name': '遊タイム',
        'bbox': (602, 1184, 670, 1220),  # 等間隔配置
        'color': 'white',
        'expected': '--',
        'detected': False
    },
    
    # 累計テーブルの補完
    'first_rate_86': {
        'name': '初当り確率8/6',
        'bbox': (432, 1326, 570, 1364),  # 3772と1/166の間
        'color': 'white',
        'expected': '1/277',
        'detected': False
    },
    'first_rate_85': {
        'name': '初当り確率8/5',
        'bbox': (432, 1386, 570, 1424),  # 3213と1/79の間
        'color': 'white',
        'expected': '1/324',
        'detected': False
    }
}

# 未検出の重要領域（赤色・青色）
CRITICAL_UNDETECTED = {
    'big_hit': {
        'name': '大当り回数',
        'bbox': (75, 590, 205, 690),  # 推定位置
        'color': 'red',
        'expected': '25',
        'priority': 'CRITICAL'
    },
    'first_hit': {
        'name': '初当り回数',
        'bbox': (345, 590, 415, 690),  # 推定位置
        'color': 'blue',
        'expected': '4',
        'priority': 'CRITICAL'
    },
    'ultra': {
        'name': '超',
        'bbox': (73, 740, 117, 790),  # 推定位置
        'color': 'red',
        'expected': '21',
        'priority': 'HIGH'
    },
    'middle': {
        'name': '中',
        'bbox': (125, 740, 155, 790),  # 推定位置
        'color': 'red',
        'expected': '0',
        'priority': 'HIGH'
    },
    'small': {
        'name': '小',
        'bbox': (165, 740, 195, 790),  # 推定位置
        'color': 'red',
        'expected': '4',
        'priority': 'HIGH'
    },
    'start_middle': {
        'name': 'スタート（中段）',
        'bbox': (320, 897, 410, 957),  # 推定位置
        'color': 'white',
        'expected': '369',
        'priority': 'MEDIUM'
    },
    'normal_count': {
        'name': '通常',
        'bbox': (750, 690, 850, 730),  # 推定位置
        'color': 'white',
        'expected': '1877',
        'priority': 'MEDIUM'
    },
    'chance_count': {
        'name': 'チャンス中',
        'bbox': (900, 690, 1000, 730),  # 推定位置
        'color': 'white',
        'expected': '1844',
        'priority': 'MEDIUM'
    }
}

# すべての領域を統合（検出成功したもののみ使用）
def get_all_verified_regions():
    """検出成功した領域のみを返す"""
    return VERIFIED_REGIONS

def get_all_regions_with_estimates():
    """検出成功した領域と推定領域を返す"""
    return {**VERIFIED_REGIONS, **ESTIMATED_REGIONS}

def get_complete_regions():
    """すべての領域（未検出含む）を返す"""
    return {**VERIFIED_REGIONS, **ESTIMATED_REGIONS, **CRITICAL_UNDETECTED}