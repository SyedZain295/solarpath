"""
Import PV installers from photovoltaik-vergleichsrechner.de (public regional directory).

Parses structured HTML (company name + city) from all 16 Bundesland pages,
geocodes unique cities via OpenPLZ + Nominatim, merges into data/suppliers.json.

Usage:
  python scripts/import_pvr_directory.py
  python scripts/import_pvr_directory.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from html import unescape

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pvgis_client import geocode_postcode  # noqa: E402

SUPPLIERS_FILE = os.path.join(ROOT, "data", "suppliers.json")
GEO_CACHE_FILE = os.path.join(ROOT, "data", "geo_cache.json")
BASE = "https://www.photovoltaik-vergleichsrechner.de"
HEADERS = {"User-Agent": "SolarPath/1.0 (solar installer directory import)"}

BUNDESLAENDER = [
    ("baden-wuerttemberg", "Baden-Württemberg"),
    ("bayern", "Bayern"),
    ("berlin", "Berlin"),
    ("brandenburg", "Brandenburg"),
    ("bremen", "Bremen"),
    ("hamburg", "Hamburg"),
    ("hessen", "Hessen"),
    ("mecklenburg-vorpommern", "Mecklenburg-Vorpommern"),
    ("niedersachsen", "Niedersachsen"),
    ("nordrhein-westfalen", "Nordrhein-Westfalen"),
    ("rheinland-pfalz", "Rheinland-Pfalz"),
    ("saarland", "Saarland"),
    ("sachsen", "Sachsen"),
    ("sachsen-anhalt", "Sachsen-Anhalt"),
    ("schleswig-holstein", "Schleswig-Holstein"),
    ("thueringen", "Thüringen"),
]

RESULT_BLOCK = re.compile(
    r'<a href="[^"]+" class="result[^"]*".*?</a>',
    re.S,
)
NAME_RE = re.compile(r'<div class="name ellipsis">([^<]+)</div>')
CITY_RE = re.compile(r'<div class="city">([^<]+)</div>')
DISTRICT_RE = re.compile(r'<div class="company ellipsis">([^<]*)</div>')


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:48] or "installer"


def extract_from_html(html: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for block in RESULT_BLOCK.findall(html):
        name_m = NAME_RE.search(block)
        city_m = CITY_RE.search(block)
        if not name_m or not city_m:
            continue
        company = unescape(name_m.group(1).strip())
        city = unescape(city_m.group(1).strip())
        district_m = DISTRICT_RE.search(block)
        district = unescape((district_m.group(1).strip() if district_m else "") or "")
        if len(company) < 3 or len(city) < 2:
            continue
        rows.append((company, city, district))
    return rows


def fetch_landkreis_slugs(state_slug: str) -> list[str]:
    url = f"{BASE}/{state_slug}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=90)
        resp.raise_for_status()
        return sorted(set(re.findall(r'href="(/landkreis-[^"]+)"', resp.text)))
    except Exception:
        return []


def fetch_bundesland(slug: str) -> list[tuple[str, str, str]]:
    return fetch_page(slug)


def fetch_page(path: str) -> list[tuple[str, str, str]]:
    url = f"{BASE}/{path.lstrip('/')}"
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=90)
            resp.raise_for_status()
            return extract_from_html(resp.text)
        except Exception as exc:
            print(f"  fetch {path} attempt {attempt + 1} failed: {exc}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return []


def load_geo_cache() -> dict:
    if os.path.isfile(GEO_CACHE_FILE):
        with open(GEO_CACHE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_geo_cache(cache: dict) -> None:
    with open(GEO_CACHE_FILE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=2)


def geocode_city(city: str, state: str, cache: dict, plz_cache: dict, fast: bool = False) -> dict | None:
    key = f"{city.lower()}|{state.lower()}"
    if key in cache:
        return cache[key] or None

    geo = None
    try:
        resp = requests.get(
            "https://openplzapi.org/de/Localities",
            params={"name": city, "limit": 15},
            headers=HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        rows = resp.json()
        match = None
        for row in rows:
            fs = (row.get("federalState") or {}).get("name", "")
            if fs.lower() == state.lower():
                match = row
                break
        if not match and rows:
            match = rows[0]
        if match:
            plz = match.get("postalCode")
            if plz:
                if fast:
                    geo = {"postal_code": plz}
                elif plz in plz_cache:
                    geo = dict(plz_cache[plz])
                else:
                    geo = geocode_postcode(plz, city=city)
                    if geo:
                        geo = dict(geo)
                        geo["postal_code"] = plz
                        plz_cache[plz] = geo
                    else:
                        geo = {"postal_code": plz}
                if geo:
                    geo = dict(geo)
                    geo["postal_code"] = plz
    except Exception as exc:
        print(f"  geocode fail {city}, {state}: {exc}", file=sys.stderr)

    cache[key] = geo
    time.sleep(0.08)
    return geo


def row_to_supplier(company: str, city: str, district: str, state: str, geo: dict | None) -> dict:
    sid = f"pvr-{slugify(company)}-{slugify(city)}"
    regions = [r for r in [city, district, state] if r]
    supplier = {
        "id": sid,
        "company_name": company,
        "email": "",
        "phone": "",
        "website": "",
        "plan": "basic",
        "verified": False,
        "locations_served": [],
        "regions": regions,
        "products": [{"name": "Photovoltaic system", "type": "system", "price_per_unit": 0, "warranty_years": 0}],
        "certifications": ["Public directory"],
        "installation_availability": "",
        "financing_options": [],
        "rating": None,
        "reviews_count": 0,
        "description": f"PV installer in {city}, {state} (public directory listing — contact via quote request).",
        "source": "photovoltaik-vergleichsrechner",
        "residential_available": True,
        "commercial_available": True,
        "battery_capable": True,
    }
    plz = (geo or {}).get("postal_code", "")
    if plz:
        supplier["locations_served"] = [plz]
    if geo and geo.get("latitude") is not None:
        supplier["latitude"] = geo["latitude"]
        supplier["longitude"] = geo["longitude"]
    return supplier


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fast", action="store_true", help="Postcodes only via OpenPLZ (skip Nominatim lat/lon)")
    parser.add_argument("--skip-geocode", action="store_true", help="Save immediately; geocode at search time in app")
    parser.add_argument("--landkreise", action="store_true", help="Also scrape all Landkreis listing pages")
    args = parser.parse_args()

    parsed: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for slug, state in BUNDESLAENDER:
        print(f"Fetching {state} ({slug})...", flush=True)
        rows = fetch_bundesland(slug)
        print(f"  {len(rows)} installers (state page)", flush=True)
        for company, city, district in rows:
            key = (company.lower(), city.lower(), state.lower())
            if key in seen:
                continue
            seen.add(key)
            parsed.append((company, city, district, state))
        if args.landkreise:
            slugs = fetch_landkreis_slugs(slug)
            print(f"  {len(slugs)} Landkreise...", flush=True)
            for lk in slugs:
                lk_rows = fetch_page(lk)
                for company, city, district in lk_rows:
                    key = (company.lower(), city.lower(), state.lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    parsed.append((company, city, district, state))
                time.sleep(0.3)
        time.sleep(0.5)

    print(f"Total unique installers: {len(parsed)}", flush=True)

    if args.dry_run:
        for row in parsed[:12]:
            print(f"  - {row[0]} | {row[1]}, {row[3]}")
        print(f"Unique cities: {len({(c, st) for _, c, _, st in parsed})}")
        return 0

    if args.skip_geocode:
        imported = [row_to_supplier(c, city, district, state, None) for c, city, district, state in parsed]
        print(f"Built {len(imported)} suppliers (geocoding deferred to search)", flush=True)
    else:
        geo_cache = load_geo_cache()
        plz_cache = {k: v for k, v in geo_cache.items() if k.isdigit() and len(k) == 5}
        city_cache = {k: v for k, v in geo_cache.items() if "|" in k}

        unique_cities = sorted({(city, state) for _, city, _, state in parsed})
        print(f"Geocoding {len(unique_cities)} cities...", flush=True)
        for i, (city, state) in enumerate(unique_cities, 1):
            geocode_city(city, state, city_cache, plz_cache, fast=args.fast)
            if i % 100 == 0:
                print(f"  {i}/{len(unique_cities)}", flush=True)
                save_geo_cache({**city_cache, **plz_cache})

        save_geo_cache({**city_cache, **plz_cache})

        imported = [
            row_to_supplier(c, city, district, state, city_cache.get(f"{city.lower()}|{state.lower()}"))
            for c, city, district, state in parsed
        ]
        with_geo = sum(1 for s in imported if s.get("latitude"))
        print(f"Built {len(imported)} suppliers ({with_geo} geocoded)", flush=True)

    existing = []
    if os.path.isfile(SUPPLIERS_FILE):
        with open(SUPPLIERS_FILE, encoding="utf-8") as fh:
            raw = fh.read().strip()
            if raw:
                existing = json.loads(raw)

    # Keep curated seed entries; replace prior PVR imports
    kept = [s for s in existing if s.get("source") != "photovoltaik-vergleichsrechner"]
    by_id = {s["id"]: s for s in kept}
    added = 0
    for row in imported:
        if row["id"] not in by_id:
            added += 1
        by_id[row["id"]] = row

    merged = list(by_id.values())
    with open(SUPPLIERS_FILE, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=2)

    print(f"Saved {len(merged)} total ({added} new PVR entries)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
