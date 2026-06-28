"""Heat pump / space heating profile — conditional intake and sizing hints."""

from __future__ import annotations

from typing import Any


def heat_goals_active(goals: list | None) -> bool:
    g = goals or []
    return "space_heating" in g or "hot_water" in g


def parse_hp_fields(data: dict) -> dict[str, Any]:
    return {
        "status": (data.get("hp_status") or "").strip(),
        "type": (data.get("hp_type") or "").strip(),
        "heated_area_m2": float(data.get("hp_heated_area_m2") or 0),
        "annual_heat_kwh": float(data.get("hp_annual_heat_kwh") or 0),
        "daytime_heating": (data.get("hp_daytime_heating") or "").strip(),
        "priority": (data.get("hp_priority") or "").strip(),
        "replacing": (data.get("hp_replacing") or "").strip(),
    }


def apply_hp_fields_to_input(inp, data: dict) -> None:
    hp = parse_hp_fields(data)
    inp.hp_status = hp["status"]
    inp.hp_type = hp["type"]
    inp.hp_heated_area_m2 = hp["heated_area_m2"]
    inp.hp_annual_heat_kwh = hp["annual_heat_kwh"]
    inp.hp_daytime_heating = hp["daytime_heating"]
    inp.hp_priority = hp["priority"]
    inp.hp_replacing = hp["replacing"]

    if hp["status"] == "have":
        inp.has_heat_pump = True
    elif hp["status"] in ("planning", "replacing_fossil"):
        inp.has_heat_pump = False
    if hp["type"] == "water_heater":
        inp.has_electric_water_heater = True


def estimate_hp_annual_kwh(inp) -> float:
    goals = getattr(inp, "goals", None) or []
    direct = float(getattr(inp, "hp_annual_heat_kwh", 0) or 0)
    if direct > 0:
        return round(direct)

    area = float(getattr(inp, "hp_heated_area_m2", 0) or 0)
    hp_type = getattr(inp, "hp_type", "") or ""
    space = "space_heating" in goals
    hot = "hot_water" in goals

    total = 0.0
    if space and area > 0:
        # Electricity at heat pump (rough COP ~3 → ~35 kWh/m² heated area per year)
        total += area * 35
    elif space:
        total += 3500.0

    if hot or hp_type == "water_heater":
        total += 1800.0 if hot and not space else 1200.0

    if total <= 0 and heat_goals_active(goals):
        return 3000.0 if space else 1500.0
    return round(total)


def hp_profile_complete(inp) -> bool:
    if not heat_goals_active(getattr(inp, "goals", None)):
        return False
    if not getattr(inp, "hp_status", ""):
        return False
    if not getattr(inp, "hp_type", ""):
        return False
    goals = getattr(inp, "goals", None) or []
    if "space_heating" in goals:
        if float(getattr(inp, "hp_heated_area_m2", 0) or 0) <= 0 and float(getattr(inp, "hp_annual_heat_kwh", 0) or 0) <= 0:
            return False
    return bool(getattr(inp, "hp_daytime_heating", "") and getattr(inp, "hp_priority", ""))


def build_hp_assessment(inp, electricity_price_ct: float = 32.0) -> dict:
    goals = getattr(inp, "goals", None) or []
    hp_kwh = estimate_hp_annual_kwh(inp)
    price = electricity_price_ct / 100
    grid_annual = round(hp_kwh * price)
    solar_offset = 50 if getattr(inp, "hp_daytime_heating", "") in ("yes", "managed") else 35
    with_pv_annual = round(grid_annual * (1 - solar_offset / 100))

    status_labels = {
        "have": "Heat pump already installed",
        "planning": "Planning a heat pump",
        "replacing_fossil": "Replacing gas/oil with a heat pump",
        "hot_water_only": "Hot water only (no space heating)",
    }
    type_labels = {
        "air_source": "Air-source heat pump",
        "ground_source": "Ground-source heat pump",
        "water_heater": "Heat-pump water heater",
        "unsure": "Not sure yet",
    }
    priority_labels = {
        "lowest_cost": "Lowest running cost",
        "solar_led": "Run heating from solar when possible",
        "comfort": "Comfort and stable indoor temperature",
        "backup": "Heating resilience during outages",
    }

    notes = []
    if getattr(inp, "hp_status", "") == "replacing_fossil":
        notes.append("Replacing fossil heat changes your electricity profile — PV sizing should reflect new load.")
    if getattr(inp, "hp_daytime_heating", "") == "no":
        notes.append("Heating mostly outside solar hours — battery or tariff optimisation helps more than extra panels alone.")
    if getattr(inp, "hp_priority", "") == "solar_led":
        notes.append("Solar-led heating works best with smart controls and optionally a battery for evening heat.")

    goal_labels = []
    if "space_heating" in goals:
        goal_labels.append("Space heating")
    if "hot_water" in goals:
        goal_labels.append("Hot water")

    return {
        "goals_label": " · ".join(goal_labels) or "—",
        "status": getattr(inp, "hp_status", ""),
        "status_label": status_labels.get(getattr(inp, "hp_status", ""), "—"),
        "type": getattr(inp, "hp_type", ""),
        "type_label": type_labels.get(getattr(inp, "hp_type", ""), "—"),
        "heated_area_m2": getattr(inp, "hp_heated_area_m2", 0),
        "annual_heat_kwh": hp_kwh,
        "daytime_heating": getattr(inp, "hp_daytime_heating", ""),
        "priority": getattr(inp, "hp_priority", ""),
        "priority_label": priority_labels.get(getattr(inp, "hp_priority", ""), "—"),
        "replacing": getattr(inp, "hp_replacing", ""),
        "estimated_grid_heating_cost_annual_eur": grid_annual,
        "estimated_heating_cost_with_pv_annual_eur": with_pv_annual,
        "notes": notes,
    }


def hp_snapshot(inp) -> dict:
    return {
        "hp_status": getattr(inp, "hp_status", ""),
        "hp_type": getattr(inp, "hp_type", ""),
        "hp_heated_area_m2": getattr(inp, "hp_heated_area_m2", 0),
        "hp_annual_heat_kwh": getattr(inp, "hp_annual_heat_kwh", 0),
        "hp_daytime_heating": getattr(inp, "hp_daytime_heating", ""),
        "hp_priority": getattr(inp, "hp_priority", ""),
        "hp_replacing": getattr(inp, "hp_replacing", ""),
        "hp_estimated_annual_kwh": estimate_hp_annual_kwh(inp),
    }
