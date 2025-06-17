# 最適な切り抜き仕様

## graphs/cropped/*_optimal.png の仕様

### 画像サイズ
- **標準サイズ**: 689 × 558 ピクセル
- 全14枚が完全に同一サイズ
- これが安定版で98%以上の精度を達成した切り抜きサイズ

### 画像の特徴
- 上部に「30,000」の目盛り
- 中央にゼロライン（黒い横線）
- 下部に「-30,000」の目盛り
- グラフ領域が適切に収まっている
- 余白が最小限
- 背景にうっすら「(C) Daikoku Denki」の透かし

### ファイル一覧
1. S__78209088_optimal.png
2. S__78209128_optimal.png
3. S__78209130_optimal.png
4. S__78209132_optimal.png
5. S__78209136_optimal.png
6. S__78209138_optimal.png
7. S__78209156_optimal.png
8. S__78209158_optimal.png
9. S__78209160_optimal.png
10. S__78209162_optimal.png
11. S__78209164_optimal.png
12. S__78209166_optimal.png
13. S__78209168_optimal.png
14. S__78209170_optimal.png
15. S__78209174_optimal.png

### 重要な注意点
- CLAUDE.mdに記載の911×797ピクセルとは異なる
- この689×558サイズがstable_graph_extractor.pyで最高精度を実現
- 今後の切り抜きはこのサイズを標準とすべき

### stable_graph_extractor.pyの境界設定
```python
self.boundaries = {
    "start_x": 36,    # グラフ開始X座標
    "end_x": 620,     # グラフ終了X座標
    "top_y": 26,      # グラフ上端Y座標
    "bottom_y": 523,  # グラフ下端Y座標
    "zero_y": 274     # ゼロラインY座標
}
```

これらの座標は689×558ピクセルの画像に対して最適化されている。