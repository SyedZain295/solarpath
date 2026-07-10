"""Illustrative green financing offers for Germany (not a credit offer)."""

from __future__ import annotations

from datetime import datetime, timezone

from financial_model import FINANCING_RATE_APR, calculate_financing

PROVIDERS = [
    {"provider": "KfW-style green loan (illustrative)", "apr_pct": 3.9, "badge": "Green"},
    {"provider": "Regional Volksbank solar loan", "apr_pct": 4.6, "badge": "Regional"},
    {"provider": "Installer finance partner", "apr_pct": 5.4, "badge": "Fast approval"},
]


def financing_offers(amount: float, term_years: int = 10) -> dict:
    amount = max(0.0, float(amount or 0))
    term_years = max(1, min(25, int(term_years or 10)))
    offers = []
    for p in PROVIDERS:
        apr = p["apr_pct"] / 100
        fin = calculate_financing(amount, term_years=term_years, apr=apr)
        offers.append(
            {
                "provider": p["provider"],
                "badge": p["badge"],
                "apr_pct": p["apr_pct"],
                "term_years": term_years,
                "monthly_eur": fin["monthly_payment"],
                "total_paid_eur": fin["total_paid"],
                "total_interest_eur": fin["total_interest"],
            }
        )
    baseline = calculate_financing(amount, term_years=term_years, apr=FINANCING_RATE_APR)
    return {
        "ok": True,
        "stub": False,
        "amount_eur": round(amount),
        "term_years": term_years,
        "offers": offers,
        "baseline_apr_pct": round(FINANCING_RATE_APR * 100, 1),
        "baseline_monthly_eur": baseline["monthly_payment"],
        "disclaimer": "Illustrative comparison only — not an offer of credit. Rates vary by creditworthiness and lender.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
