"""Global Solar Atlas cross-validation layer (optional yield check vs PVGIS)."""

from __future__ import annotations

import requests
from typing import Optional

# GSA LTA endpoint (World Bank) — used for validation, not primary sizing
GSA_LTA_URL = "https://globalsolaratlas.info/api/data/lta"


def get_gsa_yield_estimate(lat: float, lon: float) -> Optional[dict]:
    """
    Fetch long-term average PVOUT from Global Solar Atlas for cross-check.
    Falls back to regional estimate if API unavailable.
    """
    try:
        resp = requests.get(
            GSA_LTA_URL,
            params={"loc": f"{lat},{lon}"},
            timeout=12,
            headers={"Accept": "application/json"},
        )
        if resp.ok:
            data = resp.json()
            # PVOUT: kWh/kWp/year (annual PV power output per kWp)
            pvout = data.get("annual", {}).get("PVOUT_csi") or data.get("PVOUT_csi")
            if pvout:
                return {
                    "specific_yield_kwh_kwp": round(float(pvout), 1),
                    "source": "Global Solar Atlas",
                    "raw": data,
                }
    except Exception:
        pass

    # Regional fallback for Germany/Bavaria band (~950–1100 kWh/kWp)
    base = 980 + (48.5 - abs(lat - 48.5)) * 8 + (lon - 11.0) * 2
    base = max(850, min(1150, base))
    return {
        "specific_yield_kwh_kwp": round(base, 1),
        "source": "GSA regional estimate (API unavailable)",
        "stub": True,
    }


def validate_yield(pvgis_yield: float, gsa_yield: float) -> dict:
    """Compare PVGIS vs GSA yields; flag large deltas."""
    if not pvgis_yield or not gsa_yield:
        return {"delta_pct": None, "warning": False, "message_key": "yield.no_comparison"}
    delta_pct = round((pvgis_yield - gsa_yield) / gsa_yield * 100, 1)
    warning = abs(delta_pct) > 12
    return {
        "pvgis_yield": round(pvgis_yield, 1),
        "gsa_yield": round(gsa_yield, 1),
        "delta_pct": delta_pct,
        "warning": warning,
        "message_key": "yield.gsa_warning" if warning else "yield.gsa_ok",
        "confidence_adjustment": -5 if warning else 0,
    }
