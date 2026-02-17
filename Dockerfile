# Dockerfile for Cloud Run deployment
FROM python:3.11-slim

# Poppler（pdf2image用）とLibreOffice（.doc変換用）をインストール
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libreoffice-core \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピー（フル版を使用）
COPY requirements_full.txt .

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements_full.txt

# アプリケーションファイルをコピー
COPY . .

# uploadsディレクトリを作成
RUN mkdir -p /app/uploads

# Pythonの.pycファイル生成を無効化（キャッシュ問題を防ぐ）
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ポート設定（Cloud Runは環境変数PORTを使用）
ENV PORT=8080

# Gunicornでアプリケーションを起動（app_fullを使用）
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app_full:app
