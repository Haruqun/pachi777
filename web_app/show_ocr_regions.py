import cv2
import numpy as np
from PIL import Image
import sys

# Figmaで確認した正確なOCR領域の定義（絶対座標）
OCR_REGIONS_ABSOLUTE = {
    # 上段の大きな数値（赤と青）
    'big_hit_count': {'x': 89, 'y': 624, 'w': 239, 'h': 125, 'color': 'red'},  # 大当り回数 25
    'big_hit_rate': {'x': 89, 'y': 751, 'w': 239, 'h': 50, 'color': 'red'},  # (1/148)
    'first_hit_count': {'x': 329, 'y': 624, 'w': 239, 'h': 125, 'color': 'blue'},  # 初当り回数 4
    'first_hit_rate': {'x': 329, 'y': 751, 'w': 239, 'h': 50, 'color': 'blue'},  # (1/469)
    
    # 累計スタート（白）
    'total_start': {'x': 570, 'y': 634, 'w': 179, 'h': 60, 'color': 'white'},  # 3721
    'normal': {'x': 515, 'y': 704, 'w': 110, 'h': 50, 'color': 'white'},  # 通常 1877
    'chance': {'x': 625, 'y': 704, 'w': 110, 'h': 50, 'color': 'white'},  # チャンス中 1844
    
    # 中段の数値
    'ultra': {'x': 89, 'y': 823, 'w': 74, 'h': 60, 'color': 'red'},  # 超 21
    'middle': {'x': 163, 'y': 823, 'w': 74, 'h': 60, 'color': 'red'},  # 中 0
    'small': {'x': 237, 'y': 823, 'w': 74, 'h': 60, 'color': 'red'},  # 小 4
    
    'start': {'x': 330, 'y': 823, 'w': 155, 'h': 60, 'color': 'white'},  # スタート 369
    'max_payout': {'x': 532, 'y': 823, 'w': 217, 'h': 60, 'color': 'white'},  # 最高出玉 26830
    
    # 下段のテーブルデータ（すべて白）
    'max_hit': {'x': 57, 'y': 928, 'w': 165, 'h': 48, 'color': 'white'},  # 最高一撃獲得 25760
    'chance_hits': {'x': 224, 'y': 928, 'w': 90, 'h': 48, 'color': 'white'},  # チャンス中大当り 21
    'chance_rate': {'x': 354, 'y': 928, 'w': 115, 'h': 48, 'color': 'white'},  # チャンス中確率 1/87
    
    'initial_start': {'x': 74, 'y': 1003, 'w': 110, 'h': 48, 'color': 'white'},  # 初回特賞スタート 220
    'prev_final': {'x': 229, 'y': 1003, 'w': 110, 'h': 48, 'color': 'white'},  # 前日最終スタート 107
}

def overlay_ocr_regions(image_path):
    """OCR領域を画像にオーバーレイして表示"""
    
    # 画像を読み込み
    img = cv2.imread(image_path)
    if img is None:
        print(f"画像を読み込めませんでした: {image_path}")
        return
    
    height, width = img.shape[:2]
    
    # リサイズ（1179pxに統一）
    if width != 1179:
        scale = 1179 / width
        new_width = 1179
        new_height = int(height * scale)
        img = cv2.resize(img, (new_width, new_height))
        print(f"画像をリサイズしました: {width}x{height} → {new_width}x{new_height}")
    
    # OCR領域を描画
    for name, region in OCR_REGIONS_ABSOLUTE.items():
        x = region['x']
        y = region['y']
        w = region['w']
        h = region['h']
        
        # 色設定
        if region['color'] == 'red':
            color = (0, 0, 255)  # BGR形式で赤
        elif region['color'] == 'blue':
            color = (255, 0, 0)  # BGR形式で青
        else:  # white
            color = (200, 200, 200)  # グレー
        
        # 矩形を描画（太さ2）
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
        
        # ラベルを表示
        label = name.replace('_', ' ').title()
        
        # テキストの背景を描画（読みやすくするため）
        (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(img, (x, y - text_height - 8), (x + text_width + 4, y - 2), color, -1)
        
        # テキストを描画（白色）
        cv2.putText(img, label, (x + 2, y - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # グリッドを描画（オプション）
    # 100pxごとに薄い線
    for x in range(0, width, 100):
        cv2.line(img, (x, 0), (x, height), (100, 100, 100), 1)
        if x > 0:
            cv2.putText(img, str(x), (x-20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (150, 150, 150), 1)
    
    for y in range(0, height, 100):
        cv2.line(img, (0, y), (width, y), (100, 100, 100), 1)
        if y > 0:
            cv2.putText(img, str(y), (5, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (150, 150, 150), 1)
    
    # 結果を保存
    output_path = 'ocr_regions_overlay.png'
    cv2.imwrite(output_path, img)
    print(f"OCR領域をオーバーレイした画像を保存しました: {output_path}")
    
    # 領域の情報を出力
    print("\n=== OCR領域の座標 ===")
    for name, region in OCR_REGIONS_ABSOLUTE.items():
        print(f"{name:20} [{region['color']:5}]: x={region['x']:4}, y={region['y']:4}, w={region['w']:3}, h={region['h']:3}")
    
    return img

if __name__ == "__main__":
    # コマンドライン引数から画像パスを取得
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # デフォルトの画像パス
        image_path = "/Users/haruqun/Work/pachi777/temp_archive/スクリーンショット 2025-08-13 17.51.21.png"
    
    overlay_ocr_regions(image_path)