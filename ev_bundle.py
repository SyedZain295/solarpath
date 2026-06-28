"""Solar Path EV Phase 3 — guided EV + wallbox + PV bundle plan."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from ev_marketplace import (
    _annual_charging_kwh,
    _home_charge_hours,
    _pv_coverage_pct,
    build_vehicle_fit,
    home_energy_check,
    match_vehicles,
    parse_buyer_profile,
    vehicle_by_slug,
)

WALLBOX_PATH = Path(__file__).resolve().parent / "data" / "wallboxes.json"
BAVARIA_YIELD_KWH_KWP = 950
PV_COST_PER_KWP = 1900


@lru_cache(maxsize=1)
def load_wallboxes() -> list[dict]:
    if not WALLBOX_PATH.is_file():
        return []
    data = json.loads(WALLBOX_PATH.read_text(encoding="utf-8"))
    return list(data.get("wallboxes") or [])


def _score_wallbox(wallbox: dict, vehicle_ac: float, has_pv: bool) -> int:
    score = 40
    kw = float(wallbox.get("ac_kw") or 11)
    if kw >= vehicle_ac:
        score += 25
    elif kw >= vehicle_ac * 0.85:
        score += 15
    elif kw >= vehicle_ac * 0.6:
        score += 8
    if has_pv and wallbox.get("solar_ready"):
        score += 20
    if wallbox.get("load_management"):
        score += 8
    if wallbox.get("dynamic_tariff"):
        score += 5
    return score


def recommend_wallbox(profile: dict, vehicle: dict, wallbox_id: str = "") -> dict:
    if profile.get("has_wallbox"):
        upgrade = next((w for w in load_wallboxes() if w.get("id") == "wb-smart-upgrade"), None)
        return {
            "needed": False,
            "keep_existing": True,
            "recommended": upgrade,
            "alternatives": [],
            "vehicle_ac_kw": float(vehicle.get("ac_charge_kw") or 11),
            "install_cost_eur": upgrade.get("installed_price_eur", 0) if upgrade else 0,
            "reason": "You already have a wallbox — add PV surplus routing and smart scheduling instead of a new charger.",
        }

    vehicle_ac = float(vehicle.get("ac_charge_kw") or 11)
    has_pv = bool(profile.get("has_pv"))
    boxes = [w for w in load_wallboxes() if w.get("id") != "wb-smart-upgrade"]
    scored = sorted((( _score_wallbox(w, vehicle_ac, has_pv), w) for w in boxes), key=lambda x: -x[0])

    recommended = scored[0][1] if scored else None
    if wallbox_id:
        picked = next((w for w in load_wallboxes() if w.get("id") == wallbox_id), None)
        if picked:
            recommended = picked

    alternatives = [w for _, w in scored[1:3] if w.get("id") != (recommended or {}).get("id")]
    overnight_h = _home_charge_hours(vehicle, profile)
    reason = ""
    if recommended:
        reason = (
            f"{recommended['make']} {recommended['model']} ({recommended['ac_kw']} kW) "
            f"matches your vehicle's {vehicle_ac:g} kW AC limit — ~{overnight_h} h overnight for your driving."
        )
        if has_pv and recommended.get("solar_ready"):
            reason += " Solar-ready for surplus charging."

    return {
        "needed": True,
        "keep_existing": False,
        "recommended": recommended,
        "alternatives": alternatives,
        "vehicle_ac_kw": vehicle_ac,
        "install_cost_eur": int((recommended or {}).get("installed_price_eur") or 0),
        "reason": reason,
    }


def pv_plan_for_ev(profile: dict, vehicle: dict) -> dict:
    annual_ev_kwh = _annual_charging_kwh(vehicle, profile)
    has_pv = bool(profile.get("has_pv"))
    current_kwp = float(profile.get("system_kwp") or 0)

    if not has_pv:
        household_base = 2500
        target_offset = annual_ev_kwh * 0.65 + household_base * 0.25
        suggested_kwp = round(max(4.0, target_offset / BAVARIA_YIELD_KWH_KWP), 1)
        est_cost = round(suggested_kwp * PV_COST_PER_KWP)
        return {
            "action": "install_pv",
            "has_pv": False,
            "current_kwp": 0,
            "suggested_kwp": suggested_kwp,
            "add_kwp": suggested_kwp,
            "target_total_kwp": suggested_kwp,
            "coverage_pct": 65,
            "annual_ev_kwh": annual_ev_kwh,
            "est_cost_eur": est_cost,
            "reason": (
                f"No PV yet — a ~{suggested_kwp} kWp system could offset much of "
                f"~{annual_ev_kwh:,} kWh/year EV charging plus part of household use."
            ),
        }

    coverage = _pv_coverage_pct(profile)
    gap_kwh = annual_ev_kwh * max(0, 1 - coverage / 100)
    add_kwp = round(max(0, gap_kwh / BAVARIA_YIELD_KWH_KWP), 1)
    if add_kwp < 1.0:
        add_kwp = 0.0
    target_total = round(current_kwp + add_kwp, 1)
    est_cost = round(add_kwp * PV_COST_PER_KWP) if add_kwp else 0
    action = "expand_pv" if add_kwp >= 1 else "sufficient"

    if action == "sufficient":
        reason = (
            f"Your {current_kwp:g} kWp system may already cover ~{coverage}% of "
            f"~{annual_ev_kwh:,} kWh/year charging — smart scheduling matters more than more panels."
        )
    else:
        reason = (
            f"Adding ~{add_kwp:g} kWp (to ~{target_total:g} kWp total) helps cover EV charging "
            f"when the car is home in daylight."
        )

    return {
        "action": action,
        "has_pv": True,
        "current_kwp": current_kwp,
        "suggested_kwp": target_total,
        "add_kwp": add_kwp,
        "target_total_kwp": target_total,
        "coverage_pct": coverage,
        "annual_ev_kwh": annual_ev_kwh,
        "est_cost_eur": est_cost,
        "reason": reason,
    }


def _bundle_costs(vehicle: dict, wallbox: dict, pv: dict, energy: dict) -> dict:
    ev_price = int(vehicle.get("price_eur") or 0)
    wallbox_cost = int(wallbox.get("install_cost_eur") or 0)
    pv_cost = int(pv.get("est_cost_eur") or 0)
    return {
        "vehicle_eur": ev_price,
        "wallbox_eur": wallbox_cost,
        "pv_eur": pv_cost,
        "total_upfront_eur": ev_price + wallbox_cost + pv_cost,
        "charging_grid_annual_eur": energy.get("grid_cost_annual_eur"),
        "charging_with_pv_annual_eur": energy.get("with_pv_cost_annual_eur"),
    }


def _build_ctas(profile: dict, vehicle: dict, pv: dict) -> dict:
    params = {
        "invite": "solarpath-beta-2026",
        "weekly_km": profile.get("weekly_km") or "",
        "kwp": pv.get("target_total_kwp") or pv.get("suggested_kwp") or profile.get("system_kwp") or "",
    }
    if profile.get("has_pv"):
        params["has_pv"] = "1"
    calc_qs = urlencode({k: v for k, v in params.items() if v})
    bundle_qs = urlencode({
        "vehicle": vehicle.get("slug") or "",
        "weekly_km": profile.get("weekly_km") or "",
        "kwp": profile.get("system_kwp") or "",
        "has_pv": "1" if profile.get("has_pv") else "",
        "budget": profile.get("budget_eur") or "",
    })
    return {
        "calculator_url": f"/calculator?{calc_qs}" if calc_qs else "/calculator?invite=solarpath-beta-2026",
        "estimate_url": "/estimate",
        "compare_quotes_url": "/compare-quotes",
        "energy_check_url": f"/ev/home-energy?vehicle={vehicle.get('slug', '')}",
        "bundle_share_url": f"/ev/bundle?{bundle_qs}",
    }


def build_bundle_plan(profile_data: dict, vehicle_slug: str = "", wallbox_id: str = "") -> dict[str, Any]:
    profile = parse_buyer_profile(profile_data)
    slug = (vehicle_slug or profile_data.get("vehicle_slug") or "").strip()

    if not slug:
        matches = match_vehicles(profile_data, limit=5)
        return {
            "step": "select_vehicle",
            "profile": profile,
            "candidates": matches.get("recommendations") or [],
            "disclaimer": matches.get("disclaimer"),
        }

    vehicle = vehicle_by_slug(slug)
    if not vehicle:
        return {"error": "Vehicle not found", "step": "select_vehicle"}

    fit = build_vehicle_fit(vehicle, profile)
    energy = home_energy_check(profile_data, vehicle_slug=slug)
    wallbox = recommend_wallbox(profile, vehicle, wallbox_id)
    pv = pv_plan_for_ev(profile, vehicle)
    costs = _bundle_costs(vehicle, wallbox, pv, energy)

    vehicle_public = {
        "id": vehicle.get("id"),
        "slug": vehicle.get("slug"),
        "make": vehicle.get("make"),
        "model": vehicle.get("model"),
        "trim": vehicle.get("trim"),
        "year": vehicle.get("year"),
        "price_eur": vehicle.get("price_eur"),
        "battery_kwh": vehicle.get("battery_kwh"),
        "listing_status": vehicle.get("listing_status"),
        "dealer_name": vehicle.get("dealer_name"),
        "location": vehicle.get("location"),
        "solar_path_fit": fit,
    }

    return {
        "step": "bundle",
        "profile": profile,
        "vehicle": vehicle_public,
        "wallbox": wallbox,
        "pv": pv,
        "energy": {
            "annual_ev_kwh": energy.get("annual_ev_kwh"),
            "recommendations": energy.get("recommendations") or [],
            "grid_cost_annual_eur": energy.get("grid_cost_annual_eur"),
            "with_pv_cost_annual_eur": energy.get("with_pv_cost_annual_eur"),
        },
        "costs": costs,
        "ctas": _build_ctas(profile, vehicle, pv),
        "disclaimer": (
            "Illustrative home-energy bundle plan — not a purchase offer, installation quote, "
            "or vehicle inspection. Verify wallbox compatibility, grid connection, and PV sizing with installers."
        ),
    }


def profile_from_calculator(data: dict) -> dict:
    """Map calculator EV fields to marketplace profile for bundle prefill."""
    weekly = 0.0
    annual = float(data.get("ev_annual_km") or data.get("annual_km") or 0)
    if annual > 0:
        weekly = round(annual / 52)
    has_wallbox = (data.get("ev_has_wallbox") or "").strip().lower() in ("yes", "true", "1")
    return {
        "budget_eur": float(data.get("budget_eur") or 28000),
        "weekly_km": float(data.get("weekly_km") or weekly or 250),
        "annual_km": annual,
        "home_charging": data.get("ev_home_charging") or data.get("home_charging") or "yes",
        "has_pv": bool(data.get("has_pv") or float(data.get("system_kwp") or data.get("kwp") or 0) > 0),
        "has_battery": bool(data.get("has_battery")),
        "has_wallbox": has_wallbox,
        "system_kwp": float(data.get("system_kwp") or data.get("kwp") or 0),
        "priority": data.get("priority") or "running_cost",
        "owner_status": data.get("owner_status") or "owner",
    }
