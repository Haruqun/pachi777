import cv2
import numpy as np
import json

def extract_red_regions(mask_path):
    """マスク画像から赤い領域の座標を抽出"""
    
    # マスク画像を読み込み
    img = cv2.imread(mask_path)
    if img is None:
        print(f"画像を読み込めませんでした: {mask_path}")
        return []
    
    # 赤色を検出（BGR形式で赤は B:50-100, G:50-100, R:200-255）
    # mask.pngの赤色はRGB(255, 85, 85)なのでBGR(85, 85, 255)
    lower_red = np.array([50, 50, 200])
    upper_red = np.array([100, 100, 255])
    
    # もう少し広い範囲も試す
    red_mask = cv2.inRange(img, lower_red, upper_red)
    
    # デバッグ: 画像の色を確認
    print(f"画像サイズ: {img.shape}")
    # 画像の最初の赤い部分（上部のバー）の色を確認
    sample = img[30, 500]  # 上部バーの中心あたり
    print(f"サンプル色(BGR): {sample}")
    
    # より広い赤色の範囲を試す
    if np.sum(red_mask) == 0:
        # HSV色空間で試す
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # 赤色のHSV範囲
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 50, 50])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)
    
    # 赤色マスクを作成
    red_mask = cv2.inRange(img, lower_red, upper_red)
    
    # 輪郭を検出
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 各輪郭の矩形領域を取得
    regions = []
    for i, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        
        # 小さすぎる領域は無視（ノイズ除去）
        if w > 10 and h > 10:
            regions.append({
                'id': f'region_{i:02d}',
                'x': x,
                'y': y,
                'w': w,
                'h': h,
                'area': w * h
            })
    
    # Y座標でソート（上から下へ）、同じY座標ならX座標でソート（左から右へ）
    regions.sort(key=lambda r: (r['y'], r['x']))
    
    return regions

def assign_region_names(regions):
    """領域に意味のある名前を割り当て"""
    
    # Y座標でグループ化（同じ行にある領域をグループ化）
    rows = []
    current_row = []
    last_y = -1
    
    for region in regions:
        # Y座標が30px以内なら同じ行とみなす
        if last_y == -1 or abs(region['y'] - last_y) < 30:
            current_row.append(region)
            last_y = region['y']
        else:
            if current_row:
                rows.append(current_row)
            current_row = [region]
            last_y = region['y']
    
    if current_row:
        rows.append(current_row)
    
    # 各行の領域に名前を割り当て
    named_regions = {}
    
    # 推定される領域名（行と位置から推測）
    if len(rows) >= 5:
        # 1行目：ヘッダー（赤いバー）
        if len(rows[0]) >= 1:
            named_regions['header'] = rows[0][0]
        
        # 2行目：店舗名など
        if len(rows[1]) >= 1:
            named_regions['store_info'] = rows[1][0]
        
        # 3行目：8/7の表示
        if len(rows[2]) >= 1:
            named_regions['date_display'] = rows[2][0]
        
        # 4行目：大当り回数(25)、初当り回数(4)、累計スタート(3721)など
        if len(rows[3]) >= 2:
            rows[3].sort(key=lambda r: r['x'])  # X座標でソート
            if len(rows[3]) >= 2:
                named_regions['big_hit_count'] = rows[3][0]  # 左の大きい赤
                named_regions['first_hit_count'] = rows[3][1]  # 中央の大きい青
            if len(rows[3]) >= 3:
                named_regions['total_start'] = rows[3][2]  # 右の白
        
        # 5行目：(1/148)、(1/469)、通常/チャンス
        if len(rows[4]) >= 2:
            rows[4].sort(key=lambda r: r['x'])
            named_regions['big_hit_rate'] = rows[4][0]
            named_regions['first_hit_rate'] = rows[4][1]
            if len(rows[4]) >= 3:
                named_regions['normal_chance'] = rows[4][2]
    
    # 6行目：超、中、小、スタート、最高出玉
    if len(rows) > 5 and len(rows[5]) >= 3:
        rows[5].sort(key=lambda r: r['x'])
        named_regions['ultra'] = rows[5][0]
        named_regions['middle'] = rows[5][1]
        named_regions['small'] = rows[5][2]
        if len(rows[5]) > 3:
            named_regions['start'] = rows[5][3]
        if len(rows[5]) > 4:
            named_regions['max_payout'] = rows[5][4]
    
    # 7行目以降：テーブルデータ
    if len(rows) > 6:
        for i in range(6, len(rows)):
            row = rows[i]
            row.sort(key=lambda r: r['x'])
            for j, region in enumerate(row):
                named_regions[f'table_row{i-6}_col{j}'] = region
    
    return named_regions

def main():
    mask_path = '/Users/haruqun/Work/pachi777/web_app/mask/mask.png'
    
    # 赤い領域を抽出
    regions = extract_red_regions(mask_path)
    
    print(f"検出された領域数: {len(regions)}\n")
    
    # 領域情報を表示
    print("=== 検出された領域の座標 ===")
    for region in regions:
        print(f"{region['id']:12} : x={region['x']:4}, y={region['y']:4}, w={region['w']:3}, h={region['h']:3}")
    
    # 名前付き領域を取得
    named_regions = assign_region_names(regions)
    
    print("\n=== 推定される領域名 ===")
    for name, region in named_regions.items():
        print(f"{name:20} : x={region['x']:4}, y={region['y']:4}, w={region['w']:3}, h={region['h']:3}")
    
    # JSON形式で保存
    output = {
        'all_regions': regions,
        'named_regions': named_regions
    }
    
    with open('mask_regions.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n座標データをmask_regions.jsonに保存しました")
    
    # OCR_REGIONS形式で出力
    print("\n=== test_detail_ocr_app.py用のOCR_REGIONS定義 ===")
    print("OCR_REGIONS = {")
    for name, region in named_regions.items():
        # 色を推定（仮）
        color = 'white'  # デフォルト
        if 'hit' in name and 'first' not in name:
            color = 'red'
        elif 'first' in name:
            color = 'blue'
        elif name in ['ultra', 'middle', 'small']:
            color = 'red'
            
        print(f"    '{name}': {{'x': {region['x']}, 'y': {region['y']}, 'w': {region['w']}, 'h': {region['h']}, 'color': '{color}'}},")
    print("}")

if __name__ == "__main__":
    main()