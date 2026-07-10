"""Parse pasted quote text into compare-quotes form fields."""

from __future__ import annotations

import re
from typing import Any

_EUR = re.compile(
    r"(?:€|EUR)\s*([\d.,\s]+)|([\d.,\s]+)\s*(?:€|EUR)|"
    r"(?:gesamtpreis|gesamt|summe|brutto|netto|preis)[:\s]*([\d.,\s]+)",
    re.I,
)
_KWP = re.compile(r"([\d.,]+)\s*kWp", re.I)
_KWH_YR = re.compile(r"(?:ca\.?\s*)?([\d.,]+)\s*kWh\s*(?:/|pro\s*)?(?:Jahr|year|yr|a)?", re.I)
_WARRANTY = re.compile(r"(\d+)\s*(?:Jahre?|years?|yr)\s*(?:Garantie|warranty|Module)?", re.I)
_BATTERY = re.compile(r"([\d.,]+)\s*kWh\s*(?:Speicher|battery|Batterie|BYD|Tesla|Sonnen)?", re.I)
_PANEL_COUNT = re.compile(r"(\d+)\s*[×xX]\s*[\w\s.-]*?(\d{3})\s*Wp", re.I)
_PANEL_COUNT_DE = re.compile(r"(\d+)\s*(?:Stück|Stk\.?|Module|Modulen)\s", re.I)
_INVERTER_KW = re.compile(r"(?:Wechselrichter|inverter|WR).*?([\d.,]+)\s*kW", re.I | re.S)
_VALIDITY = re.compile(r"(?:gültig|valid)\s*(\d+)\s*(?:Tage?|days?)", re.I)
_BRANDS_PANEL = ("Trina", "JA Solar", "REC", "LONGi", "Qcells", "Heckert", "Solarwatt", "Meyer Burger", "Jinko")
_BRANDS_INV = ("Fronius", "SMA", "Sungrow", "Huawei", "Kostal", "SolarEdge")


def _num(s: str) -> float:
    s = s.strip().replace(" ", "")
    if re.match(r"^\d{1,3}(\.\d{3})+,\d+$", s):
        return float(s.replace(".", "").replace(",", "."))
    if s.count(",") == 1 and s.count(".") == 0:
        return float(s.replace(",", "."))
    if s.count(".") == 1 and s.count(",") == 0:
        return float(s)
    return float(s.replace(",", ""))


def parse_quote_text(text: str) -> dict[str, Any]:
    """Best-effort extraction from German/English installer quote paste."""
    text = text or ""
    low = text.lower()
    result: dict[str, Any] = {
        "parsed": True,
        "confidence": "low",
        "installer": "",
        "total_eur": None,
        "kwp": None,
        "production_kwh": None,
        "panel_count": None,
        "panel_wp": None,
        "panels": "",
        "inverter": "",
        "inverter_kw": None,
        "battery_kwh": None,
        "warranty_years": None,
        "validity_days": None,
        "price_per_kwp": None,
        "notes": "",
        "includes_installation": any(w in low for w in ("montage", "install", "komplettanlage", "installation")),
        "includes_mounting": any(
            w in low for w in ("montage", "unterkonstruktion", "mounting", "racking", "gestell", "module montage")
        ),
        "includes_scaffolding": "gerüst" in low or "scaffold" in low,
        "includes_grid_registration": any(w in low for w in ("netzanmeldung", "netz", "grid registration", "vnb")),
        "includes_mastr": "mastr" in low or "marktstammdaten" in low,
        "includes_battery": any(
            w in low for w in ("speicher", "battery", "batterie", "byd", "sonnen", "tesla powerwall")
        ),
        "includes_monitoring": any(w in low for w in ("monitor", "smart meter", "portal", "app")),
        "includes_optimizer": "optimierer" in low or "optimizer" in low or "solaredge" in low,
        "includes_electrician": any(w in low for w in ("elektriker", "elektro", "electrician", "zählerschrank")),
        "includes_removal": any(w in low for w in ("entsorgung", "demontage", "removal", "rückbau")),
    }

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines:
        for ln in lines[:3]:
            if not re.match(r"^(angebot|quote|offerte|nr\.?|#|\d)", ln, re.I):
                result["installer"] = ln[:80]
                break
        if not result["installer"]:
            result["installer"] = lines[0][:80]

    eurs = []
    for m in _EUR.finditer(text):
        for g in m.groups():
            if not g:
                continue
            try:
                eurs.append(_num(g))
            except ValueError:
                pass
    if eurs:
        # Prefer largest plausible total (often gross total)
        plausible = [e for e in eurs if 3000 <= e <= 150000]
        result["total_eur"] = round(max(plausible) if plausible else max(eurs))

    m = _KWP.search(text)
    if m:
        try:
            result["kwp"] = round(_num(m.group(1)), 2)
        except ValueError:
            pass

    m = _PANEL_COUNT.search(text)
    if m:
        result["panel_count"] = int(m.group(1))
        result["panel_wp"] = int(m.group(2))
    else:
        m2 = _PANEL_COUNT_DE.search(text)
        if m2:
            result["panel_count"] = int(m2.group(1))

    m = _KWH_YR.search(text)
    if m:
        try:
            val = round(_num(m.group(1)))
            if val > 500:
                result["production_kwh"] = val
        except ValueError:
            pass

    warranties = [int(x.group(1)) for x in _WARRANTY.finditer(text)]
    if warranties:
        result["warranty_years"] = max(warranties)

    m = _BATTERY.search(text)
    if m:
        try:
            val = round(_num(m.group(1)), 1)
            if 2 <= val <= 50:
                result["battery_kwh"] = val
        except ValueError:
            pass

    m = _INVERTER_KW.search(text)
    if m:
        try:
            result["inverter_kw"] = round(_num(m.group(1)), 1)
        except ValueError:
            pass

    m = _VALIDITY.search(text)
    if m:
        result["validity_days"] = int(m.group(1))

    for brand in _BRANDS_PANEL:
        if brand.lower() in low:
            wp = result.get("panel_wp")
            result["panels"] = f"{brand}" + (f" {wp} Wp" if wp else "")
            break

    for brand in _BRANDS_INV:
        if brand.lower() in low:
            kw = result.get("inverter_kw")
            result["inverter"] = brand + (f" ({kw} kW)" if kw else " (detected)")
            break

    filled = sum(1 for k in ("total_eur", "kwp", "production_kwh", "panel_count") if result.get(k))
    result["confidence"] = "high" if filled >= 3 else ("medium" if filled >= 2 else "low")
    if result.get("total_eur") and result.get("kwp"):
        result["price_per_kwp"] = round(result["total_eur"] / result["kwp"])
    result["notes"] = "Auto-parsed — verify line items, net/gross, and VAT before deciding."
    return result


def split_quote_texts(text: str) -> list[str]:
    """Split pasted content into up to 3 separate quotes."""
    text = (text or "").strip()
    if not text:
        return []
    parts = re.split(
        r"\n\s*---+\s*\n|\n\s*={3,}\s*\n|(?:\n\s*){2}(?=Angebot\s*(?:Nr\.?|#|\d)|Quote\s*(?:#|\d))", text, flags=re.I
    )
    chunks = [p.strip() for p in parts if p.strip()]
    if len(chunks) <= 1:
        return [text]
    return chunks[:3]


def parse_quotes_from_text(text: str) -> list[dict]:
    return [parse_quote_text(chunk) for chunk in split_quote_texts(text)]
