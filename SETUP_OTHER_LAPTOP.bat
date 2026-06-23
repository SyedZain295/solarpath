@echo off
title Solar Path - Setup on a new laptop
cd /d "%~dp0"
color 0B

echo.
echo  ============================================================
echo   Solar Path - First-time setup (new laptop)
echo  ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo  STEP 1: Install Python 3.10 or newer
  echo    https://www.python.org/downloads/
  echo    IMPORTANT: tick "Add python.exe to PATH" during install
  echo.
  start https://www.python.org/downloads/
  pause
  exit /b 1
)

echo  Python OK:
python --version
echo.

echo  Installing packages...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo  ERROR: pip install failed. Check your internet connection.
  pause
  exit /b 1
)

if not exist ".env" (
  echo  Creating .env ...
  copy /Y .env.example .env >nul
)

python scripts\ensure_ready.py
if errorlevel 1 (
  echo.
  echo  Data issue — try: python scripts\seed_german_installers.py
  pause
  exit /b 1
)

echo.
echo  ============================================================
echo   Setup complete. Starting the app...
echo   Browser: http://127.0.0.1:5000
echo   Admin:   http://127.0.0.1:5000/admin  (password in .env ADMIN_TOKEN)
echo  ============================================================
echo.
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5000
python app.py
