"""Electricity bill OCR — extract kWh and cost from PDF/text (German bills)."""

from __future__ import annotations

import re
from io import BytesIO
from typing import Optional

KWH_PATTERNS = [
    re.compile(r"(?:verbrauch|consumption|bezug|arbeit)[^\d]{0,40}(\d{1,5}(?:[.,]\d{1,3})?)\s*kwh", re.I),
    re.compile(r"(\d{1,5}(?:[.,]\d{1,3})?)\s*kwh", re.I),
]
EUR_PATTERNS = [
    re.compile(r"(?:gesamt|total|summe|rechnungsbetrag|zu zahlen)[^\d€]{0,30}(\d{1,5}(?:[.,]\d{2}))\s*€?", re.I),
    re.compile(r"(\d{1,5}(?:[.,]\d{2}))\s*€", re.I),
]
PERIOD_MONTHS = re.compile(r"(\d{1,2})\s*(?:monat|months?)", re.I)


def _to_float(num: str) -> Optional[float]:
    if not num:
        return None
    s = num.strip().replace(".", "").replace(",", ".") if num.count(",") == 1 and num.count(".") > 1 else num.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_bill_text(text: str) -> dict:
    text = text or ""
    monthly_kwh = None
    monthly_bill = None
    for pat in KWH_PATTERNS:
        for m in pat.finditer(text):
            val = _to_float(m.group(1))
            if val and 20 <= val <= 50000:
                monthly_kwh = val
                break
        if monthly_kwh:
            break

    for pat in EUR_PATTERNS:
        for m in pat.finditer(text):
            val = _to_float(m.group(1))
            if val and 5 <= val <= 5000:
                monthly_bill = val
                break
        if monthly_bill:
            break

    period_months = 1
    pm = PERIOD_MONTHS.search(text)
    if pm:
        try:
            period_months = max(1, int(pm.group(1)))
        except ValueError:
            pass

    if monthly_kwh and period_months > 1:
        monthly_kwh = round(monthly_kwh / period_months, 1)
    if monthly_bill and period_months > 1:
        monthly_bill = round(monthly_bill / period_months, 2)

    confidence = 0.0
    if monthly_kwh:
        confidence += 0.45
    if monthly_bill:
        confidence += 0.35
    if len(text) > 200:
        confidence += 0.1

    return {
        "ok": bool(monthly_kwh or monthly_bill),
        "stub": False,
        "parsed": {
            "monthly_kwh": monthly_kwh,
            "monthly_bill_eur": monthly_bill,
            "billing_period_months": period_months,
            "confidence": round(min(0.95, confidence), 2),
        },
        "raw_chars": len(text),
    }


def parse_bill_pdf(raw: bytes) -> dict:
    if not raw:
        return {"ok": False, "error": "empty file"}
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(raw))
        parts = []
        for page in reader.pages[:6]:
            parts.append(page.extract_text() or "")
        text = "\n".join(parts)
    except Exception as exc:
        return {"ok": False, "error": f"PDF read failed: {exc}"}
    result = parse_bill_text(text)
    result["format"] = "pdf"
    return result


def parse_bill_upload(data: dict, file_bytes: bytes | None = None, filename: str = "") -> dict:
    """JSON hints, raw text, or uploaded PDF."""
    if file_bytes:
        name = (filename or "").lower()
        if name.endswith(".pdf"):
            return parse_bill_pdf(file_bytes)
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
            out = parse_bill_text(text)
            out["format"] = "text"
            return out
        except Exception:
            return {"ok": False, "error": "Unsupported file type — use PDF or paste text"}

    if data.get("text"):
        out = parse_bill_text(str(data["text"]))
        out["format"] = "text"
        return out

    if data.get("pdf_base64"):
        import base64

        try:
            raw = base64.b64decode(data["pdf_base64"])
            return parse_bill_pdf(raw)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    est_kwh = data.get("estimated_monthly_kwh")
    est_bill = data.get("estimated_monthly_bill_eur")
    if est_kwh or est_bill:
        return {
            "ok": True,
            "stub": False,
            "parsed": {
                "monthly_kwh": float(est_kwh) if est_kwh else None,
                "monthly_bill_eur": float(est_bill) if est_bill else None,
                "confidence": 0.2,
            },
            "note": "Manual estimates only — upload a bill PDF for OCR.",
        }
    return {"ok": False, "error": "Provide text, pdf_base64, or upload a PDF file"}
