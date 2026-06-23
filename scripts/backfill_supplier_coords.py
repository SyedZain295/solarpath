"""Embed latitude/longitude on suppliers from city_coords cache for faster nationwide search."""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import resolve_supplier_coords  # noqa: E402

SUPPLIERS_FILE = os.path.join(ROOT, "data", "suppliers.json")
CITY_COORDS_FILE = os.path.join(ROOT, "data", "city_coords.json")


def main() -> int:
    with open(SUPPLIERS_FILE, encoding="utf-8") as fh:
        suppliers = json.load(fh)

    with open(CITY_COORDS_FILE, encoding="utf-8") as fh:
        city_coords = json.load(fh)

    updated = 0
    plz_added = 0
    for s in suppliers:
        lat, lon = resolve_supplier_coords(s)
        if lat is not None and (s.get("latitude") is None or s.get("longitude") is None):
            s["latitude"] = lat
            s["longitude"] = lon
            updated += 1

        if not s.get("locations_served"):
            regions = s.get("regions") or []
            if len(regions) >= 2:
                city, state = regions[0], regions[-1]
                for key in (f"{city}|{state}", f"{city.split(',')[0].strip()}|{state}"):
                    geo = city_coords.get(key)
                    if geo and geo.get("postal_code"):
                        s["locations_served"] = [geo["postal_code"]]
                        plz_added += 1
                        break

    with open(SUPPLIERS_FILE, "w", encoding="utf-8") as fh:
        json.dump(suppliers, fh, ensure_ascii=False, indent=2)

    with_coords = sum(1 for s in suppliers if s.get("latitude") is not None)
    print(f"Updated coords on {updated} suppliers")
    print(f"Added postcodes on {plz_added} suppliers")
    print(f"Total with lat/lon: {with_coords} / {len(suppliers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
