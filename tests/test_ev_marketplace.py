"""Solar Path EV marketplace — matching and API."""

from ev_marketplace import match_vehicles, filter_vehicles, home_energy_check, load_vehicles


def test_load_vehicles():
    vehicles = load_vehicles()
    assert len(vehicles) >= 5
    assert vehicles[0].get("make")


def test_match_returns_top_five():
    result = match_vehicles({"budget_eur": 30000, "weekly_km": 250, "priority": "running_cost"})
    recs = result["recommendations"]
    assert 1 <= len(recs) <= 5
    assert recs[0]["solar_path_fit"]["fit_score"] >= recs[-1]["solar_path_fit"]["fit_score"]


def test_certificate_not_claimed_without_upload():
    result = match_vehicles({"budget_eur": 20000, "weekly_km": 200})
    zoe = next((r for r in result["recommendations"] if "Zoe" in r.get("model", "")), None)
    if zoe:
        cert = zoe["solar_path_fit"]["battery_certificate_label"]
        assert cert["status"] in ("none", "test_available")


def test_home_energy_wallbox_recommendation():
    check = home_energy_check({"weekly_km": 300, "home_charging": "yes", "has_wallbox": False})
    ids = [i["id"] for i in check["recommendations"]]
    assert "wallbox" in ids


def test_api_ev_vehicles(client):
    resp = client.get("/api/ev-vehicles?budget_max=30000")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] >= 1
    assert "solar_path_fit" in data["vehicles"][0]


def test_api_ev_match(client):
    resp = client.post("/api/ev-match", json={"budget_eur": 28000, "weekly_km": 290})
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["recommendations"]) >= 1


def test_api_ev_home_energy(client):
    resp = client.post("/api/ev-home-energy", json={"weekly_km": 250, "home_charging": "yes"})
    assert resp.status_code == 200
    assert resp.get_json().get("annual_ev_kwh", 0) > 0


def test_filter_certificate_only():
    items = filter_vehicles(certificate_only=True)
    for v in items:
        assert v.get("battery_certificate", {}).get("uploaded") is True
