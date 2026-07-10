"""
Match PVR directory listings to OpenStreetMap entries and copy real contact data.

Also strips fake ratings where reviews_count is zero.

Usage:
  python scripts/enrich_pvr_from_osm.py
  python scripts/enrich_pvr_from_osm.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from supplier_utils import is_placeholder_email, is_placeholder_phone  # noqa: E402

SUPPLIERS_FILE = os.path.join(ROOT, "data", "suppliers.json")

COMPANY_SUFFIXES = re.compile(
    r"\b(gmbh|mbh|ag|kg|co\.?\s*kg|e\.?\s*k\.?|ohg|gbr|ug|inc|ltd|&+\s*co\.?)\b",
    re.I,
)

FUZZY_MIN_RATIO = 0.85
FUZZY_MIN_SCORE = 80
MIN_RATIO_WITHOUT_CITY = 0.92


def reset_osm_enrichment(pvr: dict) -> bool:
    src = pvr.get("source") or ""
    if "+openstreetmap" not in src:
        return False
    slug = re.sub(r"[^a-z0-9]", "", normalize_company(pvr.get("company_name", "installer")))[:40] or "installer"
    pvr["phone"] = "—"
    pvr["email"] = f"kontakt@{slug}.de"
    pvr["website"] = ""
    pvr["verified"] = False
    pvr["source"] = "photovoltaik-vergleichsrechner"
    pvr["certifications"] = [c for c in (pvr.get("certifications") or []) if c != "OSM contact verified"]
    return True


def build_match_pairs(pvr_rows: list[dict], osm_rows: list[dict]) -> list[tuple]:
    pairs: list[tuple] = []
    for pvr in pvr_rows:
        if "+openstreetmap" in (pvr.get("source") or ""):
            continue
        pvr_name = pvr.get("company_name", "")
        pvr_city = primary_city(pvr)
        for osm in osm_rows:
            ratio = name_similarity(pvr_name, osm.get("company_name", ""))
            if ratio < FUZZY_MIN_RATIO:
                continue
            osm_city = primary_city(osm)
            if pvr_city and osm_city and pvr_city != osm_city and ratio < MIN_RATIO_WITHOUT_CITY:
                continue
            if not pvr_city and ratio < MIN_RATIO_WITHOUT_CITY:
                continue
            score = score_osm_candidate(pvr, osm, ratio)
            if score >= FUZZY_MIN_SCORE:
                pairs.append((score, ratio, pvr.get("id"), osm.get("id"), pvr, osm))
    pairs.sort(key=lambda row: (-row[0], -row[1]))
    return pairs


def greedy_enrich(pvr_rows: list[dict], osm_rows: list[dict]) -> int:
    used_pvr: set[str] = set()
    used_osm: set[str] = set()
    enriched = 0
    for score, ratio, pvr_id, osm_id, pvr, osm in build_match_pairs(pvr_rows, osm_rows):
        if not pvr_id or not osm_id or pvr_id in used_pvr or osm_id in used_osm:
            continue
        if enrich_from_osm(pvr, osm):
            used_pvr.add(str(pvr_id))
            used_osm.add(str(osm_id))
            enriched += 1
    return enriched


def normalize_company(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = COMPANY_SUFFIXES.sub("", text.lower())
    return re.sub(r"[^a-z0-9]", "", text)


def primary_city(supplier: dict) -> str:
    regions = supplier.get("regions") or []
    if not regions:
        return ""
    city = str(regions[0]).split(",")[0].strip().lower()
    return unicodedata.normalize("NFKD", city).encode("ascii", "ignore").decode("ascii")


def name_similarity(a: str, b: str) -> float:
    a_norm = normalize_company(a)
    b_norm = normalize_company(b)
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    if a_norm in b_norm or b_norm in a_norm:
        return max(0.88, SequenceMatcher(None, a_norm, b_norm).ratio())
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def strip_fake_ratings(supplier: dict) -> None:
    if int(supplier.get("reviews_count") or 0) <= 0:
        supplier["rating"] = None


def score_osm_candidate(pvr: dict, osm: dict, name_ratio: float) -> int:
    if name_ratio >= 0.98:
        score = 100
    elif name_ratio >= 0.92:
        score = 92
    elif name_ratio >= 0.85:
        score = 85
    elif name_ratio >= FUZZY_MIN_RATIO:
        score = 78
    else:
        return 0

    pvr_city = primary_city(pvr)
    osm_city = primary_city(osm)
    if pvr_city and osm_city:
        if pvr_city == osm_city:
            score += 8
        elif name_ratio < 0.92:
            score -= 15

    if not is_placeholder_phone(osm.get("phone")):
        score += 10
    if (osm.get("website") or "").strip():
        score += 8
    if (osm.get("email") or "").strip():
        score += 4
    return score


def pick_osm_match(pvr: dict, candidates: list[dict]) -> dict | None:
    """Pick best OSM row from a pre-filtered candidate list (used in tests)."""
    if not candidates:
        return None
    best = None
    best_score = 0
    pvr_name = pvr.get("company_name", "")
    for osm in candidates:
        ratio = name_similarity(pvr_name, osm.get("company_name", ""))
        if ratio < FUZZY_MIN_RATIO:
            continue
        score = score_osm_candidate(pvr, osm, ratio)
        if score > best_score:
            best_score = score
            best = osm
    return best if best_score >= FUZZY_MIN_SCORE else None


def collect_candidates(pvr: dict, index: dict, osm_rows: list[dict]) -> list[dict]:
    """Legacy helper – prefer city + name index, then same-city pool."""
    name_key = normalize_company(pvr.get("company_name", ""))
    city = primary_city(pvr)
    pool: list[dict] = []

    if name_key:
        pool.extend(index.get((name_key, city), []))
        if not pool:
            for (n, c), rows in index.items():
                if n == name_key and (not city or not c or c == city):
                    pool.extend(rows)

    if not pool and city:
        for osm in osm_rows:
            if primary_city(osm) == city:
                ratio = name_similarity(pvr.get("company_name", ""), osm.get("company_name", ""))
                if ratio >= FUZZY_MIN_RATIO:
                    pool.append(osm)

    seen: set[str] = set()
    unique: list[dict] = []
    for row in pool:
        rid = str(row.get("id"))
        if rid in seen:
            continue
        seen.add(rid)
        unique.append(row)
    return unique


def enrich_from_osm(pvr: dict, osm: dict) -> bool:
    changed = False
    if not is_placeholder_phone(osm.get("phone")) and is_placeholder_phone(pvr.get("phone")):
        pvr["phone"] = osm["phone"]
        changed = True
    website = (osm.get("website") or "").strip()
    if website and not (pvr.get("website") or "").strip():
        pvr["website"] = website
        changed = True
    email = (osm.get("email") or "").strip()
    if email and is_placeholder_email(pvr.get("email"), pvr.get("company_name", "")):
        if not is_placeholder_email(email, pvr.get("company_name", "")):
            pvr["email"] = email
            changed = True
    if osm.get("latitude") is not None and pvr.get("latitude") is None:
        pvr["latitude"] = osm["latitude"]
        pvr["longitude"] = osm["longitude"]
        changed = True
    if osm.get("locations_served") and not pvr.get("locations_served"):
        pvr["locations_served"] = list(osm["locations_served"])
        changed = True
    if changed:
        src = pvr.get("source") or "photovoltaik-vergleichsrechner"
        if "openstreetmap" not in src:
            pvr["source"] = f"{src}+openstreetmap"
        if not is_placeholder_phone(pvr.get("phone")) and (pvr.get("website") or "").strip():
            pvr["verified"] = True
        certs = list(pvr.get("certifications") or [])
        if "OSM contact verified" not in certs:
            certs.append("OSM contact verified")
        pvr["certifications"] = certs
        desc = pvr.get("description", "")
        if "OpenStreetMap contact" not in desc:
            pvr["description"] = desc.replace(
                "(public directory listing",
                "(directory listing enriched with OpenStreetMap contact",
            )
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reset", action="store_true", help="Strip prior OSM enrichment from PVR rows before matching")
    args = parser.parse_args()

    with open(SUPPLIERS_FILE, encoding="utf-8") as fh:
        suppliers = json.load(fh)

    osm_rows = [s for s in suppliers if s.get("source") == "openstreetmap" or str(s.get("id", "")).startswith("osm-")]
    pvr_rows = [s for s in suppliers if "photovoltaik-vergleichsrechner" in (s.get("source") or "")]

    reset_count = 0
    if args.reset:
        for pvr in pvr_rows:
            if reset_osm_enrichment(pvr):
                reset_count += 1
        print(f"Reset prior OSM enrichment on {reset_count} PVR rows")

    enriched = greedy_enrich(pvr_rows, osm_rows)

    for s in suppliers:
        strip_fake_ratings(s)

    print(f"OSM entries indexed: {len(osm_rows)}")
    print(f"PVR entries: {len(pvr_rows)}")
    print(f"Enriched with OSM contact: {enriched}")

    if args.dry_run:
        return 0

    with open(SUPPLIERS_FILE, "w", encoding="utf-8") as fh:
        json.dump(suppliers, fh, ensure_ascii=False, indent=2)
    print(f"Saved {SUPPLIERS_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
