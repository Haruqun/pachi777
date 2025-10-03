"""機種別の払い出し球数データ"""
import re

# 機種別の払い出し球数データ
MACHINE_PAYOUT_DATA = {
    # Re:ゼロから始める異世界生活
    "P Re:ゼロから始める異世界生活 season2": {
        'big_jackpot_balls': 1500,    # 10R
        'middle_jackpot_balls': 750,   # 5R
        'small_jackpot_balls': 450     # 3R
    },
    "Pリゼロ鬼がかりver": {
        'big_jackpot_balls': 1500,
        'middle_jackpot_balls': 600,   # 4R
        'small_jackpot_balls': 300     # 2R
    },
    
    # エヴァンゲリオン
    "P新世紀エヴァンゲリオン15": {
        'big_jackpot_balls': 1500,    # 10R
        'middle_jackpot_balls': 750,   # 5R
        'small_jackpot_balls': 300     # 2R
    },
    
    # その他人気機種
    "P北斗の拳 強敵": {
        'big_jackpot_balls': 1500,
        'middle_jackpot_balls': 750,
        'small_jackpot_balls': 450
    },
    "P牙狼GOLD IMPACT": {
        'big_jackpot_balls': 1500,
        'middle_jackpot_balls': 750,
        'small_jackpot_balls': 300
    },
    "Pフィーバー機動戦士ガンダムSEED": {
        'big_jackpot_balls': 1500,
        'middle_jackpot_balls': 600,
        'small_jackpot_balls': 300
    },
    
    # パチスロ（参考）
    "SパチスロReゼロ": {
        'big_jackpot_balls': 400,     # BIG
        'middle_jackpot_balls': 150,  # REG
        'small_jackpot_balls': 50     # 小役
    }
}


def get_machine_payouts(machine_name):
    """機種名から大当たり出玉数を取得"""
    if not machine_name:
        return None
    
    # 正規化（空白、記号、型番を除去）
    # M13, L1などの型番を除去
    normalized_name = re.sub(r'\s+[A-Z]\d+$', '', machine_name)  # 末尾の型番を除去
    normalized_name = normalized_name.replace(" ", "").replace("　", "").replace(":", "").replace("：", "")
    
    # 部分一致で検索（略称や表記揺れに対応）
    for key, data in MACHINE_PAYOUT_DATA.items():
        normalized_key = key.replace(" ", "").replace("　", "").replace(":", "").replace("：", "")
        # より柔軟なマッチング
        if normalized_key in normalized_name:
            return data
        # season2のようなバリエーションも考慮
        if 'season2' in normalized_key.lower() and 'season2' in normalized_name.lower():
            return data
    
    # Re:ゼロの略称対応
    if "リゼロ" in machine_name or "rezero" in machine_name.lower():
        for key, data in MACHINE_PAYOUT_DATA.items():
            if "Re:ゼロ" in key or "Re：ゼロ" in key or "Reゼロ" in key:
                return data
    
    return None


def add_machine_payout_data(machine_name, big_balls, middle_balls, small_balls):
    """新しい機種データを追加"""
    MACHINE_PAYOUT_DATA[machine_name] = {
        'big_jackpot_balls': big_balls,
        'middle_jackpot_balls': middle_balls,
        'small_jackpot_balls': small_balls
    }


def update_machine_payout_data(machine_name, big_balls=None, middle_balls=None, small_balls=None):
    """既存の機種データを更新"""
    if machine_name in MACHINE_PAYOUT_DATA:
        if big_balls is not None:
            MACHINE_PAYOUT_DATA[machine_name]['big_jackpot_balls'] = big_balls
        if middle_balls is not None:
            MACHINE_PAYOUT_DATA[machine_name]['middle_jackpot_balls'] = middle_balls
        if small_balls is not None:
            MACHINE_PAYOUT_DATA[machine_name]['small_jackpot_balls'] = small_balls
        return True
    return False