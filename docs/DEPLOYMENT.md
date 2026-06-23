# Deployment Guide

## Environments

| Environment | Purpose | How to run |
|-------------|---------|------------|
| **Dev** | Local development | `python app.py` or `docker compose up` |
| **Stage** | Codespaces / team testing | Open in GitHub Codespaces (`.devcontainer/devcontainer.json`) |
| **Live** | Production demo | Azure Web App for Containers or `docker compose -f docker-compose.prod.yml up -d` |

## Local (Dev)

```bash
pip install -r requirements.txt
python app.py
```

Visit http://localhost:5000 — switch language with **EN | DE** in the nav.

## Docker (Dev)

```bash
docker compose up --build
```

## Docker (Production-style)

```bash
export SECRET_KEY=your-production-secret
docker compose -f docker-compose.prod.yml up --build -d
```

Data persists in the `solar_data` volume under `/app/data`.

## GitHub Codespaces (Stage)

1. Push the repo to GitHub
2. Open **Code → Codespaces → Create codespace**
3. Post-create runs `pip install` and starts the app on port 5000

## Azure (Live)

Recommended: **Azure Web App for Containers** (Linux).

### One-time setup

1. Create a resource group and App Service plan (Linux, B1 or higher)
2. Create a **Web App for Containers**
3. Configure container settings to pull from GitHub Container Registry or ACR
4. Set application settings:
   - `SECRET_KEY` — strong random string
   - `WEBSITES_PORT` — `5000`
5. Add GitHub secrets:
   - `AZURE_CREDENTIALS` — service principal JSON
   - `AZURE_WEBAPP_NAME` — your web app name

### CI/CD

- **CI** (every push/PR): `.github/workflows/ci.yml` — syntax, import, Docker build
- **Deploy** (main branch): `.github/workflows/deploy-azure.yml` — builds and deploys when Azure secrets are set

Without Azure secrets, the deploy workflow still validates the build and prints setup instructions.

## Health check

After deploy, verify:

- `/health` — `{"status":"ok","service":"solarpath"}`
- `/` — homepage (EN/DE)
- `/calculator` — full wizard
- `/suppliers?postcode=10115&radius_km=10` — nearby installers
- `/api/admin/summary` — admin stats (protect before production)

## Before production

- Replace template legal text in `/terms` and `/privacy`
- Add authentication to `/admin`
- Move JSON storage to PostgreSQL or Azure Blob + database
- Connect Stripe for supplier checkout
- Set a strong `SECRET_KEY` and HTTPS only
