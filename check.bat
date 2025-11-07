@echo off
echo ==========================================
echo Checking Environment
echo ==========================================
echo.

echo Python version:
python --version
echo.

echo Current directory:
cd
echo.

echo Python files:
dir *.py
echo.

echo Testing imports:
python -c "import sys; print('Python OK')"
python -c "import flask; print('Flask OK')"
python -c "import anthropic; print('Anthropic OK')"
python -c "import pdfplumber; print('PDFPlumber OK')"
echo.

echo Testing local imports:
python -c "import sys, os; sys.path.insert(0, os.getcwd()); import database; print('database OK')"
python -c "import sys, os; sys.path.insert(0, os.getcwd()); import pdf_parser; print('pdf_parser OK')"
python -c "import sys, os; sys.path.insert(0, os.getcwd()); import claude_validator; print('claude_validator OK')"
echo.

echo ==========================================
echo Check complete
echo ==========================================
pause
