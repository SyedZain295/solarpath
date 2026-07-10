"""Tests for EV Phase 3 bundle planner."""

from ev_bundle import build_bundle_plan, load_wallboxes, recommend_wallbox
from ev_marketplace import parse_buyer_profile, vehicle_by_slug

PROFILE = {
    "budget_eur": 30000,
    "weekly_km": 300,
    "home_charging": "yes",
    "has_pv": True,
    "system_kwp": 5,
    "has_wallbox": False,
}


def test_load_wallboxes():
    boxes = load_wallboxes()
    assert len(boxes) >= 3
    assert boxes[0].get("ac_kw")


def test_recommend_wallbox_for_new_install():
    vehicle = vehicle_by_slug("vw-id3-pro-58")
    assert vehicle
    profile = parse_buyer_profile(PROFILE)
    rec = recommend_wallbox(profile, vehicle)
    assert rec["needed"] is True
    assert rec["recommended"]
    assert rec["install_cost_eur"] > 0


def test_recommend_wallbox_existing():
    vehicle = vehicle_by_slug("vw-id3-pro-58")
    profile = parse_buyer_profile({**PROFILE, "has_wallbox": True})
    rec = recommend_wallbox(profile, vehicle)
    assert rec["keep_existing"] is True
    assert rec["needed"] is False


def test_build_bundle_select_vehicle_step():
    result = build_bundle_plan(PROFILE)
    assert result["step"] == "select_vehicle"
    assert len(result["candidates"]) >= 1


def test_build_bundle_full_plan():
    match = build_bundle_plan(PROFILE)
    slug = match["candidates"][0]["slug"]
    result = build_bundle_plan(PROFILE, vehicle_slug=slug)
    assert result["step"] == "bundle"
    assert result["vehicle"]["slug"] == slug
    assert result["wallbox"]["recommended"]
    assert result["pv"]["annual_ev_kwh"] > 0
    assert result["costs"]["total_upfront_eur"] > 0
    assert "calculator_url" in result["ctas"]


def test_api_ev_bundle(client):
    resp = client.post("/api/ev-bundle", json=PROFILE)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["step"] == "select_vehicle"

    slug = data["candidates"][0]["slug"]
    resp2 = client.post("/api/ev-bundle", json={**PROFILE, "vehicle_slug": slug})
    assert resp2.status_code == 200
    plan = resp2.get_json()
    assert plan["step"] == "bundle"
    assert plan["vehicle"]["slug"] == slug
