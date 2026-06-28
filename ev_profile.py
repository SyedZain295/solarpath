"""EV charging profile — intake questions and sizing hints."""

from __future__ import annotations

from typing import Any


def parse_ev_fields(data: dict) -> dict[str, Any]:
    return {
        "ownership": (data.get("ev_ownership") or "").strip(),
        "vehicle_model": (data.get("ev_vehicle_model") or "").strip(),
        "annual_km": float(data.get("ev_annual_km") or 0),
        "consumption_kwh_100km": float(data.get("ev_consumption_kwh_100km") or 18),
        "home_charging": (data.get("ev_home_charging") or "").strip(),
        "park_home_daytime": (data.get("ev_park_home_daytime") or "").strip(),
        "has_wallbox": (data.get("ev_has_wallbox") or "").strip(),
        "charging_priority": (data.get("ev_charging_priority") or "").strip(),
        "dynamic_tariff_interest": (data.get("ev_dynamic_tariff_interest") or "").strip(),
    }


def apply_ev_fields_to_input(inp, data: dict) -> None:
    ev = parse_ev_fields(data)
    inp.ev_ownership = ev["ownership"]
    inp.ev_vehicle_model = ev["vehicle_model"]
    inp.ev_annual_km = ev["annual_km"]
    inp.ev_consumption_kwh_100km = ev["consumption_kwh_100km"] or 18.0
    inp.ev_home_charging = ev["home_charging"]
    inp.ev_park_home_daytime = ev["park_home_daytime"]
    inp.ev_has_wallbox = ev["has_wallbox"]
    inp.ev_charging_priority = ev["charging_priority"]
    inp.ev_dynamic_tariff_interest = ev["dynamic_tariff_interest"]

    if ev["ownership"] == "own":
        inp.has_ev = True
        inp.planned_ev = False
    elif ev["ownership"] == "planning":
        inp.has_ev = False
        inp.planned_ev = True


def estimate_ev_annual_kwh(inp) -> float:
    km = float(getattr(inp, "ev_annual_km", 0) or 0)
    per_100 = float(getattr(inp, "ev_consumption_kwh_100km", 0) or 0)
    if km > 0 and per_100 > 0:
        return round(km * per_100 / 100)
    goals = getattr(inp, "goals", None) or []
    if getattr(inp, "has_ev", False) or getattr(inp, "planned_ev", False) or "ev_charging" in goals:
        return 2500.0
    return 0.0


def ev_home_charging_viable(inp) -> bool:
    home = getattr(inp, "ev_home_charging", "")
    if home == "no":
        return False
    if home in ("yes", "limited"):
        return True
    return getattr(inp, "owner_status", "owner") == "owner"


def recommend_ev_battery_kwh(inp, system_kwp: float, annual_kwh: float, goals: list) -> float | None:
    """Return battery kWh for EV-led sizing, or None to use generic logic."""
    if "ev_charging" not in goals:
        return None
    priority = getattr(inp, "ev_charging_priority", "") or "solar"
    if priority == "cheapest":
        return 0.0
    if priority == "fastest":
        return 0.0
    if priority == "backup":
        return round(min(15, max(7, annual_kwh / 365 * 0.3)), 1)
    ev_kwh = estimate_ev_annual_kwh(inp)
    daily_ev = ev_kwh / 365 if ev_kwh else system_kwp * 0.8
    park = getattr(inp, "ev_park_home_daytime", "")
    if park in ("yes", "sometimes"):
        return round(min(12, max(5, daily_ev * 0.9)), 1)
    return round(min(15, max(7, daily_ev * 1.2)), 1)


def ev_wallbox_needed(inp) -> bool:
    return getattr(inp, "ev_has_wallbox", "") not in ("yes",)


def build_ev_assessment(inp, electricity_price_ct: float = 32.0) -> dict:
    ev_kwh = estimate_ev_annual_kwh(inp)
    price = electricity_price_ct / 100
    grid_annual = round(ev_kwh * price)
    solar_offset_pct = 55 if getattr(inp, "ev_park_home_daytime", "") in ("yes", "sometimes") else 40
    with_pv_annual = round(grid_annual * (1 - solar_offset_pct / 100))

    priority = getattr(inp, "ev_charging_priority", "") or "solar"
    priority_labels = {
        "cheapest": "Lowest charging cost (grid-focused)",
        "fastest": "Fastest home charging",
        "solar": "Solar-led charging",
        "backup": "Backup power during outages",
    }
    ownership_labels = {"own": "Already own an EV", "planning": "Planning to buy an EV"}

    notes = []
    if not ev_home_charging_viable(inp):
        notes.append("Home charging may be limited — balcony or workplace charging may be more relevant.")
    if getattr(inp, "ev_has_wallbox", "") == "yes":
        notes.append("Existing wallbox detected — PV surplus routing and tariff optimisation are the main upgrade.")
    if getattr(inp, "ev_dynamic_tariff_interest", "") in ("yes", "maybe"):
        notes.append("Dynamic tariffs pair well with smart wallbox scheduling and optional battery storage.")

    return {
        "ownership": getattr(inp, "ev_ownership", ""),
        "ownership_label": ownership_labels.get(getattr(inp, "ev_ownership", ""), "—"),
        "vehicle_model": getattr(inp, "ev_vehicle_model", "") or "—",
        "annual_km": getattr(inp, "ev_annual_km", 0),
        "consumption_kwh_100km": getattr(inp, "ev_consumption_kwh_100km", 18),
        "annual_charging_kwh": ev_kwh,
        "home_charging": getattr(inp, "ev_home_charging", ""),
        "park_home_daytime": getattr(inp, "ev_park_home_daytime", ""),
        "has_wallbox": getattr(inp, "ev_has_wallbox", ""),
        "charging_priority": priority,
        "charging_priority_label": priority_labels.get(priority, priority),
        "dynamic_tariff_interest": getattr(inp, "ev_dynamic_tariff_interest", ""),
        "home_charging_viable": ev_home_charging_viable(inp),
        "wallbox_needed": ev_wallbox_needed(inp),
        "estimated_grid_charging_cost_annual_eur": grid_annual,
        "estimated_charging_cost_with_pv_annual_eur": with_pv_annual,
        "notes": notes,
        "future_features": [
            "Browse used EVs with Solar Path fit on EV Marketplace",
            "Battery certificate checks when uploaded by dealer",
        ],
    }


def ev_snapshot(inp) -> dict:
    return {
        "ev_ownership": getattr(inp, "ev_ownership", ""),
        "ev_vehicle_model": getattr(inp, "ev_vehicle_model", ""),
        "ev_annual_km": getattr(inp, "ev_annual_km", 0),
        "ev_consumption_kwh_100km": getattr(inp, "ev_consumption_kwh_100km", 18),
        "ev_home_charging": getattr(inp, "ev_home_charging", ""),
        "ev_park_home_daytime": getattr(inp, "ev_park_home_daytime", ""),
        "ev_has_wallbox": getattr(inp, "ev_has_wallbox", ""),
        "ev_charging_priority": getattr(inp, "ev_charging_priority", ""),
        "ev_dynamic_tariff_interest": getattr(inp, "ev_dynamic_tariff_interest", ""),
        "ev_annual_charging_kwh": estimate_ev_annual_kwh(inp),
    }
