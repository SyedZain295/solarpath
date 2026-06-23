# SolarPath — Tech Course Deliverables

**Use this document for all tech presentations (10 min each).**  
Business milestones are documented separately in [COURSE_IMPLEMENTATION.md](./COURSE_IMPLEMENTATION.md).

| Date | Session | Tech deliverable |
|------|---------|------------------|
| **27 Mar** | Team & Idea | One-button app + technology choices |
| **17 Apr** | Deployment & CI | Cloud, Docker, environments |
| **8 May** | Feature Set 1 | Core feature + agile workflow |
| **12 Jun** | Feature Set 2 | Metrics, code quality, roadmap |
| **19 Jun** | Final | Realistic tech + business picture |

---

# Milestone 1 — 27 March  
## Team & Idea (Tech): One-Button App + Stack

### Slide 1 — What we built (demo in 30 seconds)

**One-button app:** Open → Calculator → enter München PLZ `80331` + 350 kWh/month → **Get recommendation** → see kWp, 3 packages, matched installers.

Live URL (local): `http://127.0.0.1:5000/calculator`

```bash
pip install -r requirements.txt && python app.py
# or
docker compose up --build
```

### Slide 2 — Technology choices

| Decision | Choice | Why |
|----------|--------|-----|
| **Backend framework** | **Flask 3** (Python) | Fast MVP, strong ecosystem for PDF/data/science, team knows Python |
| **Frontend** | **Jinja2 + vanilla JS + CSS** | No build step, SSR for SEO, full control over UX polish; course focus on product not framework churn |
| **Database** | **JSON files** (`data/`) | Zero setup for prototype; 18k+ installer records work fine read-only; migrate to Postgres later |
| **External data** | **PVGIS v5.2** (EU JRC) | Authoritative solar yield for Germany — real engineering credibility |
| **Geocoding** | Nominatim, Open-Meteo, OpenPLZ | Free tier, postcode → lat/lon for Bayern |
| **PDF** | ReportLab | Server-side bilingual decision reports |
| **ML / AI (optional)** | Rule-based + stubs | `lead_qualification.py`, `quote_parse_stub.py` — pipeline hooks for future ML teammate |

**Not chosen (and why):** React SPA (overhead for semester MVP), Django (heavier than needed), MongoDB (relational quotes/leads fit SQL better long-term).

### Slide 3 — How it fits together

```
Browser (Jinja + JS)  →  Flask REST API  →  Domain engines  →  JSON + PVGIS
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for diagram.

### Slide 4 — GitHub

Repo structure pushed to GitHub/GitLab:

```
├── app.py              # Monolith entry
├── solar_engine.py     # Core logic
├── templates/          # Frontend pages
├── static/             # CSS, JS
├── data/               # JSON storage
├── tests/              # pytest
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/  # CI + Azure deploy
```

**Checklist before presentation:**
- [ ] `git init` → push to GitHub
- [ ] CI badge green on `main`
- [ ] Demo works from fresh clone (`README.md`)

---

# Milestone 2 — 17 April  
## Deployment & CI Strategy

### Slide 1 — Cloud provider

**Choice: Microsoft Azure — Web App for Containers (Linux)**

| Criterion | Azure |
|-----------|-------|
| Student credits / startup programs | Often available via university |
| Flask + Docker | First-class container deploy |
| HTTPS + custom domain | Built into App Service |
| Alternative considered | AWS ECS — more setup for same MVP |

### Slide 2 — System architecture

- **Monolith container** — one Docker image runs Flask on port 5000
- **Persistent volume** — `/app/data` for JSON (prod compose) → future Blob + DB
- **Health probe** — `GET /health` returns `{"status":"ok"}`

Files: `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`

### Slide 3 — Container solution

```dockerfile
FROM python:3.12-slim
COPY requirements.txt . && pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

**Local orchestration:** Docker Compose (`docker compose up`)

### Slide 4 — Dependency management

| Tool | Usage |
|------|-------|
| **pip** | `requirements.txt` — Flask, requests, reportlab, pytest |
| **venv** | Local isolation |
| **Docker** | Reproducible runtime in CI and production |

No nix/poetry — deliberate simplicity for course velocity.

### Slide 5 — Three environments

| Environment | Purpose | How |
|-------------|---------|-----|
| **Dev** | Daily coding | `python app.py` or `docker compose up` |
| **Stage** | Peer review, coach demo | **GitHub Codespaces** (`.devcontainer/devcontainer.json`) |
| **Live** | Public demo URL | Azure Web App + `deploy-azure.yml` |

### Slide 6 — CI pipeline

**Workflow:** `.github/workflows/ci.yml`

On every push / PR:
1. Python 3.12 setup
2. `pip install -r requirements.txt`
3. `python -m compileall .`
4. Import smoke test
5. **`pytest tests/`** — 8 API/page tests
6. `docker build`

**Deploy:** `.github/workflows/deploy-azure.yml` (on `main`, when secrets configured)

Secrets: `AZURE_CREDENTIALS`, `AZURE_WEBAPP_NAME`

---

# Milestone 3 — 8 May  
## Feature Set 1 — Core Feature (non-login)

### Slide 1 — Priority #1 core feature

**PV Recommendation Engine with live PVGIS integration**

Not login, not CRUD — the **7-step energy calculator** that turns goals + location + usage into a sized system with financial model.

**Why this feature first:** Everything else (installers, quotes, compatibility, PDF) consumes the recommendation output.

### Slide 2 — Agile workflow (requirement → screen → code)

| Step | Artifact | Location |
|------|----------|----------|
| Requirement | User needs trustworthy kWp + cost range for Bayern | User interviews / surveys |
| Wireframe | 7-step wizard + goal cards | Calculator mockups |
| Screen design | Glass-panel UI, bilingual, progress stepper | `templates/calculator.html`, `pages.css` |
| API contract | `POST /api/calculate` | `app.py` |
| Domain logic | Goals → tech → packages → ROI | `solar_engine.py`, `decision_engine.py`, `financial_model.py` |
| Integration | PVGIS yield + geocode | `pvgis_client.py` |
| Frontend | Wizard state, validation | `static/js/calculator.js` |
| Results | Packages + supplier match | `templates/results.html`, `results.js` |

### Slide 3 — Prioritization (MoSCoW)

| Priority | Feature | Status |
|----------|---------|--------|
| **Must** | Calculator + PVGIS + results | ✅ Done |
| **Must** | Bayern installer search | ✅ Done |
| **Should** | Quote comparison | ✅ Done |
| **Should** | Component compatibility | ✅ Done |
| **Should** | Bilingual EN/DE | ✅ Done |
| **Could** | Supplier portal + intake links | ✅ Done |
| **Won't (this semester)** | Stripe payments, full auth, Postgres | Documented |

### Slide 4 — Current backlog (top items)

1. PostgreSQL migration for quotes + customers
2. Production auth (OAuth or magic link)
3. Complete Azure live deploy + custom domain
4. Expand pytest coverage (calculate edge cases)
5. Quote OCR / ML parse (replace stub)
6. Accessibility audit (WCAG 2.1 AA on calculator)
7. Performance: cache PVGIS responses per lat/lon

---

# Milestone 4 — 12 June  
## Feature Set 2 — Metrics, Quality, Realistic Scope

### Slide 1 — Feature Set 2 focus

**Quote comparison + installer discovery at scale**

- Compare up to 5 quotes with scoring (`compare_quotes.html`)
- 18k+ installer records with postcode radius search
- Component compatibility checker (16 panels, 18 inverters, 12 batteries)

### Slide 2 — Performance metrics

| Metric | Target | How measured |
|--------|--------|--------------|
| Calculator API (mocked PVGIS) | < 500 ms | pytest + local timing |
| Calculator API (live PVGIS) | 2–8 s | External API bound — show loading state |
| Supplier search (Bayern filter) | < 300 ms | In-memory cache of `suppliers.json` |
| Page TTFB (local) | < 200 ms | Flask SSR, no heavy bundler |
| Docker image size | ~200 MB | python:3.12-slim base |

**Improvements shipped:** Supplier list caching, geocode cache in `city_coords.json`, CSS cache-busting.

### Slide 3 — Usability

- 7-step wizard with progress labels (Goals → Budget)
- Goal cards with icon + title + description (fixed layout bug)
- Mobile nav drawer with section labels
- EN/DE toggle persisted in session
- Default München for Bayern-first UX

### Slide 4 — Accessibility (current + next)

| Done | Planned |
|------|---------|
| Semantic HTML, aria-labels on nav/lang | Full keyboard path through calculator |
| Focus rings on form inputs | Color contrast audit on glass panels |
| Alt text on hero images | Screen reader test on results tables |

### Slide 5 — Code quality

- **Separation:** Routes in `app.py`, logic in engine modules (not fat controllers)
- **Tests:** `tests/` — health, pages, catalog, compatibility, suppliers, calculate (mocked)
- **CI:** compileall + pytest + Docker build on every push
- **Docs:** ARCHITECTURE.md, DEPLOYMENT.md, this file
- **i18n:** Centralized translation keys (`i18n.py`)

### Slide 6 — Realistic scope (June)

| Will ship | Will NOT ship this semester |
|-----------|----------------------------|
| Full calculator → results → quote request flow | Production payment processing |
| Installer search + compare + compatibility | Mobile native app |
| Bilingual PDF reports | Real-time chat with installers |
| Docker + CI + Azure-ready deploy | ML-based roof analysis |
| Survey + lead qualification tiers | Full marketplace escrow |

---

# Milestone 5 — 19 June  
## Final presentation (tech portion)

### Talking points

1. **Why it works technically:** Real PVGIS data, modular Python engines, containerized deploy path, tested API surface.
2. **Why it might not (honest):** JSON storage won't scale; no auth; PVGIS latency; legal/compliance not production-ready.
3. **Path to production:** Postgres → auth → Stripe → ACR image → Azure with `/health` probes.
4. **Team split:** Frontend owns templates/JS/CSS; Backend owns API/engines/data; optional ML owns quote parse + lead scoring v2.

### Demo script (3 min)

1. Home → Calculator → goals + München → results
2. Suppliers → 10 km radius
3. Compare quotes → paste sample text
4. Compatibility → pick panel + inverter
5. Show `/health` and GitHub Actions green check

---

# Quick reference commands

```bash
# Dev
pip install -r requirements.txt
python app.py

# Test
pytest tests/ -q

# Docker
docker compose up --build

# Prod-style
docker compose -f docker-compose.prod.yml up -d

# Health
curl http://localhost:5000/health
```

---

# Presentation checklist

- [ ] Laptop charged, local demo tested
- [ ] GitHub repo URL on slide 1
- [ ] Architecture diagram from ARCHITECTURE.md
- [ ] One live click-through (calculator)
- [ ] CI screenshot (Actions tab)
- [ ] Backlog slide with honest "won't do"
- [ ] 10 min max — leave 10 min for coach feedback
