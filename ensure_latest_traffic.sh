#!/bin/bash
# すべてのデプロイ後に必ず実行するスクリプト
# 最新リビジョンにトラフィックを100%向ける

set -e

SERVICE="syuugyoukisoku"
REGION="asia-northeast1"

echo "=================================="
echo "トラフィック切り替えスクリプト"
echo "=================================="

# 最新リビジョンを取得
echo "最新リビジョンを確認中..."
LATEST_REV=$(gcloud run revisions list --service=$SERVICE --region=$REGION --limit=1 --format="value(metadata.name)")
echo "最新リビジョン: $LATEST_REV"

# 現在のトラフィック状態を確認
echo ""
echo "現在のトラフィック状態:"
gcloud run services describe $SERVICE --region=$REGION --format="table(status.traffic)"

# トラフィックを最新リビジョンに切り替え
echo ""
echo "トラフィックを最新リビジョンに切り替え中..."
gcloud run services update-traffic $SERVICE --region=$REGION --to-revisions=$LATEST_REV=100

# 切り替え後の状態を確認
echo ""
echo "切り替え後のトラフィック状態:"
gcloud run services describe $SERVICE --region=$REGION --format="table(status.traffic)"

echo ""
echo "=================================="
echo "✅ トラフィック切り替え完了"
echo "=================================="
