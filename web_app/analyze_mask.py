import cv2
import numpy as np

# マスク画像を読み込み
mask = cv2.imread('/Users/haruqun/Work/pachi777/web_app/mask/mask.png')

# 赤色を検出 (BGR形式で[0, 0, 255])
lower_red = np.array([0, 0, 254])
upper_red = np.array([1, 1, 255])
red_mask = cv2.inRange(mask, lower_red, upper_red)

# 輪郭を検出
contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 各輪郭の矩形領域を取得してY座標でソート
regions = []
for contour in contours:
    x, y, w, h = cv2.boundingRect(contour)
    if w > 10 and h > 10:  # 小さすぎる領域は無視
        regions.append({'x': x, 'y': y, 'w': w, 'h': h})

# Y座標、次にX座標でソート
regions.sort(key=lambda r: (r['y'], r['x']))

print("# mask.pngから抽出したOCR領域")
print("OCR_REGIONS = {")

# 領域に名前を割り当て（位置から推測）
names = [
    'header',  # 上部の赤いバー
    'store_info',  # 店舗情報
    'date_label',  # 8/7
    # 4行目の大きな数値
    'big_hit_count', 'first_hit_count', 'total_start_area',
    # 5行目の確率と通常/チャンス
    'big_hit_rate', 'first_hit_rate', 'normal_chance_area', 
    # 中段
    'ultra', 'middle', 'small', 'start', 'max_payout',
    # 下段テーブル (上の行)
    'max_hit', 'chance_hits', 'chance_rate', 'low_start', 'play_time',
    # 下段テーブル (下の行)  
    'initial_start', 'prev_final', 'rush_count', 'low_prob_start', 'lost_time'
]

for i, region in enumerate(regions):
    name = names[i] if i < len(names) else f'region_{i}'
    # 色を推定
    color = 'white'
    if 'hit' in name and 'first' not in name:
        color = 'red'
    elif 'first' in name:
        color = 'blue'
    elif name in ['ultra', 'middle', 'small']:
        color = 'red'
        
    print(f"    '{name}': {{'x': {region['x']}, 'y': {region['y']}, 'w': {region['w']}, 'h': {region['h']}, 'color': '{color}'}},")

print("}")
print(f"\n合計 {len(regions)} 個の領域を検出")