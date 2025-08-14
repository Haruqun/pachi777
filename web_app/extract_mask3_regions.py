import cv2
import numpy as np

# mask3.pngを読み込み
mask = cv2.imread('/Users/haruqun/Work/pachi777/web_app/mask/mask3.png')

# 赤色を検出
lower_red = np.array([0, 0, 254])
upper_red = np.array([1, 1, 255])
red_mask = cv2.inRange(mask, lower_red, upper_red)

# 輪郭を検出
contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 黒背景からのオフセット（最適値）
offset_x = 0
offset_y = -188

print("# mask3.pngから抽出したOCR領域（黒背景左上を基準とした相対座標）")
print(f"# オフセット: X={offset_x}, Y={offset_y}")
print("# 大当り/初当りを上下分離（数値と確率を別々に）")
print()
print("OCR_REGIONS_FROM_MASK3 = {")

# 領域を抽出してソート
regions = []
for contour in contours:
    x, y, w, h = cv2.boundingRect(contour)
    if w > 10 and h > 10:
        # 黒背景からの相対座標として保存
        x_rel = x + offset_x
        y_rel = y + offset_y
        regions.append({'x': x_rel, 'y': y_rel, 'w': w, 'h': h, 
                       'x_orig': x, 'y_orig': y})

# Y座標、次にX座標でソート
regions.sort(key=lambda r: (r['y_orig'], r['x_orig']))

# 領域に名前を付ける（mask3用）
region_names = [
    ('header', 'white'),  # 0: ヘッダー
    ('store_info', 'white'),  # 1: 店舗情報
    ('date_info', 'white'),  # 2: 日付
    ('big_hit_count', 'red'),  # 3: 大当り回数（上段）
    ('first_hit_count', 'blue'),  # 4: 初当り回数（上段）
    ('total_start', 'white'),  # 5: 累計スタート
    ('big_hit_rate', 'red'),  # 6: 大当り確率（下段）
    ('first_hit_rate', 'blue'),  # 7: 初当り確率（下段）
    ('normal', 'white'),  # 8: 通常
    ('chance', 'white'),  # 9: チャンス中
    ('ultra', 'red'),  # 10: 超
    ('middle', 'red'),  # 11: 中
    ('small', 'red'),  # 12: 小
    ('start', 'white'),  # 13: スタート
    ('max_payout', 'white'),  # 14: 最高出玉
    ('max_hit', 'white'),  # 15: 最高一撃獲得
    ('chance_hits', 'white'),  # 16: チャンス中大当り
    ('chance_rate', 'white'),  # 17: チャンス中確率
    ('low_hits', 'white'),  # 18: 低確中大当り
    ('play_time', 'white'),  # 19: 遊タイム
    ('initial_start', 'white'),  # 20: 初回特賞スタート
    ('prev_final', 'white'),  # 21: 前日最終スタート
    ('rush_count', 'white'),  # 22: 突時回数
    ('low_start', 'white'),  # 23: 低確スタート
    ('lost_time', 'white'),  # 24: 遊タイム
]

print(f"# {len(regions)}個の領域を検出")
print()

for i, region in enumerate(regions):
    if i < len(region_names):
        name, color = region_names[i]
        r = region
        print(f"    '{name}': {{'x': {r['x']}, 'y': {r['y']}, 'w': {r['w']}, 'h': {r['h']}, 'color': '{color}'}},")

print("}")
print()

# デバッグ用：全領域の詳細
print("# 全領域の詳細（デバッグ用）")
for i, region in enumerate(regions):
    if i < len(region_names):
        name = region_names[i][0]
        print(f"# {i:2d} {name:25s}: ({region['x']:4}, {region['y']:4}) size({region['w']:3} x {region['h']:3})")