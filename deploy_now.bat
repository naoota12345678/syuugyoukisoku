@echo off
echo ===================================
echo デプロイスクリプト
echo ===================================

cd /d C:\Users\naoot\Desktop\syuugyoukisoku

echo.
echo 1. Git状態確認
git status

echo.
echo 2. 変更をステージング
git add firestore_database.py diagnose_versions.py fix_version_1.py test_firebase_connection.py .env

echo.
echo 3. コミット
git commit -m "Fix: Firebase接続エラーとバージョン管理問題を修正"

echo.
echo 4. プッシュ（Cloud Buildが自動デプロイ）
git push origin main

echo.
echo ===================================
echo デプロイ完了！
echo ===================================
echo.
echo 次のステップ:
echo 1. Cloud Buildの完了を待つ（2-3分）
echo 2. ensure_latest_traffic.sh を実行してトラフィック切り替え
pause
