"""Extended platform features: readiness, scenarios, matching, decision report."""

from __future__ import annotations

QUOTE_QUALITY_CHECKLIST = [
    "Panel make, model, and quantity",
    "Inverter make and model",
    "Battery make and usable capacity (kWh)",
    "Installation scope (roof, electrical, scaffolding)",
    "Grid registration / Marktstammdatenregister support",
    "Warranty terms (panels, inverter, battery, workmanship)",
    "Estimated timeline from contract to commissioning",
    "VAT treatment and what is included vs excluded",
    "Maintenance and monitoring provisions",
]

SUPPLIER_VERIFICATION_ITEMS = [
    {"id": "identity", "label": "Identity verified", "description": "Company registration and contact details checked"},
    {"id": "insurance", "label": "Insurance verified", "description": "Public liability and professional indemnity on file"},
    {"id": "certifications", "label": "Certifications checked", "description": "Relevant electrical and solar certifications reviewed"},
    {"id": "installations", "label": "Recent installations", "description": "Portfolio of completed projects in the last 24 months"},
    {"id": "response_time", "label": "Typical response time", "description": "Median first response to quote requests"},
    {"id": "quote_completeness", "label": "Quote completeness score", "description": "How often quotes include all checklist items"},
    {"id": "ratings", "label": "Customer rating history", "description": "Verified reviews from completed installations"},
]

QUOTE_STATUS_STEPS = [
    {"id": "received", "label": "Request received", "label_key": "quote.status.received"},
    {"id": "matched", "label": "Suppliers matched", "label_key": "quote.status.matched"},
    {"id": "viewed", "label": "Supplier viewed your request", "label_key": "quote.status.viewed"},
    {"id": "quote_expected", "label": "Quote expected", "label_key": "quote.status.quote_expected"},
    {"id": "quote_received", "label": "Quote received", "label_key": "quote.status.quote_received"},
    {"id": "appointment", "label": "Appointment scheduled", "label_key": "quote.status.appointment"},
    {"id": "chosen", "label": "Installer chosen", "label_key": "quote.status.chosen"},
]

LEAD_TIERS = {
    "basic": {"label": "Basic", "description": "Postcode and estimated electricity use"},
    "qualified": {"label": "Qualified", "description": "Roof details, ownership, budget, timing, and contact preference"},
    "quote_ready": {"label": "Quote-ready", "description": "Detailed consumption profile, roof info, and desired system type"},
    "survey_ready": {"label": "Survey-ready", "description": "Roof dimensions, shading notes, and electrical details"},
}

HOUSEHOLD_LOADS = [
    {"key": "has_heat_pump", "label": "Heat pump", "icon": "🌡️", "load_kwh_add": 3500},
    {"key": "has_ev", "label": "EV (current)", "icon": "🚗", "load_kwh_add": 2500},
    {"key": "planned_ev", "label": "EV planned", "icon": "🔌", "load_kwh_add": 2000},
    {"key": "has_electric_water_heater", "label": "Electric hot water", "icon": "🚿", "load_kwh_add": 1800},
    {"key": "has_pool", "label": "Pool", "icon": "🏊", "load_kwh_add": 1200},
    {"key": "has_home_office", "label": "Home office", "icon": "💻", "load_kwh_add": 800},
    {"key": "has_ac", "label": "Air conditioning", "icon": "❄️", "load_kwh_add": 1500},
    {"key": "high_daytime_use", "label": "High daytime use", "icon": "☀️", "load_kwh_add": 0, "self_consumption_boost": 0.08},
    {"key": "planned_extension", "label": "Planned extension/renovation", "icon": "🏗️", "load_kwh_add": 1000},
]


def _inp_flag(inp, key: str) -> bool:
    return bool(getattr(inp, key, False))


from ev_profile import estimate_ev_annual_kwh
from heat_pump_profile import estimate_hp_annual_kwh, heat_goals_active


def build_household_energy_profile(inp, annual_kwh: float) -> dict:
    active = []
    added_kwh = 0
    self_consumption_boost = 0.0
    ev_precise = float(getattr(inp, "ev_annual_km", 0) or 0) > 0 and "ev_charging" in (getattr(inp, "goals", None) or [])
    ev_precise_kwh = estimate_ev_annual_kwh(inp) if ev_precise else 0
    hp_precise = heat_goals_active(getattr(inp, "goals", None)) and (
        float(getattr(inp, "hp_annual_heat_kwh", 0) or 0) > 0
        or float(getattr(inp, "hp_heated_area_m2", 0) or 0) > 0
        or bool(getattr(inp, "hp_status", ""))
    )
    hp_precise_kwh = estimate_hp_annual_kwh(inp) if hp_precise else 0

    for load in HOUSEHOLD_LOADS:
        if load["key"] in ("has_ev", "planned_ev") and ev_precise:
            continue
        if load["key"] == "has_heat_pump" and hp_precise:
            continue
        if load["key"] == "has_electric_water_heater" and getattr(inp, "hp_type", "") == "water_heater":
            continue
        if _inp_flag(inp, load["key"]):
            active.append({
                "key": load["key"],
                "label": load["label"],
                "icon": load["icon"],
                "estimated_annual_kwh": load.get("load_kwh_add", 0),
            })
            added_kwh += load.get("load_kwh_add", 0)
            self_consumption_boost += load.get("self_consumption_boost", 0)

    if ev_precise and ev_precise_kwh > 0:
        active.append({
            "key": "ev_charging",
            "label": "EV charging (profiled)",
            "icon": "⚡",
            "estimated_annual_kwh": ev_precise_kwh,
        })
        added_kwh += ev_precise_kwh

    if hp_precise and hp_precise_kwh > 0:
        active.append({
            "key": "heat_pump_profiled",
            "label": "Heat pump load (profiled)",
            "icon": "🌡️",
            "estimated_annual_kwh": hp_precise_kwh,
        })
        if getattr(inp, "hp_status", "") in ("planning", "replacing_fossil"):
            added_kwh += round(hp_precise_kwh * 0.85)

    adjusted_kwh = annual_kwh + added_kwh
    battery_hint = "Standard sizing"
    if any(_inp_flag(inp, k) for k in ("has_ev", "planned_ev", "has_heat_pump")) or ev_precise:
        battery_hint = "Consider larger battery or smart load shifting for EV/heat pump"
    if _inp_flag(inp, "high_daytime_use"):
        battery_hint = "High daytime use – battery may be smaller; PV self-consumption likely higher"
    if getattr(inp, "ev_charging_priority", "") == "cheapest":
        battery_hint = "Cheapest charging priority — battery optional; focus on self-consumption and tariffs"
    if getattr(inp, "ev_charging_priority", "") == "fastest":
        battery_hint = "Fast charging priority — sized wallbox first; battery optional"
    if getattr(inp, "hp_priority", "") == "solar_led":
        battery_hint = "Solar-led heating — smart controls and optional battery improve evening comfort"
    if getattr(inp, "hp_priority", "") == "backup":
        battery_hint = "Backup heating priority — larger battery and hybrid inverter recommended"

    return {
        "base_annual_kwh": round(annual_kwh),
        "adjusted_annual_kwh": round(adjusted_kwh),
        "active_loads": active,
        "self_consumption_boost": round(min(0.15, self_consumption_boost), 2),
        "battery_sizing_note": battery_hint,
        "lead_value_note": "Detailed load profile improves installer quotes" if len(active) >= 2 else "Add more load details for better quotes",
    }


def calculate_readiness_score(inp, solar_viable: bool, adjusted_yield: float, system_kwp: float, annual_kwh: float, financials: dict) -> dict:
    score = 50
    reasons = []

    if not solar_viable:
        return {
            "score": 25,
            "level": "not_ideal",
            "label": "Not ideal yet",
            "summary": "Rooftop solar may not be viable for your housing situation – see alternative paths below.",
            "factors": [{"factor": "Housing type", "impact": "negative", "detail": "Limited or no rooftop access"}],
        }

    roof_scores = {"pitched_south": 18, "pitched_east_west": 14, "flat": 12, "metal": 13, "tile": 13, "slate": 12, "pitched_north": 4, "unknown": 8}
    rs = roof_scores.get(inp.roof_type, 8)
    score += rs - 10
    reasons.append({"factor": "Roof orientation", "impact": "positive" if rs >= 12 else "negative",
                    "detail": f"{inp.roof_type.replace('_', ' ').title()} – {'good' if rs >= 12 else 'suboptimal'} solar yield"})

    if inp.shading == "none":
        score += 10
        reasons.append({"factor": "Shading", "impact": "positive", "detail": "No significant shading reported"})
    elif inp.shading == "partial":
        score += 2
        reasons.append({"factor": "Shading", "impact": "neutral", "detail": "Partial shading – site survey recommended"})
    elif inp.shading == "significant":
        score -= 12
        reasons.append({"factor": "Shading", "impact": "negative", "detail": "Significant shading reduces output"})

    if annual_kwh >= 2500:
        score += 8
        reasons.append({"factor": "Usage pattern", "impact": "positive", "detail": f"~{annual_kwh:,.0f} kWh/year – enough load to justify PV"})
    else:
        score -= 5
        reasons.append({"factor": "Usage pattern", "impact": "negative", "detail": "Low consumption – economics may be weaker"})

    if adjusted_yield >= 900:
        score += 10
        reasons.append({"factor": "Location solar resource", "impact": "positive", "detail": f"~{adjusted_yield:.0f} kWh/kWp/year expected"})
    elif adjusted_yield < 750:
        score -= 8
        reasons.append({"factor": "Location solar resource", "impact": "negative", "detail": "Below-average solar resource for the site"})

    payback = financials.get("payback_years", 99)
    if payback < 10:
        score += 10
        reasons.append({"factor": "Budget & payback", "impact": "positive", "detail": f"Estimated payback ~{payback} years"})
    elif payback > 16:
        score -= 6
        reasons.append({"factor": "Budget & payback", "impact": "negative", "detail": f"Long payback (~{payback} years) at current assumptions"})

    sc_pct = financials.get("self_consumption_ratio", 35)
    if sc_pct <= 1:
        sc_pct = sc_pct * 100
    reasons.append({"factor": "Self-consumption potential", "impact": "positive" if sc_pct >= 40 else "neutral",
                    "detail": f"~{sc_pct:.0f}% of generation used on-site (estimate)"})

    if "backup" in (inp.goals or []):
        reasons.append({"factor": "Backup need", "impact": "neutral", "detail": "Backup goal requires battery + hybrid inverter – higher cost"})

    if not inp.roof_area_m2 and not inp.has_roof_photos:
        score -= 8
        reasons.append({"factor": "Site data", "impact": "negative", "detail": "Roof dimensions or photos not provided – survey needed"})
    elif inp.has_roof_photos:
        score += 5
        reasons.append({"factor": "Site data", "impact": "positive", "detail": "Roof photos available for installer review"})

    score = max(0, min(100, score))
    if score >= 80:
        level, label = "excellent", "Excellent candidate"
    elif score >= 62:
        level, label = "good", "Good candidate"
    elif score >= 42:
        level, label = "survey", "Needs roof survey"
    else:
        level, label = "not_ideal", "Not ideal yet"

    return {
        "score": score,
        "level": level,
        "label": label,
        "summary": f"{label} for rooftop solar based on your inputs — indicative site readiness, not an installation guarantee.",
        "score_label": "Site readiness index",
        "factors": reasons,
        "self_consumption_pct": round(sc_pct),
    }


def calculate_lead_qualification_tier(inp) -> dict:
    score = 0
    if inp.location_name or (inp.latitude and inp.longitude):
        score += 1
    if inp.monthly_bill_eur or inp.monthly_kwh:
        score += 1
    if inp.roof_type and inp.roof_type != "unknown":
        score += 1
    if inp.roof_area_m2 > 0:
        score += 1
    if inp.budget_eur > 0:
        score += 1
    if inp.installation_timeframe and inp.installation_timeframe != "not_sure":
        score += 1
    if inp.has_roof_photos:
        score += 1
    if inp.shading in ("none", "partial"):
        score += 1
    loads = sum(1 for load in HOUSEHOLD_LOADS if _inp_flag(inp, load["key"]))
    if loads >= 2:
        score += 1

    if score >= 8:
        tier = "survey_ready"
    elif score >= 6:
        tier = "quote_ready"
    elif score >= 4:
        tier = "qualified"
    else:
        tier = "basic"

    info = LEAD_TIERS[tier]
    return {
        "tier": tier,
        "label": info["label"],
        "description": info["description"],
        "score": score,
        "max_score": 9,
        "supplier_value": {"basic": "€8/lead", "qualified": "€12/lead", "quote_ready": "€18/lead", "survey_ready": "€25/lead"}.get(tier, "€8/lead"),
    }


def build_price_scenarios(annual_savings: float, upfront: float, payback: float) -> dict:
    scenarios = []
    for key, label, esc, note in [
        ("stable", "Prices stay stable", 0.02, "Low escalation – savings grow slowly"),
        ("expected", "Prices rise moderately", 0.04, "Central assumption (4%/year)"),
        ("faster", "Prices rise faster", 0.07, "Higher inflation / tariff shocks"),
    ]:
        ten_yr = sum(annual_savings * ((1 + esc) ** (y - 1)) for y in range(1, 11)) - upfront
        if annual_savings > 0:
            pb = round(upfront / annual_savings, 1)
            if esc > 0.04:
                pb = round(upfront / (annual_savings * 1.08), 1)
        elif payback and payback > 0:
            pb = round(payback, 1)
        else:
            pb = 99
        scenarios.append({
            "id": key,
            "label": label,
            "escalation_pct": round(esc * 100, 1),
            "payback_years": pb,
            "ten_year_net_eur": round(ten_yr),
            "note": note,
        })
    return {
        "scenarios": scenarios,
        "disclaimer": "Illustrative scenarios only – actual electricity prices are uncertain.",
        "default_id": "expected",
    }


def budget_first_recommendation(inp, adjusted_yield: float, cost_per_kwp: float = 1450) -> dict | None:
    budget = inp.budget_eur
    if budget <= 0 or not getattr(inp, "budget_first_mode", False):
        return None

    batt_reserve = 0.35 if any(g in (inp.goals or []) for g in ("backup", "ev_charging")) else 0
    pv_budget = budget * (1 - batt_reserve)
    max_kwp = max(2.0, min(40.0, round(pv_budget / cost_per_kwp, 1)))
    annual_prod = round(max_kwp * adjusted_yield)
    annual_kwh = max(2000, getattr(inp, "_adjusted_annual_kwh", 4000))

    return {
        "budget_eur": budget,
        "max_system_kwp": max_kwp,
        "estimated_annual_production_kwh": annual_prod,
        "covers_consumption_pct": round(min(100, annual_prod / annual_kwh * 100)),
        "financing_note": "Consider loan if budget is below typical system cost – see financing comparison below.",
        "summary": f"With €{budget:,.0f} available, up to ~{max_kwp} kWp may fit (PV only estimate, before installation extras).",
    }


def build_financing_comparison(upfront: float, monthly_savings: float, annual_savings: float) -> dict:
    from financial_model import calculate_financing, FINANCING_TERM_YEARS, FINANCING_RATE_APR, DISCLAIMER

    fin = calculate_financing(upfront)
    monthly_payment = fin["monthly_payment"]
    net_monthly = round(monthly_savings - monthly_payment, 2)
    return {
        "cash": {
            "label": "Cash purchase",
            "upfront": round(upfront),
            "monthly_payment": 0,
            "monthly_savings_offset": round(monthly_savings, 2),
            "net_monthly_cash": round(monthly_savings, 2),
            "total_cost_10yr": round(upfront),
        },
        "loan": {
            "label": f"Loan ({fin['term_years']} yr, {fin['apr_pct']}% APR illustrative)",
            "upfront": 0,
            "monthly_payment": monthly_payment,
            "monthly_savings_offset": round(monthly_savings, 2),
            "net_monthly_cash": net_monthly,
            "total_cost_10yr": fin["total_paid"],
            "total_interest": fin["total_interest"],
        },
        "disclaimer": f"Illustrative financing only – not an offer of credit. {DISCLAIMER}",
    }


def build_why_explanation(inp, system_kwp: float, battery_kwh: float, annual_kwh: float, annual_production: float, goals: list) -> str:
    goal_txt = ", ".join(g.replace("_", " ") for g in goals[:3]) if goals else "lower electricity bill"
    roof = inp.roof_type.replace("_", " ")
    batt = f" A {battery_kwh} kWh battery is included for your goals." if battery_kwh > 0 else " We have not assumed a battery unless your goal requires it."
    return (
        f"We recommend a {system_kwp} kWp system because your estimated consumption is about {annual_kwh:,.0f} kWh/year, "
        f"your roof profile ({roof}) appears suitable for roughly {annual_production:,.0f} kWh/year of production, "
        f"and this size balances self-consumption with export for your goals ({goal_txt}).{batt}"
    )


def build_energy_roadmap(inp, system_kwp: float, goals: list) -> list:
    steps = []
    if system_kwp > 0:
        steps.append({"phase": "Now", "title": "Rooftop PV", "detail": f"Start with ~{system_kwp} kWp as assessed", "priority": "high"})
    if not _inp_flag(inp, "has_ev") and "ev_charging" not in goals:
        steps.append({"phase": "Next", "title": "EV charger", "detail": "Add smart wallbox when you switch to an EV", "priority": "medium"})
    if not _inp_flag(inp, "has_heat_pump"):
        steps.append({"phase": "Next", "title": "Heat pump", "detail": "Pair with PV for lower heating running costs", "priority": "medium"})
    steps.append({"phase": "Later", "title": "Add battery", "detail": "Retrofit storage if backup or evening use becomes important", "priority": "low"})
    steps.append({"phase": "Later", "title": "Smart tariff", "detail": "Dynamic tariff to shift loads to cheap/solar hours", "priority": "low"})
    if inp.roof_area_m2 and system_kwp < 15:
        steps.append({"phase": "Later", "title": "Expand PV", "detail": "Additional roof area may allow system expansion", "priority": "low"})
    return steps


def supplier_verification_display(supplier: dict) -> list:
    verified = supplier.get("verified", False)
    plan = supplier.get("plan", "basic")
    items = []
    for item in SUPPLIER_VERIFICATION_ITEMS:
        status = "pending"
        if item["id"] == "identity" and supplier.get("company_name"):
            status = "verified" if verified else "submitted"
        elif item["id"] == "insurance" and supplier.get("insurance_verified"):
            status = "verified"
        elif item["id"] == "certifications" and supplier.get("certifications"):
            status = "verified" if verified else "submitted"
        elif item["id"] == "installations" and supplier.get("reviews_count", 0) > 0:
            status = "verified"
        elif item["id"] == "response_time":
            status = "verified" if plan in ("verified", "premium") else "pending"
        elif item["id"] == "quote_completeness":
            status = "verified" if plan == "premium" else "pending"
        elif item["id"] == "ratings":
            rating = supplier.get("rating")
            if rating is not None and float(rating) >= 4:
                status = "verified"
        items.append({**item, "status": status})
    return items


def calculate_supplier_fit(supplier: dict, inp, recommendation: dict) -> dict:
    score = 50
    reasons = []
    postcode = (inp.location_name or "")[:5] if hasattr(inp, "location_name") else ""
    postcodes = supplier.get("locations_served", [])
    if postcode and any(postcode.startswith(p[:5]) or p.startswith(postcode) for p in postcodes):
        score += 25
        reasons.append("Serves your postcode area")
    elif supplier.get("regions"):
        score += 10
        reasons.append("Regional coverage may include your area")

    goals = inp.goals if hasattr(inp, "goals") else recommendation.get("goals", [])
    if "business" in goals and supplier.get("commercial_available"):
        score += 15
        reasons.append("Commercial installation capability")
    if "farming" in goals and supplier.get("agricultural_available"):
        score += 15
        reasons.append("Agricultural / Agri-PV experience")

    if recommendation.get("battery_kwh", 0) > 0 and supplier.get("battery_capable", True):
        score += 10
        reasons.append("Battery installation offered")

    budget = getattr(inp, "budget_eur", 0) or 0
    upfront = recommendation.get("financials", {}).get("system_cost_typical", 15000)
    if budget > 0 and upfront <= budget * 1.15:
        score += 8
        reasons.append("Typical system cost within your budget range")

    plan = supplier.get("plan", "basic")
    if plan == "premium":
        score += 8
    elif plan == "verified":
        score += 5

    if supplier.get("verified"):
        score += 10
        reasons.append("Verified supplier")

    avail = supplier.get("earliest_install_weeks")
    if avail is not None and avail <= 8:
        score += 5
        reasons.append(f"Installation from ~{avail} weeks")

    return {
        "score": min(100, score),
        "label": "Strong fit" if score >= 75 else "Good fit" if score >= 55 else "Possible fit",
        "reasons": reasons[:5],
    }


def match_suppliers(suppliers: list, inp, recommendation: dict, limit: int = 5) -> list:
    scored = []
    for s in suppliers:
        fit = calculate_supplier_fit(s, inp, recommendation)
        scored.append({**s, "fit_score": fit["score"], "fit_label": fit["label"], "fit_reasons": fit["reasons"],
                       "verification": supplier_verification_display(s)})
    scored.sort(key=lambda x: x["fit_score"], reverse=True)
    return scored[:limit]


def build_decision_report(inp, recommendation: dict) -> dict:
    readiness = recommendation.get("readiness", {})
    pkgs = recommendation.get("three_packages", {}).get("packages", {})
    primary = recommendation.get("selected_package") or pkgs.get("best_value", {})
    return {
        "title": "Solar Decision Report",
        "sections": [
            {"id": "summary", "title": "Property & energy summary", "included": True},
            {"id": "readiness", "title": "Solar suitability score", "included": True},
            {"id": "packages", "title": "Recommended system options", "included": True},
            {"id": "scenarios", "title": "Cost & savings scenarios", "included": True},
            {"id": "payback", "title": "Payback range", "included": True},
            {"id": "co2", "title": "CO₂ estimate", "included": True},
            {"id": "battery", "title": "Battery comparison", "included": bool(recommendation.get("battery_comparison"))},
            {"id": "assumptions", "title": "Assumptions & uncertainty", "included": True},
            {"id": "site_gaps", "title": "Site information still needed", "included": True},
            {"id": "installer_brief", "title": "Installer-ready project brief", "included": True},
            {"id": "quote_checklist", "title": "Quote comparison checklist", "included": True},
            {"id": "timeline", "title": "Next-step timeline", "included": True},
        ],
        "site_gaps": recommendation.get("confidence", {}).get("missing_data", []),
        "quote_checklist": QUOTE_QUALITY_CHECKLIST,
        "primary_package_id": primary.get("id", "best_value"),
    }


def build_quote_status(quote: dict) -> list:
    status = quote.get("status", "received")
    order = [s["id"] for s in QUOTE_STATUS_STEPS]
    try:
        idx = order.index(status)
    except ValueError:
        idx = 0
    return [{"id": s["id"], "label": s["label"], "label_key": s.get("label_key", ""), "done": i <= idx, "current": i == idx} for i, s in enumerate(QUOTE_STATUS_STEPS)]
