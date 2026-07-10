"""Tests for enhancement batch: recalc, existing PV, roof analysis, EV email."""

import io

from email_service import notify_ev_buyer_lead, send_email, smtp_status
from roof_photo_store import add_photos_to_set, analyze_roof_set, create_photo_set
from solar_engine import CalculatorInput, apply_existing_pv_upgrade, generate_recommendation, recalculate_assumptions


def test_apply_existing_pv_expand_mode():
    inp = CalculatorInput(
        latitude=48.13,
        longitude=11.58,
        has_existing_pv=True,
        existing_pv_kwp=5,
        user_situation="pv_ev",
    )
    up = apply_existing_pv_upgrade(inp, 10)
    assert up["mode"] == "expand"
    assert up["expansion_kwp"] == 5
    assert up["cost_factor"] < 1.0


def test_apply_existing_pv_battery_only():
    inp = CalculatorInput(
        latitude=48.13,
        longitude=11.58,
        has_existing_pv=True,
        existing_pv_kwp=12,
        user_situation="pv_battery",
    )
    up = apply_existing_pv_upgrade(inp, 10)
    assert up["mode"] == "battery_only"
    assert up["cost_factor"] == 0.35


def test_recalculate_assumptions_returns_financials():
    base = {
        "monthly_kwh": 300,
        "electricity_price_ct": 35,
        "roof_type": "pitched_south",
        "goals": ["lower_bill"],
        "shading": "none",
    }
    location = {"latitude": 48.13, "longitude": 11.58}
    pvgis = {"specific_yield_kwh_kwp": 980}
    result = recalculate_assumptions(
        base,
        location,
        pvgis,
        {"annual_kwh": 4200, "battery_kwh": 5, "loan_years": 12},
    )
    assert result["system_kwp"] > 0
    assert result["financials"]["annual_savings"] > 0
    assert result["financing_comparison"]["loan"]["term_years"] == 12


def test_generate_recommendation_pv_upgrade(client):
    inp = CalculatorInput(
        latitude=48.13,
        longitude=11.58,
        monthly_kwh=350,
        has_existing_pv=True,
        existing_pv_kwp=6,
        user_situation="pv_battery",
        goals=["lower_bill", "backup"],
        battery_interest="yes",
    )
    rec = generate_recommendation(inp, {"specific_yield_kwh_kwp": 950})
    assert rec["pv_upgrade"]["has_existing_pv"] is True
    assert rec["pv_upgrade"]["existing_pv_kwp"] == 6


def test_analyze_roof_set_empty():
    result = analyze_roof_set("missing-set")
    assert result.get("ok") is False


def test_analyze_roof_set_with_photos():
    set_id = create_photo_set(postcode="80331")
    file = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    class FakeUpload:
        filename = "roof-south.jpg"
        content_type = "image/jpeg"

        def read(self):
            return file.getvalue()

    add_photos_to_set(set_id, [FakeUpload()])
    result = analyze_roof_set(set_id, hints={"roof_area_m2": 45})
    assert result["ok"] is True
    assert result["photo_count"] >= 1
    assert result["confidence"] in ("low", "medium")


def test_notify_ev_buyer_lead_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("SMTP_USER", "")
    notify_ev_buyer_lead(
        {
            "id": "evl-test",
            "buyer_name": "Alex",
            "buyer_email": "buyer@example.com",
            "buyer_phone": "",
            "buyer_postcode": "80331",
            "qualified": True,
            "message": "Interested",
        },
        "dealer@example.com",
        "Test Motors",
        "VW ID.4",
    )
    assert send_email("dealer@example.com", "test", "body") is True


def test_api_recalc_endpoint(client):
    resp = client.post(
        "/api/calculate/recalc",
        json={
            "calculator_inputs": {
                "monthly_kwh": 300,
                "electricity_price_ct": 32,
                "goals": ["lower_bill"],
                "roof_type": "pitched_south",
            },
            "location": {"latitude": 48.13, "longitude": 11.58},
            "pvgis": {"specific_yield_kwh_kwp": 950},
            "overrides": {"annual_kwh": 4000, "loan_years": 10},
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["system_kwp"] > 0
    assert "financials" in data


def test_smtp_status_file_log_mode(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    status = smtp_status()
    assert status["configured"] is False
    assert status["mode"] == "file_log"
    assert "SMTP_HOST" in status["missing"]


def test_smtp_status_ready_when_password_set(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    status = smtp_status()
    assert status["configured"] is True
    assert status["ready"] is True
    assert status["password_set"] is True
    assert status["missing"] == []
