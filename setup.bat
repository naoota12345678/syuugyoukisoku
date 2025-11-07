@echo off
echo ========================================
echo 就業規則管理システム セットアップ
echo ========================================
echo.

REM Pythonのバージョンチェック
python --version >nul 2>&1
if errorlevel 1 (
    echo [エラー] Pythonがインストールされていません
    echo Python 3.8以上をインストールしてください
    pause
    exit /b 1
)

echo [1/3] 必要なパッケージをインストール中...
pip install -r requirements.txt

if errorlevel 1 (
    echo [エラー] パッケージのインストールに失敗しました
    pause
    exit /b 1
)

echo.
echo [2/3] 環境変数の設定を確認中...
if not exist .env (
    echo .envファイルが見つかりません
    echo .env.exampleをコピーして.envを作成してください
    copy .env.example .env
    echo.
    echo ANTHROPIC_API_KEYを設定してください
    notepad .env
)

echo.
echo [3/3] セットアップ完了！
echo.
echo ========================================
echo アプリを起動しますか？ (Y/N)
echo ========================================
set /p START=">"

if /i "%START%"=="Y" (
    echo.
    echo アプリを起動しています...
    echo ブラウザで http://localhost:5000 にアクセスしてください
    echo.
    python app.py
) else (
    echo.
    echo 後で起動する場合は以下のコマンドを実行してください:
    echo python app.py
    echo.
)

pause
