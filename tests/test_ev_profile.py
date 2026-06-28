from unittest.mock import patch

from ev_profile import (
    apply_ev_fields_to_input,
    estimate_ev_annual_kwh,
    recommend_ev_battery_kwh,
    build_ev_assessment,
)
from solar_engine import CalculatorInput, generate_recommendation


MOCK_PVGIS = {"specific_yield_kwh_kwp": 950, "monthly": []}


def test_estimate_ev_annual_kwh_from_profile():
    inp = CalculatorInput(latitude=48.1, longitude=11.5, ev_annual_km=15000, ev_consumption_kwh_100km=18)
    assert estimate_ev_annual_kwh(inp) == 2700


def test_cheapest_ev_priority_skips_battery():
    inp = CalculatorInput(
        latitude=48.1,
        longitude=11.5,
        goals=["ev_charging"],
        ev_charging_priority="cheapest",
        ev_annual_km=12000,
        ev_consumption_kwh_100km=18,
    )
    assert recommend_ev_battery_kwh(inp, 6.0, 4000, inp.goals) == 0.0


def test_solar_ev_priority_sizes_battery():
    inp = CalculatorInput(
        latitude=48.1,
        longitude=11.5,
        goals=["ev_charging"],
        ev_charging_priority="solar",
        ev_annual_km=15000,
        ev_consumption_kwh_100km=18,
        ev_park_home_daytime="yes",
    )
    batt = recommend_ev_battery_kwh(inp, 6.0, 4000, inp.goals)
    assert batt >= 5


@patch("app.get_pv_estimate", return_value=MOCK_PVGIS)
@patch("app.get_gsa_yield_estimate", return_value=None)
def test_api_calculate_includes_ev_assessment(_gsa, _pvgis, client):
    r = client.post(
        "/api/calculate",
        json={
            "latitude": 48.1351,
            "longitude": 11.582,
            "location_name": "München",
            "monthly_kwh": 350,
            "goals": ["ev_charging"],
            "ev_ownership": "own",
            "ev_annual_km": 15000,
            "ev_consumption_kwh_100km": 18,
            "ev_home_charging": "yes",
            "ev_park_home_daytime": "yes",
            "ev_has_wallbox": "no",
            "ev_charging_priority": "solar",
            "ev_dynamic_tariff_interest": "maybe",
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "ev_assessment" in data
    assert data["ev_assessment"]["annual_charging_kwh"] == 2700
    assert data["calculator_inputs"]["ev_ownership"] == "own"


def test_budget_package_not_more_expensive_than_balanced_with_ev():
    from solar_engine import CalculatorInput, build_three_packages
    inp = CalculatorInput(
        latitude=48.1,
        longitude=11.5,
        goals=["ev_charging"],
        ev_charging_priority="solar",
        ev_annual_km=15000,
        ev_consumption_kwh_100km=18,
        has_ev=True,
        monthly_kwh=350,
        roof_area_m2=50,
    )
    pkgs = build_three_packages(inp, 5.0, 4750, 950, inp.goals, 4200)["packages"]
    assert pkgs["cheapest"]["upfront_cost"] <= pkgs["best_value"]["upfront_cost"]


def test_budget_package_not_more_expensive_than_balanced_with_backup():
    from solar_engine import CalculatorInput, build_three_packages
    inp = CalculatorInput(
        latitude=48.1,
        longitude=11.5,
        goals=["backup"],
        monthly_kwh=450,
        roof_area_m2=30,
    )
    pkgs = build_three_packages(inp, 5.0, 4750, 950, inp.goals, 5400)["packages"]
    assert pkgs["cheapest"]["upfront_cost"] <= pkgs["best_value"]["upfront_cost"]


def test_confidence_score_capped_without_roof_photos():
    from confidence_score import calculate_confidence_score, _SCORE_CAP_NO_PHOTOS
    from solar_engine import CalculatorInput
    inp = CalculatorInput(
        latitude=48.1,
        longitude=11.5,
        location_name="München",
        monthly_kwh=350,
        roof_area_m2=40,
        roof_type="pitched_south",
        shading="none",
        housing_type="detached",
    )
    conf = calculate_confidence_score(inp, pvgis_available=True, specific_yield=950)
    assert conf["score"] <= _SCORE_CAP_NO_PHOTOS
    assert conf["score_label"] == "Information completeness index"
    assert "installer" in conf["survey_disclaimer"].lower()


def test_apply_ev_fields_sets_has_ev():
    inp = CalculatorInput(latitude=48.1, longitude=11.5, goals=["ev_charging"])
    apply_ev_fields_to_input(inp, {"ev_ownership": "planning", "ev_annual_km": 10000})
    assert inp.planned_ev is True
    assert inp.has_ev is False
    assert build_ev_assessment(inp)["ownership"] == "planning"
