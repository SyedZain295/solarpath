# Solar Path — Product backlog

Prioritized backlog for course demos and production hardening.
**Last updated:** July 2026 · **Live:** https://solar-path.onrender.com

---

## Done

| ID | Item | Evidence |
|----|------|----------|
| T-01 | Multi-step energy calculator with PVGIS | `/calculator`, `solar_engine.py`, `pvgis_client.py` |
| T-02 | Results page with 3 packages + PDF | `/results`, `pdf_report.py` |
| T-03 | Public demo route | `/demo`, `data/demo_recommendation.json` |
| T-04 | Installer directory + postcode search | `/suppliers`, `supplier_store.py` (~105 curated listings) |
| T-05 | Quote comparison | `/compare-quotes`, `quote_parse_stub.py` |
| T-06 | Supplier portal + Stripe demo checkout | `/suppliers/dashboard`, `stripe_checkout.py` |
| T-07 | Customer accounts + bcrypt auth | `/register`, `/login`, `/account` |
| T-08 | EV marketplace hub | `/ev/*`, `ev_marketplace.py` |
| T-09 | CI on push (Ubuntu + Windows + macOS) | `.github/workflows/ci.yml` |
| T-10 | `/health` probe | `app.py`, used by Render |
| T-11 | GitHub repo + green CI | https://github.com/SyedZain295/solarpath |
| T-12 | Render live deploy | `render.yaml` → solar-path.onrender.com |
| T-13 | SQLAlchemy + Postgres support | `database.py`, `DATABASE_URL` |
| T-14 | Auth for account, supplier, EV dealer, admin | Sessions + `ADMIN_TOKEN` |
| T-15 | Bilingual EN/DE UI | `i18n.py`, `i18n_ev_marketplace.py` |
| T-16 | Email notifications (SMTP) | `email_service.py` |
| T-17 | Automated tests (149+) | `tests/`, pytest in CI |
| T-18 | Beta gate + invite tokens | `beta_access.py`, `docs/DEMO_MODE.md` |
| T-19 | Security headers + CSP | `http_middleware.py` |
| T-20 | Compliance / audit logging | `compliance.py`, `security_events.py` |
| T-21 | Home page + calculator UI polish | `static/css/*`, recent layout fixes |
| T-22 | Project overview Word doc generator | `scripts/generate_project_doc.py` |

---

## In progress / ops

| ID | Item | Priority | Notes |
|----|------|----------|-------|
| T-30 | **Neon Postgres on Render** | P0 | Set `DATABASE_URL` in Render dashboard; run `python scripts/setup_neon_render.py` |
| T-31 | **SMTP secrets only in dashboard** | P0 | Remove plaintext passwords from `render.yaml`; rotate Gmail app password |
| T-32 | Update architecture docs | P1 | `docs/ARCHITECTURE.md` reflects SQLAlchemy + hybrid storage |

---

## Open — product

| ID | Item | Priority | Notes |
|----|------|----------|-------|
| T-40 | WCAG keyboard nav on calculator | P2 | Tab order, focus rings on goal cards |
| T-41 | Persistent PVGIS response cache | P2 | `data/pvgis_cache.json` (gitignored) |
| T-42 | Stripe live payments | P3 | `STRIPE_LIVE_ENABLED=1` + price IDs |
| T-43 | ML quote parser | P3 | Replace `quote_parse_stub.py` regex heuristics |
| T-44 | Bill OCR (real) | P3 | `bill_ocr.py` is PDF text + regex today |
| T-45 | HTML email templates | P3 | Plain-text only in `email_service.py` |
| T-46 | Admin dashboard charts | P3 | `admin.html` is stats table |
| T-47 | Smart meter integration | P3 | UI copy: "coming soon" |
| T-48 | Large installer import (~18k PVR/OSM) | P3 | Held until contact verification — see `docs/BETA.md` |
| T-49 | Alembic schema migrations | P3 | Today: `create_all()` only |
| T-50 | Native mobile wrapper | Won't | Web-first |

---

## Won't do (this repo)

- Clinical FHIR / HIPAA PHI storage
- Microservices split
- Azure primary deploy (Render is production target)

---

## Quick commands

```bash
pytest tests/ -q
python scripts/setup_neon_render.py    # push DATABASE_URL to Render (needs .env)
python scripts/generate_project_doc.py # regenerate Word overview
```
