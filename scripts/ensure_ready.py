"""Verify data files and print demo URLs — run before first launch."""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

FILES = {
    "customers.json": [],
    "quotes.json": [],
    "documents.json": [],
    "surveys.json": [],
    "assessments.json": [],
    "subscriptions.json": [],
    "intersolar_surveys.json": [],
    "intake_analytics.json": {},
}


def main() -> int:
    os.makedirs(DATA, exist_ok=True)
    for name, default in FILES.items():
        path = os.path.join(DATA, name)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(default, fh, indent=2)
            print(f"Created {name}")

    suppliers = os.path.join(DATA, "suppliers.json")
    if os.path.isfile(suppliers):
        with open(suppliers, encoding="utf-8") as fh:
            n = len(json.load(fh))
        print(f"Suppliers: {n:,}")
        if n == 0:
            print("WARNING: Run  python scripts/import_pvr_directory.py --skip-geocode")
            return 1
    else:
        print("WARNING: suppliers.json missing — run import script")
        return 1

    catalog = os.path.join(DATA, "product_catalog.json")
    if os.path.isfile(catalog):
        with open(catalog, encoding="utf-8") as fh:
            cat = json.load(fh)
        print(f"Product catalog: {len(cat.get('panels', []))} panels, {len(cat.get('inverters', []))} inverters")

    print("\nDemo intake link example (if supplier exists):")
    with open(suppliers, encoding="utf-8") as fh:
        for s in json.load(fh)[:5]:
            slug = s.get("intake_slug")
            if slug:
                print(f"  http://127.0.0.1:5000/i/{slug}")
                break

    print("\nReady. Run START.bat or: python app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
