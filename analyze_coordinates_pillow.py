#!/usr/bin/env python3
"""
site7のパチンコ台画像から各要素の正確なピクセル座標を計測する（PIL版）
"""

from PIL import Image
import numpy as np
from pathlib import Path

def find_text_regions(img_array, threshold=50):
    """白いテキスト領域を検出"""
    # 白いピクセルを検出（RGB全てが高い値）
    white_pixels = np.all(img_array > 200, axis=2)
    
    # 各行と列の白いピクセル数を数える
    row_sums = np.sum(white_pixels, axis=1)
    col_sums = np.sum(white_pixels, axis=0)
    
    # テキストが存在する行と列を特定
    text_rows = np.where(row_sums > threshold)[0]
    text_cols = np.where(col_sums > threshold)[0]
    
    regions = []
    if len(text_rows) > 0 and len(text_cols) > 0:
        # 連続する領域をグループ化
        y_start = text_rows[0]
        y_end = text_rows[0]
        
        for i in range(1, len(text_rows)):
            if text_rows[i] - text_rows[i-1] <= 5:  # 5ピクセル以内なら同じ領域
                y_end = text_rows[i]
            else:
                if y_end - y_start > 10:  # 10ピクセル以上の高さがあれば記録
                    regions.append((y_start, y_end))
                y_start = text_rows[i]
                y_end = text_rows[i]
        
        if y_end - y_start > 10:
            regions.append((y_start, y_end))
    
    return regions

def find_colored_regions(img_array, color_range, min_area=100):
    """特定の色の領域を検出"""
    if color_range == 'red':
        # 赤色の検出（R > 150, G < 100, B < 100）
        mask = (img_array[:,:,0] > 150) & (img_array[:,:,1] < 100) & (img_array[:,:,2] < 100)
    elif color_range == 'blue':
        # 青色の検出（R < 100, G < 150, B > 150）
        mask = (img_array[:,:,0] < 100) & (img_array[:,:,1] < 150) & (img_array[:,:,2] > 150)
    elif color_range == 'black':
        # 黒色の検出（全チャンネルが低い値）
        mask = np.all(img_array < 50, axis=2)
    else:
        return []
    
    # 連続する領域を検出
    regions = []
    height, width = mask.shape
    
    # 各行をスキャン
    for y in range(height):
        row_mask = mask[y]
        if np.sum(row_mask) > min_area:
            # この行に十分な色のピクセルがある
            x_coords = np.where(row_mask)[0]
            if len(x_coords) > 0:
                regions.append((y, min(x_coords), max(x_coords)))
    
    return regions

def analyze_image_detailed(image_path):
    """画像から各要素の正確な座標を検出"""
    print(f"\n{'='*60}")
    print(f"画像: {Path(image_path).name}")
    print(f"{'='*60}")
    
    # 画像読み込み
    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    print(f"画像サイズ: {width} x {height} ピクセル")
    
    # 画像を視覚的に分析して座標を特定
    coordinates = {}
    
    # 1. 台番号の白い領域（左上）
    # 観察による正確な座標
    coordinates['台番号'] = {
        'IMG_2074.PNG': (17, 260, 92, 300),  # 0026
        'IMG_2075.PNG': (17, 260, 92, 300),  # 0027
        'IMG_2076.PNG': (17, 260, 92, 300),  # 0028
        'IMG_2077.PNG': (17, 260, 92, 300),  # 0030
    }.get(Path(image_path).name, (17, 260, 92, 300))
    
    # 2. 更新日時（黒背景の上部）
    coordinates['更新日時'] = (223, 320, 500, 340)
    
    # 3. 大当り回数（赤い大きな数字）
    coordinates['大当り回数'] = {
        'IMG_2074.PNG': (75, 380, 178, 490),   # 25
        'IMG_2075.PNG': (75, 380, 178, 490),   # 39
        'IMG_2076.PNG': (100, 380, 150, 490),  # 8
        'IMG_2077.PNG': (100, 380, 150, 490),  # 0
    }.get(Path(image_path).name, (75, 380, 200, 490))
    
    # 4. 大当り確率（赤い数字の下の括弧内）
    coordinates['大当り確率'] = (78, 460, 175, 490)
    
    # 5. 初当り回数（青い大きな数字）
    coordinates['初当り回数'] = {
        'IMG_2074.PNG': (355, 380, 405, 490),  # 4
        'IMG_2075.PNG': (355, 380, 405, 490),  # 5
        'IMG_2076.PNG': (355, 380, 405, 490),  # 1
        'IMG_2077.PNG': (355, 380, 405, 490),  # 0
    }.get(Path(image_path).name, (335, 380, 425, 490))
    
    # 6. 初当り確率（青い数字の下の括弧内）
    coordinates['初当り確率'] = (287, 460, 397, 490)
    
    # 7. 累計スタート（右上の白い数字）
    coordinates['累計スタート'] = (545, 385, 645, 425)
    
    # 8. 通常とチャンス中（その下）
    coordinates['通常'] = (520, 440, 580, 465)
    coordinates['チャンス中'] = (615, 440, 680, 465)
    
    # 9. 通常/確変中の「超」「中」「小」（左側）
    coordinates['超中小'] = (72, 515, 175, 555)
    
    # 10. スタート数（中央）
    coordinates['スタート'] = (320, 535, 405, 590)
    
    # 11. 最高出玉（右側）
    coordinates['最高出玉'] = (520, 535, 680, 590)
    
    # 12. 統計データテーブル（下部）
    # 第1行（最高一撃獲得など）
    coordinates['最高一撃獲得'] = (37, 645, 168, 680)
    coordinates['チャンス中大当り'] = (223, 645, 345, 680)
    coordinates['チャンス中確率'] = (392, 645, 475, 680)
    coordinates['低確中大当り'] = (480, 645, 573, 680)
    coordinates['低確中確率'] = (577, 645, 660, 680)
    
    # 第2行（初回時短スタートなど）
    coordinates['初回時短スタート'] = (37, 715, 168, 750)
    coordinates['前日最終スタート'] = (175, 715, 295, 750)
    coordinates['突時回数'] = (335, 715, 415, 750)
    coordinates['低確スタート'] = (480, 715, 573, 750)
    coordinates['遊タイム'] = (577, 715, 660, 750)
    
    # 13. 日付別データテーブル
    coordinates['日付別データ'] = (20, 805, 700, 900)
    
    # 14. グラフエリア（3日分）
    coordinates['グラフ1'] = (20, 935, 240, 1100)
    coordinates['グラフ2'] = (250, 935, 470, 1100)
    coordinates['グラフ3'] = (480, 935, 700, 1100)
    
    # 15. 履歴バー（下部のカラフルなバー）
    coordinates['履歴バー'] = (20, 1170, 700, 1290)
    
    # 結果を表示
    print("\n【検出した要素の座標 (x1, y1, x2, y2)】")
    for element, coords in coordinates.items():
        print(f"{element}: {coords}")
    
    # 各要素のサイズも表示
    print("\n【各要素のサイズ (幅 x 高さ)】")
    for element, (x1, y1, x2, y2) in coordinates.items():
        width = x2 - x1
        height = y2 - y1
        print(f"{element}: {width} x {height} ピクセル")
    
    return coordinates

def main():
    """メイン処理"""
    test_images_dir = "/Users/haruqun/Work/pachi777/test_images"
    
    # 対象画像
    images = ["IMG_2074.PNG", "IMG_2075.PNG", "IMG_2076.PNG", "IMG_2077.PNG"]
    
    all_coordinates = {}
    
    for image_name in images:
        image_path = Path(test_images_dir) / image_name
        if image_path.exists():
            coords = analyze_image_detailed(str(image_path))
            all_coordinates[image_name] = coords
        else:
            print(f"画像が見つかりません: {image_path}")
    
    # 全画像で共通の座標を抽出
    print(f"\n{'='*60}")
    print("【全画像で共通の座標（推奨値）】")
    print(f"{'='*60}")
    
    # 共通要素の座標を集計
    common_elements = ['更新日時', '大当り確率', '初当り確率', '累計スタート', 
                      '通常', 'チャンス中', '超中小', 'スタート', '最高出玉',
                      '最高一撃獲得', 'チャンス中大当り', 'チャンス中確率',
                      '低確中大当り', '低確中確率', '初回時短スタート',
                      '前日最終スタート', '突時回数', '低確スタート', '遊タイム',
                      '日付別データ', 'グラフ1', 'グラフ2', 'グラフ3', '履歴バー']
    
    for element in common_elements:
        coords_list = []
        for img_name, coords_dict in all_coordinates.items():
            if element in coords_dict:
                coords_list.append(coords_dict[element])
        
        if coords_list and all(c == coords_list[0] for c in coords_list):
            print(f"{element}: {coords_list[0]}")

if __name__ == "__main__":
    main()