@echo off
echo =======================================================
echo     AI Data Quality Analyzer
echo =======================================================
echo.

cd /d "%~dp0"

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

echo.
echo Installing requirements...
pip install -r backend\requirements.txt

echo.
echo Starting the application...
echo The app will open in your default browser at http://localhost:5000
echo.
echo Keep this window open while using the application.
echo Press Ctrl+C to stop the server.
echo.

cd backend
start http://localhost:5000
python app.py

pause
