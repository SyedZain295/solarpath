# Reviewer / coach handoff

Use these links to test **Solar Path** without any GitHub setup or beta password.

## Primary — public app (use this)

| What | URL |
|------|-----|
| **Calculator** | https://solar-path.onrender.com/calculator |
| **Home** | https://solar-path.onrender.com/ |
| **Demo (sample results)** | https://solar-path.onrender.com/demo |
| **Installers** | https://solar-path.onrender.com/suppliers |
| **Health check** | https://solar-path.onrender.com/health |

No login required when `"beta_gate": false` on `/health`.

First visit may take ~30–60 s while Render wakes the free-tier service.

### If you still see a beta login page

1. Open **https://solar-path.onrender.com/health** — confirm `"beta_gate": false` and `"demo_mode": true`.
2. Try an **incognito/private** window (clears any old session).
3. **Fallback invite links** (work even if closed beta is re-enabled):
   - Calculator: https://solar-path.onrender.com/calculator?invite=solarpath-beta-2026
   - Home: https://solar-path.onrender.com/?invite=solarpath-beta-2026

## CI proof (automated tests)

https://github.com/SyedZain295/solarpath/actions/runs/28906946912

## Course evidence

- Rubric mapping: https://github.com/SyedZain295/solarpath/blob/main/docs/RUBRIC.md
- Compliance / enterprise controls: https://github.com/SyedZain295/solarpath/blob/main/docs/COMPLIANCE.md
- Repository: https://github.com/SyedZain295/solarpath

## What **not** to use for review

- **Codespaces port URLs** (`localhost:5000`, `*.app.github.dev`) — require GitHub login + port consent; not shareable for external review
- **`?skip_warning=true`** — does not bypass GitHub’s access port warning
- **Personal `GITHUB_TOKEN`** — never share

## Copy-paste message

```
Please review Solar Path here (public, no GitHub login or beta password):

  https://solar-path.onrender.com/calculator

If you see a beta login screen, use this invite link instead:
  https://solar-path.onrender.com/calculator?invite=solarpath-beta-2026

Verify public mode: https://solar-path.onrender.com/health  (beta_gate should be false)

CI (all passing):
  https://github.com/SyedZain295/solarpath/actions/runs/28906946912
```
