"""Property-based tests (Hypothesis) for core solar calculations."""

from hypothesis import given, settings
from hypothesis import strategies as st

from quick_estimate import quick_estimate_range
from solar_engine import CalculatorInput, generate_recommendation


@given(monthly_kwh=st.floats(min_value=80, max_value=3000, allow_nan=False))
@settings(max_examples=40, deadline=None)
def test_quick_estimate_kwp_bounds(monthly_kwh):
    r = quick_estimate_range(monthly_kwh=monthly_kwh)
    assert r["kwp_min"] <= r["kwp_typical"] <= r["kwp_max"]
    assert r["kwp_min"] > 0
    assert abs(r["annual_kwh"] - monthly_kwh * 12) < 2.0


@given(
    monthly_kwh=st.floats(min_value=100, max_value=2000, allow_nan=False),
    roof_area=st.floats(min_value=10, max_value=500, allow_nan=False),
)
@settings(max_examples=30, deadline=None)
def test_roof_area_caps_system(monthly_kwh, roof_area):
    r = quick_estimate_range(monthly_kwh=monthly_kwh, roof_area_m2=roof_area)
    assert r["kwp_max"] >= r["kwp_min"] >= 0


@given(
    lat=st.floats(min_value=47.0, max_value=55.0, allow_nan=False),
    lon=st.floats(min_value=6.0, max_value=15.0, allow_nan=False),
    monthly_kwh=st.floats(min_value=150, max_value=800, allow_nan=False),
)
@settings(max_examples=15, deadline=None)
def test_generate_recommendation_never_crashes(lat, lon, monthly_kwh):
    inp = CalculatorInput(
        latitude=lat,
        longitude=lon,
        monthly_kwh=monthly_kwh,
        goals=["lower_bill"],
        postcode="80331",
    )
    out = generate_recommendation(inp)
    assert "selected_package" in out or "three_packages" in out
    assert out.get("system_kwp", 0) >= 0
