"""Phase 4 integrations — delegates to real modules when available."""

from __future__ import annotations

from bill_ocr import parse_bill_upload
from financing_offers import financing_offers
from incentives_lookup import incentives_lookup


def stub_bill_upload(data: dict) -> dict:
    return parse_bill_upload(data)


def stub_roof_analysis(data: dict) -> dict:
    from roof_analysis import analyze_roof_request

    return analyze_roof_request(data)


def stub_financing_offers(amount: float, term_years: int = 10) -> dict:
    return financing_offers(amount, term_years)


def stub_incentives(postcode: str) -> dict:
    return incentives_lookup(postcode)
