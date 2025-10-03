"""汎用ユーティリティ関数"""
import re
import hashlib
import json
from datetime import datetime


def normalize_machine_number(number_str):
    """台番号を正規化（0005→5, 5番台→5など）"""
    if not number_str:
        return None
    
    # 文字列から数字だけを抽出
    numbers = re.findall(r'\d+', str(number_str))
    if numbers:
        # 最初の数字グループを整数に変換（先頭の0を除去）
        try:
            return str(int(numbers[0]))
        except:
            return None
    return None


def get_prioritized_data(result):
    """出玉詳細データとグラフデータから優先度に基づいてデータを取得する"""
    prioritized = {}
    
    # Claude API データの取得
    claude_data = None
    if result.get('claude_analysis') and result['claude_analysis'].get('success'):
        claude_data = result['claude_analysis'].get('data', {})
    
    # 1. 台番号
    if claude_data and claude_data.get('machine_number'):
        prioritized['machine_number'] = claude_data['machine_number']
    elif result.get('ocr_data') and result['ocr_data'].get('machine_number'):
        prioritized['machine_number'] = result['ocr_data']['machine_number']
    else:
        prioritized['machine_number'] = result.get('name', '').rsplit('.', 1)[0]
    
    # 2. 機種名
    if claude_data and claude_data.get('machine_name'):
        prioritized['machine_name'] = claude_data['machine_name']
    else:
        prioritized['machine_name'] = None
    
    # 3. 日付
    if claude_data and claude_data.get('date'):
        prioritized['date'] = claude_data['date']
    else:
        prioritized['date'] = None
    
    # 4. 大当たり回数関連
    if claude_data and claude_data.get('total_jackpots') is not None:
        prioritized['total_jackpots'] = claude_data['total_jackpots']
        prioritized['first_jackpots'] = claude_data.get('first_jackpots', 0)
        prioritized['big_jackpots'] = claude_data.get('big_jackpots')
        prioritized['medium_jackpots'] = claude_data.get('medium_jackpots')
        prioritized['small_jackpots'] = claude_data.get('small_jackpots')
    else:
        # グラフデータから取得
        prioritized['total_jackpots'] = result.get('jackpot_count', 0)
        prioritized['first_jackpots'] = (result.get('ocr_data') or {}).get('first_hit_count', 0)
        prioritized['big_jackpots'] = None
        prioritized['medium_jackpots'] = None
        prioritized['small_jackpots'] = None
    
    # 5. 回転数関連
    if claude_data and claude_data.get('total_rotations') is not None:
        prioritized['total_rotations'] = claude_data['total_rotations']
        prioritized['normal_rotations'] = claude_data.get('normal_rotations', 0)
        prioritized['chance_rotations'] = claude_data.get('chance_rotations', 0)
        prioritized['current_rotations'] = claude_data.get('current_rotations', 0)
    else:
        # グラフデータから取得
        ocr_data = result.get('ocr_data') or {}
        prioritized['total_rotations'] = ocr_data.get('total_start')
        prioritized['normal_rotations'] = None
        prioritized['chance_rotations'] = None
        prioritized['current_rotations'] = ocr_data.get('current_start')
    
    # 6. 初回特賞スタート
    if claude_data and claude_data.get('initial_ball_starts') is not None:
        prioritized['initial_ball_starts'] = claude_data['initial_ball_starts']
    else:
        # グラフから計算した初当たり回転数を使用
        metrics = result.get('rotation_metrics') or {}
        prioritized['initial_ball_starts'] = metrics.get('first_hit_spins', 0)
    
    # 7. 最高出玉
    if claude_data and claude_data.get('max_balls') is not None:
        prioritized['max_balls'] = claude_data['max_balls']
    else:
        # グラフデータから取得
        prioritized['max_balls'] = result.get('max_val', 0)
    
    # 8. 現在値
    # グラフから取得（Claude APIには通常ない）
    prioritized['current_val'] = result.get('current_val', 0)
    prioritized['min_val'] = result.get('min_val', 0)
    prioritized['max_val'] = result.get('max_val', 0)
    
    # 9. 初当たり値（グラフ専用）
    prioritized['first_hit_val'] = result.get('first_hit_val')
    
    # 10. 機種別払い出し球数
    if claude_data and claude_data.get('machine_payouts'):
        prioritized['machine_payouts'] = claude_data['machine_payouts']
    else:
        prioritized['machine_payouts'] = None
    
    return prioritized


def generate_image_hash(image):
    """画像のハッシュ値を生成"""
    import io
    from PIL import Image
    
    # 画像をバイナリに変換
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    
    # ハッシュ値を生成
    return hashlib.md5(img_byte_arr).hexdigest()


def settings_to_hash(settings):
    """設定辞書をハッシュ値に変換"""
    settings_str = json.dumps(settings, sort_keys=True)
    return hashlib.md5(settings_str.encode()).hexdigest()


def format_number_with_unit(value, unit='玉', show_sign=False):
    """数値を単位付きでフォーマット"""
    if value is None:
        return "---"
    
    # 符号の処理
    sign = ""
    if show_sign:
        if value > 0:
            sign = "+"
        elif value < 0:
            sign = "-"
            value = abs(value)
    
    # 数値のフォーマット
    formatted = f"{sign}{value:,}{unit}"
    return formatted


def calculate_rotation_rate(rotations, investment_yen):
    """回転率を計算（1000円あたり）"""
    if not investment_yen or investment_yen <= 0:
        return None
    
    rate = (rotations / investment_yen) * 1000
    return round(rate, 1)


def calculate_investment_from_balls(balls, unit_per_1000yen=250, exchange_rate=3.57145):
    """
    消費玉数から投資額を計算
    
    Args:
        balls: 消費玉数
        unit_per_1000yen: 1000円あたりの玉数（パチンコ:250玉、スロット:50枚）
        exchange_rate: 交換レート（円/玉）
        
    Returns:
        投資額（円）
    """
    if not balls or balls <= 0:
        return 0
    
    # 玉数から投資額を計算
    investment = (balls / unit_per_1000yen) * 1000
    return int(investment)


def parse_date_string(date_str):
    """日付文字列をパース"""
    if not date_str:
        return None
    
    # 一般的な日付パターン
    patterns = [
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY-MM-DD or YYYY/MM/DD
        r'(\d{1,2})[/-](\d{1,2})',              # MM-DD or MM/DD
        r'(\d{1,2})月(\d{1,2})日',              # M月D日
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            groups = match.groups()
            if len(groups) == 3:  # 年月日
                return f"{groups[0]}-{groups[1]:0>2}-{groups[2]:0>2}"
            elif len(groups) == 2:  # 月日のみ
                current_year = datetime.now().year
                return f"{current_year}-{groups[0]:0>2}-{groups[1]:0>2}"
    
    return None


def extract_numbers_from_text(text):
    """テキストから数値を抽出"""
    if not text:
        return []
    
    # カンマ付き数値も含めて抽出
    pattern = r'[\d,]+\.?\d*'
    matches = re.findall(pattern, text)
    
    numbers = []
    for match in matches:
        # カンマを除去して数値に変換
        try:
            num_str = match.replace(',', '')
            if '.' in num_str:
                num = float(num_str)
            else:
                num = int(num_str)
            numbers.append(num)
        except ValueError:
            continue
    
    return numbers