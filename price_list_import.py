"""Phase 3 — CSV price list import for supplier product catalogs."""

from __future__ import annotations

import csv
import io
import uuid
from typing import Any

# Expected columns (case-insensitive): type, brand, model, name, price, warranty, stock, power_wp, capacity_kwh, ac_power_kw
COLUMN_ALIASES = {
    "type": ("type", "category", "product_type", "produkttyp"),
    "brand": ("brand", "marke", "hersteller"),
    "model": ("model", "modell"),
    "name": ("name", "product", "product_name", "bezeichnung"),
    "price": ("price", "price_eur", "preis", "price_per_unit", "unit_price"),
    "warranty": ("warranty", "warranty_years", "garantie"),
    "stock": ("stock", "availability", "verfuegbarkeit"),
    "power_wp": ("power_wp", "wp", "watt_peak", "leistung_wp"),
    "capacity_kwh": ("capacity_kwh", "kwh", "kapazitaet_kwh"),
    "ac_power_kw": ("ac_power_kw", "ac_kw", "inverter_kw"),
}


def _normalize_header(h: str) -> str:
    return h.strip().lower().replace(" ", "_").replace("-", "_")


def _map_row(headers: list[str], row: list[str]) -> dict[str, str]:
    norm = {_normalize_header(h): (row[i] if i < len(row) else "") for i, h in enumerate(headers)}
    out: dict[str, str] = {}
    for field, aliases in COLUMN_ALIASES.items():
        for a in aliases:
            if a in norm and norm[a]:
                out[field] = norm[a].strip()
                break
    return out


def parse_csv_text(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse CSV text into supplier product dicts. Returns (products, errors)."""
    errors: list[str] = []
    products: list[dict[str, Any]] = []
    reader = csv.reader(io.StringIO(text.lstrip("\ufeff")))
    rows = list(reader)
    if not rows:
        return [], ["Empty file"]
    headers = rows[0]
    for line_no, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue
        mapped = _map_row(headers, row)
        name = mapped.get("name") or f"{mapped.get('brand', '')} {mapped.get('model', '')}".strip()
        if not name:
            errors.append(f"Line {line_no}: missing product name")
            continue
        try:
            price = float(str(mapped.get("price", "0")).replace(",", ".").replace("€", "").strip() or 0)
        except ValueError:
            errors.append(f"Line {line_no}: invalid price")
            continue
        ptype = (mapped.get("type") or "system").lower()
        if ptype in ("module", "modul", "panel", "pv"):
            ptype = "panel"
        elif ptype in ("wechselrichter", "wr"):
            ptype = "inverter"
        elif ptype in ("speicher", "storage"):
            ptype = "battery"

        product: dict[str, Any] = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "type": ptype,
            "brand": mapped.get("brand", ""),
            "model": mapped.get("model", ""),
            "price_per_unit": round(price, 2),
            "warranty_years": int(float(mapped.get("warranty", "10") or 10)),
            "stock": mapped.get("stock") or "available",
        }
        if mapped.get("power_wp"):
            try:
                product["power_wp"] = int(float(mapped["power_wp"]))
            except ValueError:
                pass
        if mapped.get("capacity_kwh"):
            try:
                product["capacity_kwh"] = float(mapped["capacity_kwh"])
            except ValueError:
                pass
        if mapped.get("ac_power_kw"):
            try:
                product["ac_power_kw"] = float(mapped["ac_power_kw"])
            except ValueError:
                pass
        products.append(product)
    return products, errors


def merge_products(existing: list, imported: list, replace: bool = False) -> list:
    if replace:
        return imported
    by_key = {(p.get("brand", ""), p.get("model", ""), p.get("name", "")): p for p in existing}
    for p in imported:
        key = (p.get("brand", ""), p.get("model", ""), p.get("name", ""))
        by_key[key] = p
    return list(by_key.values())
