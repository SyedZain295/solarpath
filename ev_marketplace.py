"""Solar Path EV — advisor matching, listings, and home-energy fit (Phase 1)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parent / "data" / "ev_vehicles.json"

PRIORITY_MAP = {
    "running_cost": "running_cost",
    "range": "range",
    "fast_charging": "fast_charging",
    "family": "practical",
    "practical": "practical",
}

FAMILY_BOOT_MIN = {"small": 0, "medium": 300, "large": 450}


def clear_vehicle_cache() -> None:
    load_demo_vehicles.cache_clear()
    load_vehicles.cache_clear()


@lru_cache(maxsize=1)
def load_demo_vehicles() -> list[dict]:
    if not DATA_PATH.is_file():
        return []
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return list(data.get("vehicles") or [])


def load_partner_vehicles() -> list[dict]:
    try:
        from ev_dealer_store import list_published_vehicles

        return list_published_vehicles()
    except Exception:
        return []


@lru_cache(maxsize=1)
def load_vehicles() -> list[dict]:
    partner = load_partner_vehicles()
    demo = load_demo_vehicles()
    return partner + demo


def vehicle_by_slug(slug: str) -> dict | None:
    slug = (slug or "").strip().lower()
    try:
        from ev_dealer_store import vehicle_by_slug_db

        found = vehicle_by_slug_db(slug)
        if found:
            return found
    except Exception:
        pass
    for v in load_demo_vehicles():
        if v.get("slug") == slug or v.get("id") == slug:
            return v
    return None


def filter_vehicles(
    *,
    budget_max: float = 0,
    range_min: float = 0,
    battery_health_min: float = 0,
    body_type: str = "",
    family_fit: str = "",
    certificate_only: bool = False,
    fast_charge_min: float = 0,
    limit: int = 50,
) -> list[dict]:
    out = []
    for v in load_vehicles():
        if budget_max > 0 and float(v.get("price_eur") or 0) > budget_max:
            continue
        if range_min > 0 and float(v.get("winter_range_km_max") or 0) < range_min:
            continue
        cert = v.get("battery_certificate") or {}
        soh = cert.get("state_of_health_pct")
        if battery_health_min > 0:
            if soh is None or float(soh) < battery_health_min:
                continue
        if certificate_only and not cert.get("uploaded"):
            continue
        if body_type and v.get("body_type") != body_type:
            continue
        if family_fit and v.get("family_fit") != family_fit:
            continue
        if fast_charge_min > 0 and float(v.get("dc_fast_charge_kw") or 0) < fast_charge_min:
            continue
        out.append(v)
    return out[:limit]


def parse_buyer_profile(data: dict) -> dict[str, Any]:
    weekly_km = float(data.get("weekly_km") or 0)
    annual_km = float(data.get("annual_km") or 0)
    if annual_km <= 0 and weekly_km > 0:
        annual_km = weekly_km * 52
    long_trips = int(data.get("long_trips_per_year") or 0)
    return {
        "budget_eur": float(data.get("budget_eur") or 0),
        "annual_km": annual_km or 12000,
        "weekly_km": weekly_km,
        "long_trips_per_year": long_trips,
        "family_size": int(data.get("family_size") or 2),
        "boot_priority": (data.get("boot_priority") or "medium").strip(),
        "owner_status": (data.get("owner_status") or "owner").strip(),
        "home_charging": (data.get("home_charging") or "yes").strip(),
        "has_pv": bool(data.get("has_pv")),
        "has_battery": bool(data.get("has_battery")),
        "has_wallbox": bool(data.get("has_wallbox")),
        "system_kwp": float(data.get("system_kwp") or 0),
        "priority": PRIORITY_MAP.get((data.get("priority") or "running_cost").strip(), "running_cost"),
        "electricity_price_ct": float(data.get("electricity_price_ct") or 32),
    }


def _daily_km(profile: dict) -> float:
    return profile["annual_km"] / 365


def _home_charge_hours(vehicle: dict, profile: dict) -> float:
    daily_kwh = _daily_km(profile) * float(vehicle.get("consumption_kwh_100km") or 18) / 100
    ac_kw = float(vehicle.get("ac_charge_kw") or 11)
    if ac_kw <= 0:
        return 0
    return round(daily_kwh / ac_kw, 1)


def _annual_charging_kwh(vehicle: dict, profile: dict) -> float:
    return round(profile["annual_km"] * float(vehicle.get("consumption_kwh_100km") or 18) / 100)


def _pv_coverage_pct(profile: dict) -> int:
    if not profile.get("has_pv"):
        return 0
    kwp = profile.get("system_kwp") or 0
    if kwp >= 8:
        return 45
    if kwp >= 5:
        return 35
    if kwp >= 3:
        return 25
    return 15


def _charging_cost_annual(vehicle: dict, profile: dict, with_pv: bool) -> int:
    kwh = _annual_charging_kwh(vehicle, profile)
    price = profile["electricity_price_ct"] / 100
    if with_pv:
        offset = _pv_coverage_pct(profile) / 100
        return round(kwh * price * (1 - offset))
    return round(kwh * price)


def _score_vehicle(vehicle: dict, profile: dict) -> tuple[int, list[str]]:
    score = 50
    reasons: list[str] = []

    price = float(vehicle.get("price_eur") or 0)
    budget = profile.get("budget_eur") or 0
    if budget > 0:
        if price <= budget:
            score += 18
            reasons.append("Within your budget")
        elif price <= budget * 1.08:
            score += 8
            reasons.append("Slightly above budget — negotiable range")
        else:
            score -= 25

    annual_km = profile["annual_km"]
    winter_max = float(vehicle.get("winter_range_km_max") or 0)
    daily = _daily_km(profile)
    if winter_max >= daily * 1.4:
        score += 12
        reasons.append(f"Suitable for {annual_km:,} km/year")
    elif winter_max >= daily:
        score += 5
    else:
        score -= 10

    if profile.get("long_trips_per_year", 0) >= 6:
        dc = float(vehicle.get("dc_fast_charge_kw") or 0)
        if dc >= 100:
            score += 10
            reasons.append("Strong DC fast charging for long trips")
        elif dc >= 70:
            score += 4

    family = profile.get("boot_priority") or "medium"
    min_boot = FAMILY_BOOT_MIN.get(family, 300)
    boot = int(vehicle.get("boot_litres") or 0)
    seats = int(vehicle.get("seats") or 5)
    fam_size = profile.get("family_size") or 2
    if boot >= min_boot and seats >= fam_size:
        score += 10
        reasons.append("Meets space needs")
    elif boot < min_boot - 50:
        score -= 8

    priority = profile.get("priority") or "running_cost"
    tags = vehicle.get("priority_tags") or []
    if priority in tags or (priority == "practical" and "family" in tags):
        score += 12
        reasons.append("Matches your priority")

    cert = vehicle.get("battery_certificate") or {}
    if cert.get("uploaded") and cert.get("state_of_health_pct"):
        score += 8
        reasons.append("Battery certificate uploaded")
    elif cert.get("independent_test_available"):
        score += 3

    if profile.get("home_charging") in ("yes", "limited") and float(vehicle.get("ac_charge_kw") or 0) >= 11:
        score += 5

    if profile.get("has_pv"):
        score += 6
        reasons.append("Works with home PV charging")

    return min(100, max(0, score)), reasons[:5]


def _fit_label(score: int) -> str:
    if score >= 80:
        return "Excellent Solar Path fit"
    if score >= 65:
        return "Good Solar Path fit"
    if score >= 50:
        return "Possible fit"
    return "Worth comparing"


def build_vehicle_fit(vehicle: dict, profile: dict) -> dict:
    score, match_reasons = _score_vehicle(vehicle, profile)
    cert = vehicle.get("battery_certificate") or {}
    pv_pct = _pv_coverage_pct(profile)
    wallbox_rec = profile.get("home_charging") in ("yes", "limited") and not profile.get("has_wallbox")
    annual_kwh = _annual_charging_kwh(vehicle, profile)

    setup_parts = []
    if wallbox_rec:
        setup_parts.append(f"{int(vehicle.get('ac_charge_kw') or 11)} kW wallbox")
    if profile.get("has_pv") and not profile.get("has_battery"):
        setup_parts.append("smart solar charging")
    if profile.get("has_battery"):
        setup_parts.append("battery-aware scheduling")
    suggested_setup = " + ".join(setup_parts) if setup_parts else "Standard home socket (slow)"

    return {
        "vehicle_id": vehicle.get("id"),
        "slug": vehicle.get("slug"),
        "fit_score": score,
        "fit_label": _fit_label(score),
        "match_reasons": match_reasons,
        "suitable_annual_km": profile["annual_km"],
        "annual_charging_kwh_added": annual_kwh,
        "winter_range_label": f"{vehicle.get('winter_range_km_min')}–{vehicle.get('winter_range_km_max')} km",
        "summer_range_label": f"{vehicle.get('summer_range_km_min')}–{vehicle.get('summer_range_km_max')} km",
        "home_charging_hours": _home_charge_hours(vehicle, profile),
        "wallbox_recommended": wallbox_rec,
        "pv_coverage_pct": pv_pct if profile.get("has_pv") else None,
        "pv_coverage_label": (
            f"Your current PV could cover approximately {pv_pct}% of annual charging"
            if profile.get("has_pv") and pv_pct
            else None
        ),
        "suggested_setup": suggested_setup,
        "annual_charging_cost_grid_eur": _charging_cost_annual(vehicle, profile, False),
        "annual_charging_cost_with_pv_eur": _charging_cost_annual(vehicle, profile, True)
        if profile.get("has_pv")
        else None,
        "battery_certificate_label": _certificate_label(cert),
        "battery_warranty_label": _warranty_label(vehicle),
        "listing_status": vehicle.get("listing_status", "demo"),
        "is_demo_listing": vehicle.get("listing_status") == "demo",
    }


def _certificate_label(cert: dict) -> dict:
    if cert.get("uploaded"):
        return {
            "status": "uploaded",
            "text": "Battery certificate uploaded",
            "provider": cert.get("provider"),
            "test_date": cert.get("test_date"),
            "state_of_health_pct": cert.get("state_of_health_pct"),
            "independent_test_available": bool(cert.get("independent_test_available")),
        }
    if cert.get("independent_test_available"):
        return {
            "status": "test_available",
            "text": "Independent battery test available",
            "provider": None,
            "test_date": None,
            "state_of_health_pct": None,
            "independent_test_available": True,
        }
    return {
        "status": "none",
        "text": "No certificate on file — ask dealer before buying",
        "provider": None,
        "test_date": None,
        "state_of_health_pct": None,
        "independent_test_available": False,
    }


def _warranty_label(vehicle: dict) -> str:
    yrs = vehicle.get("battery_warranty_years_remaining")
    km = vehicle.get("battery_warranty_km_remaining")
    if yrs is not None and km is not None:
        return f"{yrs} years / {int(km):,} km remaining (manufacturer)"
    if yrs is not None:
        return f"{yrs} years remaining (manufacturer)"
    return "Check warranty with dealer"


def match_vehicles(profile_data: dict, limit: int = 5) -> dict:
    profile = parse_buyer_profile(profile_data)
    vehicles = load_vehicles()
    if profile.get("budget_eur") > 0:
        vehicles = [v for v in vehicles if float(v.get("price_eur") or 0) <= profile["budget_eur"] * 1.15] or vehicles

    scored = []
    for v in vehicles:
        fit = build_vehicle_fit(v, profile)
        scored.append({**v, "solar_path_fit": fit, "fit_score": fit["fit_score"]})
    scored.sort(key=lambda x: x["fit_score"], reverse=True)

    return {
        "profile": profile,
        "recommendations": scored[:limit],
        "total_listings": len(load_vehicles()),
        "disclaimer": (
            "Illustrative advisor only — not a vehicle inspection or purchase offer. "
            "Battery State of Health is shown only when a certificate is uploaded by the dealer. "
            "Always verify condition, warranty and history in person."
        ),
    }


def home_energy_check(profile_data: dict, vehicle_slug: str = "") -> dict:
    profile = parse_buyer_profile(profile_data)
    vehicle = vehicle_by_slug(vehicle_slug) if vehicle_slug else None
    if not vehicle and profile_data.get("consumption_kwh_100km"):
        vehicle = {
            "consumption_kwh_100km": float(profile_data["consumption_kwh_100km"]),
            "ac_charge_kw": float(profile_data.get("ac_charge_kw") or 11),
            "battery_kwh": float(profile_data.get("battery_kwh") or 0),
        }
    if not vehicle:
        vehicle = {"consumption_kwh_100km": 17.5, "ac_charge_kw": 11, "battery_kwh": 58}

    annual_kwh = _annual_charging_kwh(vehicle, profile)
    items = []

    if profile.get("home_charging") in ("yes", "limited") and not profile.get("has_wallbox"):
        items.append(
            {
                "id": "wallbox",
                "priority": "high",
                "title": "Wallbox recommended",
                "detail": f"An {int(vehicle.get('ac_charge_kw') or 11)} kW smart wallbox makes overnight charging practical (~{_home_charge_hours(vehicle, profile)} h/night for your driving).",
            }
        )

    if not profile.get("has_pv"):
        items.append(
            {
                "id": "pv",
                "priority": "medium",
                "title": "PV can lower charging cost",
                "detail": f"Adding rooftop PV could offset a large share of ~{annual_kwh:,} kWh/year EV charging.",
            }
        )
    elif _pv_coverage_pct(profile) < 40:
        items.append(
            {
                "id": "pv_expand",
                "priority": "medium",
                "title": "Consider expanding PV",
                "detail": f"Your current system may cover ~{_pv_coverage_pct(profile)}% of charging — more kWp helps if the car is home daytime.",
            }
        )

    if profile.get("has_pv") and not profile.get("has_battery") and annual_kwh > 2500:
        items.append(
            {
                "id": "battery",
                "priority": "low",
                "title": "Battery optional",
                "detail": "A home battery helps store midday solar for evening charging — compare cost vs smart tariff.",
            }
        )

    items.append(
        {
            "id": "smart",
            "priority": "medium",
            "title": "Smart charging",
            "detail": "Schedule charging to solar surplus hours or cheap tariff windows.",
        }
    )

    return {
        "profile": profile,
        "annual_ev_kwh": annual_kwh,
        "household_addition_kwh": annual_kwh,
        "grid_cost_annual_eur": _charging_cost_annual(vehicle, profile, False),
        "with_pv_cost_annual_eur": _charging_cost_annual(vehicle, profile, True) if profile.get("has_pv") else None,
        "recommendations": items,
        "bundle_cta": "Buy this EV, install this wallbox, and see how it works with your PV or planned PV system.",
    }


def vehicles_for_api(filters: dict | None = None) -> list[dict]:
    filters = filters or {}
    items = filter_vehicles(
        budget_max=float(filters.get("budget_max") or 0),
        range_min=float(filters.get("range_min") or 0),
        battery_health_min=float(filters.get("battery_health_min") or 0),
        body_type=(filters.get("body_type") or "").strip(),
        family_fit=(filters.get("family_fit") or "").strip(),
        certificate_only=bool(filters.get("certificate_only")),
        fast_charge_min=float(filters.get("fast_charge_min") or 0),
    )
    profile = parse_buyer_profile(filters)
    return [{**v, "solar_path_fit": build_vehicle_fit(v, profile)} for v in items]
