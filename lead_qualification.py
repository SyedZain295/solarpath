"""Qualified lead rules – prevents suppliers paying for vague 'maybe someday' requests."""

from __future__ import annotations

SERIOUS_TIMEFRAMES = {"asap", "3_months", "6_months", "12_months"}


def calculator_inputs_snapshot(inp) -> dict:
    """Persist calculator answers on the recommendation for quote-time validation."""
    return {
        "location_name": getattr(inp, "location_name", ""),
        "postcode": getattr(inp, "postcode", ""),
        "owner_status": getattr(inp, "owner_status", "owner"),
        "housing_type": getattr(inp, "housing_type", "detached"),
        "installation_timeframe": getattr(inp, "installation_timeframe", "not_sure"),
        "monthly_bill_eur": getattr(inp, "monthly_bill_eur", 0),
        "monthly_kwh": getattr(inp, "monthly_kwh", 0),
        "electricity_price_ct": getattr(inp, "electricity_price_ct", 32),
        "roof_type": getattr(inp, "roof_type", "unknown"),
        "roof_area_m2": getattr(inp, "roof_area_m2", 0),
        "shading": getattr(inp, "shading", "unknown"),
        "budget_eur": getattr(inp, "budget_eur", 0),
        "has_roof_photos": getattr(inp, "has_roof_photos", False),
        "has_heat_pump": getattr(inp, "has_heat_pump", False),
        "has_ev": getattr(inp, "has_ev", False),
        "planned_ev": getattr(inp, "planned_ev", False),
        "battery_interest": getattr(inp, "battery_interest", "unsure"),
        "financing_interest": getattr(inp, "financing_interest", "no"),
        "goals": getattr(inp, "goals", []) or [],
    }


def build_lead_inp(rec: dict, contact: dict):
    """Minimal input object for supplier matching from stored recommendation + contact."""
    ci = rec.get("calculator_inputs") or {}

    class LeadInp:
        pass

    inp = LeadInp()
    inp.location_name = (contact.get("customer_postcode") or ci.get("location_name") or "").strip()
    inp.goals = rec.get("goals") or ci.get("goals") or []
    inp.budget_eur = ci.get("budget_eur", 0)
    inp.owner_status = contact.get("owner_status") or ci.get("owner_status", "owner")
    inp.housing_type = ci.get("housing_type", "detached")
    inp.installation_timeframe = contact.get("installation_timeframe") or ci.get("installation_timeframe", "not_sure")
    inp.monthly_bill_eur = ci.get("monthly_bill_eur", 0)
    inp.monthly_kwh = ci.get("monthly_kwh", 0)
    return inp


def _can_decide_for_property(owner_status: str, housing_type: str) -> bool:
    if owner_status in ("owner", "landlord"):
        return True
    if housing_type in ("detached", "semi_detached", "terraced", "landlord"):
        return owner_status == "owner"
    if housing_type == "apartment_owner" and owner_status == "owner":
        return True
    return False


def _has_consumption_data(rec: dict, ci: dict) -> bool:
    fin = rec.get("financials") or {}
    if fin.get("annual_consumption_kwh", 0) > 0:
        return True
    return bool(ci.get("monthly_bill_eur") or ci.get("monthly_kwh"))


def _supplier_in_service_area(supplier: dict, postcode: str) -> bool:
    if not postcode:
        return False
    plz = postcode.strip()[:5]
    if not plz.isdigit():
        return False
    served = supplier.get("locations_served") or []
    if any(plz.startswith(str(p)[:5]) or str(p).startswith(plz) for p in served):
        return True
    regions = supplier.get("regions") or []
    return bool(regions)


def build_lead_profile(rec: dict, contact: dict, matched_suppliers: list) -> dict:
    ci = rec.get("calculator_inputs") or {}
    fin = rec.get("financials") or {}
    sr = rec.get("system_recommendation") or {}
    return {
        "contact": {
            "first_name": contact.get("customer_first_name", ""),
            "full_name": contact.get("customer_name", ""),
            "email": contact.get("customer_email", ""),
            "phone": contact.get("customer_phone", ""),
            "preferred_contact_time": contact.get("preferred_contact_time", ""),
            "consent_contact": bool(contact.get("consent_contact")),
            "consent_share_installers": bool(contact.get("consent_share_installers")),
        },
        "location": {
            "postcode": contact.get("customer_postcode", ""),
            "town": contact.get("customer_town", ""),
            "full_address": contact.get("full_address", ""),
            "address_shared": bool(contact.get("full_address")),
            "service_area_match": any(
                _supplier_in_service_area(s, contact.get("customer_postcode", ""))
                for s in matched_suppliers
            ),
        },
        "customer_status": {
            "owner_status": contact.get("owner_status") or ci.get("owner_status", ""),
            "housing_type": ci.get("housing_type", ""),
            "installation_timeframe": contact.get("installation_timeframe") or ci.get("installation_timeframe", ""),
            "confirm_serious": bool(contact.get("confirm_serious")),
        },
        "energy": {
            "annual_kwh": fin.get("annual_consumption_kwh"),
            "monthly_bill_eur": ci.get("monthly_bill_eur"),
            "monthly_kwh": ci.get("monthly_kwh"),
            "electricity_price_ct": ci.get("electricity_price_ct"),
            "goals": rec.get("goals") or ci.get("goals") or [],
        },
        "roof": {
            "roof_type": ci.get("roof_type"),
            "roof_area_m2": ci.get("roof_area_m2"),
            "shading": ci.get("shading"),
            "has_roof_photos": ci.get("has_roof_photos"),
        },
        "preferences": {
            "battery_interest": contact.get("battery_interest") or ci.get("battery_interest", "unsure"),
            "financing_interest": contact.get("financing_interest") or ci.get("financing_interest", "no"),
            "budget_eur": ci.get("budget_eur"),
            "system_kwp": sr.get("headline_kwp") or rec.get("system_kwp"),
            "selected_package": contact.get("selected_package_id") or sr.get("package_id"),
        },
    }


def evaluate_qualified_lead(rec: dict, contact: dict, matched_suppliers: list, selected_supplier_ids: list | None = None) -> dict:
    ci = rec.get("calculator_inputs") or {}
    postcode = (contact.get("customer_postcode") or "").strip()
    owner_status = contact.get("owner_status") or ci.get("owner_status", "owner")
    housing_type = ci.get("housing_type", "detached")
    timeframe = contact.get("installation_timeframe") or ci.get("installation_timeframe", "not_sure")

    pool = matched_suppliers
    if selected_supplier_ids:
        pool = [s for s in matched_suppliers if s.get("id") in selected_supplier_ids]

    rules = []

    def add(rule_id: str, label_key: str, passed: bool, required: bool = True, detail_key: str = ""):
        rules.append({
            "id": rule_id,
            "label_key": label_key,
            "passed": passed,
            "required": required,
            "detail_key": detail_key,
        })

    add("consent", "lead.rule.consent", bool(contact.get("consent_contact")) and bool(contact.get("consent_share_installers")))
    add("consumption", "lead.rule.consumption", _has_consumption_data(rec, ci))
    add("location", "lead.rule.location", bool(postcode) and len(postcode) >= 4)
    add("decision_authority", "lead.rule.decision_authority", _can_decide_for_property(owner_status, housing_type))
    serious = timeframe in SERIOUS_TIMEFRAMES or bool(contact.get("confirm_serious"))
    add("serious_intent", "lead.rule.serious_intent", serious)
    area_match = bool(pool) and any(
        _supplier_in_service_area(s, postcode) or (s.get("fit_score", 0) >= 55)
        for s in pool
    )
    add("service_area", "lead.rule.service_area", area_match)
    add("contact_details", "lead.rule.contact_details", bool(contact.get("customer_email")) and bool(contact.get("customer_phone")))
    system_kwp = rec.get("system_kwp") or 0
    add("system_match", "lead.rule.system_match", system_kwp > 0 and bool(pool), required=False)

    failed_required = [r for r in rules if r["required"] and not r["passed"]]
    qualified = len(failed_required) == 0

    passed_count = sum(1 for r in rules if r["passed"])
    if qualified and passed_count >= 7:
        tier = "quote_ready"
    elif qualified:
        tier = "qualified"
    else:
        tier = "unqualified"

    return {
        "qualified": qualified,
        "tier": tier,
        "rules": rules,
        "passed_count": passed_count,
        "total_rules": len(rules),
        "rejection_reasons": [r["label_key"] for r in failed_required],
        "rejection_rule_ids": [r["id"] for r in failed_required],
    }
