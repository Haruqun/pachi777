# Webアプリ版デプロイガイド

## 🚀 Streamlit Cloudへのデプロイ手順

### 1. GitHubリポジトリの準備
```bash
# リポジトリを作成してプッシュ
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/pachi777.git
git push -u origin main
```

### 2. Streamlit Cloudの設定
1. https://streamlit.io/cloud にアクセス
2. GitHubアカウントでログイン
3. "New app"をクリック
4. リポジトリを選択
5. メインファイル: `web_app/streamlit_app.py`
6. "Deploy"をクリック

### 3. 環境変数の設定（必要な場合）
Streamlit Cloudの設定画面で:
- `TESSDATA_PREFIX`: Tesseract OCRのデータパス
- その他の必要な設定

## 🐳 Dockerを使ったローカル実行

```dockerfile
# Dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-jpn \
    libgl1-mesa-glx \
    libglib2.0-0

WORKDIR /app

COPY web_app/requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "web_app/streamlit_app.py"]
```

実行:
```bash
docker build -t pachi777-web .
docker run -p 8501:8501 pachi777-web
```

## 🌐 その他の無料デプロイオプション

### 1. **Render.com**
```yaml
# render.yaml
services:
  - type: web
    name: pachi777
    env: python
    buildCommand: pip install -r web_app/requirements.txt
    startCommand: streamlit run web_app/streamlit_app.py
```

### 2. **Railway.app**
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "streamlit run web_app/streamlit_app.py"
  }
}
```

### 3. **Google Colab + ngrok（開発用）**
```python
# Colabセル
!pip install streamlit pyngrok
!ngrok authtoken YOUR_TOKEN

from pyngrok import ngrok
!streamlit run web_app/streamlit_app.py &
public_url = ngrok.connect(8501)
print(public_url)
```

## 📱 軽量版Flask API

よりシンプルなAPI版も用意：

```python
# flask_app.py
from flask import Flask, request, jsonify, send_file
import tempfile
import os

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze():
    files = request.files.getlist('images')
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 処理実行
        results = process_images(files, temp_dir)
        
        return jsonify({
            'status': 'success',
            'results': results
        })

@app.route('/download/<report_id>')
def download(report_id):
    # レポートファイルを返す
    return send_file(f'reports/{report_id}.zip')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## 🔒 セキュリティ考慮事項

1. **アップロードサイズ制限**
   ```python
   st.set_option('server.maxUploadSize', 200)  # 200MB
   ```

2. **認証機能**（必要な場合）
   ```python
   import streamlit_authenticator as stauth
   ```

3. **レート制限**
   - Cloudflareなどを使用

## 📊 パフォーマンス最適化

1. **画像の事前リサイズ**
2. **キャッシュの活用**
   ```python
   @st.cache_data
   def process_image(image):
       # 処理
   ```

3. **非同期処理**（重い処理の場合）

## 🚦 ステータス

- ✅ Streamlit版: 基本実装完了
- 🔄 本番環境との統合: 要調整
- 📝 ドキュメント: 作成中

---

最終更新: 2025年6月30日