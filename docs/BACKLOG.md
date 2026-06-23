# Solar Path — Product Backlog (Tech)

**Last updated:** Course semester 2026  
**Method:** MoSCoW + sprint-ready user stories

---

## Done ✅

| ID | Story | Component |
|----|-------|-----------|
| T-01 | As a homeowner I enter PLZ + usage and get kWp recommendation | Calculator + PVGIS |
| T-02 | As a user I see 3 package tiers with ROI | results + financial_model |
| T-03 | As a user I find installers within X km of postcode | suppliers API |
| T-04 | As a user I compare pasted quotes side-by-side | compare-quotes |
| T-05 | As a user I check panel/inverter/battery compatibility | compatibility |
| T-06 | As a user I switch EN/DE | i18n |
| T-07 | As a user I download PDF decision report | pdf_report |
| T-08 | As an installer I register and get intake link | supplier portal |
| T-09 | As a team we run CI on push | GitHub Actions |
| T-10 | As ops we health-check the service | `/health` |

---

## In progress / next sprint

| ID | Story | Priority | Owner |
|----|-------|----------|-------|
| T-11 | Push repo to GitHub; green CI badge | P0 | Backend |
| T-12 | Azure live deploy with secrets | P0 | Backend |
| T-13 | Postgres for quotes + customers | P1 | Backend |
| T-14 | Auth for /account and /admin | P1 | Backend |
| T-15 | WCAG keyboard nav on calculator | P2 | Frontend |
| T-16 | Cache PVGIS responses (lat/lon key) | P2 | Backend |
| T-17 | Expand pytest to 20+ cases | P2 | Backend |

---

## Backlog (later)

| ID | Story | Priority |
|----|-------|----------|
| T-18 | Stripe checkout (real payments) | P3 |
| T-19 | ML quote parser (replace stub) | P3 |
| T-20 | Bill OCR upload | P3 |
| T-21 | Roof photo analysis API | P3 |
| T-22 | Email templates (HTML) | P3 |
| T-23 | Admin dashboard charts | P3 |
| T-24 | Native mobile wrapper | Won't |

---

## Definition of Done (team)

- [ ] Code merged to `main`
- [ ] CI green (compile + pytest + docker build)
- [ ] Manual test on `/calculator` path
- [ ] EN + DE strings for user-facing text
- [ ] No secrets in repo
