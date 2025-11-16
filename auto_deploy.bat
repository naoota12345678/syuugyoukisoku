@echo off
echo ===================================
echo 完全自動デプロイスクリプト
echo ===================================

cd /d C:\Users\naoot\Desktop\syuugyoukisoku

:: Gitにコミット＆プッシュ
echo [1/4] 変更をコミット中...
git add -A
git commit -m "Auto-deploy: %date% %time%" || echo 変更なし

echo.
echo [2/4] プッシュ中...
git push origin main

:: ビルドの完了を待つ
echo.
echo [3/4] Cloud Buildの完了を待っています（約2分）...
timeout /t 120 /nobreak

:: 最新リビジョンにトラフィック切り替え
echo.
echo [4/4] トラフィック切り替え中...
for /f "tokens=*" %%i in ('gcloud run revisions list --service=syuugyoukisoku --region=asia-northeast1 --limit=1 --format="value(metadata.name)"') do set LATEST_REV=%%i
gcloud run services update-traffic syuugyoukisoku --region=asia-northeast1 --to-revisions=%LATEST_REV%=100

echo.
echo ===================================
echo ✅ デプロイ完全完了！
echo ===================================
echo.
echo アプリURL: https://syuugyoukisoku-bsdy2np4aa-an.a.run.app
echo.
pause
