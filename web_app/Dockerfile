# マルチステージビルドで軽量化
FROM python:3.11-slim as builder

# 必要なシステムパッケージをインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    cmake \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Tesseractをインストール
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-jpn \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ設定
WORKDIR /app

# 依存関係をコピーしてインストール
COPY web_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 本番ステージ
FROM python:3.11-slim

# 必要なランタイムライブラリのみインストール
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    tesseract-ocr \
    tesseract-ocr-jpn \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ビルダーステージから必要なファイルをコピー
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# アプリケーションコードをコピー
COPY production/ ./production/
COPY web_app/ ./web_app/

# ポート設定
EXPOSE 8501

# Streamlitの設定
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# 実行コマンド
CMD ["streamlit", "run", "web_app/app_complete.py", "--server.maxUploadSize=200"]