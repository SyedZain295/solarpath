# Enterprise compliance — Solar Path

Solar Path is a **solar lead-generation platform**, not a clinical EHR. It stores **contact PII** (email, phone, postcode) and **security audit** data. This document maps enterprise / HIPAA-adjacent controls to concrete code in the repo.

## Scope

| Data type | Examples | Classification |
|-----------|----------|----------------|
| Public marketing | Page copy, product catalog | `public` |
| Operational | PVGIS cache, supplier listings | `internal` |
| Lead / contact PII | Email, phone, postcode, bills | `pii` |
| Secrets | Passwords, tokens, API keys | `credential` |
| Security audit | Login success/failure, lockouts | `audit` |

Clinical **PHI** (diagnoses, MRNs, FHIR resources) is **not collected** — criterion 10 in the rubric uses privacy-aware patterns instead of a FHIR server.

## Implemented controls

| Control | Implementation |
|---------|----------------|
| PII minimization in logs | `compliance.py` — `sanitize_record`, `redact_value` |
| Structured audit trail | `logging_config.audit` + `security_events.py` |
| Data classification tags | `compliance_tags()` on every auth audit line |
| Retention policy (documented) | `RetentionPolicy` in `compliance.py` |
| Real-time auth anomaly detection | `anomaly_detection.py` — sliding-window lockout |
| Request correlation | `X-Request-ID` via `http_middleware.py` |
| Security headers + CSP (prod) | `http_middleware.py` |
| Encryption in transit | HTTPS on Render; `Strict-Transport-Security` |
| Secrets via env | `.env.example`, GitHub Codespaces secrets, Render dashboard |
| Dependency + SAST | `pip-audit`, CodeQL in CI |
| Session hardening (prod) | `SESSION_COOKIE_SECURE`, `SameSite=Lax` in `app.py` |

## Configuration

Optional anomaly thresholds (defaults shown):

```env
ANOMALY_WINDOW_SECONDS=300
ANOMALY_MAX_FAILURES=8
ANOMALY_BLOCK_SECONDS=900
```

## Production roadmap (multi-node)

- Centralized log aggregation (Datadog, CloudWatch, ELK)
- Redis-backed rate limiting across instances
- MFA for admin (`TOTP` — env-gated)
- Automated PII export/delete (GDPR Art. 15/17)
- WAF / bot management at edge

These are marked 🔭 in `docs/RUBRIC.md` where full infra is required.
