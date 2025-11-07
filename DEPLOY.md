# Cloud Runへのデプロイ手順

## 前提条件

- Google Cloud プロジェクト: `ocr2-435601`
- Google Cloud SDKがインストール済み
- GitHubリポジトリにコードがpush済み

## 1. 初回セットアップ

### Firestoreを有効化

```bash
gcloud config set project ocr2-435601
gcloud firestore databases create --region=asia-northeast1
```

### 必要なAPIを有効化

```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable vision.googleapis.com
gcloud services enable firestore.googleapis.com
```

## 2. Cloud Runにデプロイ

### 方法1: gcloudコマンドで直接デプロイ

```bash
gcloud run deploy syuugyoukisoku \
  --source . \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars USE_FIRESTORE=true,GOOGLE_CLOUD_PROJECT=ocr2-435601 \
  --memory 2Gi \
  --timeout 600 \
  --max-instances 10
```

### 方法2: Dockerイメージをビルドしてデプロイ

```bash
# イメージをビルド
gcloud builds submit --tag gcr.io/ocr2-435601/syuugyoukisoku

# Cloud Runにデプロイ
gcloud run deploy syuugyoukisoku \
  --image gcr.io/ocr2-435601/syuugyoukisoku \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars USE_FIRESTORE=true,GOOGLE_CLOUD_PROJECT=ocr2-435601 \
  --memory 2Gi \
  --timeout 600 \
  --max-instances 10
```

## 3. 環境変数の設定

デプロイ後、以下の環境変数が必要です：

- `USE_FIRESTORE=true` - Firestoreを使用
- `GOOGLE_CLOUD_PROJECT=ocr2-435601` - プロジェクトID
- `ANTHROPIC_API_KEY=<your-api-key>` - Claude APIキー（オプション）

環境変数を後から更新する場合：

```bash
gcloud run services update syuugyoukisoku \
  --region asia-northeast1 \
  --update-env-vars ANTHROPIC_API_KEY=<your-api-key>
```

## 4. デプロイ後の確認

デプロイが完了すると、URLが表示されます：

```
Service URL: https://syuugyoukisoku-xxxxx-an.a.run.app
```

ブラウザでアクセスして動作確認してください。

## 5. ログの確認

```bash
gcloud run services logs read syuugyoukisoku --region asia-northeast1
```

## 6. 更新デプロイ

コードを更新したら、再度デプロイコマンドを実行：

```bash
gcloud run deploy syuugyoukisoku \
  --source . \
  --platform managed \
  --region asia-northeast1
```

## トラブルシューティング

### メモリ不足エラー

```bash
gcloud run services update syuugyoukisoku \
  --region asia-northeast1 \
  --memory 4Gi
```

### タイムアウトエラー

```bash
gcloud run services update syuugyoukisoku \
  --region asia-northeast1 \
  --timeout 900
```

### Cloud Storageへのファイル保存

大きなファイルはCloud Storageに保存することを推奨：

```bash
gsutil mb -p ocr2-435601 -l asia-northeast1 gs://syuugyoukisoku-uploads
```

## コスト管理

- Cloud Run: 使用した分だけ課金
- Firestore: 読み取り/書き込み操作に対して課金
- Vision API: OCR処理に対して課金

無料枠を超える場合は、予算アラートを設定することを推奨します。
