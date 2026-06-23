"""One-time backfill: add lat/lon to suppliers from city names via Open-Meteo."""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SUPPLIERS_FILE = os.path.join(ROOT, "data", "suppliers.json")
CACHE_FILE = os.path.join(ROOT, "data", "city_coords.json")


KNOWN_CITY_COORDS = {
    "münchen|bayern": {"latitude": 48.13743, "longitude": 11.57549},
    "muenchen|bayern": {"latitude": 48.13743, "longitude": 11.57549},
    "berlin|berlin": {"latitude": 52.52, "longitude": 13.405},
    "hamburg|hamburg": {"latitude": 53.5511, "longitude": 9.9937},
    "köln|nordrhein-westfalen": {"latitude": 50.9375, "longitude": 6.9603},
    "koeln|nordrhein-westfalen": {"latitude": 50.9375, "longitude": 6.9603},
    "frankfurt am main|hessen": {"latitude": 50.1109, "longitude": 8.6821},
    "stuttgart|baden-württemberg": {"latitude": 48.7758, "longitude": 9.1829},
    "düsseldorf|nordrhein-westfalen": {"latitude": 51.2277, "longitude": 6.7735},
    "duesseldorf|nordrhein-westfalen": {"latitude": 51.2277, "longitude": 6.7735},
    "leipzig|sachsen": {"latitude": 51.3397, "longitude": 12.3731},
    "dresden|sachsen": {"latitude": 51.0504, "longitude": 13.7373},
    "hannover|niedersachsen": {"latitude": 52.3759, "longitude": 9.7320},
    "nürnberg|bayern": {"latitude": 49.4521, "longitude": 11.0767},
    "nuernberg|bayern": {"latitude": 49.4521, "longitude": 11.0767},
    "bremen|bremen": {"latitude": 53.0793, "longitude": 8.8017},
    "pfarrkirchen|bayern": {"latitude": 48.43205, "longitude": 12.93812},
}


def city_lookup_name(city: str) -> str:
    return city.split(",")[0].strip()


def admin1_matches(admin1: str, state: str) -> bool:
    if not admin1 or not state:
        return True
    a, s = admin1.lower(), state.lower()
    if a == s or s in a or a in s:
        return True
    aliases = {
        "bavaria": "bayern",
        "north rhine-westphalia": "nordrhein-westfalen",
        "lower saxony": "niedersachsen",
        "rhineland-palatinate": "rheinland-pfalz",
        "saxony-anhalt": "sachsen-anhalt",
        "mecklenburg-western pomerania": "mecklenburg-vorpommern",
        "thuringia": "thüringen",
    }
    return aliases.get(a) == s or aliases.get(s) == a


def openplz_postcode(city: str, state: str) -> str | None:
    try:
        r = requests.get(
            "https://openplzapi.org/de/Localities",
            params={"name": city_lookup_name(city), "limit": 10},
            timeout=12,
        )
        r.raise_for_status()
        for row in r.json():
            fs = (row.get("federalState") or {}).get("name", "")
            if fs.lower() == state.lower():
                return row.get("postalCode")
        rows = r.json()
        return rows[0].get("postalCode") if rows else None
    except Exception:
        return None


def open_meteo(city: str, state: str = "") -> dict | None:
    key = f"{city_lookup_name(city).lower()}|{state.lower()}"
    if key in KNOWN_CITY_COORDS:
        return dict(KNOWN_CITY_COORDS[key])
    for name in (city_lookup_name(city), city):
        try:
            r = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": name, "count": 10, "language": "de", "countryCode": "DE"},
                timeout=10,
            )
            r.raise_for_status()
            rows = r.json().get("results") or []
            if state:
                for hit in rows:
                    if admin1_matches(hit.get("admin1", ""), state):
                        plz = (hit.get("postcodes") or [None])[0]
                        return {
                            "latitude": hit["latitude"],
                            "longitude": hit["longitude"],
                            "postal_code": plz,
                        }
            if rows:
                hit = rows[0]
                plz = (hit.get("postcodes") or [None])[0]
                return {
                    "latitude": hit["latitude"],
                    "longitude": hit["longitude"],
                    "postal_code": plz,
                }
        except Exception:
            continue
    return None


def main():
    with open(SUPPLIERS_FILE, encoding="utf-8") as fh:
        suppliers = json.load(fh)

    cache = {}
    if os.path.isfile(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as fh:
            cache = json.load(fh)

    unique = sorted({
        (s["regions"][0], s["regions"][-1])
        for s in suppliers
        if s.get("regions") and len(s["regions"]) >= 2
    })
    print(f"Unique cities: {len(unique)}", flush=True)

    pending: list[tuple[str, str, str]] = []
    for city, state in unique:
        key = f"{city}|{state}"
        cached = cache.get(key)
        if cached is None or not cached.get("latitude"):
            pending.append((key, city, state))

    # Geocode once per parent city (e.g. all "Aachen, …" districts share Aachen)
    by_parent: dict[tuple[str, str], list[str]] = {}
    for key, city, state in pending:
        parent = (city_lookup_name(city), state)
        by_parent.setdefault(parent, []).append(key)

    print(f"Fetching {len(by_parent)} parent cities ({len(pending)} cache keys)...", flush=True)

    def fetch_parent(city: str, state: str) -> dict | None:
        geo = open_meteo(city, state)
        if not geo or not geo.get("latitude"):
            plz = openplz_postcode(city, state)
            if plz:
                geo = geo or {}
                geo["postal_code"] = plz
                retry = open_meteo(city, state)
                if retry and retry.get("latitude"):
                    geo.update(retry)
        if geo and not geo.get("postal_code"):
            plz = openplz_postcode(city, state)
            if plz:
                geo["postal_code"] = plz
        return geo

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {
            pool.submit(fetch_parent, city, state): (city, state, keys)
            for (city, state), keys in by_parent.items()
        }
        done = 0
        for fut in as_completed(futures):
            city, state, keys = futures[fut]
            geo = fut.result()
            for key in keys:
                cache[key] = geo
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(by_parent)}", flush=True)
                with open(CACHE_FILE, "w", encoding="utf-8") as fh:
                    json.dump(cache, fh, ensure_ascii=False, indent=2)

    with open(CACHE_FILE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh)

    updated = 0
    for s in suppliers:
        regions = s.get("regions") or []
        if len(regions) < 2:
            continue
        geo = cache.get(f"{regions[0]}|{regions[-1]}")
        if geo and geo.get("latitude"):
            s["latitude"] = geo["latitude"]
            s["longitude"] = geo["longitude"]
            plz = geo.get("postal_code")
            if plz and not s.get("locations_served"):
                s["locations_served"] = [plz]
            updated += 1

    with open(SUPPLIERS_FILE, "w", encoding="utf-8") as fh:
        json.dump(suppliers, fh, ensure_ascii=False, indent=2)

    print(f"Updated {updated}/{len(suppliers)} suppliers with coordinates", flush=True)


if __name__ == "__main__":
    main()
