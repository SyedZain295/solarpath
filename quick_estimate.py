"""Lightweight pre-calculator estimate — kWp range without full PVGIS round-trip."""

from __future__ import annotations

from product_catalog import max_kwp_from_roof_area, recommend_kwp_from_consumption

DEFAULT_YIELD = 950


def quick_estimate_range(
    monthly_kwh: float = 0,
    monthly_bill_eur: float = 0,
    electricity_price_ct: float = 32.0,
    roof_area_m2: float = 0,
    roof_type: str = "pitched_south",
    goals: list | None = None,
    specific_yield: float | None = None,
) -> dict:
    goals = goals or ["lower_bill"]
    yield_kwh = specific_yield or DEFAULT_YIELD

    if monthly_kwh > 0:
        annual_kwh = monthly_kwh * 12
    elif monthly_bill_eur > 0:
        annual_kwh = (monthly_bill_eur / (electricity_price_ct / 100)) * 12
    else:
        annual_kwh = 4000

    center = recommend_kwp_from_consumption(annual_kwh, yield_kwh, goals)
    low = max(2.0, round(center * 0.88, 1))
    high = min(40.0, round(center * 1.12, 1))

    roof_cap = max_kwp_from_roof_area(roof_area_m2) if roof_area_m2 > 0 else None
    if roof_cap is not None:
        high = min(high, roof_cap)
        low = min(low, high)
        if low > high:
            low = max(2.0, round(roof_cap * 0.85, 1))

    if high < low:
        high = low

    return {
        "kwp_min": low,
        "kwp_max": high,
        "kwp_typical": round((low + high) / 2, 1),
        "annual_kwh": round(annual_kwh),
        "specific_yield_kwh_kwp": round(yield_kwh),
        "roof_limited": roof_cap is not None and center > roof_cap,
        "message_en": f"Based on your details, a likely system range is {low:g}–{high:g} kWp.",
        "message_de": f"Basierend auf Ihren Angaben liegt eine wahrscheinliche Anlagengröße bei {low:g}–{high:g} kWp.",
    }
