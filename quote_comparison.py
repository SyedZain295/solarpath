"""Standard PV quote comparison — scoring, warnings, aligned rows."""

from __future__ import annotations

from typing import Any

CHECK_FIELDS = [
    {"key": "includes_installation", "label": "Installation labour", "weight": 2},
    {"key": "includes_mounting", "label": "Mounting / racking", "weight": 1},
    {"key": "includes_scaffolding", "label": "Scaffolding", "weight": 1},
    {"key": "includes_electrician", "label": "Electrical work", "weight": 2},
    {"key": "includes_grid_registration", "label": "Grid registration", "weight": 2},
    {"key": "includes_mastr", "label": "MaStR registration", "weight": 2},
    {"key": "includes_battery", "label": "Battery included", "weight": 1},
    {"key": "includes_monitoring", "label": "Monitoring", "weight": 1},
    {"key": "includes_optimizer", "label": "Optimizers / MLPE", "weight": 1},
    {"key": "includes_removal", "label": "Removal / disposal", "weight": 1},
]

CPK_LOW_WARN = 1200
CPK_HIGH_WARN = 3200


def normalize_quote(raw: dict) -> dict:
    checks = {f["key"]: bool(raw.get(f["key"]) or (raw.get("checks") or {}).get(f["key"])) for f in CHECK_FIELDS}
    total = float(raw.get("total_eur") or 0)
    kwp = float(raw.get("kwp") or 0)
    completeness = sum(f["weight"] for f in CHECK_FIELDS if checks.get(f["key"]))
    max_c = sum(f["weight"] for f in CHECK_FIELDS)
    missing = [f["label"] for f in CHECK_FIELDS if not checks.get(f["key"])]
    production = raw.get("production_kwh")
    return {
        "installer": (raw.get("installer") or "—").strip() or "—",
        "total_eur": round(total) if total else 0,
        "kwp": round(kwp, 2) if kwp else None,
        "cost_per_kwp": round(total / kwp) if total and kwp else raw.get("cost_per_kwp"),
        "production_kwh": int(production) if production else None,
        "panel_count": raw.get("panel_count"),
        "panel_wp": raw.get("panel_wp"),
        "panels": raw.get("panels") or "—",
        "inverter": raw.get("inverter") or "—",
        "inverter_kw": raw.get("inverter_kw"),
        "battery_kwh": float(raw.get("battery_kwh") or 0),
        "warranty_years": raw.get("warranty_years"),
        "validity_days": raw.get("validity_days"),
        "checks": checks,
        "completeness_pct": round(completeness / max_c * 100) if max_c else 0,
        "missing": missing,
        "notes": raw.get("notes") or "",
        "parse_confidence": raw.get("confidence"),
    }


def _warnings(q: dict, all_quotes: list[dict]) -> list[dict]:
    warns: list[dict] = []
    cpk = q.get("cost_per_kwp")
    if cpk and cpk < CPK_LOW_WARN:
        warns.append({"level": "high", "code": "cpk_low", "message": f"€/kWp unusually low ({cpk:,} €) — check what's excluded."})
    if cpk and cpk > CPK_HIGH_WARN:
        warns.append({"level": "medium", "code": "cpk_high", "message": f"€/kWp high ({cpk:,} €) — verify premium components justify cost."})
    if not q["checks"].get("includes_grid_registration"):
        warns.append({"level": "high", "code": "no_grid", "message": "Grid-operator registration not stated — often €500–1,500 extra."})
    if not q["checks"].get("includes_mastr"):
        warns.append({"level": "medium", "code": "no_mastr", "message": "MaStR registration not stated — required in Germany."})
    if not q["checks"].get("includes_electrician"):
        warns.append({"level": "medium", "code": "no_electrical", "message": "Electrical / meter cabinet work not clearly included."})
    if q.get("warranty_years") and q["warranty_years"] < 10:
        warns.append({"level": "medium", "code": "short_warranty", "message": f"Module warranty only {q['warranty_years']} years — typical is 20–25."})
    if q.get("validity_days") and q["validity_days"] < 14:
        warns.append({"level": "low", "code": "short_validity", "message": f"Quote valid only {q['validity_days']} days — limited time to decide."})
    if q.get("kwp") and q.get("inverter_kw") and q["inverter_kw"] < q["kwp"] * 0.65:
        warns.append({"level": "high", "code": "inverter_undersized", "message": "Inverter may be undersized vs DC capacity — confirm AC/DC ratio."})
    if q["completeness_pct"] < 50:
        warns.append({"level": "medium", "code": "incomplete", "message": "Many standard line items not mentioned — ask for itemised quote."})
    totals = [x["total_eur"] for x in all_quotes if x.get("total_eur")]
    if len(totals) >= 2 and q.get("total_eur"):
        median = sorted(totals)[len(totals) // 2]
        if q["total_eur"] < median * 0.75:
            warns.append({"level": "high", "code": "price_outlier_low", "message": "Total cost much lower than other quotes — verify scope matches."})
    return warns


def _value_score(q: dict, min_cpk: int | None) -> int:
    score = 50
    if q.get("cost_per_kwp") and min_cpk:
        score += max(0, 30 - round((q["cost_per_kwp"] - min_cpk) / min_cpk * 100))
    score += round(q["completeness_pct"] * 0.2)
    if q.get("production_kwh") and q.get("kwp"):
        score += 5
    if (q.get("warranty_years") or 0) >= 20:
        score += 5
    if len(q.get("warnings") or []) == 0:
        score += 5
    elif any(w["level"] == "high" for w in q.get("warnings") or []):
        score -= 10
    return max(0, min(100, round(score)))


def compare_quotes(raw_quotes: list[dict]) -> dict[str, Any]:
    quotes = [normalize_quote(q) for q in raw_quotes if q.get("total_eur") or (q.get("installer") and q.get("installer") != "—")]
    if not quotes:
        return {"quotes": [], "error": "No quotes to compare"}

    for q in quotes:
        q["warnings"] = _warnings(q, quotes)

    cpks = [q["cost_per_kwp"] for q in quotes if q.get("cost_per_kwp")]
    min_cpk = min(cpks) if cpks else None
    for q in quotes:
        q["value_score"] = _value_score(q, min_cpk)

    best_value_idx = max(range(len(quotes)), key=lambda i: quotes[i]["value_score"])
    lowest_cpk_idx = min(
        (i for i, q in enumerate(quotes) if q.get("cost_per_kwp")),
        key=lambda i: quotes[i]["cost_per_kwp"],
        default=best_value_idx,
    )

    rows = [
        {"key": "total_eur", "label": "Total cost", "values": [q["total_eur"] for q in quotes]},
        {"key": "cost_per_kwp", "label": "€/kWp", "values": [q.get("cost_per_kwp") for q in quotes], "highlight": "lowest"},
        {"key": "kwp", "label": "System size (kWp)", "values": [q.get("kwp") for q in quotes]},
        {"key": "panels", "label": "Panel model", "values": [
            f"{q['panel_count']}× {q['panels']}" if q.get("panel_count") else q["panels"] for q in quotes
        ]},
        {"key": "inverter", "label": "Inverter", "values": [
            f"{q['inverter']}" + (f" ({q['inverter_kw']} kW)" if q.get("inverter_kw") else "") for q in quotes
        ]},
        {"key": "battery_kwh", "label": "Battery", "values": [q["battery_kwh"] or None for q in quotes]},
        {"key": "includes_mounting", "label": "Mounting", "values": [q["checks"].get("includes_mounting") for q in quotes], "bool": True},
        {"key": "includes_electrician", "label": "Electrical work", "values": [q["checks"].get("includes_electrician") for q in quotes], "bool": True},
        {"key": "includes_grid_registration", "label": "Grid registration", "values": [q["checks"].get("includes_grid_registration") for q in quotes], "bool": True},
        {"key": "includes_mastr", "label": "MaStR", "values": [q["checks"].get("includes_mastr") for q in quotes], "bool": True},
        {"key": "warranty_years", "label": "Warranty (yr)", "values": [q.get("warranty_years") for q in quotes]},
        {"key": "completeness_pct", "label": "Completeness", "values": [q["completeness_pct"] for q in quotes]},
        {"key": "value_score", "label": "Value score", "values": [q["value_score"] for q in quotes], "highlight": "highest"},
        {"key": "missing", "label": "Likely missing", "values": [", ".join(q["missing"][:4]) or "—" for q in quotes]},
    ]

    return {
        "quotes": quotes,
        "summary": {
            "count": len(quotes),
            "best_value_index": best_value_idx,
            "best_value_installer": quotes[best_value_idx]["installer"],
            "lowest_cpk_index": lowest_cpk_idx,
            "lowest_cpk_installer": quotes[lowest_cpk_idx]["installer"],
            "lowest_cpk": quotes[lowest_cpk_idx].get("cost_per_kwp"),
        },
        "rows": rows,
        "disclaimer": (
            "Comparison based on what you entered or parsed — not a contract review. "
            "Verify net/gross, VAT, and every line item with each installer before signing."
        ),
    }
