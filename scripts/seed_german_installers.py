"""
Build data/suppliers.json from data/installer_seed.json with geocoded coordinates.

Usage:
  python scripts/seed_german_installers.py
  python scripts/seed_german_installers.py --replace   # drop existing, use seed only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pvgis_client import geocode_postcode  # noqa: E402

SEED_FILE = os.path.join(ROOT, "data", "installer_seed.json")
SUPPLIERS_FILE = os.path.join(ROOT, "data", "suppliers.json")


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:36] or "installer"


def seed_to_supplier(row: dict, geo: dict | None) -> dict:
    plz = row["postcode"]
    city = row.get("city", "")
    website = row.get("website", "")
    domain = ""
    if website:
        domain = re.sub(r"^https?://(www\.)?", "", website).split("/")[0]

    email = f"info@{domain}" if domain else f"kontakt@{slugify(row['company_name'])}.de"

    supplier = {
        "id": f"sup-{slugify(row['company_name'])}",
        "company_name": row["company_name"],
        "email": email,
        "phone": row.get("phone", "—"),
        "website": website,
        "plan": row.get("plan", "basic"),
        "verified": row.get("verified", True),
        "locations_served": [plz],
        "regions": [r for r in [city, row.get("state", "")] if r],
        "products": [
            {
                "name": "Residential PV system",
                "type": "system",
                "price_per_unit": 0,
                "warranty_years": 0,
            }
        ],
        "certifications": row.get("certifications", ["VDE"]),
        "installation_availability": row.get("installation_availability", "2-6 weeks"),
        "financing_options": row.get("financing_options", []),
        "rating": row.get("rating", 4.0),
        "reviews_count": row.get("reviews_count", 0),
        "description": row.get("description", f"Photovoltaic installer in {city}."),
        "source": "public_directory",
        "residential_available": True,
        "commercial_available": row.get("commercial_available", True),
        "battery_capable": True,
        "ev_charger_capable": row.get("ev_charger_capable", False),
        "heat_pump_capable": row.get("heat_pump_capable", False),
        "agricultural_available": row.get("agricultural_available", False),
    }

    if geo:
        supplier["latitude"] = geo["latitude"]
        supplier["longitude"] = geo["longitude"]

    return supplier


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replace", action="store_true", help="Replace suppliers.json entirely")
    args = parser.parse_args()

    with open(SEED_FILE, encoding="utf-8") as fh:
        seed = json.load(fh)

    geo_cache: dict[str, dict | None] = {}
    suppliers: list[dict] = []
    failed: list[str] = []

    for i, row in enumerate(seed, 1):
        plz = row["postcode"]
        city = row.get("city", "")
        cache_key = f"{plz}:{city.lower()}"
        if cache_key not in geo_cache:
            geo_cache[cache_key] = geocode_postcode(plz, city=city)
            time.sleep(1.1)
        geo = geo_cache[cache_key]
        if not geo:
            failed.append(f"{row['company_name']} ({plz})")
        suppliers.append(seed_to_supplier(row, geo))
        print(f"  [{i}/{len(seed)}] {row['company_name']}", flush=True)

    if failed:
        print(f"Warning: {len(failed)} entries without coordinates:")
        for name in failed[:10]:
            print(f"  - {name}")

    if args.replace:
        final = suppliers
    else:
        existing = []
        if os.path.isfile(SUPPLIERS_FILE):
            with open(SUPPLIERS_FILE, encoding="utf-8") as fh:
                existing = json.load(fh)
        by_id = {s["id"]: s for s in existing}
        for s in suppliers:
            by_id[s["id"]] = s
        final = list(by_id.values())

    with open(SUPPLIERS_FILE, "w", encoding="utf-8") as fh:
        json.dump(final, fh, ensure_ascii=False, indent=2)

    with_coords = sum(1 for s in final if s.get("latitude"))
    print(f"Saved {len(final)} suppliers ({with_coords} with coordinates) to {SUPPLIERS_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
