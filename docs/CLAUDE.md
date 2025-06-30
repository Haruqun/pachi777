# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

最終更新: 2025年6月30日

## Project Overview

This is a pachinko (Japanese pinball gambling) data analysis toolkit written in Python. The project extracts and analyzes data from pachinko machine screenshots, particularly focusing on:
- Graph data extraction from images (difference in ball count over spins)
- Statistical analysis of game performance
- OCR-based text extraction for game statistics
- Image cropping and preprocessing for accurate data extraction

## Development Environment Setup

```bash
# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install dependencies (if needed)
pip install -r requirements.txt  # Note: requirements.txt doesn't exist yet
# Current key dependencies: opencv-python, pillow, numpy, pandas, matplotlib, pytesseract
```

## Common Development Commands

```bash
# 本番用システム（production/ディレクトリ）

# 完全パイプライン実行（推奨）
python production/complete_pipeline.py

# クイック分析（切り抜き済み画像から）
python production/quick_analysis.py

# 個別実行
python production/manual_graph_cropper.py      # 画像切り抜き
python production/professional_graph_report.py # レポート生成
python production/web_package_creator.py       # ZIPパッケージ作成
```

## Architecture Overview

### Core Processing Pipeline
1. **Image Input**: Screenshots from pachinko machines (stored in `graphs/`)
2. **Graph Cropping**: 
   - 最適: `graphs/cropped/*_optimal.png` のような689×558px (98%以上の精度)
   - Legacy: `perfect_graph_cropper.py` - 911×797px
3. **Data Extraction**: `perfect_data_extractor.py` - Extracts numerical data from graphs
4. **Statistical Analysis**: Various analyzer scripts process the extracted data
5. **Output**: CSV files, visualization images, and JSON reports

### Key Components

- **Graph Processing**:
  - Optimal graph dimensions: 689×558 pixels (最高精度を実現)
  - Legacy dimensions: 911×797 pixels (perfect_graph_cropper.py)
  - Y-axis range: -30,000 to +30,000 (ball difference)
  - Zero-line detection for accurate calibration
  - Orange bar detection for graph area identification
  - Note: graphs/cropped/*_optimal.png が最適な切り抜きサンプル

- **OCR Integration**:
  - Uses Tesseract for Japanese text recognition
  - Extracts game statistics from UI elements

- **Font Handling**:
  - macOS-specific Japanese font configuration (Hiragino Sans GB)
  - Fallback font handling for cross-platform compatibility

### Data Workflow
1. Place screenshot images in `graphs/original/` directory
2. Run cropping tool to create standardized graph images in `graphs/manual_crop/cropped/`
3. Extract data and generate analysis images
4. All results saved in `reports/YYYYMMDDHHMMSS/` with timestamps:
   - `html/` - HTMLレポート
   - `images/` - 分析画像
   - `packages/` - ZIPパッケージ

### Image Processing Standards
- Input images: Various sizes from pachinko machine screenshots
- Standardized cropped graphs: 597×500 pixels (現在の標準)
- Color detection uses HSV color space for reliability
- Multiple detection algorithms for robustness (orange bars, grid lines, zero line)

## Key Technical Details

- **Python Version**: 3.13 (uses .venv virtual environment)
- **Image Processing**: OpenCV for detection, PIL/Pillow for manipulation
- **Data Analysis**: NumPy, Pandas, SciPy for numerical processing
- **Visualization**: Matplotlib with Japanese font support
- **OCR**: Tesseract via pytesseract wrapper

## File Naming Conventions
- Cropped images: `{original_name}_graph_only.png`
- Analysis images: `professional_analysis_{original_name}.png`
- HTML reports: `professional_graph_report_{timestamp}.html`
- ZIP packages: `pptown_graph_analysis_report_{timestamp}.zip`
- All outputs organized in: `reports/YYYYMMDDHHMMSS/`

## ディレクトリ構造（2025年6月30日更新）

```
pachi777/
├── production/          # 本番用システム
│   ├── complete_pipeline.py      # 完全パイプライン
│   ├── quick_analysis.py         # クイック分析
│   ├── manual_graph_cropper.py   # 画像切り抜き
│   ├── professional_graph_report.py  # レポート生成
│   └── web_package_creator.py    # パッケージ作成
├── graphs/              # 画像データ
│   ├── original/        # 元画像
│   └── manual_crop/     # 切り抜き済み画像
├── reports/             # 生成レポート（日時別）
│   └── YYYYMMDDHHMMSS/  # タイムスタンプディレクトリ
│       ├── html/        # HTMLレポート
│       ├── images/      # 分析画像
│       └── packages/    # ZIPパッケージ
├── dev/                 # 開発・テスト用
│   ├── test_scripts/    # テストスクリプト
│   └── analyzers/       # 分析ツール
├── legacy/              # 旧バージョン
├── docs/                # ドキュメント
└── output/              # その他の出力
```

## High-Precision Analysis System (2025年6月版)

### 現在の高精度システム仕様

#### 1. ゼロライン自動検出システム
- **精度**: ±1px以下の誤差
- **手法**: ガウシアンフィルタ + エッジ検出 + 統計分析
- **信頼性**: 100%検出成功率（27枚全てで検証済み）

```python
# 最適な設定値
self.zero_y = 250  # 自動検出ベース
self.target_30k_y = 4  # +30,000ライン位置（1px上調整済み）
self.scale = 30000 / (250 - 4)  # スケール計算: 121.95
```

#### 2. 10色マルチカラー検出システム
- **対応色**: pink, magenta, red, red_high, blue, green, cyan, yellow, orange, purple
- **成功率**: 100% (従来40.7%→改善後100%)
- **HSV色空間**: 各色に最適化された検出範囲

#### 3. グリッドライン位置精密調整
```python
# 最終調整値（2025年6月26日更新）
±30,000ライン: 1px上方向調整
+20,000ライン: 2px上方向調整
-20,000ライン: 2px下方向調整
±15,000以下: 調整なし
```

#### 4. プロフェッショナルレポート機能
- **HTML生成**: Font Awesome アイコン統合
- **レスポンシブデザイン**: モバイル・デスクトップ対応
- **画像拡大機能**: モーダル表示
- **Web配信**: ZIP パッケージ化対応
- **初当たり検出**: 100玉以上の増加を自動検出（2025年6月26日追加）
- **最高値補正**: グラフが常に負の場合は最高値を0と表示（2025年6月26日修正）

### 開発ノウハウ

#### A. 色検出の最適化
```python
# 成功の鍵：複数色範囲の並列処理
for color_name, color_range in self.color_ranges.items():
    mask = cv2.inRange(hsv, color_range['lower'], color_range['upper'])
    if cv2.countNonZero(mask) > min_pixels:  # 最小画素数しきい値
        return color_name, mask
```

#### B. 初当たり検出アルゴリズム（2025年6月26日追加）
```python
# 初当たり検出：100玉以上の連続増加を検出
min_payout = 100  # 最低払い出し玉数
for i in range(1, min(len(values)-2, 150)):  # 最大150点まで探索
    current_increase = values[i+1] - values[i]
    if current_increase > min_payout:
        # 次の点も上昇または維持していることを確認
        if values[i+2] >= values[i+1] - 50:
            # 現在値が2000以下（0付近）であること
            if values[i] < 2000:
                first_hit_idx = i
                break
```

#### C. ゼロライン検出の安定化
```python
# 重要：複数手法の組み合わせ
1. 水平線検出（Hough変換）
2. エッジ密度分析
3. グレースケール勾配解析
4. 統計的外れ値除去
```

#### D. グリッド位置の微調整手法
```python
# ユーザーフィードバックベースの段階的調整（2025年6月26日更新）
# 1px単位での位置調整が視覚的精度に大きく影響
if value == 20000:
    plus_adjustment = -1  # +20000ラインは2px上方向に調整
    minus_adjustment = 1  # -20000ラインは2px下方向に調整
else:
    plus_adjustment = 0
    minus_adjustment = 0
plus_y += plus_adjustment
minus_y += minus_adjustment
```

#### E. 最高値検出の特殊処理（2025年6月26日追加）
```python
# グラフが一度もプラスにならない場合の処理
if max_val < 0:
    # グラフが常に負の場合は最大値を0とする
    max_val = 0
    max_idx = 0  # インデックスも0に設定
```

### 今後の拡張可能性
1. **機械学習**: より高度な色検出モデル
2. **OCR精度向上**: 日本語特化モデル
3. **リアルタイム処理**: 動画解析対応
4. **クラウド展開**: Web API化

### 注意事項
- 架空の認証情報（ISO 27001等）は記載しない
- 実際の技術仕様のみ記載する
- システム宣伝ではなく純粋な技術レポートとして扱う