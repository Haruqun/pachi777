import cv2
import numpy as np
import sys

def overlay_mask_on_image(image_path, mask_path):
    """マスク画像を元画像にオーバーレイして表示"""
    
    # 画像を読み込み
    img = cv2.imread(image_path)
    mask = cv2.imread(mask_path)
    
    if img is None or mask is None:
        print("画像の読み込みに失敗しました")
        return
    
    # 画像サイズを確認
    img_h, img_w = img.shape[:2]
    mask_h, mask_w = mask.shape[:2]
    
    print(f"元画像サイズ: {img_w} x {img_h}")
    print(f"マスクサイズ: {mask_w} x {mask_h}")
    
    # リサイズが必要な場合
    if img_w != 1179:
        scale = 1179 / img_w
        new_width = 1179
        new_height = int(img_h * scale)
        img = cv2.resize(img, (new_width, new_height))
        print(f"画像をリサイズ: {new_width} x {new_height}")
        img_h, img_w = new_height, new_width
    
    # マスクもリサイズ（必要に応じて）
    if mask_w != img_w or mask_h != img_h:
        mask = cv2.resize(mask, (img_w, img_h))
        print(f"マスクをリサイズ: {img_w} x {img_h}")
    
    # マスクから赤い領域を抽出
    # mask.pngの赤色はRGB(#FF5555) = RGB(255, 85, 85) = BGR(85, 85, 255)
    # サンプル色は[0, 0, 255]なので、純粋な赤
    lower_red = np.array([0, 0, 254])  # BGR形式 - ほぼ純粋な赤のみ
    upper_red = np.array([1, 1, 255])
    red_mask = cv2.inRange(mask, lower_red, upper_red)
    
    # デバッグ: マスクの色を確認
    sample_color = mask[30, 500]  # 上部の赤いバーあたり
    print(f"マスクのサンプル色(BGR): {sample_color}")
    
    detected_pixels = np.sum(red_mask > 0)
    print(f"検出された赤いピクセル数: {detected_pixels}")
    
    # 赤い領域の輪郭を検出
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # オーバーレイ画像を作成（半透明の赤い矩形を描画）
    overlay = img.copy()
    
    # 各輪郭に対して矩形を描画
    regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # 小さすぎる領域は無視
        if w > 10 and h > 10:
            # 半透明の赤い矩形を描画
            cv2.rectangle(overlay, (x, y), (x+w, y+h), (0, 0, 255), 2)  # 赤い枠線
            # 薄い赤で塗りつぶし
            roi = overlay[y:y+h, x:x+w]
            red_overlay = np.ones_like(roi, dtype=np.uint8) * np.array([0, 0, 255], dtype=np.uint8)  # 赤色
            result = cv2.addWeighted(roi, 0.7, red_overlay, 0.3, 0)
            overlay[y:y+h, x:x+w] = result
            
            regions.append({'x': x, 'y': y, 'w': w, 'h': h})
    
    print(f"\n検出された領域数: {len(regions)}")
    
    # 黒背景領域を検出して表示
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, black_mask = cv2.threshold(gray, 40, 255, cv2.THRESH_BINARY_INV)
    
    # 黒背景の輪郭を検出
    black_contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if black_contours:
        # 最大の輪郭（黒背景）
        largest_contour = max(black_contours, key=cv2.contourArea)
        black_x, black_y, black_w, black_h = cv2.boundingRect(largest_contour)
        
        # 黒背景の枠を緑色で描画
        cv2.rectangle(overlay, (black_x, black_y), (black_x + black_w, black_y + black_h), (0, 255, 0), 3)
        
        print(f"\n黒背景領域: 左上({black_x}, {black_y}), サイズ({black_w} x {black_h})")
        
        # 黒背景の左上隅にマーカーを表示
        cv2.circle(overlay, (black_x, black_y), 10, (0, 255, 0), -1)
        cv2.putText(overlay, f"Black BG: ({black_x}, {black_y})", 
                   (black_x + 15, black_y + 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 各マスク領域と黒背景からの相対位置を表示
        print("\n=== マスク領域の座標（黒背景からの相対位置）===")
        for i, region in enumerate(regions):
            rel_x = region['x'] - black_x
            rel_y = region['y'] - black_y
            print(f"領域{i:2d}: 絶対({region['x']:4}, {region['y']:4}) -> 相対({rel_x:4}, {rel_y:4}) サイズ({region['w']:3} x {region['h']:3})")
    
    # グリッドを描画（100pxごと）
    for x in range(0, img_w, 100):
        cv2.line(overlay, (x, 0), (x, img_h), (200, 200, 200), 1)
        if x > 0:
            cv2.putText(overlay, str(x), (x-20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
    
    for y in range(0, img_h, 100):
        cv2.line(overlay, (0, y), (img_w, y), (200, 200, 200), 1) 
        if y > 0:
            cv2.putText(overlay, str(y), (5, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
    
    # 結果を保存
    output_path = 'mask_overlay_result.png'
    cv2.imwrite(output_path, overlay)
    print(f"\nオーバーレイ画像を保存: {output_path}")
    
    return overlay

if __name__ == "__main__":
    # 画像パス
    image_path = "/Users/haruqun/Work/pachi777/temp_archive/スクリーンショット 2025-08-13 17.51.21.png"
    mask_path = "/Users/haruqun/Work/pachi777/web_app/mask/mask.png"
    
    overlay_mask_on_image(image_path, mask_path)