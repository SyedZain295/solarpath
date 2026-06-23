@echo off
title Solar Path - Deploy to Render
color 0A
echo.
echo  ============================================================
echo   Solar Path - Deploy to Render (free tier)
echo  ============================================================
echo.
echo  STEP 1 - Neon database (if you don't have DATABASE_URL yet)
echo    https://console.neon.tech/app/projects
echo    New project: Solar Path  |  Region: Frankfurt
echo    Copy the Postgres connection string
echo.
echo  STEP 2 - Render blueprint (opens in browser)
echo    Repo: SyedZain295/solarpath
echo    Blueprint file: render.yaml
echo.
echo  Paste these when Render asks:
echo.
echo    DATABASE_URL        = (from Neon)
echo    SUPPORT_EMAIL       = zainhaseeb0716@gmail.com
echo    BETA_ACCESS_PASSWORD= H90Gh_ffx_jlSQ
echo    BETA_INVITE_TOKENS  = solarpath-beta-2026
echo.
echo  After deploy (~10 min), test:
echo    https://solar-path.onrender.com/health
echo.
echo  Event invite link:
echo    https://solar-path.onrender.com/?invite=solarpath-beta-2026
echo.
pause
start https://console.neon.tech/app/projects
timeout /t 3 /nobreak >nul
start https://render.com/deploy?repo=https://github.com/SyedZain295/solarpath
