# Demo mode & beta invite — spec for collaborators (e.g. ChatGPT)

## Goal

Make **Solar Path** easy to demo publicly while keeping invite links working when the beta gate is turned back on.

**Live site:** https://solar-path.onrender.com  
**Repo:** https://github.com/SyedZain295/solarpath

---

## What was implemented

### 1. Temporarily disable beta gate (demo deploy)

Environment variables:

| Variable | Demo value | Effect |
|----------|------------|--------|
| `BETA_GATE_ENABLED` | `0` | Beta gate off — site is public |
| `BETA_DEMO_MODE` | `1` | Same effect (alias) |
| `BETA_INVITE_TOKENS` | `solarpath-beta-2026` | Still used for link tagging |
| `BETA_INVITE_DEFAULT` | `solarpath-beta-2026` | Auto-appended to internal links |

To **re-enable** closed beta on Render: set `BETA_GATE_ENABLED=1` and `BETA_DEMO_MODE=0`.

### 2. Public `/demo` route

- **URL:** `/demo` (always public, even when beta gate is on)
- **Data:** Fixed sample recommendation — München detached house, ~350 kWh/month, 12 k€ budget
- **File:** `data/demo_recommendation.json` loaded via `demo_data.py`
- **Template:** `templates/demo.html` (extends results page, preloads JSON into storage)

**Share this link for demos:**

```
https://solar-path.onrender.com/demo
```

### 3. Persistent invite session

After first visit with `?invite=solarpath-beta-2026`:

- **Server:** Flask session `beta_authenticated` + `beta_invite_token`, 30-day cookie (`PERMANENT_SESSION_LIFETIME`)
- **Client:** `localStorage` + `sessionStorage` key `betaInviteToken` (30-day TTL)
- **API:** `X-Beta-Invite` header on calculator POST

Logic lives in `beta_access.py` (`persist_beta_invite_session`, `check_beta_access`) and `static/js/beta_invite.js`.

### 4. Auto-invite on internal links

- **Jinja:** `invite_href('/path')` → `/path?invite=solarpath-beta-2026`
- **Templates:** `templates/base.html` nav + footer use `invite_href`
- **JS fallback:** `beta_invite.js` patches all `a[href^="/"]` on page load
- **Context:** `window.BETA_INVITE_DEFAULT` from `beta_invite_default` in Flask context processor

---

## Key files

| File | Purpose |
|------|---------|
| `beta_access.py` | Gate on/off, invite session, `invite_href()` |
| `demo_data.py` | Load fixed demo JSON |
| `data/demo_recommendation.json` | Sample calculation output |
| `templates/demo.html` | Demo results page |
| `templates/base.html` | Nav links with invite |
| `static/js/beta_invite.js` | Client invite persistence + link patching |
| `render.yaml` | Demo env vars for Render |
| `app.py` | `/demo` route, context processor |

---

## URLs to share

| Purpose | URL |
|---------|-----|
| Demo (no form) | `https://solar-path.onrender.com/demo` |
| Full calculator | `https://solar-path.onrender.com/calculator?invite=solarpath-beta-2026` |
| Health check | `https://solar-path.onrender.com/health` |

---

## Re-enable closed beta later

1. Render dashboard → Environment:
   - `BETA_GATE_ENABLED` = `1`
   - `BETA_DEMO_MODE` = `0`
   - Keep `BETA_ACCESS_PASSWORD` set
2. `/demo` stays public (exempt path)
3. `POST /api/calculate` stays exempt (calculator works with invite header)
4. Internal links still carry `?invite=…` for first-time visitors

---

## Stack reminder

Flask + Jinja2, vanilla JS, SQLite/Postgres, PVGIS API, deployed on Render free tier.
