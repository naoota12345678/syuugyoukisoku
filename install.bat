@echo off
echo Installing packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Installation failed
    pause
    exit /b 1
)
echo.
echo SUCCESS!
pause
