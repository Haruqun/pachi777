import cv2
import numpy as np

# mask2.pngを読み込み
mask = cv2.imread('/Users/haruqun/Work/pachi777/web_app/mask/mask2.png')

# 赤色を検出
lower_red = np.array([0, 0, 254])
upper_red = np.array([1, 1, 255])
red_mask = cv2.inRange(mask, lower_red, upper_red)

# 輪郭を検出
contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 黒背景からのオフセット
offset_x = 0
offset_y = -191

print("# mask2.pngから抽出したOCR領域（黒背景左上を基準とした相対座標）")
print(f"# オフセット: X={offset_x}, Y={offset_y}")
print("# 統合領域を使用して精度向上")
print()
print("OCR_REGIONS_FROM_MASK2 = {")

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

# 領域に名前を付ける
region_names = [
    ('header', 'white'),  # 0: ヘッダー
    ('store_info', 'white'),  # 1: 店舗情報
    ('date_info', 'white'),  # 2: 日付
    ('big_first_hit_combined', 'mixed'),  # 3: 大当り・初当り統合領域
    ('first_hit_combined', 'mixed'),  # 4: 初当り側の統合領域
    ('total_start_combined', 'white'),  # 5: 累計スタート統合領域
    ('normal', 'white'),  # 6: 通常
    ('chance', 'white'),  # 7: チャンス中
    ('start', 'white'),  # 8: スタート
    ('max_payout', 'white'),  # 9: 最高出玉
    ('ultra', 'red'),  # 10: 超
    ('middle', 'red'),  # 11: 中
    ('small', 'red'),  # 12: 小
    ('max_hit', 'white'),  # 13: 最高一撃獲得
    ('chance_hits', 'white'),  # 14: チャンス中大当り
    ('chance_rate', 'white'),  # 15: チャンス中確率
    ('low_hits', 'white'),  # 16: 低確中大当り
    ('play_time', 'white'),  # 17: 遊タイム
    ('initial_start', 'white'),  # 18: 初回特賞スタート
    ('prev_final', 'white'),  # 19: 前日最終スタート
    ('rush_count', 'white'),  # 20: 突時回数
    ('low_start', 'white'),  # 21: 低確スタート
    ('lost_time', 'white'),  # 22: 遊タイム
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