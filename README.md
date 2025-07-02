# パチンコグラフ解析システム v2.0

site7のグラフデータを高精度で解析するWebアプリケーション

## 🚀 概要

このシステムは、[site7](https://m.site777.jp/)のパチンコ台グラフ画像から自動的にデータを抽出し、詳細な統計分析を提供するStreamlitベースのWebアプリケーションです。

### 主な機能
- 📸 **自動画像切り抜き**: ゼロラインを基準に±30,000玉の範囲を精密に切り抜き
- 📊 **高精度グラフ解析**: AIによるグラフライン自動検出
- 📈 **統計分析**: 最高値・最低値・現在値・初当たり値を自動計算
- 🔍 **OCRデータ抽出**: site7の画像から台番号、累計スタート、大当り回数などを自動抽出
- ⚙️ **端末別調整設定**: 撮影デバイスに応じた詳細な調整が可能
- 📏 **非線形スケール対応**: グラフの非線形性を考慮した高精度解析
- 🔐 **パスワード認証**: セキュアなアクセス管理（パスワード: 059）
- 💾 **プリセット機能**: 設定をサーバー側に保存し、複数端末で共有可能
- 🌐 **Web対応**: ブラウザから簡単にアクセス・利用可能

## 🛠️ インストール

### 必要な環境
- Python 3.8以上
- Tesseract OCR（日本語対応）

### セットアップ

```bash
# リポジトリのクローン
git clone https://github.com/Haruqun/pachi777.git
cd pachi777

# 仮想環境の作成と有効化
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# または
.venv\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt

# Tesseract OCRのインストール
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-jpn

# Windows
# https://github.com/UB-Mannheim/tesseract/wiki からインストーラーをダウンロード
```

## 📁 ディレクトリ構造

```
pachi777/
├── web_app/                      # Webアプリケーション
│   ├── streamlit_app_full.py     # メインアプリケーション
│   └── web_analyzer.py           # グラフ解析エンジン
├── production/                   # スタンドアロン版（レガシー）
├── graphs/                       # テスト用画像データ
├── reports/                      # 生成レポート
├── requirements.txt              # Python依存関係
├── README.md                     # このファイル
└── CLAUDE.md                     # AI開発ガイド
```

## 🎯 使い方

### Webアプリケーションの起動

```bash
# ローカル環境で起動
streamlit run web_app/streamlit_app_full.py

# ポート指定して起動
streamlit run web_app/streamlit_app_full.py --server.port 8080
```

### 使用手順

1. **画像のアップロード**
   - 「Browse files」ボタンをクリック
   - site7のグラフ画像を選択（複数選択可）
   - 対応形式：JPG/JPEG、PNG

2. **自動解析**
   - アップロード後、自動的に以下の処理が実行されます：
     - グラフ領域の検出と切り抜き
     - ゼロラインの自動検出
     - グラフデータの抽出
     - 統計情報の計算
     - OCRによるテキストデータ抽出

3. **結果の確認**
   - 解析結果は2列で表示（モバイルでは1列）
   - 各結果には以下が含まれます：
     - 解析済みグラフ画像（緑色のライン）
     - 統計情報（最高値、最低値、現在値、初当たり）
     - OCRで抽出したsite7データ
     - 元画像（折りたたみ可能）

## 📊 技術仕様

### グラフ解析
- **ゼロライン検出**: オレンジバーの下部を基準に自動検出
- **切り抜き範囲**: ゼロラインから上246px、下247px（±30,000玉相当）
- **スケール**: 約122玉/ピクセル
- **左右余白**: 125px除外

### 統計計算
- **最高値（MAX）**: グラフ全体の最大値（マイナスの場合は0）
- **最低値（MIN）**: グラフ全体の最小値
- **現在値（CURRENT）**: グラフの最終値
- **初当たり値（FIRST HIT）**: 100玉以上の急激な増加を検出

### OCR機能
- **抽出可能データ**:
  - 台番号
  - 累計スタート
  - 大当り回数
  - 初当り回数
  - 現在のスタート
  - 大当り確率
  - 最高出玉

### 処理性能
- **画像あたりの処理時間**: 約2-5秒
- **複数画像の並列処理**: 対応
- **メモリ効率**: 大量画像の処理に最適化

## 🌐 デプロイ

### Streamlit Community Cloud
1. GitHubリポジトリをStreamlit Cloudに接続
2. アプリファイルパス: `web_app/streamlit_app_full.py`
3. Python 3.8以上を指定

### その他のデプロイオプション
- Heroku
- AWS EC2
- Google Cloud Platform
- Azure App Service

## ⚙️ 設定とカスタマイズ

### 画像処理パラメータ
```python
# web_analyzer.py内で調整可能
ZERO_LINE_OFFSET_TOP = 246    # ゼロラインから上のピクセル数
ZERO_LINE_OFFSET_BOTTOM = 247 # ゼロラインから下のピクセル数
CROP_MARGIN_LEFT = 125        # 左右の余白
SCALE = 30000 / 246           # 玉数/ピクセルのスケール
```

## 🔧 トラブルシューティング

### OCRが動作しない
- Tesseract OCRが正しくインストールされているか確認
- 日本語言語パックがインストールされているか確認
- `pytesseract.pytesseract.tesseract_cmd`のパスを確認

### メモリエラー
- 画像サイズを確認（推奨: 2MB以下）
- 一度に処理する画像数を減らす

### グラフ検出エラー
- site7の画像形式であることを確認
- 画像が切れていないか確認
- グラフ全体が含まれているか確認

## 📝 更新履歴

### v2.0 (2025-01-01)
- Streamlit Webアプリケーション版リリース
- 複数画像の一括処理機能追加
- OCRによるデータ抽出機能追加
- モバイル対応レスポンシブデザイン
- 処理速度の大幅改善

### v1.0 (2024-12-15)
- 初回リリース（スタンドアロン版）

## 📄 ライセンス

Proprietary - PPタウン様専用システム

## 👥 開発者

- 開発: [ファイブナインデザイン](https://fivenine-design.com)
- 制作協力: [PPタウン](https://pp-town.com/)

---

最終更新: 2025年1月1日