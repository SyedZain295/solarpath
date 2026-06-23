@echo off
title SolarPath - Free cloud deploy
echo.
echo  Opening Neon (free database) and Render (free hosting)...
echo.
echo  After Neon creates a project, copy the Postgres connection string.
echo  Paste it into Render as DATABASE_URL when prompted.
echo.
echo  Also paste these in Render:
echo    SUPPORT_EMAIL=zainhaseeb0716@gmail.com
echo    BETA_ACCESS_PASSWORD=H90Gh_ffx_jlSQ
echo    BETA_INVITE_TOKENS=solarpath-beta-2026
echo.
start https://console.neon.tech/app/projects
timeout /t 2 /nobreak >nul
start "https://render.com/deploy?repo=https://github.com/SyedZain295/solarpath"
echo.
pause
