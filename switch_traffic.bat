@echo off
echo ===================================
echo トラフィック切り替えスクリプト
echo ===================================

echo 最新リビジョンを確認中...
for /f "tokens=*" %%i in ('gcloud run revisions list --service=syuugyoukisoku --region=asia-northeast1 --limit=1 --format="value(metadata.name)"') do set LATEST_REV=%%i
echo 最新リビジョン: %LATEST_REV%

echo.
echo 現在のトラフィック状態:
gcloud run services describe syuugyoukisoku --region=asia-northeast1 --format="table(status.traffic)"

echo.
echo トラフィックを最新リビジョンに切り替え中...
gcloud run services update-traffic syuugyoukisoku --region=asia-northeast1 --to-revisions=%LATEST_REV%=100

echo.
echo 切り替え後のトラフィック状態:
gcloud run services describe syuugyoukisoku --region=asia-northeast1 --format="table(status.traffic)"

echo.
echo ===================================
echo トラフィック切り替え完了！
echo ===================================
pause
