from unittest.mock import patch

from heat_pump_profile import apply_hp_fields_to_input, build_hp_assessment, estimate_hp_annual_kwh
from solar_engine import CalculatorInput, build_three_packages


def test_estimate_hp_from_heated_area():
    inp = CalculatorInput(
        latitude=48.1,
        longitude=11.5,
        goals=["space_heating"],
        hp_heated_area_m2=120,
        hp_status="planning",
        hp_type="air_source",
    )
    kwh = estimate_hp_annual_kwh(inp)
    assert kwh == 4200


def test_apply_hp_fields_sets_has_heat_pump_when_installed():
    inp = CalculatorInput(latitude=48.1, longitude=11.5, goals=["space_heating"])
    apply_hp_fields_to_input(inp, {"hp_status": "have", "hp_type": "air_source"})
    assert inp.has_heat_pump is True


@patch("app.get_pv_estimate", return_value={"specific_yield_kwh_kwp": 950, "monthly": []})
@patch("app.get_gsa_yield_estimate", return_value=None)
def test_api_calculate_includes_hp_assessment(_gsa, _pvgis, client):
    r = client.post(
        "/api/calculate",
        json={
            "latitude": 48.1351,
            "longitude": 11.582,
            "location_name": "München",
            "monthly_kwh": 350,
            "goals": ["space_heating"],
            "hp_status": "planning",
            "hp_type": "air_source",
            "hp_heated_area_m2": 110,
            "hp_daytime_heating": "managed",
            "hp_priority": "solar_led",
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "hp_assessment" in data
    assert data["hp_assessment"]["annual_heat_kwh"] > 0
    assert data["calculator_inputs"]["hp_status"] == "planning"


def test_budget_not_more_than_balanced_with_heat_goal():
    inp = CalculatorInput(
        latitude=48.1,
        longitude=11.5,
        goals=["space_heating"],
        hp_status="planning",
        hp_type="air_source",
        hp_heated_area_m2=100,
        monthly_kwh=400,
        roof_area_m2=45,
    )
    pkgs = build_three_packages(inp, 5.0, 4750, 950, inp.goals, 4800)["packages"]
    assert pkgs["cheapest"]["upfront_cost"] <= pkgs["best_value"]["upfront_cost"]


def test_build_hp_assessment_notes_for_solar_priority():
    inp = CalculatorInput(
        latitude=48.1,
        longitude=11.5,
        goals=["hot_water"],
        hp_status="planning",
        hp_type="water_heater",
        hp_daytime_heating="yes",
        hp_priority="solar_led",
    )
    assessment = build_hp_assessment(inp)
    assert any("solar" in n.lower() for n in assessment["notes"])
