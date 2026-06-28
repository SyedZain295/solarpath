"""Tests for quick_estimate module and API."""

from quick_estimate import quick_estimate_range


def test_quick_estimate_default_range():
    result = quick_estimate_range(monthly_kwh=350)
    assert 2.0 <= result["kwp_min"] <= result["kwp_max"] <= 40.0
    assert result["kwp_min"] <= result["kwp_typical"] <= result["kwp_max"]
    assert result["annual_kwh"] == 4200
    assert "kWp" in result["message_en"]


def test_quick_estimate_roof_cap():
    result = quick_estimate_range(monthly_kwh=500, roof_area_m2=12)
    assert result["kwp_max"] <= 6.5
    assert result.get("roof_limited") is True


def test_quick_estimate_ev_goal_sizes_up():
    base = quick_estimate_range(monthly_kwh=300, goals=["lower_bill"])
    ev = quick_estimate_range(monthly_kwh=300, goals=["lower_bill", "ev_charging"])
    assert ev["kwp_typical"] >= base["kwp_typical"]


def test_api_quick_estimate(client):
    resp = client.post(
        "/api/quick-estimate",
        json={"postcode": "80331", "monthly_kwh": 350, "goal": "lower_bill"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "kwp_min" in data
    assert "kwp_max" in data
    assert "message" in data
