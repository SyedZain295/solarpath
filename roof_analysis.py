"""Roof analysis — photo heuristics + optional Google Solar API."""

from __future__ import annotations

from google_solar_client import merge_solar_insights
from roof_photo_store import analyze_roof_set as _analyze_photo_set


def analyze_roof_request(data: dict) -> dict:
    set_id = (data.get("set_id") or data.get("roof_photo_set_id") or "").strip()
    hints = {
        "shading": data.get("shading"),
        "roof_area_m2": data.get("roof_area_m2"),
    }
    lat = data.get("latitude")
    lon = data.get("longitude")
    if lat is None and data.get("lat") is not None:
        lat = data.get("lat")
    if lon is None and data.get("lon") is not None:
        lon = data.get("lon")

    if set_id:
        result = _analyze_photo_set(set_id, hints=hints)
        if not result.get("ok"):
            return result
        return merge_solar_insights(result, lat, lon)

    if lat is not None and lon is not None:
        base = {
            "ok": True,
            "stub": False,
            "set_id": "",
            "photo_count": 0,
            "shading_suggestion": hints.get("shading") or "unknown",
            "roof_area_hint_m2": hints.get("roof_area_m2"),
            "has_meter_photo": False,
            "notes": ["Location-based analysis from Google Solar API."],
            "confidence": "medium",
        }
        return merge_solar_insights(base, float(lat), float(lon))

    return {
        "ok": False,
        "error": "Provide set_id or latitude/longitude for roof analysis",
    }
