@echo off
title Solar Path
cd /d "%~dp0"

echo.
echo  ========================================
echo   Solar Path - Solar Pre-Assessment App
echo  ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python is not installed. Install Python 3.10+ from https://python.org
  pause
  exit /b 1
)

echo [1/3] Installing dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (
  echo ERROR: pip install failed
  pause
  exit /b 1
)

echo [2/3] Checking data files...
python scripts/ensure_ready.py
if errorlevel 1 (
  echo WARNING: Some data missing — app may have limited features.
)

echo [3/3] Starting server...
echo.
echo  Open in your browser:  http://127.0.0.1:5000
echo.
echo  Key pages:
echo    Home          http://127.0.0.1:5000/
echo    Calculator    http://127.0.0.1:5000/calculator
echo    Compare       http://127.0.0.1:5000/compare-quotes
echo    Compatibility http://127.0.0.1:5000/compatibility
echo    Admin         http://127.0.0.1:5000/admin
echo.
echo  Press Ctrl+C to stop.
echo.

start /B cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:5000"
python app.py
