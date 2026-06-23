"""Quick fix: backfill coordinates for München metro suppliers."""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.backfill_city_coords import open_meteo, CACHE_FILE, SUPPLIERS_FILE  # noqa: E402

MUNICH_CENTER = {"latitude": 48.13743, "longitude": 11.57549}
MUNICH_POSTCODES = ["80331", "80333", "80335", "80336", "80469", "80636", "80796", "80801", "80992"]


def is_munich_metro(regions: list) -> bool:
    text = " ".join(regions).lower()
    return "münchen" in text or "muenchen" in text or "munich" in text


def main():
    with open(SUPPLIERS_FILE, encoding="utf-8") as fh:
        suppliers = json.load(fh)

    cache = {}
    if os.path.isfile(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as fh:
            cache = json.load(fh)

    cache["München|Bayern"] = MUNICH_CENTER
    updated = 0
    for s in suppliers:
        regions = s.get("regions") or []
        if not is_munich_metro(regions):
            continue
        city = regions[0]
        state = regions[-1] if len(regions) > 1 else "Bayern"
        key = f"{city}|{state}"
        geo = cache.get(key)
        if not geo or not geo.get("latitude"):
            geo = open_meteo(city, state) or (MUNICH_CENTER if city == "München" else None)
            if geo:
                cache[key] = geo
        if geo and geo.get("latitude"):
            s["latitude"] = geo["latitude"]
            s["longitude"] = geo["longitude"]
            if not s.get("locations_served") and city == "München":
                s["locations_served"] = ["80331"]
            updated += 1

    with open(CACHE_FILE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=2)
    with open(SUPPLIERS_FILE, "w", encoding="utf-8") as fh:
        json.dump(suppliers, fh, ensure_ascii=False, indent=2)

    print(f"Updated {updated} München metro suppliers")


if __name__ == "__main__":
    main()
