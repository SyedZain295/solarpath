"""Phase 4 API stubs — placeholders for future integrations (no real partners yet)."""

from __future__ import annotations

from datetime import datetime, timezone


def _stub(name: str, **extra):
    return {
        "stub": True,
        "status": "not_implemented",
        "feature": name,
        "message": "This integration is planned for a future release.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **extra,
    }


def stub_bill_upload(data: dict) -> dict:
    return _stub(
        "bill_upload_ocr",
        parsed={
            "monthly_kwh": data.get("estimated_monthly_kwh"),
            "monthly_bill_eur": data.get("estimated_monthly_bill_eur"),
            "confidence": 0.0,
        },
        hint="Upload a PDF/image of your electricity bill — OCR will extract kWh and cost.",
    )


def stub_roof_analysis(data: dict) -> dict:
    set_id = (data.get("set_id") or data.get("roof_photo_set_id") or "").strip()
    if set_id:
        try:
            from roof_photo_store import analyze_roof_set

            result = analyze_roof_set(
                set_id,
                hints={
                    "shading": data.get("shading"),
                    "roof_area_m2": data.get("roof_area_m2"),
                },
            )
            if result.get("ok"):
                return result
        except Exception:
            pass
    return _stub(
        "roof_analysis",
        lat=data.get("latitude"),
        lon=data.get("longitude"),
        estimated={
            "roof_area_m2": data.get("roof_area_m2"),
            "shading": data.get("shading", "unknown"),
            "usable_area_m2": None,
        },
        hint="Premium roof/shading analysis (e.g. Google Solar API) planned for Phase 4.",
    )


def stub_financing_offers(amount: float, term_years: int = 10) -> dict:
    rate = 0.049
    monthly = (amount * rate / 12) / (1 - (1 + rate / 12) ** (-term_years * 12)) if amount > 0 else 0
    return _stub(
        "financing_offers",
        amount_eur=amount,
        term_years=term_years,
        illustrative_offers=[
            {"provider": "Partner bank (stub)", "apr_pct": 4.9, "monthly_eur": round(monthly, 2)},
            {"provider": "Green loan (stub)", "apr_pct": 3.9, "monthly_eur": round(monthly * 0.95, 2)},
        ],
        disclaimer="Illustrative only — not an offer of credit.",
    )


def stub_incentives(postcode: str) -> dict:
    plz = (postcode or "")[:5]
    state_hint = "Bayern" if plz.startswith(("80", "81", "82", "83", "84", "85", "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97")) else "Germany"
    return _stub(
        "incentives_lookup",
        postcode=plz,
        region=state_hint,
        programs=[
            {"name": "EEG feed-in tariff", "type": "feed_in", "status": "active"},
            {"name": "KfW 270 (stub)", "type": "loan", "status": "check_eligibility"},
            {"name": "Local municipality bonus (stub)", "type": "grant", "status": "varies"},
        ],
        hint="Connect to KfW / BAFA / municipal databases in Phase 4.",
    )
