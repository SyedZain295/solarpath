"""Google Solar API — building insights for roof analysis (optional API key)."""

from __future__ import annotations

import os
from typing import Optional

import requests

SOLAR_API_BASE = "https://solar.googleapis.com/v1"


def solar_api_configured() -> bool:
    return bool(os.environ.get("GOOGLE_SOLAR_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY"))


def _api_key() -> str:
    return (os.environ.get("GOOGLE_SOLAR_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY") or "").strip()


def fetch_building_insights(lat: float, lon: float) -> Optional[dict]:
    key = _api_key()
    if not key:
        return None
    try:
        resp = requests.get(
            f"{SOLAR_API_BASE}/buildingInsights:findClosest",
            params={
                "location.latitude": lat,
                "location.longitude": lon,
                "requiredQuality": "MEDIUM",
            },
            headers={"X-Goog-Api-Key": key},
            timeout=20,
        )
        if not resp.ok:
            return None
        data = resp.json()
        solar = data.get("solarPotential") or {}
        panels = int(solar.get("maxArrayPanelsCount") or 0)
        panel_w = float(solar.get("panelCapacityWatts") or 400)
        max_kwp = round(panels * panel_w / 1000, 1) if panels else 0
        sunshine = solar.get("maxSunshineHoursPerYear")
        segments = solar.get("roofSegmentStats") or []
        usable_m2 = 0.0
        for seg in segments:
            stats = seg.get("stats") or {}
            area = stats.get("areaMeters2") or stats.get("groundAreaMeters2")
            if area:
                usable_m2 += float(area)
        shading = "none"
        if segments:
            avg_pitch = sum(float(s.get("pitchDegrees") or 0) for s in segments) / len(segments)
            if avg_pitch < 5:
                shading = "partial"
        return {
            "source": "google_solar_api",
            "stub": False,
            "max_system_kwp": max_kwp,
            "max_panels": panels,
            "panel_watts": panel_w,
            "max_sunshine_hours_per_year": sunshine,
            "roof_segments": len(segments),
            "estimated_roof_area_m2": round(usable_m2, 1) if usable_m2 else None,
            "shading_suggestion": shading,
            "imagery_date": (data.get("imageryDate") or {}).get("year"),
            "center": data.get("center"),
        }
    except Exception:
        return None


def merge_solar_insights(base: dict, lat: float | None, lon: float | None) -> dict:
    """Enrich heuristic roof analysis with Google Solar when coordinates available."""
    if lat is None or lon is None:
        base["google_solar"] = {"configured": solar_api_configured(), "available": False}
        return base
    insights = fetch_building_insights(float(lat), float(lon))
    if not insights:
        base["google_solar"] = {
            "configured": solar_api_configured(),
            "available": False,
            "message": "Google Solar API unavailable — using photo heuristics only.",
        }
        return base
    base["google_solar"] = {"configured": True, "available": True, **insights}
    base["stub"] = False
    base["source"] = "photo_heuristic+google_solar"
    if insights.get("max_system_kwp"):
        base["max_system_kwp_hint"] = insights["max_system_kwp"]
    if insights.get("estimated_roof_area_m2") and not base.get("roof_area_hint_m2"):
        base["roof_area_hint_m2"] = insights["estimated_roof_area_m2"]
    if insights.get("shading_suggestion") and base.get("shading_suggestion") in ("unknown", None):
        base["shading_suggestion"] = insights["shading_suggestion"]
    if base.get("confidence") == "low" and insights.get("roof_segments", 0) >= 2:
        base["confidence"] = "medium"
    base["notes"] = list(base.get("notes") or [])
    base["notes"].append(
        f"Google Solar estimates up to ~{insights['max_system_kwp']} kWp "
        f"({insights['max_panels']} panels) at this address."
    )
    return base
