"""
Import German PV installers from OpenStreetMap into data/suppliers.json.

Uses Overpass API (craft=solar_installer, shop=solar) — real public business data,
not scraped from Google. Re-run to refresh; merges by OSM id without duplicating.

Usage:
  python scripts/import_osm_installers.py
  python scripts/import_osm_installers.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUPPLIERS_FILE = os.path.join(ROOT, "data", "suppliers.json")
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# Germany tiles (coarse)
TILES_DE = [
    (47.2, 5.8, 49.2, 10.5),
    (47.2, 10.5, 49.2, 15.2),
    (49.2, 5.8, 51.2, 10.5),
    (49.2, 10.5, 51.2, 15.2),
    (51.2, 5.8, 53.2, 10.5),
    (51.2, 10.5, 53.2, 15.2),
    (53.2, 5.8, 55.2, 10.5),
    (53.2, 10.5, 55.2, 15.2),
]

# Bavaria — smaller tiles for reliable Overpass responses
TILES_BAYERN = [
    (47.27, 8.98, 48.40, 11.40),
    (47.27, 11.40, 48.40, 13.84),
    (48.40, 8.98, 49.60, 11.40),
    (48.40, 11.40, 49.60, 13.84),
    (49.60, 8.98, 50.56, 11.40),
    (49.60, 11.40, 50.56, 13.84),
]

PLZ_RE = re.compile(r"^\d{5}$")


def overpass_tile(south: float, west: float, north: float, east: float) -> list[dict]:
    query = f"""
[out:json][timeout:120];
(
  node["craft"="photovoltaic"]({south},{west},{north},{east});
  way["craft"="photovoltaic"]({south},{west},{north},{east});
  node["craft"="solar_installer"]({south},{west},{north},{east});
  way["craft"="solar_installer"]({south},{west},{north},{east});
  node["shop"="solar"]({south},{west},{north},{east});
  way["shop"="solar"]({south},{west},{north},{east});
  node["craft"="electrician"]["name"~"Solar|Photovoltaik|Solartechnik|PV ",i]({south},{west},{north},{east});
  way["craft"="electrician"]["name"~"Solar|Photovoltaik|Solartechnik|PV ",i]({south},{west},{north},{east});
);
out center tags;
"""
    last_exc: Exception | None = None
    for url in OVERPASS_ENDPOINTS:
        for attempt in range(2):
            try:
                resp = requests.post(
                    url,
                    data=query.encode("utf-8"),
                    headers={
                        "User-Agent": "SolarPath/1.0 (installer import)",
                        "Content-Type": "text/plain; charset=utf-8",
                    },
                    timeout=180,
                )
                resp.raise_for_status()
                return resp.json().get("elements", [])
            except Exception as exc:
                last_exc = exc
                print(f"  {url} attempt {attempt + 1} failed: {exc}", file=sys.stderr)
                time.sleep(3 * (attempt + 1))
    if last_exc:
        print(f"  tile skipped after all endpoints failed: {last_exc}", file=sys.stderr)
    return []


def element_coords(element: dict) -> tuple[float | None, float | None]:
    if element.get("lat") and element.get("lon"):
        return float(element["lat"]), float(element["lon"])
    center = element.get("center") or {}
    if center.get("lat") and center.get("lon"):
        return float(center["lat"]), float(center["lon"])
    return None, None


def normalize_phone(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith("+"):
        return raw
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("49"):
        return "+" + digits
    if digits.startswith("0"):
        return "+49 " + digits[1:]
    return raw


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:40] or "installer"


def osm_to_supplier(element: dict) -> dict | None:
    tags = element.get("tags") or {}
    name = (tags.get("name") or tags.get("brand") or "").strip()
    if not name:
        return None

    lat, lon = element_coords(element)
    if lat is None or lon is None:
        return None

    postcode = (tags.get("addr:postcode") or tags.get("postal_code") or "").strip()
    city = (tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village") or "").strip()
    state = (tags.get("addr:state") or tags.get("is_in:state") or "").strip()
    phone = normalize_phone(tags.get("phone") or tags.get("contact:phone") or "")
    website = (tags.get("website") or tags.get("contact:website") or "").strip()
    email = (tags.get("email") or tags.get("contact:email") or "").strip()
    if email and ("@" not in email or email.endswith(".local")):
        email = ""

    osm_id = f"osm-{element.get('type', 'node')}-{element.get('id')}"

    locations = [postcode] if PLZ_RE.match(postcode) else []
    regions = [r for r in [city, state] if r]
    if state and state not in regions:
        regions.append(state)
    elif not state and 47.27 <= lat <= 50.56 and 8.98 <= lon <= 13.84:
        regions.append("Bayern")

    description_parts = ["Photovoltaic installer listed in OpenStreetMap."]
    if city:
        description_parts.append(f"Based in {city}.")
    if tags.get("craft") == "solar_installer":
        description_parts.append("Solar installation specialist.")

    return {
        "id": osm_id,
        "company_name": name,
        "email": email,
        "phone": phone or "",
        "website": website,
        "plan": "basic",
        "verified": bool(phone and website),
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "locations_served": locations,
        "regions": regions,
        "products": [
            {
                "name": "Residential PV system",
                "type": "system",
                "price_per_unit": 0,
                "warranty_years": 0,
            }
        ],
        "certifications": ["OSM listed"],
        "installation_availability": "",
        "financing_options": [],
        "rating": None,
        "reviews_count": 0,
        "description": " ".join(description_parts),
        "source": "openstreetmap",
        "osm_id": element.get("id"),
        "residential_available": True,
        "commercial_available": True,
        "battery_capable": True,
    }


def load_suppliers() -> list[dict]:
    if not os.path.isfile(SUPPLIERS_FILE):
        return []
    with open(SUPPLIERS_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def save_suppliers(suppliers: list[dict]) -> None:
    os.makedirs(os.path.dirname(SUPPLIERS_FILE), exist_ok=True)
    with open(SUPPLIERS_FILE, "w", encoding="utf-8") as fh:
        json.dump(suppliers, fh, ensure_ascii=False, indent=2)


def merge_suppliers(existing: list[dict], imported: list[dict]) -> list[dict]:
    by_id = {s["id"]: s for s in existing}
    added = 0
    updated = 0
    for row in imported:
        if row["id"] in by_id:
            prev = by_id[row["id"]]
            merged = {**prev, **row}
            # Keep demo/example emails if already verified demo data
            if prev.get("email", "").endswith(".example"):
                merged["email"] = prev["email"]
            by_id[row["id"]] = merged
            updated += 1
        else:
            by_id[row["id"]] = row
            added += 1
    print(f"Added {added}, updated {updated}, total {len(by_id)}")
    return list(by_id.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Import OSM solar installers into suppliers.json")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and report counts without writing")
    parser.add_argument("--bayern", action="store_true", help="Import Bavaria tiles only (faster, recommended)")
    parser.add_argument("--germany", action="store_true", help="Import all Germany tiles (slow)")
    args = parser.parse_args()

    tiles = TILES_BAYERN
    if args.germany:
        tiles = TILES_DE
    elif not args.bayern and not args.germany:
        tiles = TILES_BAYERN  # default to Bavaria for SolarPath focus

    seen: set[str] = set()
    imported: list[dict] = []

    for i, tile in enumerate(tiles, 1):
        print(f"Tile {i}/{len(tiles)} {tile}...", flush=True)
        elements = overpass_tile(*tile)
        print(f"  {len(elements)} elements", flush=True)
        for element in elements:
            supplier = osm_to_supplier(element)
            if not supplier or supplier["id"] in seen:
                continue
            seen.add(supplier["id"])
            imported.append(supplier)
        time.sleep(2)

    print(f"Unique installers from OSM: {len(imported)}")

    if args.dry_run:
        for s in imported[:10]:
            print(f"  - {s['company_name']} ({s.get('latitude')}, {s.get('longitude')}) {s['locations_served']}")
        return 0

    existing = load_suppliers()
    merged = merge_suppliers(existing, imported)
    save_suppliers(merged)
    print(f"Saved to {SUPPLIERS_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
