from io import BytesIO

from pdf_report import generate_decision_report_pdf
from demo_data import load_demo_recommendation


def _page_count(pdf_bytes: bytes) -> int:
  text = pdf_bytes.decode("latin-1", errors="ignore")
  return text.count("/Type /Page") - text.count("/Type /Pages")


def test_pdf_generates_non_trivial_document():
    rec = load_demo_recommendation()
    rec["hp_assessment"] = {
        "status": "planning",
        "status_label": "Planning a heat pump",
        "type_label": "Air-source heat pump",
        "annual_heat_kwh": 4200,
        "priority_label": "Solar-led heating",
    }
    rec["sizing_summary"] = rec.get("sizing_summary") or {}
    rec["sizing_summary"].update({
        "capped_by_roof": True,
        "demand_note": "Roof limits system to 4.6 kWp - covers part of demand.",
    })
    buf = generate_decision_report_pdf(rec, {"name": "Test User"}, lang="en")
    assert isinstance(buf, BytesIO)
    data = buf.getvalue()
    assert data.startswith(b"%PDF")
    assert len(data) > 5000
    assert _page_count(data) >= 1
