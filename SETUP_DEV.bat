@echo off
title Solar Path - Developer setup
cd /d "%~dp0"

echo.
echo  Standard dev setup (pre-commit, tests, env check)
echo  ==================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Install Python 3.10+ from https://python.org
  pause
  exit /b 1
)

echo [1/5] Installing app + dev dependencies...
python -m pip install --upgrade pip -q
pip install -r requirements-dev.txt -q
if errorlevel 1 exit /b 1

echo [2/5] .env file...
if not exist ".env" copy /Y .env.example .env >nul

echo [3/5] Pre-commit hooks...
pre-commit install
if errorlevel 1 (
  echo WARNING: pre-commit install failed — continue without hooks
)

echo [4/5] Environment validation...
python scripts\validate_env.py
set VALID=%ERRORLEVEL%

echo [5/5] Data check...
python scripts\ensure_ready.py
set READY=%ERRORLEVEL%

echo.
echo  Dev setup complete.
echo    Run tests:     pytest tests/ -q
echo    Full CI local: RUN_CI_LOCAL.bat
echo    With coverage: pytest tests/ --cov --cov-report=term-missing
echo    Start app:     START.bat
echo.
if %VALID% neq 0 pause & exit /b %VALID%
if %READY% neq 0 echo NOTE: Import suppliers if you need the full directory feature.
pause
