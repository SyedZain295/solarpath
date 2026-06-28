# Trust, clarity & release priorities

This doc maps external product review feedback to Solar Path implementation status.

## Keep (already strong)

- "What you give up" under each package
- Feed-in vs self-consumption savings split
- Non-guaranteed returns disclaimer
- Assumptions & uncertainty panel
- Roof-photo request
- Quote-quality checklist
- Grid-registration / legal checklist
- Finance marked illustrative (not a credit offer)

## Priority fixes (implemented / in progress)

| Priority | Item | Status |
|----------|------|--------|
| 1 | Budget ≤ Balanced pricing | Budget package picks **lowest-cost panel/inverter mix** (not fixed low-Wp SKU); backup + EV tests |
| 2 | 100/100 score certainty | **Digital suitability check** / information completeness index; capped at 78 (no photos) or 88 (with photos); on-site survey disclaimer |
| 3 | Roof area vs demand | Explicit demand note + **next steps** (garage, balcony, expansion, etc.) when roof caps size |
| 4 | Define verified / quality / reliability | Glossary + softened supplier framework copy; **Registered partner** not “Verified”; quote CTA without “verified” |
| 5 | Faster first estimate | `/estimate` → pre-fills calculator (60 sec entry) |
| 6 | Conditional EV questions | EV step when EV charging goal selected |
| 6b | Conditional heat-pump questions | Heat step when space heating / hot water goal selected |
| 7 | PDF hardening | Binding-quote banner, data source, page break, table KeepTogether, optional contact in PDF |
| 8 | Mobile + quote handoff | Manual QA before supplier demo |

## Business positioning (no code change)

Solar Path is a **decision + conversion workflow**, not generic AI advice. Early GTM: **white-label intake/report for local installers** rather than paid consumer acquisition at scale.

## PDF QA checklist before release

- [ ] Download PDF on desktop Chrome, Firefox, Safari
- [ ] Download on mobile (share/save)
- [ ] Every page has visible content (no blank pages)
- [ ] Package table does not split mid-row
- [ ] Yellow **NOT A BINDING QUOTE** banner on page 1
- [ ] Date + PVGIS/estimate data source shown
- [ ] Contact opt-in checkbox before sharing with installers

## URLs

- Quick estimate: `/estimate`
- Full calculator: `/calculator`
- Demo results: `/demo`
