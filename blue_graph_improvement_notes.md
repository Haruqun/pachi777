# 青いグラフ抽出の改善案

## 問題の要約
- 青いグラフ（特にS__78209162）で1.6215倍の調整が必要
- 実際の値の61.5%しか検出できていない
- ピーク・ボトムの検出精度が低い

## 技術的な改善提案

### 1. 色検出の改善
```python
# 現在の青検出範囲
"blue": [(75, 20, 70), (125, 255, 255)]

# 提案：より広い範囲と低い彩度閾値
"blue": [(75, 10, 50), (125, 255, 255)]  # 彩度を10、明度を50に下げる
"light_blue": [(85, 5, 100), (115, 100, 255)]  # 超薄い青専用
```

### 2. 強度計算の色別最適化
```python
def calculate_intensity(self, pixel, color_type):
    r, g, b = pixel.astype(float)
    if color_type == "pink":
        return r - 0.5*g - 0.5*b
    elif color_type == "blue":
        return b - 0.5*r - 0.5*g  # 青成分を重視
    else:  # purple
        return (r + b) * 0.5 - g
```

### 3. 線の太さに応じた補正
```python
def adaptive_peak_correction(self, y, line_thickness, color_type):
    if color_type == "blue":
        # 青は細い線なので補正を小さく
        return 1.0 if line_thickness < 3 else 1.5
    else:
        # ピンクは標準の2ピクセル補正
        return 2.0
```

### 4. モルフォロジー処理の最適化
```python
if detected_color == "blue":
    # 細い線を保護するため、処理を最小限に
    kernel_tiny = np.ones((1, 1), np.uint8)
    # クロージングのみ（線の接続）
    mask_cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_tiny)
```

### 5. エッジ検出の感度調整
```python
# 色別のCanny閾値
if color_type == "blue":
    edges = cv2.Canny(gray, 10, 50)  # より低い閾値
else:
    edges = cv2.Canny(gray, 30, 100)  # 標準閾値
```

## 検証方法
1. S__78209162で調整係数が1.0に近づくか確認
2. 他の青いグラフ（S__78209160, S__78209164）でも精度向上を確認
3. ピンクグラフの精度が維持されることを確認

## 期待される改善
- 調整係数を1.6→1.1程度に削減
- 青いグラフの最終値精度を75.9%→95%以上に向上
- ピーク検出の精度向上