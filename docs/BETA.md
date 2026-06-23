# SolarPath closed beta — validation playbook

Use this during the **10–15 homeowner / 5–10 installer** pilot in Bavaria.

## Access control

Set in production environment:

| Variable | Purpose |
|----------|---------|
| `BETA_ACCESS_PASSWORD` | Shared password on `/beta-login` |
| `BETA_INVITE_TOKENS` | Comma-separated tokens; invite URL: `https://your-app.onrender.com/?invite=TOKEN` |
| `STRIPE_LIVE_ENABLED=0` | Keeps supplier checkout in **demo mode** (default) |

## Metrics to track

View in admin: `GET /api/admin/beta-metrics` (requires admin token).

| Metric | Event type | Goal |
|--------|------------|------|
| Calculator completion | `calculator_complete` | ≥50% of starts |
| PDF downloads | `pdf_download` | Shows installer-ready intent |
| Quote requests | `quote_request` | Core conversion |
| Package choice | `package_select` | cheapest / best_value / most_reliable split |

**Installer side (manual during beta):**

- Response time to leads
- % of leads installers call “qualified”
- Would they pay for similar leads? (interview)

## Supplier data policy (beta)

- Directory shows **~100 demo seed listings** labelled “Demo listing (beta sample)”.
- Do **not** import the old 18k PVR dump until contact verification is in place.
- Grow to **50–200 real installers** with `listing_status=verified` and `contact_verified=true`.

## Database backups

```bash
python scripts/backup_db.py
```

On Render: schedule a cron job or download Postgres snapshots from the dashboard.

## Deploy (Render)

1. Push repo to GitHub
2. New **Blueprint** from `render.yaml`
3. Set `SUPPORT_EMAIL` in Render dashboard
4. Copy `BETA_ACCESS_PASSWORD` and share with pilot users only
5. Verify `/health` → `"status":"ok"`

## What to postpone

- Live Stripe (`STRIPE_LIVE_ENABLED=1`)
- 18k supplier import
- PDF quote parsing (use **Supplier dashboard → Submit quote** structured form)
- Bill OCR, roof AI, finance/incentive APIs
