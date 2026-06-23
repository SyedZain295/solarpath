"""Apply existing city_coords.json to suppliers without API calls."""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUPPLIERS_FILE = os.path.join(ROOT, "data", "suppliers.json")
CACHE_FILE = os.path.join(ROOT, "data", "city_coords.json")


def main():
    with open(SUPPLIERS_FILE, encoding="utf-8") as fh:
        suppliers = json.load(fh)
    with open(CACHE_FILE, encoding="utf-8") as fh:
        cache = json.load(fh)

    updated = 0
    for s in suppliers:
        regions = s.get("regions") or []
        if len(regions) < 2:
            continue
        geo = cache.get(f"{regions[0]}|{regions[-1]}")
        if not geo or not geo.get("latitude"):
            continue
        s["latitude"] = geo["latitude"]
        s["longitude"] = geo["longitude"]
        plz = geo.get("postal_code")
        if plz and not s.get("locations_served"):
            s["locations_served"] = [plz]
        updated += 1

    with open(SUPPLIERS_FILE, "w", encoding="utf-8") as fh:
        json.dump(suppliers, fh, ensure_ascii=False, indent=2)
    print(f"Applied coords to {updated}/{len(suppliers)} suppliers")


if __name__ == "__main__":
    main()
