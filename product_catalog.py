"""Manual product catalog – Phase 1 MVP (no supplier APIs)."""

import json
import math
import os
from typing import Optional

ROOT = os.path.dirname(os.path.abspath(__file__))
CATALOG_FILE = os.path.join(ROOT, "data", "product_catalog.json")

# Module area + spacing allowance (m² per panel)
PANEL_AREA_WITH_SPACING_M2 = 2.0

STANDARD_KWP_SIZES = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30, 40, 50]

TIER_BY_PACKAGE = {
    "cheapest": "budget",
    "best_value": "balanced",
    "most_reliable": "premium",
}

SHADING_YIELD_FACTORS = {
    "none": 1.0,
    "partial": 0.92,
    "heavy": 0.80,
    "unknown": 0.97,
}

_catalog_cache: Optional[dict] = None
_catalog_mtime: float = 0


def load_catalog() -> dict:
    global _catalog_cache, _catalog_mtime
    try:
        mtime = os.path.getmtime(CATALOG_FILE)
    except OSError:
        return {"panels": [], "inverters": [], "batteries": [], "mounting": []}
    if _catalog_cache is None or mtime != _catalog_mtime:
        with open(CATALOG_FILE, encoding="utf-8") as fh:
            _catalog_cache = json.load(fh)
        _catalog_mtime = mtime
    return _catalog_cache


def save_catalog(catalog: dict) -> None:
    global _catalog_cache, _catalog_mtime
    with open(CATALOG_FILE, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, ensure_ascii=False, indent=2)
    _catalog_cache = catalog
    _catalog_mtime = os.path.getmtime(CATALOG_FILE)


def round_to_standard_kwp(raw_kwp: float) -> float:
    """Round up to a practical install size (e.g. 4.5 → 5 kWp)."""
    raw_kwp = max(2.0, raw_kwp)
    for size in STANDARD_KWP_SIZES:
        if size >= raw_kwp - 0.01:
            return float(size)
    return 50.0


def recommend_kwp_from_consumption(annual_kwh: float, specific_yield: float, goals: list | None = None) -> float:
    """
    Core MVP formula: required kWp ≈ annual electricity use ÷ specific yield (kWh/kWp/yr).
    Example: 4,500 kWh ÷ 1,000 = 4.5 → recommend 5 kWp.
    """
    if specific_yield <= 0:
        specific_yield = 950
    goals = goals or []
    if "hot_water" in goals and "lower_bill" not in goals:
        return 0.0

    raw = annual_kwh / specific_yield
    # Slight oversizing for backup / EV goals (still grounded in use ÷ yield)
    if "backup" in goals or "ev_charging" in goals:
        raw *= 1.08
    return round_to_standard_kwp(raw)


def max_kwp_from_roof_area(roof_area_m2: float, panel_wp: int = 430) -> Optional[float]:
    """Maximum DC capacity that fits on available roof area."""
    if roof_area_m2 <= 0:
        return None
    max_panels = max(1, math.floor(roof_area_m2 / PANEL_AREA_WITH_SPACING_M2))
    return round(max_panels * panel_wp / 1000, 2)


def apply_shading_factor(yield_kwh_kwp: float, shading: str) -> float:
    return yield_kwh_kwp * SHADING_YIELD_FACTORS.get(shading, 0.97)


def _panel_for_tier(tier: str, roof_type: str = "pitched_south") -> dict:
    panels = load_catalog()["panels"]
    if roof_type == "balcony" or "balcony" in roof_type:
        match = next((p for p in panels if p["tier"] == "balcony"), panels[0])
        return match
    for p in panels:
        if p["tier"] == tier:
            return p
    return panels[0]


def _panel_candidates_for_budget_package(roof_type: str) -> list:
    """Economy panels only — Budget package picks lowest installed cost, not a fixed SKU."""
    panels = load_catalog()["panels"]
    if roof_type == "balcony" or "balcony" in roof_type:
        return [next((p for p in panels if p["tier"] == "balcony"), panels[0])]
    return [p for p in panels if p.get("tier") in ("budget", "balanced")]


def _hardware_cost_estimate(
    num_panels: int,
    panel: dict,
    actual_kwp: float,
    inverter: dict,
    battery: Optional[dict],
    mounting: dict,
) -> int:
    panel_cost = num_panels * panel["price_eur"]
    inv_cost = inverter["price_eur"]
    batt_cost = battery["price_eur"] if battery else 0
    mount_cost = round(actual_kwp * mounting.get("price_per_kwp", 180))
    install_cost = round(actual_kwp * 350)
    cables_cost = round(actual_kwp * 90)
    return panel_cost + inv_cost + batt_cost + mount_cost + install_cost + cables_cost


def _pick_lowest_cost_panel_configuration(
    system_kwp: float,
    battery_kwh: float,
    backup_needed: bool,
    roof_type: str,
) -> tuple:
    """Return panel, counts, inverter, battery, tier with minimum hardware subtotal."""
    mounting = _mounting_for_roof(roof_type)
    best = None
    best_cost = float("inf")
    for candidate in _panel_candidates_for_budget_package(roof_type):
        num_panels = panel_count_for_kwp(system_kwp, candidate["power_wp"])
        actual_kwp = actual_system_kwp(num_panels, candidate["power_wp"])
        tier = candidate["tier"]
        inverter = _inverter_for_system(tier, actual_kwp, backup_needed, battery_kwh)
        battery = _battery_for_system(tier, battery_kwh, inverter)
        cost = _hardware_cost_estimate(num_panels, candidate, actual_kwp, inverter, battery, mounting)
        if cost < best_cost:
            best_cost = cost
            best = (candidate, num_panels, actual_kwp, inverter, battery, tier)
    if best is None:
        panel = _panel_for_tier("budget", roof_type)
        num_panels = panel_count_for_kwp(system_kwp, panel["power_wp"])
        actual_kwp = actual_system_kwp(num_panels, panel["power_wp"])
        inverter = _inverter_for_system("budget", actual_kwp, backup_needed, battery_kwh)
        battery = _battery_for_system("budget", battery_kwh, inverter)
        return panel, num_panels, actual_kwp, inverter, battery, "budget"
    return best


def _mounting_for_roof(roof_type: str) -> dict:
    mounting = load_catalog().get("mounting") or []
    if roof_type == "flat":
        key = "mount-flat"
    elif "balcony" in roof_type:
        key = "mount-balcony"
    elif roof_type == "ground_mount":
        key = "mount-ground"
    else:
        key = "mount-pitched"
    for m in mounting:
        if m["id"] == key:
            return m
    return mounting[0] if mounting else {"id": "mount-pitched", "name": "Mounting", "price_per_kwp": 180}


def _inverter_for_system(
    tier: str,
    system_kwp: float,
    backup_needed: bool,
    battery_kwh: float = 0,
) -> dict:
    inverters = sorted(load_catalog()["inverters"], key=lambda x: x["ac_power_kw"])
    tier_order = {"budget": 0, "balanced": 1, "premium": 2}
    candidates = [i for i in inverters if tier_order.get(i["tier"], 0) >= tier_order.get(tier, 0)]
    if not candidates:
        candidates = inverters

    # Battery needs a hybrid inverter with compatible battery list
    if battery_kwh > 0:
        hybrid = [i for i in candidates if i.get("hybrid") and i.get("compatible_battery_ids")]
        if hybrid:
            candidates = hybrid

    for inv in candidates:
        if inv["ac_power_kw"] < system_kwp * 0.85:
            continue
        if inv.get("dc_max_kw", 99) < system_kwp * 0.95:
            continue
        if backup_needed and not inv.get("backup_capable"):
            continue
        return inv
    return candidates[-1]


def _battery_for_system(tier: str, target_kwh: float, inverter: dict) -> Optional[dict]:
    if target_kwh <= 0:
        return None
    batteries = sorted(load_catalog()["batteries"], key=lambda b: b["capacity_kwh"])
    allowed_ids = set(inverter.get("compatible_battery_ids") or [])
    tier_order = {"budget": 0, "balanced": 1, "premium": 2}

    if allowed_ids:
        candidates = [b for b in batteries if b["id"] in allowed_ids]
    else:
        candidates = [b for b in batteries if tier_order.get(b["tier"], 0) >= tier_order.get(tier, 0)]
    if not candidates:
        candidates = batteries

    for bat in candidates:
        if bat["capacity_kwh"] >= target_kwh * 0.85:
            return bat
    return candidates[-1] if candidates else None


def panel_count_for_kwp(system_kwp: float, panel_wp: int) -> int:
    return max(1, math.ceil(system_kwp * 1000 / panel_wp))


def actual_system_kwp(num_panels: int, panel_wp: int) -> float:
    return round(num_panels * panel_wp / 1000, 2)


def check_roof_fit(num_panels: int, roof_area_m2: float) -> dict:
    required = num_panels * PANEL_AREA_WITH_SPACING_M2
    if roof_area_m2 <= 0:
        return {
            "status": "unknown",
            "required_m2": round(required, 1),
            "available_m2": None,
            "fits": None,
            "message_key": "sizing.roof_unknown",
        }
    fits = roof_area_m2 >= required
    return {
        "status": "ok" if fits else "too_small",
        "required_m2": round(required, 1),
        "available_m2": round(roof_area_m2, 1),
        "fits": fits,
        "message_key": "sizing.roof_ok" if fits else "sizing.roof_too_small",
    }


def build_package_spec(
    package_id: str,
    system_kwp: float,
    battery_kwh: float,
    goals: list,
    roof_type: str = "pitched_south",
    roof_area_m2: float = 0,
) -> dict:
    tier = TIER_BY_PACKAGE.get(package_id, "balanced")
    backup_needed = "backup" in (goals or [])
    mounting = _mounting_for_roof(roof_type)

    if package_id == "cheapest":
        panel, num_panels, actual_kwp, inverter, battery, tier = _pick_lowest_cost_panel_configuration(
            system_kwp, battery_kwh, backup_needed, roof_type,
        )
    else:
        panel = _panel_for_tier(tier, roof_type)
        num_panels = panel_count_for_kwp(system_kwp, panel["power_wp"])
        actual_kwp = actual_system_kwp(num_panels, panel["power_wp"])
        inverter = _inverter_for_system(tier, actual_kwp, backup_needed, battery_kwh)
        battery = _battery_for_system(tier, battery_kwh, inverter)

    roof_check = check_roof_fit(num_panels, roof_area_m2)
    hardware_subtotal = _hardware_cost_estimate(num_panels, panel, actual_kwp, inverter, battery, mounting)
    panel_cost = num_panels * panel["price_eur"]
    inv_cost = inverter["price_eur"]
    batt_cost = battery["price_eur"] if battery else 0
    mount_cost = round(actual_kwp * mounting.get("price_per_kwp", 180))
    install_cost = round(actual_kwp * 350)
    cables_cost = round(actual_kwp * 90)

    compatibility = {
        "inverter_dc_ok": inverter.get("dc_max_kw", 0) >= actual_kwp * 0.95,
        "battery_compatible": battery is None or battery["id"] in (inverter.get("compatible_battery_ids") or []),
        "backup_available": not backup_needed or inverter.get("backup_capable", False),
    }

    return {
        "tier": tier,
        "panel": {
            "id": panel["id"],
            "brand": panel["brand"],
            "model": panel["model"],
            "power_wp": panel["power_wp"],
            "quantity": num_panels,
            "unit_price_eur": panel["price_eur"],
            "total_eur": panel_cost,
            "warranty_years": panel["warranty_years"],
            "stock": panel.get("stock", "available"),
        },
        "inverter": {
            "id": inverter["id"],
            "brand": inverter["brand"],
            "model": inverter["model"],
            "ac_power_kw": inverter["ac_power_kw"],
            "dc_max_kw": inverter.get("dc_max_kw"),
            "hybrid": inverter["hybrid"],
            "backup_capable": inverter["backup_capable"],
            "price_eur": inv_cost,
            "warranty_years": inverter["warranty_years"],
            "stock": inverter.get("stock", "available"),
        },
        "battery": None if not battery else {
            "id": battery["id"],
            "brand": battery["brand"],
            "model": battery["model"],
            "capacity_kwh": battery["capacity_kwh"],
            "usable_kwh": battery["usable_kwh"],
            "backup_capable": battery["backup_capable"],
            "price_eur": batt_cost,
            "warranty_years": battery["warranty_years"],
            "stock": battery.get("stock", "available"),
        },
        "mounting": {
            "id": mounting["id"],
            "name": mounting["name"],
            "price_eur": mount_cost,
        },
        "accessories": {
            "mounting_eur": mount_cost,
            "cabling_protection_eur": cables_cost,
            "installation_eur": install_cost,
        },
        "compatibility": compatibility,
        "system_kwp_nominal": system_kwp,
        "system_kwp_actual": actual_kwp,
        "num_panels": num_panels,
        "hardware_subtotal_eur": hardware_subtotal,
        "roof_check": roof_check,
        "summary_line": _summary_line(panel, num_panels, inverter, battery, actual_kwp),
    }


def components_from_spec(spec: dict) -> list:
    """Build results component list from catalog product_spec (replaces generic placeholders)."""
    items = []
    p = spec.get("panel") or {}
    if p:
        items.append({
            "name": f"{p.get('brand', '')} {p.get('model', '')} ({p.get('power_wp', '')} Wp)",
            "quantity": p.get("quantity", 0),
            "unit": "panels",
            "estimated_cost_eur": p.get("total_eur", 0),
            "notes": f"Catalog: {p.get('id', '')} · {spec.get('system_kwp_actual', '')} kWp DC",
        })
    inv = spec.get("inverter") or {}
    if inv:
        items.append({
            "name": f"{inv.get('brand', '')} {inv.get('model', '')}",
            "quantity": 1,
            "unit": "unit",
            "estimated_cost_eur": inv.get("price_eur", 0),
            "notes": f"{inv.get('ac_power_kw', '')} kW AC · hybrid={inv.get('hybrid', False)}",
        })
    bat = spec.get("battery")
    if bat:
        items.append({
            "name": f"{bat.get('brand', '')} {bat.get('model', '')}",
            "quantity": 1,
            "unit": "unit",
            "estimated_cost_eur": bat.get("price_eur", 0),
            "notes": f"{bat.get('capacity_kwh', '')} kWh ({bat.get('usable_kwh', '')} kWh usable)",
        })
    acc = spec.get("accessories") or {}
    mount = spec.get("mounting") or {}
    items.append({
        "name": mount.get("name", "Mounting system"),
        "quantity": 1,
        "unit": "set",
        "estimated_cost_eur": acc.get("mounting_eur", 0),
        "notes": "From internal product catalog",
    })
    items.append({
        "name": "Cabling, protection & installation",
        "quantity": 1,
        "unit": "set",
        "estimated_cost_eur": (acc.get("cabling_protection_eur", 0) + acc.get("installation_eur", 0)),
        "notes": "Labour, cables, breakers, commissioning",
    })
    return items


def _summary_line(panel: dict, num_panels: int, inverter: dict, battery: Optional[dict], kwp: float) -> str:
    parts = [f"{num_panels}× {panel['brand']} {panel['model']} ({panel['power_wp']} Wp)"]
    parts.append(f"1× {inverter['brand']} {inverter['model']} ({inverter['ac_power_kw']} kW)")
    if battery:
        parts.append(f"1× {battery['brand']} {battery['model']} ({battery['capacity_kwh']} kWh)")
    parts.append(f"≈ {kwp} kWp total")
    return " · ".join(parts)


def build_sizing_summary(
    annual_kwh: float,
    adjusted_yield: float,
    system_kwp: float,
    annual_production: float,
    pvgis_used: bool,
    raw_kwp: float | None = None,
    roof_area_m2: float = 0,
) -> dict:
    raw = raw_kwp if raw_kwp is not None else (annual_kwh / adjusted_yield if adjusted_yield > 0 else 0)
    coverage = (annual_production / annual_kwh * 100) if annual_kwh > 0 else 0
    roof_max = max_kwp_from_roof_area(roof_area_m2)
    capped_by_roof = roof_max is not None and system_kwp < raw - 0.15
    coverage_rounded = round(coverage)
    demand_note = None
    roof_limit_next_steps = None
    if capped_by_roof and roof_max:
        demand_note = (
            f"Your roof area limits the system to approximately {system_kwp} kWp "
            f"(~{roof_max} kWp max on the area you entered). "
            f"This will cover about {coverage_rounded}% of your annual demand, not all of it."
        )
        roof_limit_next_steps = [
            "Check another roof section or extension",
            "Consider garage or carport mounting",
            "Consider balcony or plug-in solar where permitted",
            "Shift flexible loads to daytime to improve self-use",
            "Plan a later expansion when roof space or budget allows",
        ]
    return {
        "annual_consumption_kwh": round(annual_kwh),
        "specific_yield_kwh_kwp": round(adjusted_yield),
        "raw_kwp_needed": round(raw, 1),
        "recommended_kwp": system_kwp,
        "annual_production_kwh": annual_production,
        "coverage_pct": coverage_rounded,
        "formula_text": f"{round(annual_kwh):,} kWh ÷ {round(adjusted_yield):,} kWh/kWp ≈ {raw:.1f} kWp",
        "data_source": "PVGIS" if pvgis_used else "estimate",
        "roof_area_m2": round(roof_area_m2, 1) if roof_area_m2 else 0,
        "roof_max_kwp": round(roof_max, 1) if roof_max is not None else None,
        "capped_by_roof": capped_by_roof,
        "demand_note": demand_note,
        "roof_limit_next_steps": roof_limit_next_steps,
    }


def _find_by_id(category: str, item_id: str) -> Optional[dict]:
    for item in load_catalog().get(category, []):
        if item.get("id") == item_id:
            return item
    return None


def catalog_for_ui() -> dict:
    """Flatten catalog for compatibility checker dropdowns."""
    cat = load_catalog()
    panels = [{
        "id": p["id"],
        "label": f"{p['brand']} {p['model']} — {p['power_wp']} Wp · {p.get('efficiency_pct', '—')}% · €{p['price_eur']}",
        **p,
    } for p in cat.get("panels", [])]
    inverters = [{
        "id": i["id"],
        "label": f"{i['brand']} {i['model']} — {i['ac_power_kw']} kW AC · {i.get('dc_max_kw', '—')} kW DC · {i.get('mppt_count', 2)} MPPT",
        **i,
    } for i in cat.get("inverters", [])]
    batteries = [{
        "id": b["id"],
        "label": f"{b['brand']} {b['model']} — {b['capacity_kwh']} kWh ({b.get('usable_kwh', b['capacity_kwh'])} usable) · €{b['price_eur']}",
        **b,
    } for b in cat.get("batteries", [])]
    return {
        "panels": panels,
        "inverters": inverters,
        "batteries": batteries,
        "counts": {
            "panels": len(panels),
            "inverters": len(inverters),
            "batteries": len(batteries),
        },
    }


def check_component_compatibility(
    panel_id: str,
    inverter_id: str,
    system_kwp: float,
    battery_id: str | None = None,
    goals: list | None = None,
) -> dict:
    """Standalone compatibility check from catalog IDs."""
    goals = goals or []
    panel = _find_by_id("panels", panel_id)
    inverter = _find_by_id("inverters", inverter_id)
    battery = _find_by_id("batteries", battery_id) if battery_id else None

    if not panel or not inverter:
        return {"ok": False, "errors": ["invalid_ids"], "checks": []}

    num_panels = panel_count_for_kwp(system_kwp, panel["power_wp"])
    actual_kwp = actual_system_kwp(num_panels, panel["power_wp"])
    dc_ok = inverter.get("dc_max_kw", 99) >= actual_kwp * 0.95
    ac_min_ratio = 0.80 if actual_kwp >= 15 else 0.85
    ac_ok = inverter.get("ac_power_kw", 0) >= actual_kwp * ac_min_ratio
    hybrid_ok = True
    batt_ok = True
    if battery:
        hybrid_ok = inverter.get("hybrid", False)
        allowed = inverter.get("compatible_battery_ids") or []
        batt_ok = battery["id"] in allowed if allowed else hybrid_ok
    backup_needed = "backup" in goals
    backup_ok = not backup_needed or (inverter.get("backup_capable", False) and (not battery or battery.get("backup_capable", False)))

    checks = [
        {"id": "dc_input", "passed": dc_ok, "label_key": "compat.dc_input", "detail": f"{inverter.get('dc_max_kw')} kW DC max ≥ {actual_kwp} kWp ({round(actual_kwp / max(inverter.get('dc_max_kw', 1), 0.1) * 100)}% load)"},
        {"id": "ac_output", "passed": ac_ok, "label_key": "compat.ac_output", "detail": f"{inverter.get('ac_power_kw')} kW AC ≥ {round(actual_kwp * ac_min_ratio, 1)} kWp needed (ratio {round(actual_kwp / max(inverter.get('ac_power_kw', 1), 0.1), 2)})"},
    ]
    if battery:
        checks.extend([
            {"id": "hybrid", "passed": hybrid_ok, "label_key": "compat.hybrid", "detail": "Hybrid inverter required when battery selected"},
            {"id": "battery_match", "passed": batt_ok, "label_key": "compat.battery_match", "detail": f"Battery on compatible list ({len(inverter.get('compatible_battery_ids') or [])} approved)"},
        ])
    if backup_needed:
        checks.append({"id": "backup", "passed": backup_ok, "label_key": "compat.backup", "detail": "Backup / island mode for outage goals"})

    dc_ac_ratio = round(actual_kwp / max(inverter.get("ac_power_kw", 1), 0.1), 2)
    ratio_min = 0.60 if actual_kwp <= 4 else 0.75
    ratio_ok = ratio_min <= dc_ac_ratio <= 1.55
    checks.append({
        "id": "dc_ac_ratio",
        "passed": ratio_ok,
        "label_key": "compat.dc_ac_ratio",
        "detail": f"DC/AC ratio {dc_ac_ratio} (typical {ratio_min}–1.55 for DE installs)",
    })

    max_panels_per_mppt = 28
    mppt_ok = num_panels <= inverter.get("mppt_count", 2) * max_panels_per_mppt
    checks.append({
        "id": "mppt_panels",
        "passed": mppt_ok,
        "label_key": "compat.mppt_panels",
        "detail": f"{num_panels} panels · {inverter.get('mppt_count', 2)} MPPT (max ~{inverter.get('mppt_count', 2) * max_panels_per_mppt} modules)",
    })

    if battery:
        usable = battery.get("usable_kwh", battery.get("capacity_kwh", 0))
        nightly_ok = usable >= 3.0
        checks.append({
            "id": "battery_size",
            "passed": nightly_ok,
            "label_key": "compat.battery_size",
            "detail": f"{usable} kWh usable ({battery.get('max_power_kw', '—')} kW max power)",
        })
    passed = [c for c in checks if c["passed"]]
    failed = [c for c in checks if not c["passed"]]

    return {
        "ok": len(failed) == 0,
        "system_kwp_actual": actual_kwp,
        "num_panels": num_panels,
        "panel_wp": panel["power_wp"],
        "dc_ac_ratio": dc_ac_ratio,
        "panel": {"id": panel["id"], "brand": panel["brand"], "model": panel["model"], "power_wp": panel["power_wp"], "efficiency_pct": panel.get("efficiency_pct")},
        "inverter": {"id": inverter["id"], "brand": inverter["brand"], "model": inverter["model"], "ac_power_kw": inverter["ac_power_kw"], "dc_max_kw": inverter.get("dc_max_kw"), "mppt_count": inverter.get("mppt_count")},
        "battery": {"id": battery["id"], "brand": battery["brand"], "model": battery["model"], "capacity_kwh": battery["capacity_kwh"], "usable_kwh": battery.get("usable_kwh")} if battery else None,
        "checks": checks,
        "passed_count": len(passed),
        "failed_count": len(failed),
    }


def find_alternatives(
    panel_id: str,
    inverter_id: str,
    system_kwp: float,
    battery_id: str | None = None,
    goals: list | None = None,
) -> dict:
    """Suggest compatible alternatives when primary selection fails checks."""
    goals = goals or []
    primary = check_component_compatibility(panel_id, inverter_id, system_kwp, battery_id, goals)
    cat = load_catalog()
    alts: dict[str, list] = {"panels": [], "inverters": [], "batteries": []}

    panel = _find_by_id("panels", panel_id)
    tier = panel.get("tier", "balanced") if panel else "balanced"
    actual_kwp = primary.get("system_kwp_actual") or system_kwp

    for p in cat.get("panels", []):
        if p["id"] == panel_id:
            continue
        if p.get("stock") == "on_request":
            continue
        kwp = actual_system_kwp(panel_count_for_kwp(system_kwp, p["power_wp"]), p["power_wp"])
        alts["panels"].append({
            "id": p["id"],
            "label": f"{p['brand']} {p['model']}",
            "power_wp": p["power_wp"],
            "price_eur": p["price_eur"],
            "stock": p.get("stock", "available"),
            "datasheet_url": p.get("datasheet_url", ""),
            "actual_kwp": kwp,
        })

    for inv in cat.get("inverters", []):
        if inv["id"] == inverter_id:
            continue
        if inv.get("ac_power_kw", 0) >= actual_kwp * 0.85 and inv.get("dc_max_kw", 0) >= actual_kwp * 0.95:
            alts["inverters"].append({
                "id": inv["id"],
                "label": f"{inv['brand']} {inv['model']}",
                "ac_power_kw": inv["ac_power_kw"],
                "hybrid": inv.get("hybrid"),
                "compatible_battery_ids": inv.get("compatible_battery_ids", []),
                "stock": inv.get("stock", "available"),
                "datasheet_url": inv.get("datasheet_url", ""),
            })

    target_inv = _find_by_id("inverters", inverter_id)
    allowed = set(target_inv.get("compatible_battery_ids") or []) if target_inv else set()
    for b in cat.get("batteries", []):
        if battery_id and b["id"] == battery_id:
            continue
        if allowed and b["id"] not in allowed:
            continue
        alts["batteries"].append({
            "id": b["id"],
            "label": f"{b['brand']} {b['model']}",
            "capacity_kwh": b["capacity_kwh"],
            "price_eur": b["price_eur"],
            "stock": b.get("stock", "available"),
            "datasheet_url": b.get("datasheet_url", ""),
        })

    for key in alts:
        alts[key] = alts[key][:8]

    return {"primary": primary, "alternatives": alts}
