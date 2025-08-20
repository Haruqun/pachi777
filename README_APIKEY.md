# APIキーの設定方法

このアプリケーションでClaude APIを使用するには、APIキーを設定する必要があります。
セキュリティのため、APIキーは絶対にGitHubにコミットしないでください。

## 設定方法

### 方法1: Streamlit Cloud（推奨 - デプロイ環境）

1. Streamlit Cloudの管理画面にアクセス
2. アプリの設定（Settings）を開く
3. 「Secrets」セクションに以下を追加：

```toml
ANTHROPIC_API_KEY = "your-api-key-here"
```

### 方法2: ローカル環境変数（ローカル開発）

#### macOS/Linux:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
streamlit run web_app/test_detail_ocr_app.py
```

#### Windows:
```cmd
set ANTHROPIC_API_KEY=your-api-key-here
streamlit run web_app/test_detail_ocr_app.py
```

### 方法3: .streamlit/secrets.toml（ローカル開発）

1. プロジェクトルートに`.streamlit`フォルダを作成
2. `.streamlit/secrets.toml`ファイルを作成
3. 以下の内容を追加：

```toml
ANTHROPIC_API_KEY = "your-api-key-here"
```

**注意**: このファイルは`.gitignore`に含まれているため、GitHubにはアップロードされません。

### 方法4: .env ファイル（ローカル開発）

1. プロジェクトルートに`.env`ファイルを作成
2. 以下の内容を追加：

```
ANTHROPIC_API_KEY=your-api-key-here
```

3. python-dotenvを使用する場合は、コードに以下を追加：

```python
from dotenv import load_dotenv
load_dotenv()
```

## セキュリティ注意事項

- **絶対にAPIキーをコードに直接書かないでください**
- **絶対にAPIキーをGitHubにコミットしないでください**
- `.gitignore`ファイルに以下が含まれていることを確認：
  - `.env`
  - `.streamlit/secrets.toml`
  - `api_keys.json`
  - `secrets.json`

## APIキーの取得

Anthropic APIキーは以下から取得できます：
https://console.anthropic.com/

## トラブルシューティング

- APIキーが認識されない場合は、アプリを再起動してください
- Streamlit Cloudの場合、Secretsを設定後にアプリの再デプロイが必要な場合があります
- 環境変数が正しく設定されているか確認：`echo $ANTHROPIC_API_KEY`（macOS/Linux）