@echo off
chcp 65001 > nul
echo ===================================
echo Complete Auto Deploy Script
echo ===================================

cd /d C:\Users\naoot\Desktop\syuugyoukisoku

:: Git commit and push
echo [1/4] Committing changes...
git add -A
git commit -m "Auto-deploy: %date% %time%" || echo No changes

echo.
echo [2/4] Pushing to GitHub...
git push origin main

:: Wait for build
echo.
echo [3/4] Waiting for Cloud Build (about 2 minutes)...
timeout /t 120 /nobreak

:: Switch traffic
echo.
echo [4/4] Switching traffic...
for /f "tokens=*" %%i in ('gcloud run revisions list --service=syuugyoukisoku --region=asia-northeast1 --limit=1 --format="value(metadata.name)"') do set LATEST_REV=%%i
gcloud run services update-traffic syuugyoukisoku --region=asia-northeast1 --to-revisions=%LATEST_REV%=100

echo.
echo ===================================
echo DEPLOY COMPLETE!
echo ===================================
echo.
echo App URL: https://syuugyoukisoku-bsdy2np4aa-an.a.run.app
echo.
pause
