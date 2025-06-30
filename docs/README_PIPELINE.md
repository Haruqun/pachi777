# パチンコグラフ解析パイプライン

## 概要
画像の切り抜きからデータ抽出、レポート生成、Web配信パッケージ作成までを一括で実行するパイプラインシステムです。

## 使用方法

### 1. 完全パイプライン実行（切り抜きから開始）
```bash
python complete_pipeline.py
```

オプション:
- `--no-backup`: 既存ファイルのバックアップをスキップ
- `--original-dir <path>`: 元画像ディレクトリを指定（デフォルト: graphs/original）

例:
```bash
# バックアップなしで実行
python complete_pipeline.py --no-backup

# 別のディレクトリの画像を処理
python complete_pipeline.py --original-dir /path/to/images
```

### 2. クイック分析（切り抜き済み画像から）
既に切り抜き済みの画像がある場合:
```bash
python quick_analysis.py
```

## 処理フロー

### complete_pipeline.py
1. **画像切り抜き** (manual_graph_cropper.py)
   - graphs/original/*.jpg → graphs/manual_crop/cropped/*_graph_only.png
   - サイズ: 597×500px

2. **データ分析・レポート生成** (professional_graph_report.py)
   - グラフデータ抽出
   - 統計分析（最高値、最低値、初当たり検出）
   - HTMLレポート生成

3. **Webパッケージ作成** (web_package_creator.py)
   - ZIPファイル生成
   - 画像、HTML、設定ファイルを含む

### quick_analysis.py
- ステップ2と3のみを実行（切り抜き済み画像が必要）

## ディレクトリ構成
```
graphs/
├── original/           # 元画像（*.jpg）
├── manual_crop/
│   ├── cropped/       # 切り抜き済み画像（*_graph_only.png）
│   └── overlays/      # 解析オーバーレイ画像
└── extracted_data/    # 抽出データ（CSV等）

professional_analysis_*.png  # 分析結果画像
professional_graph_report_*.html  # HTMLレポート
pptown_graph_analysis_report_*.zip  # 配信用パッケージ
```

## 主要機能

### 画像切り抜き
- オレンジバー検出による自動位置調整
- ゼロライン検出
- 597×500pxの統一サイズ

### データ分析
- 10色対応マルチカラー検出
- ゼロライン自動検出（±1px精度）
- 初当たり検出（マイナス値のみ）
- 最高値補正（常に負の場合は0表示）

### レポート機能
- インタラクティブHTML
- 画像クリックで拡大表示
- レスポンシブデザイン
- Font Awesomeアイコン統合

## エラー対処

### 画像が見つからない場合
```
エラー: 元画像が見つかりません
```
→ graphs/original/ に JPG画像を配置してください

### 切り抜きエラー
```
エラー: オレンジバーが検出できません
```
→ 画像フォーマットが異なる可能性があります

### 分析エラー
```
エラー: グラフデータを抽出できません
```
→ 切り抜き範囲が正しくない可能性があります

## 出力ファイル

### 成功時
- `pipeline_summary_YYYYMMDD_HHMMSS.txt`: 処理サマリー
- `professional_graph_report_YYYYMMDD_HHMMSS.html`: 分析レポート
- `pptown_graph_analysis_report_YYYYMMDD_HHMMSS.zip`: 配信用パッケージ

### ログ
コンソールに詳細なログが出力されます。エラー時は[ERROR]タグで表示。

## 注意事項
- 元画像は上書きされません
- 既存の切り抜き画像はバックアップされます（--no-backupで無効化可能）
- 処理には画像枚数により数分かかる場合があります