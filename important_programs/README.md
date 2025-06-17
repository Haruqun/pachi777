# 重要プログラム一覧

## stable_graph_extractor.py
- **目的**: 安定版コミット(7d59150)の高精度抽出手法を再現
- **特徴**: 
  - 2ピクセル補正（線の太さ考慮）
  - サブピクセル精度（パラボラフィッティング）
  - 適応的スムージング（ピーク保護）
- **精度**: 最大値98.1%、最終値98.9%

## accuracy_checker.py
- **目的**: 抽出データと実際の値を比較して精度を検証
- **機能**:
  - results.txtとの比較
  - 異常値検出（MAX_DIFF = 20000）
  - ピーク・バレー検出
  - 詳細なレポート生成

## advanced_graph_extractor.py
- **目的**: 高度な画像処理技術によるグラフデータ抽出
- **特徴**:
  - 複数色空間での色検出（HSV、LAB）
  - エッジ強調アルゴリズム
  - 多段階スムージング
  - graph_boundaries_final_config.json使用

## perfect_crop_pipeline.py
- **目的**: 100%の切り抜き精度を目指す統合パイプライン
- **特徴**:
  - オレンジバー検出
  - 84ピクセルオフセット適用
  - ゼロライン自動検出
  - 標準サイズ: 911×797ピクセル

## compare_stable_vs_reported.py
- **目的**: 安定版抽出結果とresults.txtの比較
- **機能**:
  - 詳細な精度統計
  - 機種別分析
  - CSVレポート生成

## 使用順序
1. perfect_crop_pipeline.py → 元画像から切り抜き
2. stable_graph_extractor.py → データ抽出（最高精度）
3. accuracy_checker.py → 精度検証
4. compare_stable_vs_reported.py → 詳細分析