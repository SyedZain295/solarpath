# Solar Path

Home energy platform for **Bavaria (Bayern)** — solar PV sizing, heat pumps, batteries, EV charging, installer matching, and quote comparison.

**Stack:** Python 3.12 · Flask · SQLite/Postgres · Jinja + vanilla JS · PVGIS solar data

---

## Try the app (no setup)

### For coaches, reviewers, and anyone testing the app

**Use the public live site — no GitHub login required:**

**https://solar-path.onrender.com**

| Page | URL |
|------|-----|
| Home | https://solar-path.onrender.com/ |
| Calculator | https://solar-path.onrender.com/calculator |
| Installers | https://solar-path.onrender.com/suppliers |
| Compare quotes | https://solar-path.onrender.com/compare-quotes |
| Demo | https://solar-path.onrender.com/demo |
| Health | https://solar-path.onrender.com/health |

First load may take ~30–60 seconds on Render’s free tier (service wakes from sleep).

> **Do not use Codespaces port URLs for external review.** GitHub forwarded ports require the viewer’s own GitHub session and a one-time consent step — they cannot be bypassed with query parameters. Codespaces is for **developers** who open their own codespace while logged into GitHub.

### Run from GitHub (developers only — not for sharing with reviewers)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/SyedZain295/solarpath?quickstart=1)

**One-click:** https://codespaces.new/SyedZain295/solarpath?quickstart=1

1. Click the link or badge (**Code → Codespaces → Create codespace on main**)
2. Wait ~2–3 minutes
3. App opens at **http://localhost:5000** (use **Ports** tab if needed)

GitHub Actions smoke-tests this on every push. No beta login in Codespaces.

Details: [docs/CODESPACES.md](docs/CODESPACES.md) · Coach handoff: [docs/REVIEWER.md](docs/REVIEWER.md)

---

## Run locally (Windows)

```text
SETUP_DEV.bat    ← first time only (deps + pre-commit)
START.bat        ← run the app
```

Open **http://127.0.0.1:5000**

Copy `.env.example` to `.env` for admin/beta passwords (optional for local dev).

### Run locally (Mac/Linux)

```bash
pip install -r requirements.txt
cp .env.example .env
python app.py
```

### Docker

```bash
docker compose -f docker-compose.codespaces.yml up --build
```

---

## Development

```bash
pytest tests/ -q              # run tests
RUN_CI_LOCAL.bat              # full CI checks (Windows)
pre-commit run --all-files    # lint/hygiene hooks
```

Course rubric mapping: [docs/RUBRIC.md](docs/RUBRIC.md)

---

## Main features

| Page | Path | What it does |
|------|------|--------------|
| Calculator | `/calculator` | 7-step energy check with real PVGIS yield data |
| Results | `/results` | kWp sizing, 3 packages, savings, matched installers |
| Installers | `/suppliers` | Directory + map (demo seed + registered installers) |
| Compare quotes | `/compare-quotes` | Side-by-side quote comparison |
| Supplier portal | `/suppliers/dashboard` | Leads and structured quote forms |
| EV hub | `/ev` | EV marketplace and bundle planning |
| Admin | `/admin` | Stats and catalog (`ADMIN_TOKEN` in env) |

---

## Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/SyedZain295/solarpath)

Uses `render.yaml`. **Postgres (required for production data):** create a free database at [Neon](https://neon.tech), then set `DATABASE_URL` on Render — see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) or run `python scripts/setup_neon_render.py`.

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask session secret |
| `ADMIN_TOKEN` | Password for `/admin` |
| `DATABASE_URL` | Postgres on Render; SQLite locally if unset |
| `BETA_ACCESS_PASSWORD` | Optional beta gate password |
| `BETA_INVITE_TOKENS` | Comma-separated invite tokens |

Never commit `.env`. For Codespaces, set secrets under **Settings → Secrets and variables → Codespaces**.

---

## Repo

**GitHub:** https://github.com/SyedZain295/solarpath

**Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
