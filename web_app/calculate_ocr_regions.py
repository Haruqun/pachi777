import cv2
import numpy as np

# mask.pngを読み込み
mask = cv2.imread('/Users/haruqun/Work/pachi777/web_app/mask/mask.png')

# 赤色を検出
lower_red = np.array([0, 0, 254])
upper_red = np.array([1, 1, 255])
red_mask = cv2.inRange(mask, lower_red, upper_red)

# 輪郭を検出
contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 黒背景の位置（test_detail_ocr_app.pyで検出される黒背景領域）
# 注意: 黒背景は画像によって異なる可能性があるため、
# mask.pngの座標は黒背景からの相対座標として保存すべき

# オフセット（mask.pngの原点を黒背景左上に合わせるための値）
offset_x = 0
offset_y = -191

# マスクの座標は、黒背景に対してoffset_x, offset_yだけずらした位置にある
# つまり、mask.png内の座標(x, y)は、黒背景左上を基準にすると
# (x + offset_x, y + offset_y)の位置になる

print("# mask.pngから抽出したOCR領域（黒背景左上を基準とした相対座標）")
print(f"# オフセット: X={offset_x}, Y={offset_y}")
print("# 使用方法: 黒背景の左上座標を検出し、その座標にこれらの相対座標を加算")
print()
print("OCR_REGIONS_FROM_MASK = {")

# 領域を抽出してソート
regions = []
for contour in contours:
    x, y, w, h = cv2.boundingRect(contour)
    if w > 10 and h > 10:
        # 黒背景からの相対座標として保存
        # mask.png内の座標にオフセットを適用
        x_rel = x + offset_x
        y_rel = y + offset_y
        regions.append({'x': x_rel, 'y': y_rel, 'w': w, 'h': h, 
                       'x_orig': x, 'y_orig': y})

# Y座標、次にX座標でソート
regions.sort(key=lambda r: (r['y_orig'], r['x_orig']))

# 領域名を推定（位置から）
# 行ごとにグループ化
rows = []
current_row = []
last_y = -1

for region in regions:
    if last_y == -1 or abs(region['y_orig'] - last_y) < 30:
        current_row.append(region)
        last_y = region['y_orig']
    else:
        if current_row:
            rows.append(current_row)
        current_row = [region]
        last_y = region['y_orig']

if current_row:
    rows.append(current_row)

print(f"# {len(rows)}行、合計{len(regions)}個の領域を検出")
print()

# 重要な領域に名前を付ける
if len(rows) > 3:
    # 4行目（Y=311付近）- 大当り回数と初当り回数
    row3 = sorted(rows[3], key=lambda r: r['x_orig'])
    if len(row3) >= 2:
        r = row3[0]
        print(f"    'big_hit_count': {{'x': {r['x']}, 'y': {r['y']}, 'w': {r['w']}, 'h': {r['h']}, 'color': 'red'}},  # 大当り回数 25")
        r = row3[1]
        print(f"    'first_hit_count': {{'x': {r['x']}, 'y': {r['y']}, 'w': {r['w']}, 'h': {r['h']}, 'color': 'blue'}},  # 初当り回数 4")
        
    if len(row3) >= 3:
        r = row3[2]
        print(f"    'total_start': {{'x': {r['x']}, 'y': {r['y']}, 'w': {r['w']}, 'h': {r['h']}, 'color': 'white'}},  # 累計スタート 3721")

if len(rows) > 4:
    # 5行目（Y=438付近）- 確率と通常/チャンス
    row4 = sorted(rows[4], key=lambda r: r['x_orig'])
    if len(row4) >= 2:
        r = row4[0]
        print(f"    'big_hit_rate': {{'x': {r['x']}, 'y': {r['y']}, 'w': {r['w']}, 'h': {r['h']}, 'color': 'red'}},  # (1/148)")
        r = row4[1]
        print(f"    'first_hit_rate': {{'x': {r['x']}, 'y': {r['y']}, 'w': {r['w']}, 'h': {r['h']}, 'color': 'blue'}},  # (1/469)")
        
    if len(row4) >= 3:
        # 通常とチャンス中
        for i in range(2, len(row4)):
            r = row4[i]
            if i == 2:
                print(f"    'normal': {{'x': {r['x']+50}, 'y': {r['y']+10}, 'w': 80, 'h': 30, 'color': 'white'}},  # 通常 1877")
                print(f"    'chance': {{'x': {r['x']+140}, 'y': {r['y']+10}, 'w': 80, 'h': 30, 'color': 'white'}},  # チャンス中 1844")

if len(rows) > 5:
    # 6行目（Y=576付近）- 超、中、小、スタート、最高出玉
    row5 = sorted(rows[5], key=lambda r: r['x_orig'])
    if len(row5) >= 3:
        # 左側の3つの小さい領域が超、中、小
        small_regions = [r for r in row5 if r['w'] < 100]
        if len(small_regions) >= 3:
            r = small_regions[0]
            print(f"    'ultra': {{'x': {r['x']}, 'y': {r['y']}, 'w': {r['w']}, 'h': {r['h']}, 'color': 'red'}},  # 超 21")
            r = small_regions[1]
            print(f"    'middle': {{'x': {r['x']}, 'y': {r['y']}, 'w': {r['w']}, 'h': {r['h']}, 'color': 'red'}},  # 中 0")
            r = small_regions[2]
            print(f"    'small': {{'x': {r['x']}, 'y': {r['y']}, 'w': {r['w']}, 'h': {r['h']}, 'color': 'red'}},  # 小 4")
        
        # 大きい領域がスタートと最高出玉
        large_regions = [r for r in row5 if r['w'] >= 100]
        if len(large_regions) >= 1:
            r = large_regions[0]
            print(f"    'start': {{'x': {r['x']}, 'y': {r['y']}, 'w': {r['w']}, 'h': {r['h']}, 'color': 'white'}},  # スタート 369")
        if len(large_regions) >= 2:
            r = large_regions[1]
            print(f"    'max_payout': {{'x': {r['x']}, 'y': {r['y']}, 'w': {r['w']}, 'h': {r['h']}, 'color': 'white'}},  # 最高出玉 26830")

print("}")
print()

# 全領域も出力（デバッグ用）
print("\n# 全領域（デバッグ用）")
for i, region in enumerate(regions):
    print(f"# {i:2d}: orig({region['x_orig']:4}, {region['y_orig']:4}) -> final({region['x']:4}, {region['y']:4}) size({region['w']:3} x {region['h']:3})")