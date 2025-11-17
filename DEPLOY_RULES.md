# 🚨 Cloud Run デプロイルール（絶対遵守）🚨

## ⚠️ 重要：いついかなる時も必ず守ること

**あらゆる変更（コード、環境変数、設定など）の後は、必ず最新リビジョンにトラフィックを切り替える**

## 問題の本質
- **新しいコードはデプロイされるが、トラフィックが古いリビジョンに向いたまま**
- **環境変数を変更しても、新しいリビジョンが作成されるがトラフィックは自動で切り替わらない**
- 結果：ユーザーは古いコードを見続ける

## ✅ 正しいデプロイ手順（必須）

### 【パターンA】コード変更時

#### STEP 1: コードをコミット・プッシュ
```bash
git add <変更ファイル>
git commit -m "変更内容"
git push origin main
```

#### STEP 2: ビルドがSUCCESSになるまで待つ（最重要）
```bash
# ビルドの開始を確認
sleep 15 && gcloud builds list --limit=1

# ビルドが完了するまで待つ（STATUS=SUCCESSを確認）
gcloud builds list --limit=1
```

**⚠️ 重要**: ビルドのSTATUSが`SUCCESS`になるまで、次のステップに進んではいけない！

#### STEP 3: 最新リビジョンにトラフィックを切り替え
```bash
# 最新リビジョンを取得
LATEST_REV=$(gcloud run revisions list --service=syuugyoukisoku --region=asia-northeast1 --limit=1 --format="value(metadata.name)")

# リビジョン名を確認
echo "最新リビジョン: $LATEST_REV"

# トラフィックを100%最新リビジョンに向ける
gcloud run services update-traffic syuugyoukisoku --region=asia-northeast1 --to-revisions=$LATEST_REV=100
```

#### STEP 4: 動作確認
```bash
# 現在のトラフィック設定を確認
gcloud run services describe syuugyoukisoku --region=asia-northeast1 --format="table(status.traffic)"
```

ブラウザで動作確認：
https://syuugyoukisoku-bsdy2np4aa-an.a.run.app

---

### 【パターンB】環境変数変更時（コード変更なし）

環境変数を変更した場合も新しいリビジョンが作成されますが、トラフィックは自動で切り替わりません。

#### STEP 1: 環境変数を変更
```bash
# 例：デバッグモードを有効化
gcloud run services update syuugyoukisoku --region=asia-northeast1 --set-env-vars PDF_PARSER_DEBUG=1
```

#### STEP 2: すぐにトラフィックを最新リビジョンに切り替え
```bash
# 最新リビジョンを取得
LATEST_REV=$(gcloud run revisions list --service=syuugyoukisoku --region=asia-northeast1 --limit=1 --format="value(metadata.name)")

# リビジョン名を確認
echo "最新リビジョン: $LATEST_REV"

# トラフィックを100%最新リビジョンに向ける
gcloud run services update-traffic syuugyoukisoku --region=asia-northeast1 --to-revisions=$LATEST_REV=100
```

#### STEP 3: 動作確認
```bash
# 現在のトラフィック設定を確認
gcloud run services describe syuugyoukisoku --region=asia-northeast1 --format="table(status.traffic)"
```

---

### 【簡易版】すべてのデプロイ後に実行
```bash
# ensure_latest_traffic.shを実行（あらゆる変更後に必ず実行）
bash ensure_latest_traffic.sh
```

Windows版:
```cmd
# simple_traffic.batを実行
simple_traffic.bat
```

---

## ❌ 絶対にやってはいけないこと

### 1. ビルド完了前にトラフィックを切り替える
```bash
# ❌ 間違い：ビルド中にトラフィック切り替え
git push && gcloud run services update-traffic ... --to-latest

# ✅ 正しい：ビルド完了を待ってから切り替え
git push
# ビルド完了を待つ
gcloud builds list --limit=1  # STATUS=SUCCESSを確認
# 最新リビジョンに切り替え
LATEST_REV=$(...)
gcloud run services update-traffic ... --to-revisions=$LATEST_REV=100
```

### 2. `--to-latest`を状況によっては使わない
```bash
# ⚠️ 注意：タイミングによってはバックグラウンドビルドに上書きされるリスク
gcloud run services update-traffic syuugyoukisoku --region=asia-northeast1 --to-latest

# ✅ より安全：具体的なリビジョンを指定
gcloud run services update-traffic syuugyoukisoku --region=asia-northeast1 --to-revisions=syuugyoukisoku-00029-7n9=100
```

### 3. 自動デプロイ時のトラフィック切り替えを期待する
Cloud Buildの自動デプロイは**新しいリビジョンを作成するだけ**で、トラフィックは切り替えません。
**必ず手動でトラフィックを切り替える必要があります。**

---

## ⚡ 環境変数・データベース接続の問題（2025年11月17日追加）

### 問題の症状
- Firestoreにデータがあるのに表示されない
- SQLiteモードで動作してしまう
- 環境変数を設定してもFirestoreに接続しない

### 原因
1. **リージョン移行時に環境変数がリセットされる**
   - `us-central1` → `asia-northeast1`への変更時など
2. **環境変数の文字列評価の問題**
   - `USE_FIRESTORE=true`が正しく認識されない場合がある
3. **URLが変わる問題**
   - リージョン変更やサービス更新でURLが変わることがある

### 解決方法

#### 1. 環境変数の確認と再設定
```bash
# 現在の環境変数を確認
gcloud run services describe syuugyoukisoku --region=asia-northeast1 --format="get(spec.template.spec.containers[0].env[].name)"

# 環境変数を設定
gcloud run services update syuugyoukisoku --region=asia-northeast1 --set-env-vars USE_FIRESTORE=True,GOOGLE_CLOUD_PROJECT=syuugyoukisoku

# トラフィックを最新リビジョンに切り替え（重要！）
gcloud run services update-traffic syuugyoukisoku --region=asia-northeast1 --to-latest
```

#### 2. cloudbuild.yamlに環境変数を永続化
```yaml
# Cloud Runデプロイステップに追加
- '--set-env-vars'
- 'USE_FIRESTORE=true,GOOGLE_CLOUD_PROJECT=syuugyoukisoku'
```

#### 3. コードで強制的にFirestoreを使用（一時的な対処）
```python
# app.py
USE_FIRESTORE = True  # 強制的にTrue
```

### URLの固定化
```bash
# カスタムドメインの設定（推奨）
gcloud run domain-mappings create --service=syuugyoukisoku --domain=yourdomain.com --region=asia-northeast1
```

### デバッグ方法
```bash
# ログでデータベース接続を確認
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=syuugyoukisoku AND (textPayload:\"Database\" OR textPayload:\"Firestore\")" --limit=10 --format=text
```

---

## 📋 よくある問題と対処法

### Q: デプロイしたのにデータが表示されない
A: 環境変数が設定されているか確認し、トラフィックが最新リビジョンに向いているか確認

### Q: URLが変わってしまった
A: リージョン変更や環境変数更新で発生。カスタムドメインの設定で解決

### Q: SQLiteモードになってしまう
A: `USE_FIRESTORE`環境変数が正しく設定されているか確認

---

## 🔍 トラブルシューティング

### 「変更が反映されない」場合のチェックリスト

1. **ビルドは成功しているか？**
   ```bash
   gcloud builds list --limit=1
   # STATUS=SUCCESS を確認
   ```

2. **最新リビジョンは作成されているか？**
   ```bash
   gcloud run revisions list --service=syuugyoukisoku --region=asia-northeast1 --limit=3
   # 最新のリビジョンのタイムスタンプを確認
   ```

3. **トラフィックは最新リビジョンに向いているか？**
   ```bash
   gcloud run services describe syuugyoukisoku --region=asia-northeast1 --format="table(status.traffic)"
   # 100%が最新リビジョンに向いているか確認
   ```

4. **ブラウザのキャッシュをクリアしたか？**
   - Ctrl+Shift+R (Windows/Linux)
   - Cmd+Shift+R (Mac)

### 古いリビジョンにトラフィックが向いている場合

```bash
# 最新リビジョンを確認
gcloud run revisions list --service=syuugyoukisoku --region=asia-northeast1 --limit=1

# トラフィックを最新に切り替え
LATEST_REV=$(gcloud run revisions list --service=syuugyoukisoku --region=asia-northeast1 --limit=1 --format="value(metadata.name)")
gcloud run services update-traffic syuugyoukisoku --region=asia-northeast1 --to-revisions=$LATEST_REV=100
```

---

## 📝 参考：完全なデプロイスクリプト例

```bash
#!/bin/bash

# 変更をコミット・プッシュ
git add .
git commit -m "変更内容"
git push origin main

# ビルド開始を待つ
echo "ビルド開始を待機中..."
sleep 20

# ビルドの完了を待つ
echo "ビルド完了を待機中..."
while true; do
    STATUS=$(gcloud builds list --limit=1 --format="value(status)")
    echo "現在のステータス: $STATUS"

    if [ "$STATUS" = "SUCCESS" ]; then
        echo "ビルド成功！"
        break
    elif [ "$STATUS" = "FAILURE" ]; then
        echo "ビルド失敗！"
        exit 1
    fi

    sleep 10
done

# 最新リビジョンを取得
LATEST_REV=$(gcloud run revisions list --service=syuugyoukisoku --region=asia-northeast1 --limit=1 --format="value(metadata.name)")
echo "最新リビジョン: $LATEST_REV"

# トラフィックを切り替え
echo "トラフィックを切り替え中..."
gcloud run services update-traffic syuugyoukisoku --region=asia-northeast1 --to-revisions=$LATEST_REV=100

echo "デプロイ完了！"
echo "URL: https://syuugyoukisoku-bsdy2np4aa-an.a.run.app"
```

---

## 🎯 重要ポイントまとめ

1. **ビルドが完了するまで待つ** - STATUS=SUCCESSを確認
2. **必ず手動でトラフィックを切り替える** - 自動では切り替わらない
3. **環境変数の設定後もトラフィック切り替えが必要**
4. **トラフィック設定を確認** - デプロイ後に必ず確認
5. **Firestore接続の問題は環境変数で解決**

このルールを守れば、今回のような問題は発生しません。
