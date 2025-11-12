# 就業規則管理システム - 引継ぎ資料

## 現在の状況（2025-11-11）

### 決定事項
**Firebaseプロジェクトとして再構築することが決定**
- 理由: ブラックボックスを排除し、データの透明性を確保
- 現在のFirestore実装からFirebase Admin SDKベースに移行

### 現在の問題
1. **会社データが表示されない**
   - 原因: Firestoreにデータが存在しない（原因不明）
   - 対症療法ではなく、根本的な再構築を選択

2. **OCR項番号抽出の問題**
   - 章/条/項の番号が正しく抽出されない
   - 特に項番号（①②③など）が文末や間違った位置に出現
   - デバッグ機能は実装済み（coordinate_ocr.py）

---

## 次のセッションでやること

### 【優先度1】Firebaseプロジェクトとしてデータベース再構築

#### ステップ1: Firebase設計
```
companies (コレクション)
  ├─ {companyId} (ドキュメント)
       ├─ name: string
       ├─ address: string
       ├─ created_at: timestamp
       └─ regulations (サブコレクション)
            ├─ {regulationId} (ドキュメント)
                 ├─ name: string
                 ├─ type: string
                 ├─ status: string
                 ├─ created_at: timestamp
                 └─ versions (サブコレクション)
                      └─ {versionId} (ドキュメント)
                           ├─ version_number: number
                           ├─ raw_text: string
                           ├─ blocks: array
                           ├─ tables: array
                           └─ created_at: timestamp
```

#### ステップ2: Firebase Admin SDK導入
1. Firebaseプロジェクト作成（Webコンソール）
2. サービスアカウントキー生成
3. Secret Managerに保存
4. `firestore_database.py`を`firebase_database.py`に書き直し
5. Firebase Admin SDK初期化コード追加

#### ステップ3: Cloud Run設定変更
- 環境変数 `USE_FIREBASE=true` 追加
- Secret Manager参照設定

#### ステップ4: テスト
- ローカルでテスト
- デプロイ → トラフィック切り替え（デプロイルール遵守）

---

## 【優先度2】OCR項番号問題の解決

### 現状
- デバッグ機能実装済み（`coordinate_ocr.py`の`_debug_print_item_numbers()`）
- 環境変数 `PDF_PARSER_DEBUG=1` で有効化済み

### 調査方法
1. PDFをアップロード
2. Cloud Runログを確認
3. 項番号が各ステップ（抽出→並べ替え→ノイズ除去）でどう移動しているか追跡

### 予想される原因
- Y座標の閾値（y_threshold=20）が狭すぎる
- X座標ソートで項番号が後ろに押し出される
- ブロック分割が不適切

---

## 技術的な重要事項

### デプロイルール（絶対遵守）
```bash
# 1. コードをプッシュ
git add . && git commit -m "..." && git push origin main

# 2. ビルド完了を待つ（STATUS=SUCCESS）
sleep 20 && gcloud builds list --limit=1
# ... 待機 ...
gcloud builds list --limit=1  # SUCCESS確認

# 3. トラフィックを最新リビジョンに切り替え
LATEST_REV=$(gcloud run revisions list --service=syuugyoukisoku --region=asia-northeast1 --limit=1 --format="value(metadata.name)")
echo "最新リビジョン: $LATEST_REV"
gcloud run services update-traffic syuugyoukisoku --region=asia-northeast1 --to-revisions=$LATEST_REV=100

# 4. 確認
gcloud run services describe syuugyoukisoku --region=asia-northeast1 --format="table(status.traffic)"
```

**または簡易スクリプト:**
```bash
bash ensure_latest_traffic.sh
```

### 環境変数
```
USE_FIRESTORE=true  # 現在
PDF_PARSER_DEBUG=1  # デバッグモード有効
GOOGLE_CLOUD_PROJECT=syuugyoukisoku
```

---

## ファイル構成

### 主要ファイル
- `app.py`: Flaskアプリケーション
- `firestore_database.py`: 現在のDB層（→ `firebase_database.py`に移行予定）
- `coordinate_ocr.py`: 座標ベースOCR（デバッグ機能あり）
- `pdf_parser.py`: PDF処理
- `claude_validator.py`: AI検証

### 設定ファイル
- `DEPLOY_RULES.md`: デプロイ手順（必読）
- `ensure_latest_traffic.sh`: トラフィック切り替えスクリプト
- `Dockerfile`: コンテナ定義
- `cloudbuild.yaml`: ビルド設定
- `requirements.txt`: 依存関係

---

## Git状態

### 最新コミット
```
6673133 - 項番号デバッグ機能を追加
5fe7fd6 - デプロイルール強化とトラフィック切り替えスクリプト追加
```

### デプロイ済みリビジョン
```
syuugyoukisoku-00034-z78 (最新)
トラフィック: 100%
```

---

## 注意事項・反省点

### やってはいけないこと
1. **データの勝手な削除**: 絶対にしない
2. **曖昧な報告**: 「〇〇していませんでした」と言う前に事実確認
3. **デプロイルール違反**: 必ずビルド完了を待ってからトラフィック切り替え

### 改善点
1. **事実確認を最優先**: 推測で動かない
2. **透明性の確保**: すべての操作を明示的に報告
3. **ブラックボックスの排除**: データベースを可視化

---

## 次のセッションの開始方法

1. この`HANDOVER.md`を読む
2. 現在のCloud Run状態を確認:
   ```bash
   gcloud run services describe syuugyoukisoku --region=asia-northeast1 --format="table(status.traffic)"
   ```
3. Firebaseプロジェクト再構築から開始

---

## 参考リンク

- Cloud Run: https://console.cloud.google.com/run?project=syuugyoukisoku
- Firestore: https://console.cloud.google.com/firestore?project=syuugyoukisoku
- GitHub: https://github.com/naoota12345678/syuugyoukisoku
- デプロイルール: `DEPLOY_RULES.md`

---

## 質問・不明点

もし次のセッションで不明点があれば:
1. このHANDOVER.mdを参照
2. DEPLOY_RULES.mdを参照
3. git logで履歴確認
4. ログで状況確認

**とにかく、勝手に進めず、必ず相談しながら進める。**
