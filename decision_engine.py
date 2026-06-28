"""Goal → technology decision engine with explicit recommendations."""

GOAL_TECHNOLOGY_DECISIONS = {
    "lower_bill": {
        "goal_label": "Lower electricity bill",
        "primary": "Rooftop PV sized around annual usage and daytime consumption",
        "components": ["Grid-tied PV panels", "String or hybrid inverter", "Smart meter / energy monitor"],
        "battery_default": False,
        "battery_note": "A battery is not required to lower your bill. We show three honest options below.",
        "icon": "💡",
        "alternatives": [],
    },
    "backup": {
        "goal_label": "Backup during power cuts",
        "primary": "PV + battery + hybrid inverter + dedicated backup circuit",
        "components": [
            "PV array",
            "Hybrid inverter with EPS/backup output",
            "Battery storage (minimum 5 kWh)",
            "Dedicated backup consumer unit for critical loads",
            "Automatic transfer switch",
        ],
        "battery_default": True,
        "battery_note": "Battery and backup circuitry are essential for outage protection.",
        "icon": "🔋",
        "alternatives": [],
    },
    "hot_water": {
        "goal_label": "Hot water",
        "primary": "PV + heat-pump water heater or smart immersion diverter",
        "components": [
            "Rooftop PV (daytime surplus routing)",
            "Heat-pump water heater OR smart hot-water diverter",
            "Hot water cylinder with immersion backup",
        ],
        "battery_default": False,
        "battery_note": "Compare against solar thermal – often lower upfront but less flexible long-term.",
        "icon": "🚿",
        "alternatives": [
            {
                "name": "Solar thermal collectors",
                "pros": "Direct hot water generation, proven technology",
                "cons": "Less flexible, harder to expand, separate system",
                "typical_cost_eur": 4500,
            },
            {
                "name": "PV + heat-pump water heater",
                "pros": "Uses surplus PV, works year-round, integrates with future battery",
                "cons": "Higher upfront if no PV yet",
                "typical_cost_eur": 3500,
            },
        ],
    },
    "space_heating": {
        "goal_label": "Space heating",
        "primary": "Heat pump + PV + smart energy management",
        "components": [
            "Air-source or ground-source heat pump",
            "PV array sized for heat-pump daytime load",
            "Smart energy manager (heat pump scheduling)",
            "Optional buffer tank",
        ],
        "battery_default": False,
        "battery_note": "More panels alone will not heat your home efficiently – a heat pump is the core technology.",
        "icon": "🏠",
        "alternatives": [],
    },
    "business": {
        "goal_label": "Business/commercial power",
        "primary": "Commercial PV based on half-hourly load profile, roof/land area, and demand peaks",
        "components": [
            "Commercial PV array (3-phase)",
            "Commercial inverter with monitoring dashboard",
            "Optional peak-shaving battery",
            "Half-hourly consumption analysis",
        ],
        "battery_default": False,
        "battery_note": "Battery recommended only for peak shaving on time-of-use tariffs.",
        "icon": "🏢",
        "alternatives": [],
    },
    "farming": {
        "goal_label": "Farming/agriculture",
        "primary": "Farm PV with irrigation/pump optimisation",
        "components": [
            "Barn roof or ground-mount PV",
            "Irrigation pump motor optimisation",
            "Optional Agri-PV (dual-use elevated panels)",
            "EV charging for farm vehicles",
        ],
        "battery_default": False,
        "battery_note": "Battery optional for irrigation pumps and equipment charging.",
        "icon": "🌾",
        "alternatives": [
            {"name": "Barn roof PV", "pros": "Uses existing structure", "cons": "Limited area"},
            {"name": "Agri-PV", "pros": "Dual land use", "cons": "Higher mounting cost"},
            {"name": "Ground-mount", "pros": "Maximum capacity", "cons": "Land use"},
        ],
    },
    "ev_charging": {
        "goal_label": "EV charging",
        "primary": "PV + smart wallbox + battery/dynamic charging controls",
        "components": [
            "Rooftop PV",
            "Smart wallbox (11–22 kW)",
            "Battery or dynamic charging controller",
            "Solar surplus routing to EV",
        ],
        "battery_default": True,
        "battery_note": "Battery or smart controls maximise charging from solar, not grid.",
        "icon": "⚡",
        "alternatives": [],
    },
}

PACKAGE_DEFINITIONS = {
    "cheapest": {
        "id": "cheapest",
        "label": "Budget",
        "subtitle": "Lowest upfront — string inverter, catalog budget tier components",
        "badge": "💰 Budget",
        "battery_multiplier": 0,
        "inverter_type": "String inverter",
        "backup_capable": False,
        "warranty_years": 10,
        "cost_multiplier": 0.92,
        "reliability_score": 70,
    },
    "best_value": {
        "id": "best_value",
        "label": "Balanced",
        "subtitle": "Best long-term value — hybrid inverter and right-sized battery",
        "badge": "⚖️ Best Value",
        "battery_multiplier": 1.0,
        "inverter_type": "Hybrid inverter",
        "backup_capable": False,
        "warranty_years": 15,
        "cost_multiplier": 1.0,
        "reliability_score": 85,
    },
    "most_reliable": {
        "id": "most_reliable",
        "label": "Premium",
        "subtitle": "Premium components — larger battery, backup-capable hybrid inverter",
        "badge": "🛡️ Premium",
        "battery_multiplier": 1.6,
        "inverter_type": "Hybrid inverter with backup EPS",
        "backup_capable": True,
        "warranty_years": 20,
        "cost_multiplier": 1.18,
        "reliability_score": 95,
    },
}


def get_goal_decisions(goals: list) -> list:
    """Return explicit technology decisions for each selected goal."""
    results = []
    for g in goals:
        if g in GOAL_TECHNOLOGY_DECISIONS:
            results.append({"goal": g, **GOAL_TECHNOLOGY_DECISIONS[g]})
    return results


def battery_required_for_goal(goals: list) -> bool:
    """Battery only required for backup/EV goals – not for lower_bill alone."""
    return "backup" in goals


def economically_size_battery(system_kwp: float, annual_kwh: float, goals: list) -> float:
    """Size battery only where financially justified."""
    if battery_required_for_goal(goals):
        return round(min(15, max(5, annual_kwh / 365 * 0.3)), 1)
    if "ev_charging" in goals:
        return round(min(10, max(5, system_kwp * 1.0)), 1)
    # For lower_bill: small battery only if system is large enough
    if system_kwp >= 6:
        return round(min(7, system_kwp * 0.8), 1)
    return 0


def resilience_battery_kwh(system_kwp: float, annual_kwh: float, goals: list) -> float:
    """Larger battery for backup/resilience package."""
    base = economically_size_battery(system_kwp, annual_kwh, goals)
    if "backup" in goals:
        return round(min(20, max(10, annual_kwh / 365 * 0.5)), 1)
    return round(max(base * 1.6, 8), 1)


def get_tradeoffs(cheapest: dict, best_value: dict, most_reliable: dict) -> dict:
    """What customer gives up with cheaper option."""
    def _clean(items):
        return [i for i in items if i]

    return {
        "cheapest_gives_up": _clean([
            f"€{most_reliable['upfront_cost'] - cheapest['upfront_cost']:,} less resilience vs Best Resilience package",
            "No backup power during outages" if not cheapest.get("backup_capable") else None,
            f"{best_value['self_consumption_ratio'] - cheapest['self_consumption_ratio']:.0f}% lower self-consumption without right-sized battery",
            f"Shorter warranty ({cheapest['warranty_years']} vs {most_reliable['warranty_years']} years)",
        ]),
        "best_value_gives_up": _clean([
            "Partial backup only – not full resilience",
            f"€{most_reliable['upfront_cost'] - best_value['upfront_cost']:,} saved vs full backup package",
        ]),
        "most_reliable_gives_up": _clean([
            f"€{most_reliable['upfront_cost'] - cheapest['upfront_cost']:,} higher upfront cost",
            f"{most_reliable['payback_years'] - cheapest['payback_years']:.1f} years longer payback vs PV-only",
        ]),
    }
