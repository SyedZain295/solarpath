# GitHub Codespaces — run the app from GitHub

**For coaches / course review:** use the **public Render URL**, not a Codespaces port link.

**https://solar-path.onrender.com**

GitHub forwarded ports (`*.app.github.dev` or `localhost:5000` in a shared link) require the viewer to be logged into GitHub and accept an access warning. That cannot be bypassed for external testers. Do **not** share your `GITHUB_TOKEN`.

**Quick start (repo contributors with a GitHub account):** [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/SyedZain295/solarpath?quickstart=1)

**Live site (everyone else):** https://solar-path.onrender.com

## Open the app from GitHub (your own Codespace)

1. Go to https://github.com/SyedZain295/solarpath
2. Click **Code** → **Codespaces** → **Create codespace on main**
3. Wait ~2–3 minutes — browser opens **http://localhost:5000**
4. Use calculator, installers, compare quotes — **no beta login** in Codespaces

Or use the one-click link: **https://codespaces.new/SyedZain295/solarpath?quickstart=1**

## Secrets (repo owner — already set)

Codespaces loads secrets from **Settings → Secrets and variables → Codespaces**.

| Secret | Required for Codespaces | Notes |
|--------|-------------------------|--------|
| `SECRET_KEY` | Yes | Flask sessions |
| `ADMIN_TOKEN` | Yes | `/admin` password |
| `POSTGRES_USER` | No (Codespaces only) | Only for `docker-compose.yml` with Postgres |
| `POSTGRES_PASSWORD` | No (Codespaces only) | Only for full Docker stack |

Codespaces uses **SQLite** via `docker-compose.codespaces.yml` (faster, no DB password needed).

## What happens when the Codespace builds

1. `.devcontainer/devcontainer.json` starts the web container
2. `scripts/codespaces_bootstrap.py` seeds suppliers + database
3. **Beta login disabled** — app is usable immediately
4. Port **5000** forwarded — opens in browser automatically

### Pages to try

| Page | URL |
|------|-----|
| Home | http://localhost:5000/ |
| Calculator | http://localhost:5000/calculator |
| Installers | http://localhost:5000/suppliers |
| Compare quotes | http://localhost:5000/compare-quotes |
| Admin | http://localhost:5000/admin (`ADMIN_TOKEN` secret) |
| Health | http://localhost:5000/health |

## Manual command (inside Codespace)

```bash
docker compose -f docker-compose.codespaces.yml up --build
```

Full Postgres stack (optional):

```bash
docker compose up --build
```

## Local Windows (no GitHub)

```bash
SETUP_DEV.bat
START.bat
```
