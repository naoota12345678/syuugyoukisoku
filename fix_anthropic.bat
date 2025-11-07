@echo off
echo ==========================================
echo Fixing Anthropic Library
echo ==========================================
echo.
echo Uninstalling current version...
pip uninstall anthropic -y
echo.
echo Installing compatible version...
pip install anthropic==0.25.0
echo.
echo ==========================================
echo Done! Please restart the application.
echo ==========================================
pause
