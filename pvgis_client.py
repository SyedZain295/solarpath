"""PVGIS API client for solar radiation and PV performance data."""

import json
import os
import re
from typing import Optional

import requests

_GERMAN_PLZ = re.compile(r"^\d{5}$")

PVGIS_BASE = "https://re.jrc.ec.europa.eu/api/v5_2"
_CACHE_FILE = os.path.join(os.path.dirname(__file__), "data", "pvgis_cache.json")
_CITY_COORDS_FILE = os.path.join(os.path.dirname(__file__), "data", "city_coords.json")
_pvgis_cache: dict | None = None
_plz_coord_index: dict[str, dict] | None = None


def _cache_key(lat: float, lon: float, peakpower: float, loss: float, angle: float, aspect: float) -> str:
    return f"{round(lat, 4)}_{round(lon, 4)}_{peakpower}_{loss}_{angle}_{aspect}"


def _load_pvgis_cache() -> dict:
    global _pvgis_cache
    if _pvgis_cache is not None:
        return _pvgis_cache
    try:
        with open(_CACHE_FILE, encoding="utf-8") as fh:
            _pvgis_cache = json.load(fh)
    except (OSError, json.JSONDecodeError):
        _pvgis_cache = {}
    return _pvgis_cache


def _save_pvgis_cache(key: str, value: dict) -> None:
    cache = _load_pvgis_cache()
    cache[key] = value
    if len(cache) > 500:
        for old_key in list(cache.keys())[: len(cache) - 500]:
            del cache[old_key]
    os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
    with open(_CACHE_FILE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh)


def get_pv_estimate(
    lat: float,
    lon: float,
    peakpower: float = 1.0,
    loss: float = 14.0,
    angle: float = 35.0,
    aspect: float = 0.0,
) -> Optional[dict]:
    """
    Query PVGIS PVcalc tool for annual and monthly PV production.
    Returns specific yield (kWh/kWp) and monthly breakdown per kWp.
    Results are cached locally by location and roof parameters.
    """
    key = _cache_key(lat, lon, peakpower, loss, angle, aspect)
    cached = _load_pvgis_cache().get(key)
    if cached:
        return {**cached, "cached": True}

    params = {
        "lat": lat,
        "lon": lon,
        "peakpower": peakpower,
        "loss": loss,
        "angle": angle,
        "aspect": aspect,
        "outputformat": "json",
    }
    try:
        from retry_utils import retry_http

        def _fetch():
            resp = requests.get(f"{PVGIS_BASE}/PVcalc", params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()

        data = retry_http(_fetch, attempts=3, exceptions=(requests.RequestException, ValueError))
        if not data:
            return None

        outputs = data.get("outputs", {})
        totals = outputs.get("totals", {}).get("fixed", {})
        monthly = outputs.get("monthly", {}).get("fixed", [])

        annual_kwh = totals.get("E_y", 0)
        specific_yield = annual_kwh / peakpower if peakpower > 0 else annual_kwh

        monthly_production = []
        if monthly:
            monthly_production = [m.get("E_m", 0) for m in monthly]

        result = {
            "annual_production_kwh": round(annual_kwh, 1),
            "specific_yield_kwh_kwp": round(specific_yield, 1),
            "monthly_production_kwh": [round(m, 1) for m in monthly_production],
            "solar_radiation_kwh_m2": round(totals.get("H_y", 0), 1),
            "optimal_angle": outputs.get("mounting_system", {}).get("fixed", {}).get("slope", angle),
            "source": "PVGIS v5.2 (EU Joint Research Centre)",
        }
        _save_pvgis_cache(key, result)
        return {**result, "cached": False}
    except Exception:
        return None


def roof_type_to_pvgis_params(roof_type: str) -> tuple[float, float]:
    """Map roof type to tilt angle and aspect (azimuth)."""
    mapping = {
        "flat": (10, 0),
        "pitched_south": (35, 0),
        "pitched_east_west": (35, 90),
        "pitched_north": (35, 180),
        "metal": (30, 0),
        "tile": (35, 0),
        "slate": (40, 0),
        "ground_mount": (25, 0),
        "balcony": (90, 0),
    }
    return mapping.get(roof_type, (35, 0))


def _nominatim_hit(result: dict) -> dict:
    return {
        "latitude": float(result["lat"]),
        "longitude": float(result["lon"]),
        "display_name": result["display_name"],
    }


def _open_meteo_search(name: str) -> Optional[dict]:
    try:
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": name, "count": 1, "language": "de", "countryCode": "DE"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
        if not results:
            return None
        hit = results[0]
        admin = hit.get("admin1") or ""
        display = f"{hit['name']}, {admin}, Deutschland".strip(", ")
        return {
            "latitude": float(hit["latitude"]),
            "longitude": float(hit["longitude"]),
            "display_name": display,
        }
    except Exception:
        return None


def _plz_lookup_city(plz: str) -> Optional[str]:
    try:
        resp = requests.get(
            "https://openplzapi.org/de/Localities",
            params={"postalCode": plz, "limit": 1},
            headers={"User-Agent": "SolarPreAssessment/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json()
        if rows:
            return rows[0].get("name")
    except Exception:
        pass
    return None


def _load_plz_coord_index() -> dict[str, dict]:
    """Build PLZ → coords index from data/city_coords.json (offline fallback)."""
    global _plz_coord_index
    if _plz_coord_index is not None:
        return _plz_coord_index
    index: dict[str, dict] = {}
    try:
        with open(_CITY_COORDS_FILE, encoding="utf-8") as fh:
            raw = json.load(fh)
        for key, geo in raw.items():
            if not isinstance(geo, dict):
                continue
            lat = geo.get("latitude")
            lon = geo.get("longitude")
            if lat is None or lon is None:
                continue
            postal = str(geo.get("postal_code") or "").strip()
            if postal:
                index.setdefault(postal, geo)
            if "|" in key:
                plz_part = key.split("|", 1)[0].strip()
                if _GERMAN_PLZ.match(plz_part):
                    index.setdefault(plz_part, geo)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    _plz_coord_index = index
    return index


def _lookup_plz_in_city_coords(plz: str) -> Optional[dict]:
    geo = _load_plz_coord_index().get(plz)
    if not geo:
        return None
    name = geo.get("display_name") or f"{plz}, Deutschland"
    return {
        "latitude": float(geo["latitude"]),
        "longitude": float(geo["longitude"]),
        "display_name": name,
    }


def geocode_postcode(postcode: str, city: str = "") -> Optional[dict]:
    """Geocode a German PLZ (5-digit post code)."""
    plz = postcode.strip()
    if not _GERMAN_PLZ.match(plz):
        return None

    queries = [f"{plz}, Deutschland", plz]
    city = city.strip()
    if city:
        queries.insert(0, f"{plz}, {city}, Deutschland")

    for query in queries:
        result = _nominatim_search(query, plz)
        if result:
            return result

    lookup_city = city or _plz_lookup_city(plz) or ""
    if lookup_city:
        result = _open_meteo_search(lookup_city)
        if result:
            return result

    return _lookup_plz_in_city_coords(plz)


def _nominatim_search(query: str, plz: str) -> Optional[dict]:
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "json",
                "limit": 5,
                "countrycodes": "de",
                "addressdetails": 1,
            },
            headers={"User-Agent": "SolarPreAssessment/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None

        for result in results:
            address = result.get("address", {})
            if address.get("postcode") == plz:
                return _nominatim_hit(result)
            if result.get("display_name", "").startswith(plz):
                return _nominatim_hit(result)

        return _nominatim_hit(results[0])
    except Exception:
        return None


def geocode_location(query: str) -> Optional[dict]:
    """Geocode a location name using Nominatim (OpenStreetMap)."""
    raw = query.strip()
    if _GERMAN_PLZ.match(raw):
        return geocode_postcode(raw)

    plz = raw.split(",")[0].strip()
    if _GERMAN_PLZ.match(plz) and raw.lower().endswith(("germany", "deutschland")):
        return geocode_postcode(plz)

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "SolarPreAssessment/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            return _nominatim_hit(results[0])
    except Exception:
        pass

    name = query.split(",")[0].strip()
    return _open_meteo_search(name)
