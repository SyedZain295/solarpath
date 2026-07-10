@echo off
title Solar Path - CI checks (local)
cd /d "%~dp0"
set APP_ENV=development

echo Running local CI checks...
echo.

python -m pip install -r requirements-dev.txt -q
if errorlevel 1 exit /b 1

python scripts\validate_env.py --ci
if errorlevel 1 exit /b 1

python -m compileall -q .
if errorlevel 1 exit /b 1

python -c "import app; print('app import ok')"
if errorlevel 1 exit /b 1

pytest tests/ -q --cov --cov-report=term-missing:skip-covered
if errorlevel 1 exit /b 1

pre-commit run --all-files
if errorlevel 1 exit /b 1

echo.
echo All checks passed.
pause
