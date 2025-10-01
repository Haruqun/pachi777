# Web App Claude版

このフォルダは、Claude API統合版のWebアプリケーションです。
リファクタリング作業用に`web_app`から分離されています。

## 構成

- `streamlit_app_full_claude.py` - メインアプリケーション
- `web_analyzer.py` - 画像解析エンジン  
- `modules/` - リファクタリングで分離されたモジュール
  - `image_processor.py` - 画像処理共通関数
  - （今後追加予定）

## 注意事項

- このフォルダは開発・テスト用です
- 本番環境は`web_app/`フォルダを使用しています
- 変更を本番に反映する際は十分なテストを行ってください