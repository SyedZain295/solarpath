@echo off
title SolarPath - EVENT MODE
cd /d "%~dp0"

echo.
echo  ========================================
echo   SolarPath - Event demo (free, local)
echo  ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python is not installed.
  pause
  exit /b 1
)

pip install -r requirements.txt -q
python scripts/ensure_ready.py >nul 2>&1

echo Starting server for phones on the same WiFi...
echo.
python scripts/print_event_urls.py
echo.

python app.py
