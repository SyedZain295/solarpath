# Rubric mapping — Solar Path (enterprise criteria)

How this project maps to advanced course / enterprise evaluation criteria.

**Legend:** ✅ implemented in repo · ⚠️ partial (appropriate for MVP scope) · 🔭 roadmap (documented, not faked)

**Scope:** Bavaria solar lead platform (Flask monolith). Not a clinical EHR — FHIR/PHI controls are mapped to **PII + audit** patterns instead.

---

## 1. Fully automated setup

> Pre-commit hooks, CI/CD, dependency caching, cross-platform reproducibility, automatic environment validation

| Item | Status | Evidence |
|------|--------|----------|
| Pre-commit hooks | ✅ | `.pre-commit-config.yaml` — whitespace, YAML/JSON, large files, private keys |
| CI/CD | ✅ | `.github/workflows/ci.yml` — push + PR on all branches |
| Dependency caching | ✅ | `actions/setup-python@v6` with `cache: pip` |
| Cross-platform reproducibility | ✅ | CI matrix: **Ubuntu, Windows, macOS**; `SETUP_DEV.bat` / `setup.sh` / Docker |
| Automatic environment validation | ✅ | `scripts/validate_env.py --ci`, `config.py` production checks, `scripts/ensure_ready.py` |

---

## 2. Testing & regression

> Property-based tests, fuzz testing, continuous regression detection, test coverage analytics integrated with CI/CD

| Item | Status | Evidence |
|------|--------|----------|
| Property-based tests | ✅ | `tests/test_property.py` (Hypothesis) |
| Fuzz testing | ✅ | `tests/test_fuzz_api.py` |
| Continuous regression | ✅ | **150 tests** on every push; Docker + Codespaces smoke in CI |
| Coverage analytics in CI | ✅ | `pytest --cov`, `coverage.xml` artifact, 60% gate in `pyproject.toml` |

---

## 3. Configuration & deployment

> Fully automated config deployment, validation, secrets rotation; environment isolation; CI/CD integration

| Item | Status | Evidence |
|------|--------|----------|
| Environment isolation | ✅ | `APP_ENV` / `FLASK_ENV`, `config.py` dev vs prod validation |
| Config validation | ✅ | Startup rejects weak `SECRET_KEY` / `ADMIN_TOKEN` in production |
| Secrets rotation support | ✅ | `SECRET_KEY_PREVIOUS` comma-separated window in `config.py` |
| Automated deploy config | ⚠️ | `render.yaml` blueprint + `scripts/configure_render.py` / `scripts/setup_neon_render.py` |
| Secrets in CI/CD | ✅ | GitHub Codespaces secrets; Render dashboard (`sync: false`); `.env` gitignored |
| Full secrets auto-rotation | 🔭 | Manual rotation documented in `docs/DEPLOYMENT.md` |

---

## 4. Logging & anomaly detection

> HIPAA-compliant logging, real-time anomaly detection, alerting, log-driven decision automation

| Item | Status | Evidence |
|------|--------|----------|
| Structured logging | ✅ | `logging_config.py` — JSON in production |
| PII-safe / HIPAA-adjacent logging | ✅ | `compliance.py` — classification, redaction, retention tags |
| Real-time anomaly detection | ✅ | `anomaly_detection.py` — auth failure sliding window + lockout |
| Request correlation | ✅ | `X-Request-ID` in `http_middleware.py` |
| Audit trail | ✅ | `security_events.py` + `compliance_tags()` |
| Centralized alerting (PagerDuty/Slack) | 🔭 | Logs local / Render stdout today |
| Log-driven automation (runbooks) | 🔭 | Lockout is automated; infra scaling is not |

See **`docs/COMPLIANCE.md`**.

---

## 5. Microservices & orchestration

> Microservices with dynamic orchestration, automated scaling, high availability, advanced monitoring, minimal downtime

| Item | Status | Evidence |
|------|--------|----------|
| Architecture | ⚠️ | **Monolith** by design (`docs/ARCHITECTURE.md`) — simpler for MVP |
| Health monitoring | ✅ | `/health` — DB, email, beta gate, supplier count |
| Container-ready | ✅ | `Dockerfile`, `docker-compose.yml`, CI Docker build |
| Dynamic orchestration / K8s / autoscale | 🔭 | Render free tier; no multi-service mesh |
| Multi-node HA | 🔭 | Single web service + optional Neon Postgres |

---

## 6. Security pipelines

> Automated validation pipelines, continuous threat modeling, runtime security monitoring, real-time anomaly detection

| Item | Status | Evidence |
|------|--------|----------|
| Automated validation pipelines | ✅ | CI: compileall, import smoke, UI smoke, tests, coverage |
| Dependency audit | ✅ | `pip-audit` in CI (`.github/workflows/ci.yml`) |
| Static analysis (SAST) | ✅ | CodeQL (`.github/workflows/codeql.yml`) |
| Runtime security headers | ✅ | CSP, HSTS, `X-Frame-Options`, etc. (`http_middleware.py`) |
| Auth anomaly (runtime) | ✅ | `anomaly_detection.py` |
| WAF / runtime RASP | 🔭 | Edge WAF not deployed |
| Formal threat modeling docs | 🔭 | Implicit in `COMPLIANCE.md`; no STRIDE doc |

---

## 7. Fault tolerance & self-healing

> Self-healing mechanisms, alerting, retry/backoff, fault isolation in real-time pipelines

| Item | Status | Evidence |
|------|--------|----------|
| Retry / backoff | ✅ | `retry_utils.py` — PVGIS HTTP (`pvgis_client.py`) |
| Graceful degradation | ✅ | PVGIS cache + offline PLZ fallback; health `ok` / `degraded` |
| External API fault isolation | ✅ | Geocode/PVGIS failures return safe API errors, not crashes |
| Self-healing (auto-restart pods) | ⚠️ | Render restarts on crash; no custom orchestrator |
| Pipeline alerting | 🔭 | No on-call integration |

---

## 8. Zero-trust & auth

> Zero-trust design; end-to-end encryption; MFA; automated compliance verification; granular auditing

| Item | Status | Evidence |
|------|--------|----------|
| Encryption in transit | ✅ | HTTPS on Render; `Strict-Transport-Security` |
| Session auth (customer, supplier, EV dealer) | ✅ | bcrypt passwords; Flask sessions |
| Admin token auth | ✅ | `ADMIN_TOKEN` / `X-Admin-Token` |
| Granular auditing | ✅ | `security_events.py`, classified audit logs |
| Beta gate / invite tokens | ✅ | `beta_access.py` |
| MFA | 🔭 | Documented roadmap in `COMPLIANCE.md` |
| Full zero-trust (mTLS, per-request policy) | 🔭 | Beyond MVP scope |
| E2E encryption at rest (DB) | ⚠️ | Neon/Postgres provider encryption when `DATABASE_URL` set |

---

## 9. Distributed fault tolerance

> Distributed fault-tolerant architecture; auto-healing, load balancing, graceful degradation, continuous monitoring

| Item | Status | Evidence |
|------|--------|----------|
| Graceful degradation | ✅ | See §7 |
| Continuous monitoring | ✅ | `/health` + CI on every push |
| Load balancing / multi-instance | 🔭 | Gunicorn 2 workers; no LB config in repo |
| Distributed / auto-healing cluster | 🔭 | Single Render web service |

---

## 10. FHIR & HIPAA integration

> End-to-end FHIR system integration; automated compliance checks; interoperability with external FHIR servers; HIPAA-ready logging, encryption, access control

| Item | Status | Evidence |
|------|--------|----------|
| FHIR server / clinical resources | 🔭 | **Not applicable** — solar leads, not clinical PHI |
| Interop with external FHIR servers | 🔭 | N/A for product domain |
| HIPAA-ready logging & access control | ⚠️ | **PII layer** at appropriate level: `compliance.py`, audit, redaction, retention policy |
| Automated compliance checks | ✅ | `tests/test_compliance.py`, `tests/test_anomaly_detection.py` |
| Encryption & session hardening | ✅ | TLS, secure cookies in prod (`app.py`) |

**Honest scope:** Criterion 10 is met via **privacy-aware lead handling**, not a FHIR stack. Clinical PHI is never collected.

---

## Summary scorecard

| Criterion | MVP fit |
|-----------|---------|
| 1. Automated setup | ✅ Strong |
| 2. Testing | ✅ Strong |
| 3. Config / deploy | ⚠️ Strong locally; Render secrets manual |
| 4. Logging / anomaly | ⚠️ Core patterns; no central SIEM |
| 5. Microservices | 🔭 Monolith by design |
| 6. Security pipelines | ✅ Strong for student project |
| 7. Fault tolerance | ⚠️ Retry + degrade; not self-healing cluster |
| 8. Zero-trust | ⚠️ Auth + audit; no MFA |
| 9. Distributed HA | 🔭 Single-node deploy |
| 10. FHIR / HIPAA | ⚠️ PII patterns only; no FHIR |

---

## Quick commands

```bash
# Windows
SETUP_DEV.bat
RUN_CI_LOCAL.bat
pytest tests/ -q --cov

# macOS / Linux
./setup.sh
pre-commit run --all-files
```

## Related docs

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [COMPLIANCE.md](./COMPLIANCE.md)
- [DEPLOYMENT.md](./DEPLOYMENT.md)
- [BACKLOG.md](./BACKLOG.md)
