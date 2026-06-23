# Solar Path Course Implementation Notes

## Business Milestones

### Problem validation
- Separate homeowner and solar-company surveys added at `/survey/homeowners` and `/survey/companies`
- Company survey captures B2B lead qualification pain points, solution fit, and pricing preferences
- Homeowner survey captures trust, quote friction, and decision priorities

### Pretotype / problem exploration
- Landing page, calculator, supplier search, surveys, and PDF report together act as the pretotype
- Users can simulate the journey from interest to installer matching before a full marketplace exists

### Personas
- Homeowner focused on lowest upfront cost
- Homeowner preparing for EV or heat pump electrification
- Installer sales team qualifying residential leads
- Regional solar supplier looking for fitter-qualified leads

### Learnings / reflection structure
- What users struggle with now: trust, quote comparison, low-quality leads, missing roof data
- What changed in the product: split surveys, quote-ready reports, radius-based installer search, bilingual support
- Why it changed: interviews and survey questions focus on pre-qualification and supplier trust

## Tech Milestones

### Cloud provider
- Recommended: Azure App Service or Azure Container Apps
- Reason: simple path for Flask deployment, easy environment split for student/startup workflow

### Architecture
- Current architecture: Flask monolith
- Frontend: Jinja templates + vanilla JavaScript
- Data storage: JSON files for prototype stage
- Future upgrade path: Postgres + background workers

### Container solution
- `Dockerfile` added
- `docker-compose.yml` added for local dev orchestration

### Dependency management
- Python dependencies managed with `pip` and `requirements.txt`

### Orchestration
- Docker Compose used for local orchestration
- Current single-service setup is enough for MVP

### Environments
- Dev: local machine with Flask or Docker Compose
- Stage: GitHub Codespaces via `.devcontainer/devcontainer.json`
- Live: Azure deployment using the same container image

### CI strategy
- GitHub Actions workflow added at `.github/workflows/ci.yml`
- Checks:
  - dependency installation
  - Python syntax compile
  - import smoke test
  - **pytest** (`tests/` — health, pages, catalog, compatibility, suppliers)
  - Docker image build

### Tech presentation docs
- **`docs/TECH_COURSE.md`** — slide-ready content for all tech milestones (Mar 27 – Jun 19)
- **`docs/ARCHITECTURE.md`** — system diagram, API, module map
- **`docs/BACKLOG.md`** — prioritized product backlog for Feature Set presentations

## Product Features Implemented For Presentations

### Bilingual support
- Added EN/DE language switching with session persistence
- Core shared navigation/footer and key landing pages support translation keys

### Nearby installer discovery
- Supplier search now supports postcode-based lookup with radius filtering
- Default UX supports finding PV installers within 10 km of a postcode

## Realistic Scope

### Implemented now
- Full EN/DE bilingual support across all pages
- Surveys for homeowners and solar companies
- Radius-based installer search (10 km)
- Bilingual PDF decision reports
- Docker/Compose/Codespaces/CI + Azure deploy workflow
- Account, registration, supplier dashboard, checkout

### Not fully implemented yet
- Full database-backed marketplace
- Production-grade authentication
- Full automated deployment pipeline to Azure
- Complete translation coverage across every UI string
