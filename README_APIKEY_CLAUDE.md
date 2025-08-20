# Claude API キー設定ガイド

## 🔐 セキュリティ最重要事項

**⚠️ 絶対にAPIキーをGitHubにコミットしないでください！**

このプロジェクトはPublicリポジトリです。APIキーが公開されると、不正利用により高額な請求が発生する可能性があります。

## 📋 APIキー設定方法

### 方法1: Streamlit Cloud Secrets（本番環境・推奨）

Streamlit Cloudでデプロイする場合の最も安全な方法です。

1. **Streamlit Cloud管理画面にアクセス**
   - https://share.streamlit.io/ にログイン
   - 対象アプリケーションを選択

2. **Settings → Secretsを開く**

3. **以下の内容を追加**
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-api03-..."
   ```

4. **保存してアプリを再起動**

✅ **メリット**: 
- GitHubに一切APIキーが保存されない
- Streamlit Cloud上で安全に管理される
- チームメンバーと共有しても安全

### 方法2: 環境変数（ローカル開発）

#### macOS/Linux
```bash
# 一時的に設定（ターミナルセッション内のみ有効）
export ANTHROPIC_API_KEY="sk-ant-api03-..."
streamlit run web_app/test_detail_ocr_app.py

# または永続的に設定（.bashrc or .zshrcに追加）
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-..."' >> ~/.zshrc
source ~/.zshrc
```

#### Windows（コマンドプロンプト）
```cmd
set ANTHROPIC_API_KEY=sk-ant-api03-...
streamlit run web_app/test_detail_ocr_app.py
```

#### Windows（PowerShell）
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-api03-..."
streamlit run web_app/test_detail_ocr_app.py
```

### 方法3: .streamlit/secrets.toml（ローカル開発）

1. **フォルダとファイルを作成**
   ```bash
   mkdir -p .streamlit
   touch .streamlit/secrets.toml
   ```

2. **.streamlit/secrets.tomlに以下を記述**
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-api03-..."
   ```

3. **確認: .gitignoreに含まれているか**
   ```bash
   grep "secrets.toml" .gitignore
   # 出力: .streamlit/secrets.toml
   ```

### 方法4: .envファイル（ローカル開発）

1. **プロジェクトルートに.envファイルを作成**
   ```bash
   touch .env
   ```

2. **.envファイルに以下を記述**
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ```

3. **確認: .gitignoreに含まれているか**
   ```bash
   grep "^.env" .gitignore
   # 出力: .env
   ```

## 🔑 APIキーの取得方法

1. **Anthropic Consoleにアクセス**
   - https://console.anthropic.com/

2. **アカウント作成またはログイン**

3. **API Keys セクションに移動**

4. **「Create Key」をクリック**

5. **キーをコピー（sk-ant-api03-で始まる文字列）**

⚠️ **注意**: APIキーは作成時にのみ表示されます。必ず安全な場所に保管してください。

## 🛡️ セキュリティチェックリスト

### ✅ 必須確認事項

- [ ] `.gitignore`に以下が含まれているか確認
  ```
  .env
  .env.local
  .streamlit/secrets.toml
  api_keys.json
  secrets.json
  ```

- [ ] APIキーがコード内にハードコードされていないか確認
  ```bash
  # 危険なパターンを検索
  grep -r "sk-ant-api" --include="*.py" .
  # 何も出力されないことを確認
  ```

- [ ] コミット前に確認
  ```bash
  # ステージングエリアを確認
  git status
  # APIキー関連ファイルが含まれていないことを確認
  ```

### 🚫 絶対にやってはいけないこと

```python
# ❌ 悪い例：直接コードに記述
api_key = "sk-ant-api03-xxxxx"  # 絶対ダメ！

# ✅ 良い例：環境変数から取得
import os
api_key = os.getenv("ANTHROPIC_API_KEY")
```

## 🔧 トラブルシューティング

### APIキーが認識されない

1. **環境変数を確認**
   ```bash
   # macOS/Linux
   echo $ANTHROPIC_API_KEY
   
   # Windows (cmd)
   echo %ANTHROPIC_API_KEY%
   
   # Windows (PowerShell)
   echo $env:ANTHROPIC_API_KEY
   ```

2. **Streamlitを再起動**
   ```bash
   # Ctrl+C で停止してから再起動
   streamlit run web_app/test_detail_ocr_app.py
   ```

3. **Pythonから確認**
   ```python
   import os
   print(os.getenv("ANTHROPIC_API_KEY"))
   ```

### Streamlit Cloudで動作しない

1. **Secrets設定を確認**
   - Streamlit Cloud管理画面 → Settings → Secrets

2. **アプリを再デプロイ**
   - 「Reboot app」ボタンをクリック

3. **ログを確認**
   - 「View logs」でエラーメッセージを確認

## 📊 コスト管理

### 料金体系（2024年12月時点）

| モデル | 入力料金 | 出力料金 |
|--------|----------|----------|
| Claude 3 Haiku | $0.25/1M tokens | $1.25/1M tokens |
| Claude 3.5 Sonnet | $3.00/1M tokens | $15.00/1M tokens |

### 使用量の目安

- パチンコ画像1枚: 約1,000-2,000 tokens
- 1,000枚処理: 約$0.30-$0.60（Haiku使用時）

### 使用量制限の設定

Anthropic Consoleで月額上限を設定できます：
1. Console → Billing → Usage Limits
2. Monthly limitを設定（例：$10）

## 🆘 サポート

### よくある質問

**Q: APIキーはどこで確認できますか？**
A: https://console.anthropic.com/ のAPI Keysセクション

**Q: 無料枠はありますか？**
A: 新規アカウントには$5のクレジットが付与されます

**Q: APIキーを漏洩してしまった場合は？**
A: 即座にConsoleから該当キーを無効化し、新しいキーを発行してください

## 📝 開発メモ

### アプリケーションでの実装

```python
# web_app/test_detail_ocr_app.py での実装例

# 1. Streamlit Secretsから取得を試みる
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
except:
    pass

# 2. 環境変数から取得を試みる
if not api_key:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

# 3. UIで入力を求める（最終手段）
api_key = st.text_input(
    "Anthropic API Key",
    type="password",
    value=api_key,
    help="APIキーを入力してください"
)
```

### GitHubでの安全な管理

1. **Protected branchesを設定**
   - Settings → Branches → Add rule
   - Require pull request reviews before merging

2. **Secret scanningを有効化**
   - Settings → Security → Secret scanning

3. **定期的な監査**
   ```bash
   # APIキーのパターンを検索
   git log -p | grep -E "sk-ant-api[0-9]{2}-"
   ```

---

最終更新: 2024年12月
開発: ファイブナインデザイン