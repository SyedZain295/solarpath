# SolarPath – Energy Platform for Bavaria (closed beta)

Home energy platform for **Bavaria (Bayern)**: PV sizing, heat pump & battery goals, quote comparison, installer directory, and project tracking.

**Beta status:** Installer directory uses **~100 demo seed listings** clearly labelled as samples — not a verified national database. Stripe checkout runs in **demo mode** until supplier demand is proven.

## Start (local)

```bash
pip install -r requirements.txt
cp .env.example .env   # then edit secrets
python app.py
```

Open **http://127.0.0.1:5000**

```bash
pytest tests/ -q
python scripts/backup_db.py
```

## Production / closed beta checklist

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Strong random string for sessions (**required**) |
| `ADMIN_TOKEN` | Password for `/admin` (**required**) |
| `BETA_ACCESS_PASSWORD` | Gates the whole site behind `/beta-login` |
| `BETA_INVITE_TOKENS` | Optional comma-separated invite tokens (`?invite=…`) |
| `SUPPORT_EMAIL` | Legal / contact email on `/terms` and `/privacy` |
| `FLASK_ENV=production` | Production mode |
| `FLASK_DEBUG=0` | Disable debug |
| `STRIPE_LIVE_ENABLED=0` | Keep demo checkout (default for beta) |
| `DATABASE_URL` | Postgres on Render; SQLite locally |

Never commit `.env` — it is gitignored.

### Docker

```bash
docker compose -f docker-compose.prod.yml up --build -d
curl localhost:8000/health
```

### Render

Deploy via [render.yaml](render.yaml) blueprint. See **[docs/BETA.md](docs/BETA.md)** for pilot metrics and validation steps.

## Features

| Page | URL | Purpose |
|------|-----|---------|
| Home | `/` | Energy platform landing |
| Calculator | `/calculator` | 7-step energy check with PVGIS |
| Results | `/results` | kWp recommendation, 3 packages, quotes |
| Installers | `/suppliers` | **Beta directory** (demo + registered installers) |
| Compare quotes | `/compare-quotes` | Side-by-side comparison |
| Supplier portal | `/suppliers/dashboard` | Leads + **structured quote form** |
| Admin | `/admin` | Stats, catalog, beta metrics API |

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12, Flask 3, Gunicorn |
| Database | SQLite (dev) / Postgres (Render) |
| Suppliers | SQLite `suppliers` table (migrated from JSON seed) |
| Frontend | Jinja2, vanilla JS, CSS |
| Solar data | PVGIS v5.2, Global Solar Atlas |
| Tests | pytest |

See **[docs/BETA.md](docs/BETA.md)** for closed-beta validation and **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for Azure/CI notes.
