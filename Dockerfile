# Dockerfile for Cloud Run deployment
FROM python:3.11-slim

# Poppler（pdf2imageが必要とする）をインストール
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements.txt .

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY . .

# Pythonの.pycファイル生成を無効化（キャッシュ問題を防ぐ）
ENV PYTHONDONTWRITEBYTECODE=1

# ポート設定（Cloud Runは環境変数PORTを使用）
ENV PORT=8080

# Gunicornでアプリケーションを起動
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
