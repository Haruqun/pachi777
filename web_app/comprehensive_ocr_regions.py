"""
包括的なOCR領域定義 - 実際の検出結果に基づく完全版
"""

# 画像サイズと黒背景領域
IMAGE_INFO = {
    'width': 1179,
    'height': 2556,
    'black_region': [11, 507, 1172, 2080]  # 黒背景の実際の座標
}

# 実際に検出成功した領域（白色テキスト）
DETECTED_WHITE_REGIONS = {
    'total_start': {
        'name': '累計スタート',
        'bbox': (886, 638, 1040, 691),
        'color': 'white',
        'expected': '3721',
        'status': '✅'
    },
    'max_payout': {
        'name': '最高出玉',
        'bbox': (851, 897, 1087, 957),
        'color': 'white',
        'expected': '26830',
        'status': '✅'
    },
    'max_hit': {
        'name': '最高一撃獲得',
        'bbox': (65, 1066, 213, 1102),
        'color': 'white',
        'expected': '25760',
        'status': '✅'
    },
    'chance_rate': {
        'name': 'チャンス中確率',
        'bbox': (555, 1066, 663, 1104),
        'color': 'white',
        'expected': '1/87',
        'status': '✅'
    },
    'initial_start': {
        'name': '初回特賞スタート',
        'bbox': (96, 1184, 182, 1220),
        'color': 'white',
        'expected': '220',
        'status': '✅'
    },
    
    # 累計テーブル（8/6）
    'date_86': {
        'name': '日付8/6',
        'bbox': (50, 1326, 124, 1364),
        'color': 'white',
        'expected': '8/6',
        'status': '✅'
    },
    'total_86': {
        'name': '累計8/6',
        'bbox': (204, 1326, 322, 1362),
        'color': 'white',
        'expected': '3772',
        'status': '✅'
    },
    'chance_rate_86': {
        'name': 'チャンス中確率8/6',
        'bbox': (693, 1326, 831, 1364),
        'color': 'white',
        'expected': '1/166',
        'status': '✅'
    },
    'payout_86': {
        'name': '最高出玉8/6',
        'bbox': (953, 1326, 1099, 1362),
        'color': 'white',
        'expected': '14670',
        'status': '✅'
    },
    
    # 累計テーブル（8/5）
    'date_85': {
        'name': '日付8/5',
        'bbox': (50, 1386, 124, 1424),
        'color': 'white',
        'expected': '8/5',
        'status': '✅'
    },
    'total_85': {
        'name': '累計8/5',
        'bbox': (204, 1386, 321, 1422),
        'color': 'white',
        'expected': '3213',
        'status': '✅'
    },
    'chance_rate_85': {
        'name': 'チャンス中確率8/5',
        'bbox': (709, 1386, 815, 1424),
        'color': 'white',
        'expected': '1/79',
        'status': '✅'
    },
    'payout_85': {
        'name': '最高出玉8/5',
        'bbox': (951, 1386, 1099, 1422),
        'color': 'white',
        'expected': '22100',
        'status': '✅'
    }
}

# 下部の統計データ（検出成功）
BOTTOM_STATS = {
    'start_bottom': {
        'name': 'スタート（下部）',
        'bbox': (45, 2035, 106, 2063),
        'color': 'white',
        'expected': '369',
        'status': '✅'
    },
    'stat_1': {
        'name': '統計1',
        'bbox': (169, 2035, 210, 2063),
        'color': 'white',
        'expected': '23',
        'status': '✅'
    },
    'stat_2': {
        'name': '統計2',
        'bbox': (283, 2035, 324, 2063),
        'color': 'white',
        'expected': '49',
        'status': '✅'
    },
    'stat_3': {
        'name': '統計3',
        'bbox': (512, 2035, 552, 2063),
        'color': 'white',
        'expected': '96',
        'status': '✅'
    },
    'stat_4': {
        'name': '統計4',
        'bbox': (968, 2035, 1009, 2063),
        'color': 'white',
        'expected': '28',
        'status': '✅'
    },
    'stat_5': {
        'name': '統計5',
        'bbox': (1082, 2035, 1123, 2063),
        'color': 'white',
        'expected': '38',
        'status': '✅'
    }
}

# 未検出領域（推定座標）- 優先度高
UNDETECTED_CRITICAL = {
    # 赤色テキスト（最重要）
    'big_hit': {
        'name': '大当り回数',
        'bbox': (128, 636, 287, 741),  # 累計スタートの左側、赤色の大きな「25」
        'color': 'red',
        'expected': '25',
        'status': '❌',
        'priority': 'CRITICAL'
    },
    'ultra': {
        'name': '超',
        'bbox': (106, 908, 163, 951),  # 中段左側、赤色の「21」
        'color': 'red',
        'expected': '21',
        'status': '❌',
        'priority': 'CRITICAL'
    },
    'middle': {
        'name': '中',
        'bbox': (208, 908, 237, 952),  # 超の右側、赤色の「0」
        'color': 'red',
        'expected': '0',
        'status': '❌',
        'priority': 'CRITICAL'
    },
    'small': {
        'name': '小',
        'bbox': (275, 908, 307, 951),  # 中の右側、赤色の「4」
        'color': 'red',
        'expected': '4',
        'status': '❌',
        'priority': 'CRITICAL'
    },
    
    # 青色テキスト
    'first_hit': {
        'name': '初当り回数',
        'bbox': (493, 636, 640, 741),  # 大当りと累計の間、青色の「4」
        'color': 'blue',
        'expected': '4',
        'status': '⚠️',
        'priority': 'HIGH'
    }
}

# 未検出領域（推定座標）- 白色
UNDETECTED_WHITE = {
    'normal_count': {
        'name': '通常',
        'bbox': (750, 690, 850, 730),  # 累計スタートの下、「1877」
        'color': 'white',
        'expected': '1877',
        'status': '❌'
    },
    'chance_count': {
        'name': 'チャンス中',
        'bbox': (900, 690, 1000, 730),  # 通常の右側、「1844」
        'color': 'white',
        'expected': '1844',
        'status': '❌'
    },
    'start_middle': {
        'name': 'スタート（中段）',
        'bbox': (520, 897, 660, 957),  # 最高出玉の左側、白色の「369」
        'color': 'white',
        'expected': '369',
        'status': '❌'
    },
    'chance_hits': {
        'name': 'チャンス中大当り',
        'bbox': (395, 1066, 490, 1104),  # チャンス中確率の左側、「21」
        'color': 'white',
        'expected': '21',
        'status': '❌'
    },
    'prev_final': {
        'name': '前日最終スタート',
        'bbox': (343, 1184, 427, 1220),  # 初回特賞の右側、「107」
        'color': 'white',
        'expected': '107',
        'status': '❌'
    },
    'first_rate_86': {
        'name': '初当り確率8/6',
        'bbox': (432, 1326, 570, 1364),  # 累計とチャンス確率の間、「1/277」
        'color': 'white',
        'expected': '1/277',
        'status': '❌'
    },
    'first_rate_85': {
        'name': '初当り確率8/5',
        'bbox': (432, 1386, 570, 1424),  # 累計とチャンス確率の間、「1/324」
        'color': 'white',
        'expected': '1/324',
        'status': '❌'
    }
}

# 下部の小さなグラフの日付（検出成功）
GRAPH_DATES = {
    'graph_date_86': {
        'name': 'グラフ日付8/6',
        'bbox': (710, 1482, 757, 1509),
        'color': 'white',
        'expected': '8/6',
        'status': '✅'
    },
    'graph_date_85': {
        'name': 'グラフ日付8/5',
        'bbox': (1093, 1482, 1142, 1509),
        'color': 'white',
        'expected': '8/5',
        'status': '✅'
    }
}

# すべての領域を統合
ALL_REGIONS = {
    **DETECTED_WHITE_REGIONS,
    **BOTTOM_STATS,
    **UNDETECTED_CRITICAL,
    **UNDETECTED_WHITE,
    **GRAPH_DATES
}

# カテゴリ別に整理
REGIONS_BY_CATEGORY = {
    '検出成功（白色）': DETECTED_WHITE_REGIONS,
    '下部統計': BOTTOM_STATS,
    'グラフ日付': GRAPH_DATES,
    '未検出（赤色・最重要）': {k: v for k, v in UNDETECTED_CRITICAL.items() if v['color'] == 'red'},
    '未検出（青色）': {k: v for k, v in UNDETECTED_CRITICAL.items() if v['color'] == 'blue'},
    '未検出（白色）': UNDETECTED_WHITE
}

# 統計情報
STATISTICS = {
    'total_regions': len(ALL_REGIONS),
    'detected': len([v for v in ALL_REGIONS.values() if v['status'] == '✅']),
    'undetected': len([v for v in ALL_REGIONS.values() if v['status'] == '❌']),
    'partial': len([v for v in ALL_REGIONS.values() if v['status'] == '⚠️']),
    'critical_undetected': len([v for v in UNDETECTED_CRITICAL.values() if v['color'] == 'red'])
}

def get_critical_regions():
    """最重要の未検出領域を取得"""
    return {k: v for k, v in UNDETECTED_CRITICAL.items() if v.get('priority') == 'CRITICAL'}

def get_detected_regions():
    """検出成功した領域を取得"""
    return {k: v for k, v in ALL_REGIONS.values() if v['status'] == '✅'}

def print_summary():
    """検出状況のサマリーを表示"""
    print(f"📊 OCR領域検出状況")
    print(f"  全領域数: {STATISTICS['total_regions']}")
    print(f"  ✅ 検出成功: {STATISTICS['detected']}")
    print(f"  ❌ 未検出: {STATISTICS['undetected']}")
    print(f"  ⚠️ 部分検出: {STATISTICS['partial']}")
    print(f"  🔴 赤色未検出（最重要）: {STATISTICS['critical_undetected']}")
    
    print(f"\n🎯 最重要の未検出項目:")
    for key, region in get_critical_regions().items():
        print(f"  - {region['name']}: {region['expected']} ({region['color']})")

if __name__ == "__main__":
    print_summary()