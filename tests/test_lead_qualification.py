"""Tests for lead qualification rules and profile builders."""

from types import SimpleNamespace

from lead_qualification import (
    build_lead_inp,
    build_lead_profile,
    calculator_inputs_snapshot,
    evaluate_qualified_lead,
)


def _supplier(sid="sup-1", plz="80331", fit=80):
    return {
        "id": sid,
        "locations_served": [plz],
        "regions": ["Bayern"],
        "fit_score": fit,
    }


def _rec(**overrides):
    base = {
        "system_kwp": 8,
        "goals": ["lower_bill"],
        "financials": {"annual_consumption_kwh": 4500},
        "calculator_inputs": {
            "location_name": "Munich",
            "postcode": "80331",
            "monthly_kwh": 375,
            "monthly_bill_eur": 120,
            "owner_status": "owner",
            "housing_type": "detached",
            "installation_timeframe": "asap",
            "roof_type": "pitched_south",
            "roof_area_m2": 45,
            "battery_interest": "yes",
            "financing_interest": "maybe",
            "goals": ["lower_bill"],
        },
    }
    if overrides:
        ci = {**base["calculator_inputs"], **overrides.pop("calculator_inputs", {})}
        base.update(overrides)
        base["calculator_inputs"] = ci
    return base


def _contact(**overrides):
    base = {
        "customer_postcode": "80331",
        "customer_email": "home@example.com",
        "customer_phone": "+49 89 123456",
        "customer_first_name": "Alex",
        "customer_name": "Alex Example",
        "consent_contact": True,
        "consent_share_installers": True,
        "owner_status": "owner",
        "installation_timeframe": "asap",
        "confirm_serious": False,
    }
    base.update(overrides)
    return base


def test_calculator_inputs_snapshot_merges_ev_and_hp_fields():
    inp = SimpleNamespace(
        location_name="Nuremberg",
        postcode="90402",
        goals=["ev_charging", "space_heating"],
        ev_ownership="own",
        ev_annual_km=12000,
        hp_status="planning",
        hp_type="air_source",
        hp_heated_area_m2=120,
    )
    snap = calculator_inputs_snapshot(inp)
    assert snap["postcode"] == "90402"
    assert snap["ev_ownership"] == "own"
    assert snap["ev_annual_km"] == 12000
    assert snap["hp_status"] == "planning"
    assert snap["hp_heated_area_m2"] == 120
    assert snap["ev_annual_charging_kwh"] > 0


def test_build_lead_inp_from_stored_recommendation():
    rec = _rec()
    contact = _contact(customer_postcode="80331", installation_timeframe="6_months")
    inp = build_lead_inp(rec, contact)
    assert inp.location_name == "80331"
    assert inp.goals == ["lower_bill"]
    assert inp.installation_timeframe == "6_months"
    assert inp.monthly_kwh == 375


def test_build_lead_profile_includes_roof_handoff():
    rec = _rec()
    contact = _contact()
    profile = build_lead_profile(rec, contact, [_supplier()], roof_photos={"count": 2, "photos": [{}, {}]})
    assert profile["roof"]["roof_photo_count"] == 2
    assert "attached" in profile["roof"]["installer_handoff"]
    assert profile["location"]["service_area_match"] is True
    assert profile["energy"]["annual_kwh"] == 4500


def test_evaluate_qualified_lead_quote_ready():
    result = evaluate_qualified_lead(_rec(), _contact(), [_supplier()])
    assert result["qualified"] is True
    assert result["tier"] == "quote_ready"
    assert result["passed_count"] >= 7
    assert result["rejection_reasons"] == []


def test_evaluate_qualified_lead_unqualified_missing_consent():
    result = evaluate_qualified_lead(_rec(), _contact(consent_contact=False), [_supplier()])
    assert result["qualified"] is False
    assert result["tier"] == "unqualified"
    assert "lead.rule.consent" in result["rejection_reasons"]
    assert "consent" in result["rejection_rule_ids"]


def test_evaluate_qualified_lead_tenant_apartment_not_decision_authority():
    rec = _rec(calculator_inputs={"housing_type": "apartment_owner", "owner_status": "tenant"})
    result = evaluate_qualified_lead(rec, _contact(owner_status="tenant"), [_supplier()])
    rule_ids = [r["id"] for r in result["rules"]]
    decision = next(r for r in result["rules"] if r["id"] == "decision_authority")
    assert decision["passed"] is False
    assert "decision_authority" in result["rejection_rule_ids"] or not result["qualified"]


def test_evaluate_qualified_lead_serious_via_confirm_flag():
    rec = _rec(calculator_inputs={"installation_timeframe": "not_sure"})
    contact = _contact(installation_timeframe="not_sure", confirm_serious=True)
    serious = next(r for r in evaluate_qualified_lead(rec, contact, [_supplier()])["rules"] if r["id"] == "serious_intent")
    assert serious["passed"] is True


def test_evaluate_qualified_lead_service_area_via_fit_score():
    rec = _rec()
    contact = _contact(customer_postcode="99999")
    supplier = _supplier(plz="10115", fit=60)
    supplier["locations_served"] = []
    result = evaluate_qualified_lead(rec, contact, [supplier])
    area = next(r for r in result["rules"] if r["id"] == "service_area")
    assert area["passed"] is True


def test_evaluate_qualified_lead_filters_selected_suppliers():
    rec = _rec()
    contact = _contact()
    suppliers = [_supplier("a"), _supplier("b", plz="10115")]
    result = evaluate_qualified_lead(rec, contact, suppliers, selected_supplier_ids=["b"])
    assert result["qualified"] is True


def test_evaluate_qualified_lead_consumption_from_financials_only():
    rec = _rec(calculator_inputs={"monthly_kwh": 0, "monthly_bill_eur": 0})
    rec["financials"] = {"annual_consumption_kwh": 3200}
    consumption = next(
        r for r in evaluate_qualified_lead(rec, _contact(), [_supplier()])["rules"] if r["id"] == "consumption"
    )
    assert consumption["passed"] is True


def test_evaluate_qualified_lead_fails_without_consumption_data():
    rec = _rec(calculator_inputs={"monthly_kwh": 0, "monthly_bill_eur": 0})
    rec["financials"] = {}
    result = evaluate_qualified_lead(rec, _contact(), [_supplier()])
    consumption = next(r for r in result["rules"] if r["id"] == "consumption")
    assert consumption["passed"] is False


def test_evaluate_qualified_lead_landlord_can_decide():
    rec = _rec(calculator_inputs={"owner_status": "landlord", "housing_type": "landlord"})
    result = evaluate_qualified_lead(rec, _contact(owner_status="landlord"), [_supplier()])
    decision = next(r for r in result["rules"] if r["id"] == "decision_authority")
    assert decision["passed"] is True


def test_evaluate_qualified_lead_apartment_owner_can_decide():
    rec = _rec(calculator_inputs={"housing_type": "apartment_owner", "owner_status": "owner"})
    result = evaluate_qualified_lead(rec, _contact(owner_status="owner"), [_supplier()])
    decision = next(r for r in result["rules"] if r["id"] == "decision_authority")
    assert decision["passed"] is True


def test_evaluate_qualified_lead_service_area_fails_invalid_postcode():
    rec = _rec()
    contact = _contact(customer_postcode="AB")
    low_fit = _supplier(fit=10)
    low_fit["locations_served"] = []
    low_fit["regions"] = []
    result = evaluate_qualified_lead(rec, contact, [low_fit])
    location = next(r for r in result["rules"] if r["id"] == "location")
    area = next(r for r in result["rules"] if r["id"] == "service_area")
    assert location["passed"] is False
    assert area["passed"] is False


def test_evaluate_qualified_lead_service_area_fails_empty_postcode():
    rec = _rec()
    contact = _contact(customer_postcode="")
    sup = _supplier()
    sup["locations_served"] = []
    profile = build_lead_profile(rec, contact, [sup])
    assert profile["location"]["service_area_match"] is False


def test_evaluate_qualified_lead_tenant_detached_not_decision_authority():
    rec = _rec(calculator_inputs={"housing_type": "detached", "owner_status": "tenant"})
    result = evaluate_qualified_lead(rec, _contact(owner_status="tenant"), [_supplier()])
    decision = next(r for r in result["rules"] if r["id"] == "decision_authority")
    assert decision["passed"] is False


def test_supplier_in_service_area_via_regions_only():
    rec = _rec()
    contact = _contact(customer_postcode="80331")
    sup = _supplier(fit=10)
    sup["locations_served"] = []
    result = evaluate_qualified_lead(rec, contact, [sup])
    area = next(r for r in result["rules"] if r["id"] == "service_area")
    assert area["passed"] is True


def test_build_lead_profile_no_photos_handoff_message():
    profile = build_lead_profile(_rec(), _contact(), [])
    assert "No roof photos" in profile["roof"]["installer_handoff"]
