"""Solar recommendation engine with German tariff support."""

from dataclasses import dataclass, field
from typing import Optional

from confidence_score import PVGIS_LIMITATION, calculate_confidence_score
from decision_engine import (
    PACKAGE_DEFINITIONS,
    battery_required_for_goal,
    economically_size_battery,
    get_goal_decisions,
    get_tradeoffs,
    resilience_battery_kwh,
)
from energy_advisor import (
    HOUSING_PATHS,
    analyze_household_usage,
    build_quote_ready_profile,
    estimate_meter_timeline,
    get_apartment_recommendations,
)
from ev_profile import (
    build_ev_assessment,
    estimate_ev_annual_kwh,
    ev_wallbox_needed,
    recommend_ev_battery_kwh,
)
from financial_model import DISCLAIMER, build_financial_model
from heat_pump_profile import build_hp_assessment, estimate_hp_annual_kwh, heat_goals_active
from lead_qualification import calculator_inputs_snapshot
from platform_features import (
    QUOTE_QUALITY_CHECKLIST,
    budget_first_recommendation,
    build_decision_report,
    build_energy_roadmap,
    build_financing_comparison,
    build_household_energy_profile,
    build_price_scenarios,
    build_why_explanation,
    calculate_lead_qualification_tier,
    calculate_readiness_score,
)
from product_catalog import (
    SHADING_YIELD_FACTORS,
    apply_shading_factor,
    build_package_spec,
    build_sizing_summary,
    components_from_spec,
    max_kwp_from_roof_area,
    recommend_kwp_from_consumption,
)

# Bundesnetzagentur feed-in tariffs (Feb–Jul 2026, Germany)
GERMAN_TARIFFS = {
    "partial_feed_in": {  # ct/kWh
        "up_to_10kw": 7.78,
        "up_to_40kw": 6.83,
    },
    "full_feed_in": {  # ct/kWh
        "up_to_10kw": 12.34,
        "up_to_40kw": 10.87,
    },
}

# Average German electricity price (ct/kWh) for self-consumption savings
DEFAULT_ELECTRICITY_PRICE_CT = 32.0

# CO2 factor: kg CO2 per kWh (German grid average)
CO2_KG_PER_KWH = 0.385

# Cost estimates per kWp installed (EUR) – Germany 2026 ranges
COST_PER_KWP = {
    "residential": {"min": 1200, "max": 1800, "typical": 1450},
    "commercial": {"min": 900, "max": 1400, "typical": 1100},
    "agricultural": {"min": 800, "max": 1200, "typical": 950},
}

BATTERY_COST_PER_KWH = {"min": 450, "max": 650, "typical": 550}

GOAL_TECHNOLOGY_MAP = {
    "lower_bill": {
        "primary": "Rooftop Photovoltaic (PV)",
        "secondary": "Grid-tied solar panels with net metering",
        "battery_recommended": False,
        "battery_reason": "Optional – increases self-consumption but adds cost",
        "icon": "☀️",
        "description": "A grid-connected PV system converts sunlight into electricity, offsetting your grid consumption and earning feed-in tariff income on surplus generation.",
    },
    "backup": {
        "primary": "PV + Battery Storage System",
        "secondary": "Hybrid inverter with backup capability",
        "battery_recommended": True,
        "battery_reason": "Essential for power during outages – stores daytime solar for evening and blackout use",
        "icon": "🔋",
        "description": "A solar-plus-battery system keeps critical circuits powered during grid outages while still saving on your electricity bill.",
    },
    "hot_water": {
        "primary": "Solar Thermal Collectors",
        "secondary": "Heat pump water heater (hybrid option)",
        "battery_recommended": False,
        "battery_reason": "Not applicable – thermal systems heat water directly",
        "icon": "🚿",
        "description": "Solar thermal panels heat water directly, reducing gas or electric water heating costs by 50–70%.",
    },
    "space_heating": {
        "primary": "Solar Thermal + Heat Pump",
        "secondary": "PV-powered air-source heat pump",
        "battery_recommended": False,
        "battery_reason": "Optional PV battery can run heat pump during outages",
        "icon": "🏠",
        "description": "Combining solar thermal or PV with a heat pump provides efficient space heating with significantly lower running costs.",
    },
    "business": {
        "primary": "Commercial PV System",
        "secondary": "Three-phase inverter, monitoring dashboard",
        "battery_recommended": False,
        "battery_reason": "Consider battery for peak shaving if on time-of-use tariffs",
        "icon": "🏢",
        "description": "Commercial-scale PV reduces operating costs, improves ESG credentials, and may qualify for accelerated depreciation.",
    },
    "farming": {
        "primary": "Agri-PV / Ground-Mount Solar",
        "secondary": "Dual-use elevated panels for crop shading",
        "battery_recommended": False,
        "battery_reason": "Optional for farm equipment charging and irrigation pumps",
        "icon": "🌾",
        "description": "Agri-PV systems generate power while allowing farming underneath, or ground-mount arrays maximise land use for energy production.",
    },
    "ev_charging": {
        "primary": "PV + EV Charger + Battery",
        "secondary": "Smart charging with solar surplus routing",
        "battery_recommended": True,
        "battery_reason": "Recommended – charge your EV from stored solar, not grid power at night",
        "icon": "⚡",
        "description": "Solar-powered EV charging lets you drive on sunshine, slashing fuel costs and carbon emissions.",
    },
}

ROOF_TYPE_FACTORS = {
    "flat": 0.92,
    "pitched_south": 1.0,
    "pitched_east_west": 0.88,
    "pitched_north": 0.55,
    "metal": 1.0,
    "tile": 0.98,
    "slate": 0.95,
    "unknown": 0.90,
    "ground_mount": 1.0,
    "balcony": 0.75,
}


@dataclass
class CalculatorInput:
    latitude: float
    longitude: float
    location_name: str = ""
    postcode: str = ""
    monthly_bill_eur: float = 0
    monthly_kwh: float = 0
    roof_type: str = "pitched_south"
    roof_area_m2: float = 0
    budget_eur: float = 0
    goals: list = field(default_factory=list)
    electricity_price_ct: float = DEFAULT_ELECTRICITY_PRICE_CT
    feed_in_type: str = "partial"
    housing_type: str = "detached"
    owner_status: str = "owner"
    shading: str = "unknown"
    has_heat_pump: bool = False
    has_ev: bool = False
    has_electric_water_heater: bool = False
    has_pool: bool = False
    has_roof_photos: bool = False
    roof_photo_set_id: str = ""
    roof_photo_count: int = 0
    has_home_office: bool = False
    has_ac: bool = False
    planned_ev: bool = False
    high_daytime_use: bool = False
    planned_extension: bool = False
    budget_first_mode: bool = False
    installation_timeframe: str = "not_sure"
    selected_package: str = ""
    connect_meter: bool = False
    battery_interest: str = "unsure"
    financing_interest: str = "no"
    ev_ownership: str = ""
    ev_vehicle_model: str = ""
    ev_annual_km: float = 0
    ev_consumption_kwh_100km: float = 18.0
    ev_home_charging: str = ""
    ev_park_home_daytime: str = ""
    ev_has_wallbox: str = ""
    ev_charging_priority: str = ""
    ev_dynamic_tariff_interest: str = ""
    hp_status: str = ""
    hp_type: str = ""
    hp_heated_area_m2: float = 0
    hp_annual_heat_kwh: float = 0
    hp_daytime_heating: str = ""
    hp_priority: str = ""
    hp_replacing: str = ""
    user_situation: str = ""
    has_existing_pv: bool = False
    existing_pv_kwp: float = 0
    existing_inverter_kwp: float = 0
    existing_pv_year: int = 0


@dataclass
class ComponentItem:
    name: str
    quantity: int
    unit: str
    estimated_cost_eur: float
    notes: str = ""


def estimate_annual_consumption_kwh(inp: CalculatorInput) -> float:
    if inp.monthly_kwh > 0:
        base = inp.monthly_kwh * 12
    elif inp.monthly_bill_eur > 0:
        price_eur = inp.electricity_price_ct / 100
        base = (inp.monthly_bill_eur / price_eur) * 12
    else:
        base = 4000  # German household average
    goals = inp.goals or []
    if "ev_charging" in goals:
        ev_kwh = estimate_ev_annual_kwh(inp)
        if ev_kwh > 0 and not getattr(inp, "has_ev", False) and not getattr(inp, "planned_ev", False):
            base += ev_kwh
    if heat_goals_active(goals):
        hp_kwh = estimate_hp_annual_kwh(inp)
        if hp_kwh > 0 and getattr(inp, "hp_status", "") in ("planning", "replacing_fossil"):
            base += hp_kwh * 0.85
    return base


def recommend_system_size_kwp(
    annual_kwh: float,
    specific_yield: float,
    goals: list,
    roof_area_m2: float = 0,
    panel_wp: int = 430,
) -> float:
    """MVP sizing: annual use ÷ PVGIS specific yield, rounded to standard kWp."""
    size = recommend_kwp_from_consumption(annual_kwh, specific_yield, goals)
    roof_cap = max_kwp_from_roof_area(roof_area_m2, panel_wp)
    if roof_cap is not None and size > roof_cap:
        size = max(2.0, round(roof_cap, 1))
    return max(0.0, min(40.0, size))


def round_to_standard_kwp(raw_kwp: float) -> float:
    from product_catalog import round_to_standard_kwp as _round

    return _round(raw_kwp)


def recommend_battery_kwh(
    system_kwp: float, goals: list, annual_kwh: float, inp: CalculatorInput | None = None
) -> float:
    tech = _primary_goal_tech(goals)
    ev_override = recommend_ev_battery_kwh(inp, system_kwp, annual_kwh, goals) if inp else None
    if ev_override is not None:
        if ev_override > 0:
            return ev_override
        if "backup" not in goals:
            return 0.0
    if not tech["battery_recommended"]:
        if "backup" not in goals and "ev_charging" not in goals:
            return 0
    if "backup" in goals:
        return round(min(15, max(5, annual_kwh / 365 * 0.3)), 1)
    if "ev_charging" in goals:
        return round(min(15, max(7, system_kwp * 1.5)), 1)
    return round(min(10, system_kwp * 1.2), 1)


def _primary_goal_tech(goals: list) -> dict:
    priority = ["backup", "ev_charging", "farming", "business", "hot_water", "space_heating", "lower_bill"]
    for g in priority:
        if g in goals:
            return GOAL_TECHNOLOGY_MAP[g]
    return GOAL_TECHNOLOGY_MAP["lower_bill"]


def get_feed_in_rate_ct(system_kwp: float, feed_in_type: str) -> float:
    tier = "up_to_10kw" if system_kwp <= 10 else "up_to_40kw"
    if feed_in_type == "full":
        return GERMAN_TARIFFS["full_feed_in"][tier]
    return GERMAN_TARIFFS["partial_feed_in"][tier]


def _estimate_self_consumption_ratio(inp: CalculatorInput, battery_kwh: float, goals: list) -> float:
    """Estimate share of PV generation used on-site (Eigenverbrauch)."""
    ratio = 0.35
    if getattr(inp, "high_daytime_use", False):
        ratio += 0.08
    if getattr(inp, "has_ev", False) or getattr(inp, "planned_ev", False) or "ev_charging" in goals:
        ratio += 0.06
    if getattr(inp, "has_heat_pump", False) or "space_heating" in goals:
        ratio += 0.05
    if "hot_water" in goals:
        ratio += 0.03
    if battery_kwh > 0:
        ratio = min(0.85, ratio + battery_kwh * 0.04)
    return min(0.85, max(0.25, ratio))


def build_energy_economics(financials: dict, inp: CalculatorInput) -> dict:
    """Self-use vs feed-in breakdown for results UI (Überschusseinspeisung)."""
    sc_savings = financials["self_consumption_savings_annual"]
    feed_in = financials["feed_in_income_annual"]
    total = financials["annual_savings"]
    sc_share = round(sc_savings / total * 100) if total > 0 else 0
    price_ct = inp.electricity_price_ct
    feed_rate = financials["feed_in_rate_ct"]
    return {
        "self_consumed_kwh": financials["self_consumed_kwh"],
        "exported_kwh": financials["exported_kwh"],
        "self_consumption_savings_annual": sc_savings,
        "feed_in_income_annual": feed_in,
        "annual_savings_total": total,
        "self_consumption_ratio": financials["self_consumption_ratio"],
        "self_consumption_share_of_savings_pct": sc_share,
        "electricity_price_ct": price_ct,
        "feed_in_rate_ct": feed_rate,
        "feed_in_type": inp.feed_in_type,
        "value_per_kwh_self_use_ct": price_ct,
        "value_per_kwh_export_ct": feed_rate,
        "export_premium_ratio": round(price_ct / feed_rate, 1) if feed_rate > 0 else 0,
    }


def calculate_financials_with_upfront(
    inp: CalculatorInput,
    upfront_cost: float,
    system_kwp: float,
    annual_production_kwh: float,
    battery_kwh: float,
) -> dict:
    """Financial model using catalog BOM cost instead of generic €/kWp."""
    annual_kwh = estimate_annual_consumption_kwh(inp)
    goals = inp.goals or ["lower_bill"]
    self_consumption_ratio = _estimate_self_consumption_ratio(inp, battery_kwh, goals)

    self_consumed_kwh = annual_production_kwh * self_consumption_ratio
    exported_kwh = annual_production_kwh - self_consumed_kwh

    price_eur = inp.electricity_price_ct / 100
    feed_in_rate = get_feed_in_rate_ct(system_kwp, inp.feed_in_type) / 100

    savings_self_consumption = self_consumed_kwh * price_eur
    savings_feed_in = exported_kwh * feed_in_rate
    annual_savings = savings_self_consumption + savings_feed_in
    monthly_savings = annual_savings / 12

    payback_years = upfront_cost / annual_savings if annual_savings > 0 else 99
    co2_reduction_kg = annual_production_kwh * CO2_KG_PER_KWH

    return {
        "system_cost_min": round(upfront_cost * 0.95),
        "system_cost_max": round(upfront_cost * 1.05),
        "system_cost_typical": round(upfront_cost),
        "monthly_savings": round(monthly_savings, 2),
        "annual_savings": round(annual_savings, 2),
        "payback_years": round(payback_years, 1),
        "savings_10yr": round(annual_savings * 10 - upfront_cost),
        "savings_20yr": round(annual_savings * 20 - upfront_cost),
        "co2_reduction_kg": round(co2_reduction_kg),
        "co2_reduction_tonnes": round(co2_reduction_kg / 1000, 2),
        "self_consumption_ratio": round(self_consumption_ratio * 100),
        "self_consumed_kwh": round(self_consumed_kwh),
        "exported_kwh": round(exported_kwh),
        "feed_in_income_annual": round(savings_feed_in, 2),
        "self_consumption_savings_annual": round(savings_self_consumption, 2),
        "feed_in_rate_ct": get_feed_in_rate_ct(system_kwp, inp.feed_in_type),
        "annual_consumption_kwh": round(annual_kwh),
    }


def _resolve_package_battery(
    package_id: str,
    inp: CalculatorInput,
    system_kwp: float,
    annual_kwh: float,
    goals: list,
) -> float:
    """Respect user battery_interest (yes/no/unsure) and package tier."""
    interest = getattr(inp, "battery_interest", "unsure")
    required = battery_required_for_goal(goals)
    ev_override = recommend_ev_battery_kwh(inp, system_kwp, annual_kwh, goals)

    # Budget tier stays PV-first — battery belongs in Balanced / Premium unless backup is mandatory.
    if package_id == "cheapest":
        if "backup" in goals:
            return round(min(10, max(5, annual_kwh / 365 * 0.25)), 1)
        if interest == "yes":
            return round(min(5, max(3, system_kwp * 0.6)), 1)
        return 0.0

    if interest == "no" and not required:
        if ev_override is not None and ev_override == 0:
            return 0.0
        if ev_override is None and "ev_charging" not in goals:
            return 0.0
        if ev_override is None and "ev_charging" in goals and interest == "no":
            return 0.0

    if package_id == "best_value":
        if interest == "no" and not required and ev_override in (None, 0):
            return 0.0
        if ev_override is not None and ev_override > 0:
            return ev_override
        return economically_size_battery(system_kwp, annual_kwh, goals)
    if interest == "no" and not required and ev_override in (None, 0):
        return 0.0
    if ev_override is not None and ev_override > 0:
        return max(ev_override, resilience_battery_kwh(system_kwp, annual_kwh, goals) * 0.85)
    return resilience_battery_kwh(system_kwp, annual_kwh, goals)


def calculate_financials(
    inp: CalculatorInput,
    system_kwp: float,
    annual_production_kwh: float,
    battery_kwh: float,
    specific_yield: float,
) -> dict:
    annual_kwh = estimate_annual_consumption_kwh(inp)
    goals = inp.goals or ["lower_bill"]

    if "business" in goals or "farming" in goals:
        cost_profile = "commercial" if "business" in goals else "agricultural"
    else:
        cost_profile = "residential"

    cost_range = COST_PER_KWP[cost_profile]
    system_cost_min = system_kwp * cost_range["min"]
    system_cost_max = system_kwp * cost_range["max"]
    system_cost_typical = system_kwp * cost_range["typical"]

    if battery_kwh > 0:
        batt_min = battery_kwh * BATTERY_COST_PER_KWH["min"]
        batt_max = battery_kwh * BATTERY_COST_PER_KWH["max"]
        batt_typical = battery_kwh * BATTERY_COST_PER_KWH["typical"]
        system_cost_min += batt_min
        system_cost_max += batt_max
        system_cost_typical += batt_typical

    # Extra costs for special technologies
    extras = 0
    if "hot_water" in goals:
        extras += 4500
    if "space_heating" in goals:
        extras += 8000
    if "ev_charging" in goals:
        extras += 1200
    if "farming" in goals and system_kwp > 10:
        extras += system_kwp * 80

    system_cost_min += extras
    system_cost_max += extras
    system_cost_typical += extras

    self_consumption_ratio = _estimate_self_consumption_ratio(inp, battery_kwh, goals)

    self_consumed_kwh = annual_production_kwh * self_consumption_ratio
    exported_kwh = annual_production_kwh - self_consumed_kwh

    price_eur = inp.electricity_price_ct / 100
    feed_in_rate = get_feed_in_rate_ct(system_kwp, inp.feed_in_type) / 100

    savings_self_consumption = self_consumed_kwh * price_eur
    savings_feed_in = exported_kwh * feed_in_rate
    annual_savings = savings_self_consumption + savings_feed_in
    monthly_savings = annual_savings / 12

    payback_years = system_cost_typical / annual_savings if annual_savings > 0 else 99
    savings_10yr = annual_savings * 10 - system_cost_typical
    savings_20yr = annual_savings * 20 - system_cost_typical

    co2_reduction_kg = annual_production_kwh * CO2_KG_PER_KWH

    return {
        "system_cost_min": round(system_cost_min),
        "system_cost_max": round(system_cost_max),
        "system_cost_typical": round(system_cost_typical),
        "monthly_savings": round(monthly_savings, 2),
        "annual_savings": round(annual_savings, 2),
        "payback_years": round(payback_years, 1),
        "savings_10yr": round(savings_10yr),
        "savings_20yr": round(savings_20yr),
        "co2_reduction_kg": round(co2_reduction_kg),
        "co2_reduction_tonnes": round(co2_reduction_kg / 1000, 2),
        "self_consumption_ratio": round(self_consumption_ratio * 100),
        "self_consumed_kwh": round(self_consumed_kwh),
        "exported_kwh": round(exported_kwh),
        "feed_in_income_annual": round(savings_feed_in, 2),
        "self_consumption_savings_annual": round(savings_self_consumption, 2),
        "feed_in_rate_ct": get_feed_in_rate_ct(system_kwp, inp.feed_in_type),
        "annual_consumption_kwh": round(annual_kwh),
    }


def build_component_list(system_kwp: float, battery_kwh: float, goals: list) -> list:
    num_panels = max(1, round(system_kwp * 1000 / 420))
    inverter_kw = max(3, round(system_kwp * 1.1))

    components = [
        ComponentItem(
            name="Monocrystalline PV Panels (420W)",
            quantity=num_panels,
            unit="panels",
            estimated_cost_eur=round(num_panels * 165),
            notes=f"Total DC capacity: ~{system_kwp} kWp",
        ),
        ComponentItem(
            name=f"Hybrid/String Inverter ({inverter_kw} kW)",
            quantity=1,
            unit="unit",
            estimated_cost_eur=round(800 + inverter_kw * 120),
            notes="Includes MPPT trackers",
        ),
        ComponentItem(
            name="Mounting & Racking System",
            quantity=1,
            unit="set",
            estimated_cost_eur=round(system_kwp * 180),
            notes="Roof or ground mount rails and clamps",
        ),
        ComponentItem(
            name="DC/AC Cabling & Protection",
            quantity=1,
            unit="set",
            estimated_cost_eur=round(system_kwp * 90),
            notes="Cables, fuses, surge protection",
        ),
        ComponentItem(
            name="Installation & Commissioning",
            quantity=1,
            unit="set",
            estimated_cost_eur=round(system_kwp * 350),
            notes="Labour, scaffolding, grid connection",
        ),
        ComponentItem(
            name="Smart Energy Monitor",
            quantity=1,
            unit="unit",
            estimated_cost_eur=250,
            notes="Real-time production & consumption tracking",
        ),
    ]

    if battery_kwh > 0:
        components.append(
            ComponentItem(
                name=f"Lithium Battery Storage ({battery_kwh} kWh)",
                quantity=1,
                unit="unit",
                estimated_cost_eur=round(battery_kwh * BATTERY_COST_PER_KWH["typical"]),
                notes="Includes BMS and inverter integration",
            )
        )

    if "hot_water" in goals:
        components.append(
            ComponentItem(
                name="Solar Thermal Collector Array",
                quantity=1,
                unit="set",
                estimated_cost_eur=4500,
                notes="Flat-plate collectors + hot water tank",
            )
        )

    if "ev_charging" in goals and ev_wallbox_needed(inp):
        components.append(
            ComponentItem(
                name="Smart EV Charger (11–22 kW)",
                quantity=1,
                unit="unit",
                estimated_cost_eur=1200,
                notes="Solar-optimised charging with app control",
            )
        )
    elif "ev_charging" in goals and not ev_wallbox_needed(inp):
        components.append(
            ComponentItem(
                name="PV surplus routing / smart wallbox upgrade",
                quantity=1,
                unit="unit",
                estimated_cost_eur=450,
                notes="Integrate existing wallbox with solar surplus and tariff scheduling",
            )
        )

    if "farming" in goals and system_kwp > 10:
        components.append(
            ComponentItem(
                name="Ground-Mount / Agri-PV Structure",
                quantity=1,
                unit="set",
                estimated_cost_eur=round(system_kwp * 80),
                notes="Galvanised steel frames, concrete foundations",
            )
        )

    return components


def calculate_suitability_score(
    inp: CalculatorInput,
    specific_yield: float,
    system_kwp: float,
) -> dict:
    score = 50
    factors = []

    roof_factor = ROOF_TYPE_FACTORS.get(inp.roof_type, 0.90)
    if roof_factor >= 0.95:
        score += 15
        factors.append(
            {"factor": "Roof orientation", "impact": "positive", "detail": "Good roof type for solar generation"}
        )
    elif roof_factor >= 0.85:
        score += 8
        factors.append(
            {
                "factor": "Roof orientation",
                "impact": "neutral",
                "detail": "Acceptable roof type with minor production reduction",
            }
        )
    else:
        score -= 10
        factors.append(
            {
                "factor": "Roof orientation",
                "impact": "negative",
                "detail": "Suboptimal roof orientation reduces output significantly",
            }
        )

    if specific_yield >= 1000:
        score += 20
        factors.append(
            {
                "factor": "Solar irradiance",
                "impact": "positive",
                "detail": f"Excellent solar resource ({specific_yield:.0f} kWh/kWp/year)",
            }
        )
    elif specific_yield >= 850:
        score += 12
        factors.append(
            {
                "factor": "Solar irradiance",
                "impact": "positive",
                "detail": f"Good solar resource ({specific_yield:.0f} kWh/kWp/year)",
            }
        )
    else:
        score += 5
        factors.append(
            {
                "factor": "Solar irradiance",
                "impact": "neutral",
                "detail": f"Moderate solar resource ({specific_yield:.0f} kWh/kWp/year)",
            }
        )

    annual_kwh = estimate_annual_consumption_kwh(inp)
    if annual_kwh >= 3000:
        score += 10
        factors.append(
            {
                "factor": "Electricity consumption",
                "impact": "positive",
                "detail": "Sufficient consumption to justify solar investment",
            }
        )
    else:
        score += 3
        factors.append(
            {
                "factor": "Electricity consumption",
                "impact": "neutral",
                "detail": "Lower consumption – smaller system may be more appropriate",
            }
        )

    if inp.budget_eur > 0:
        cost_est = system_kwp * COST_PER_KWP["residential"]["typical"]
        if inp.budget_eur >= cost_est:
            score += 10
            factors.append(
                {"factor": "Budget alignment", "impact": "positive", "detail": "Budget covers estimated system cost"}
            )
        elif inp.budget_eur >= cost_est * 0.7:
            score += 5
            factors.append(
                {
                    "factor": "Budget alignment",
                    "impact": "neutral",
                    "detail": "Budget covers most of the estimated cost – financing may help",
                }
            )
        else:
            score -= 5
            factors.append(
                {
                    "factor": "Budget alignment",
                    "impact": "negative",
                    "detail": "Budget below estimated cost – consider smaller system or financing",
                }
            )

    score = max(0, min(100, score))

    if score >= 80:
        rating = "Excellent"
    elif score >= 65:
        rating = "Good"
    elif score >= 45:
        rating = "Fair"
    else:
        rating = "Poor"

    return {"score": score, "rating": rating, "factors": factors}


def build_package(
    inp: CalculatorInput,
    package_id: str,
    system_kwp: float,
    annual_production: float,
    adjusted_yield: float,
    goals: list,
    annual_kwh: float,
) -> dict:
    """Build one of three system packages from the internal product catalog."""
    pkg_def = PACKAGE_DEFINITIONS[package_id]
    battery_kwh = _resolve_package_battery(package_id, inp, system_kwp, annual_kwh, goals)

    product_spec = build_package_spec(
        package_id,
        system_kwp,
        battery_kwh,
        goals,
        roof_type=inp.roof_type,
        roof_area_m2=inp.roof_area_m2,
    )
    actual_kwp = product_spec["system_kwp_actual"]
    actual_production = round(actual_kwp * adjusted_yield)
    upfront = product_spec["hardware_subtotal_eur"]
    actual_battery = product_spec["battery"]["capacity_kwh"] if product_spec.get("battery") else 0

    fin = calculate_financials_with_upfront(inp, upfront, actual_kwp, actual_production, actual_battery)
    fin_model = build_financial_model(
        upfront,
        fin["annual_savings"],
        fin["monthly_savings"],
        fin["feed_in_income_annual"],
        fin["self_consumption_savings_annual"],
        actual_battery,
        actual_kwp,
        actual_production,
    )

    gives_up = []
    if package_id == "cheapest":
        gives_up = [
            "No backup power during outages",
            "Lower self-consumption without battery",
            "Shorter component warranty",
        ]
    elif package_id == "best_value":
        gives_up = ["Not full backup resilience", "Smaller battery than resilience package"]
    else:
        gives_up = ["Highest upfront cost", "Longer payback period"]

    return {
        "id": package_id,
        "label": pkg_def["label"],
        "subtitle": pkg_def["subtitle"],
        "badge": pkg_def["badge"],
        "tier": product_spec["tier"],
        "system_kwp": actual_kwp,
        "battery_kwh": actual_battery,
        "inverter_type": pkg_def["inverter_type"],
        "backup_capable": pkg_def["backup_capable"] or battery_required_for_goal(goals),
        "warranty_years": pkg_def["warranty_years"],
        "upfront_cost": round(upfront),
        "upfront_cost_range": f"€{round(upfront * 0.95):,} – €{round(upfront * 1.05):,}",
        "monthly_savings": fin["monthly_savings"],
        "annual_savings": fin["annual_savings"],
        "export_income_annual": fin["feed_in_income_annual"],
        "self_consumption_savings": fin["self_consumption_savings_annual"],
        "self_consumption_ratio": fin["self_consumption_ratio"],
        "battery_contribution_pct": round(max(0, fin["self_consumption_ratio"] - 35)) if actual_battery > 0 else 0,
        "payback_years": fin["payback_years"],
        "savings_10yr": fin_model["projection_10yr"]["net_benefit"],
        "savings_20yr": fin_model["projection_20yr"]["net_benefit"],
        "co2_reduction_tonnes": fin["co2_reduction_tonnes"],
        "reliability_score": pkg_def["reliability_score"],
        "financial_model": fin_model,
        "tradeoffs": gives_up,
        "recommended": package_id == "best_value" and not battery_required_for_goal(goals),
        "product_spec": product_spec,
    }


def build_three_packages(inp, system_kwp, annual_production, adjusted_yield, goals, annual_kwh) -> dict:
    packages = {}
    for pid in ("cheapest", "best_value", "most_reliable"):
        packages[pid] = build_package(inp, pid, system_kwp, annual_production, adjusted_yield, goals, annual_kwh)

    if battery_required_for_goal(goals):
        packages["most_reliable"]["recommended"] = True
        packages["best_value"]["recommended"] = False
    else:
        packages["best_value"]["recommended"] = True
        packages["cheapest"]["recommended"] = False
        packages["most_reliable"]["recommended"] = False

    tradeoffs = get_tradeoffs(packages["cheapest"], packages["best_value"], packages["most_reliable"])
    return {"packages": packages, "tradeoffs": tradeoffs}


def generate_recommendation(inp: CalculatorInput, pvgis_data: Optional[dict] = None) -> dict:
    goals = inp.goals or ["lower_bill"]
    annual_kwh = estimate_annual_consumption_kwh(inp)

    specific_yield = 950
    monthly_production = []
    if pvgis_data:
        specific_yield = pvgis_data.get("specific_yield_kwh_kwp", 950)
        monthly_production = pvgis_data.get("monthly_production_kwh", [])

    roof_factor = ROOF_TYPE_FACTORS.get(inp.roof_type, 0.90)  # noqa: F841 — legacy reference only
    # PVGIS already models roof tilt/azimuth via roof_type_to_pvgis_params — only apply shading here
    adjusted_yield = apply_shading_factor(specific_yield, inp.shading)

    raw_kwp = annual_kwh / adjusted_yield if adjusted_yield > 0 else 0
    system_kwp = recommend_system_size_kwp(
        annual_kwh,
        adjusted_yield,
        goals,
        roof_area_m2=inp.roof_area_m2,
    )
    household_profile = build_household_energy_profile(inp, annual_kwh)
    annual_kwh_adj = household_profile["adjusted_annual_kwh"]
    inp._adjusted_annual_kwh = annual_kwh_adj  # noqa: SLF001

    budget_info = budget_first_recommendation(inp, adjusted_yield)
    if budget_info:
        system_kwp = min(system_kwp, budget_info["max_system_kwp"])

    pv_upgrade = apply_existing_pv_upgrade(inp, system_kwp)
    annual_production = round(system_kwp * adjusted_yield) if system_kwp > 0 else 0

    if monthly_production and system_kwp > 0:
        scale = system_kwp / 1.0  # PVGIS returns per 1 kWp
        shade = SHADING_YIELD_FACTORS.get(inp.shading, 0.97)
        monthly_production = [round(m * scale * shade) for m in monthly_production]

    battery_kwh = _resolve_package_battery("best_value", inp, system_kwp, annual_kwh, goals)
    tech = _primary_goal_tech(goals)
    goal_decisions = get_goal_decisions(goals)

    nominal_kwp = system_kwp
    if inp.roof_type == "balcony" or inp.housing_type in ("apartment_renter", "apartment_owner"):
        system_kwp = min(system_kwp, 0.8)  # DE balcony plug-in ~800 Wp typical
        nominal_kwp = system_kwp

    three_packages = build_three_packages(inp, system_kwp, annual_production, adjusted_yield, goals, annual_kwh)
    if pv_upgrade.get("has_existing_pv"):
        for pkg in three_packages["packages"].values():
            scaled = scale_upfront_for_pv_upgrade(pkg["upfront_cost"], pv_upgrade)
            if scaled == pkg["upfront_cost"]:
                continue
            fin_adj = calculate_financials_with_upfront(
                inp,
                scaled,
                pkg["system_kwp"],
                round(pkg["system_kwp"] * adjusted_yield),
                pkg["battery_kwh"],
            )
            pkg["upfront_cost"] = scaled
            pkg["upfront_cost_range"] = f"€{round(scaled * 0.95):,} – €{round(scaled * 1.05):,}"
            pkg["monthly_savings"] = fin_adj["monthly_savings"]
            pkg["annual_savings"] = fin_adj["annual_savings"]
            pkg["payback_years"] = fin_adj["payback_years"]
            pkg["financial_model"] = build_financial_model(
                scaled,
                fin_adj["annual_savings"],
                fin_adj["monthly_savings"],
                fin_adj["feed_in_income_annual"],
                fin_adj["self_consumption_savings_annual"],
                pkg["battery_kwh"],
                pkg["system_kwp"],
                round(pkg["system_kwp"] * adjusted_yield),
            )
            pkg["savings_10yr"] = pkg["financial_model"]["projection_10yr"]["net_benefit"]
            pkg["savings_20yr"] = pkg["financial_model"]["projection_20yr"]["net_benefit"]
    primary_pkg = next(
        (p for p in three_packages["packages"].values() if p.get("recommended")),
        three_packages["packages"]["best_value"],
    )
    primary_spec = primary_pkg["product_spec"]

    financials = calculate_financials_with_upfront(
        inp,
        primary_pkg["upfront_cost"],
        primary_pkg["system_kwp"],
        round(primary_pkg["system_kwp"] * adjusted_yield),
        primary_pkg["battery_kwh"],
    )
    components = components_from_spec(primary_spec)
    suitability = calculate_suitability_score(inp, adjusted_yield, primary_pkg["system_kwp"])
    confidence = calculate_confidence_score(inp, bool(pvgis_data), adjusted_yield)

    pkg_no_batt = three_packages["packages"]["cheapest"]
    fin_no_batt = calculate_financials_with_upfront(
        inp,
        pkg_no_batt["upfront_cost"],
        pkg_no_batt["system_kwp"],
        round(pkg_no_batt["system_kwp"] * adjusted_yield),
        0,
    )
    pkg_with_batt = three_packages["packages"]["best_value"]
    fin_with_batt = (
        calculate_financials_with_upfront(
            inp,
            pkg_with_batt["upfront_cost"],
            pkg_with_batt["system_kwp"],
            round(pkg_with_batt["system_kwp"] * adjusted_yield),
            pkg_with_batt["battery_kwh"],
        )
        if pkg_with_batt["battery_kwh"] > 0
        else None
    )

    system_kwp = primary_pkg["system_kwp"]
    annual_production = round(system_kwp * adjusted_yield)
    battery_kwh = primary_pkg["battery_kwh"]

    housing_info = HOUSING_PATHS.get(inp.housing_type, HOUSING_PATHS["detached"])
    solar_viable = housing_info.get("solar_viable", True)

    usage_breakdown = analyze_household_usage(annual_kwh, inp.has_ev, inp.has_heat_pump)
    meter_timeline = estimate_meter_timeline(
        inp.monthly_bill_eur, inp.monthly_kwh, inp.electricity_price_ct, financials["annual_savings"]
    )

    apartment_path = None
    if not solar_viable or inp.housing_type in ("apartment_renter", "apartment_owner"):
        apartment_path = get_apartment_recommendations(inp.housing_type, annual_kwh)
        solar_viable = False

    all_technologies = []
    for g in goals:
        if g in GOAL_TECHNOLOGY_MAP:
            all_technologies.append({"goal": g, **GOAL_TECHNOLOGY_MAP[g]})

    assumptions = [
        f"Location: {inp.location_name or f'{inp.latitude:.4f}, {inp.longitude:.4f}'}",
        f"Property type: {housing_info.get('label', inp.housing_type)}",
        f"Annual electricity consumption: {annual_kwh:,.0f} kWh",
        f"Electricity price: {inp.electricity_price_ct} ct/kWh (escalation 2–6%/year modelled)",
        f"Feed-in tariff ({inp.feed_in_type}): {get_feed_in_rate_ct(system_kwp, inp.feed_in_type)} ct/kWh",
        f"Specific yield: {adjusted_yield:.0f} kWh/kWp/year (PVGIS + shading adjustment)",
        "Component costs from internal product catalog (Phase 1 — no supplier APIs)",
        f"Battery replacement assumed at year {12} (65% of original cost)",
        f"Inverter replacement assumed at year {15} (35% of original cost)",
        "Maintenance allowance: 0.8%/year of system cost",
        f"CO₂ factor: {CO2_KG_PER_KWH} kg/kWh (German grid mix)",
        "Production estimates from PVGIS via backend API (not browser-direct)",
        PVGIS_LIMITATION,
        DISCLAIMER,
    ]

    why_recommend = _build_why_recommend(goals, system_kwp, battery_kwh, tech, financials, goal_decisions)
    why_explanation = build_why_explanation(inp, system_kwp, battery_kwh, annual_kwh_adj, annual_production, goals)
    readiness = calculate_readiness_score(inp, solar_viable, adjusted_yield, system_kwp, annual_kwh_adj, financials)
    lead_tier = calculate_lead_qualification_tier(inp)
    price_scenarios = build_price_scenarios(
        financials["annual_savings"], financials["system_cost_typical"], financials["payback_years"]
    )
    financing_comparison = build_financing_comparison(
        financials["system_cost_typical"], financials["monthly_savings"], financials["annual_savings"]
    )
    energy_roadmap = build_energy_roadmap(inp, system_kwp, goals)
    sizing_summary = build_sizing_summary(
        annual_kwh,
        adjusted_yield,
        nominal_kwp,
        annual_production,
        bool(pvgis_data),
        raw_kwp=raw_kwp,
        roof_area_m2=inp.roof_area_m2,
    )
    why_limitations = _build_why_limitations(inp, goals, system_kwp, annual_production, annual_kwh_adj, sizing_summary)

    result = {
        "goals": goals,
        "goal_decisions": goal_decisions,
        "technologies": all_technologies,
        "primary_technology": tech,
        "system_kwp": system_kwp,
        "battery_kwh": primary_pkg["battery_kwh"],
        "annual_production_kwh": annual_production,
        "monthly_production_kwh": monthly_production,
        "specific_yield_kwh_kwp": round(adjusted_yield),
        "financials": financials,
        "financial_model": primary_pkg["financial_model"],
        "three_packages": three_packages,
        "selected_package": primary_pkg,
        "components": components,
        "suitability": suitability,
        "confidence": confidence,
        "assumptions": assumptions,
        "why_recommend": why_recommend,
        "why_explanation": why_explanation,
        "why_limitations": why_limitations,
        "readiness": readiness,
        "household_profile": household_profile,
        "lead_qualification": lead_tier,
        "price_scenarios": price_scenarios,
        "budget_first": budget_info,
        "financing_comparison": financing_comparison,
        "energy_roadmap": energy_roadmap,
        "quote_quality_checklist": QUOTE_QUALITY_CHECKLIST,
        "estimated_accuracy": confidence["estimated_accuracy"],
        "solar_viable": solar_viable,
        "housing_type": inp.housing_type,
        "usage_breakdown": usage_breakdown,
        "meter_timeline": meter_timeline,
        "apartment_path": apartment_path,
        "battery_comparison": {
            "without_battery": fin_no_batt,
            "with_battery": fin_with_batt,
            "note": "For 'lower bill' goals, battery is optional – see three packages above.",
        }
        if fin_with_batt
        else None,
        "energy_economics": build_energy_economics(financials, inp),
        "sizing_summary": sizing_summary,
        "system_recommendation": {
            "headline_kwp": primary_spec["system_kwp_actual"],
            "num_panels": primary_spec["num_panels"],
            "panel_label": f"{primary_spec['panel']['brand']} {primary_spec['panel']['model']}",
            "inverter_label": f"{primary_spec['inverter']['brand']} {primary_spec['inverter']['model']}",
            "battery_kwh": primary_spec["battery"]["capacity_kwh"] if primary_spec.get("battery") else 0,
            "battery_label": (
                f"{primary_spec['battery']['brand']} {primary_spec['battery']['model']}"
                if primary_spec.get("battery")
                else None
            ),
            "estimated_cost_eur": primary_pkg["upfront_cost"],
            "annual_savings_eur": primary_pkg["annual_savings"],
            "annual_production_kwh": annual_production,
            "summary_line": primary_spec["summary_line"],
            "product_spec": primary_spec,
            "package_id": primary_pkg["id"],
            "package_label": primary_pkg["label"],
        },
        "legal_checklist": _project_tracker(),
        "project_path": _project_path_timeline(),
        "calculator_inputs": calculator_inputs_snapshot(inp),
        "pv_upgrade": pv_upgrade,
        "disclaimer": DISCLAIMER,
    }
    if "ev_charging" in goals:
        result["ev_assessment"] = build_ev_assessment(inp, inp.electricity_price_ct)
    if heat_goals_active(goals):
        result["hp_assessment"] = build_hp_assessment(inp, inp.electricity_price_ct)
    result["quote_ready_profile"] = build_quote_ready_profile(inp, result)
    result["decision_report"] = build_decision_report(inp, result)
    return result


def apply_existing_pv_upgrade(inp: CalculatorInput, target_kwp: float) -> dict:
    """Adjust sizing/cost context when customer already has PV."""
    existing = float(getattr(inp, "existing_pv_kwp", 0) or 0)
    if not getattr(inp, "has_existing_pv", False) or existing <= 0:
        return {
            "has_existing_pv": False,
            "existing_pv_kwp": 0,
            "target_kwp": target_kwp,
            "expansion_kwp": target_kwp,
            "mode": "new_install",
            "cost_factor": 1.0,
            "summary": "",
        }
    expansion = round(max(0.0, target_kwp - existing), 1)
    situation = getattr(inp, "user_situation", "") or ""
    if situation == "pv_battery" and expansion < 1.0:
        mode = "battery_only"
        cost_factor = 0.35
        summary = f"Existing ~{existing:g} kWp — focus on battery and smart energy integration."
    elif expansion < 0.5:
        mode = "optimize"
        cost_factor = 0.25
        summary = f"Existing ~{existing:g} kWp already meets target — monitoring and tariff optimization may be enough."
    else:
        mode = "expand"
        cost_factor = max(0.3, min(1.0, expansion / target_kwp if target_kwp else 0.5))
        summary = f"Expand by ~{expansion:g} kWp from existing {existing:g} kWp to reach ~{target_kwp:g} kWp."
    inv = float(getattr(inp, "existing_inverter_kwp", 0) or 0)
    if inv > 0 and inv < target_kwp * 0.7:
        summary += " Inverter upgrade may be required — verify AC capacity with installer."
    return {
        "has_existing_pv": True,
        "existing_pv_kwp": existing,
        "existing_pv_year": int(getattr(inp, "existing_pv_year", 0) or 0),
        "target_kwp": target_kwp,
        "expansion_kwp": expansion,
        "mode": mode,
        "cost_factor": round(cost_factor, 2),
        "summary": summary,
    }


def scale_upfront_for_pv_upgrade(upfront: float, upgrade: dict) -> int:
    if not upgrade.get("has_existing_pv"):
        return int(round(upfront))
    return int(round(upfront * float(upgrade.get("cost_factor") or 1.0)))


def inp_from_recalc_payload(base: dict, location: dict, overrides: dict) -> CalculatorInput:
    merged = {**base, **{k: v for k, v in overrides.items() if v is not None}}
    monthly_kwh = float(merged.get("monthly_kwh") or 0)
    if overrides.get("annual_kwh"):
        monthly_kwh = float(overrides["annual_kwh"]) / 12
    return CalculatorInput(
        latitude=float(location.get("latitude") or 48.13),
        longitude=float(location.get("longitude") or 11.58),
        location_name=merged.get("location_name") or merged.get("postcode") or "",
        postcode=merged.get("postcode") or "",
        monthly_bill_eur=float(merged.get("monthly_bill_eur") or 0),
        monthly_kwh=monthly_kwh,
        roof_type=merged.get("roof_type") or "pitched_south",
        roof_area_m2=float(merged.get("roof_area_m2") or overrides.get("roof_area_m2") or 0),
        budget_eur=float(merged.get("budget_eur") or overrides.get("budget_eur") or 0),
        goals=merged.get("goals") or ["lower_bill"],
        electricity_price_ct=float(merged.get("electricity_price_ct") or overrides.get("electricity_price_ct") or 32),
        feed_in_type=merged.get("feed_in_type") or "partial",
        housing_type=merged.get("housing_type") or "detached",
        owner_status=merged.get("owner_status") or "owner",
        shading=merged.get("shading") or "unknown",
        has_heat_pump=bool(merged.get("has_heat_pump")),
        has_ev=bool(merged.get("has_ev")),
        planned_ev=bool(merged.get("planned_ev")),
        has_roof_photos=bool(merged.get("has_roof_photos")),
        installation_timeframe=merged.get("installation_timeframe") or "not_sure",
        battery_interest=merged.get("battery_interest") or "unsure",
        ev_annual_km=float(merged.get("ev_annual_km") or overrides.get("ev_annual_km") or 0),
        ev_consumption_kwh_100km=float(merged.get("ev_consumption_kwh_100km") or 18),
        ev_home_charging=merged.get("ev_home_charging") or "",
        ev_park_home_daytime=merged.get("ev_park_home_daytime") or "",
        ev_has_wallbox=merged.get("ev_has_wallbox") or "",
        ev_charging_priority=merged.get("ev_charging_priority") or "",
        user_situation=merged.get("user_situation") or "",
        has_existing_pv=bool(merged.get("has_existing_pv")),
        existing_pv_kwp=float(merged.get("existing_pv_kwp") or 0),
        existing_inverter_kwp=float(merged.get("existing_inverter_kwp") or 0),
        existing_pv_year=int(merged.get("existing_pv_year") or 0),
    )


def recalculate_assumptions(
    base_inputs: dict,
    location: dict,
    pvgis_data: dict | None,
    overrides: dict,
    package_id: str = "best_value",
) -> dict:
    """Re-run financials after slider changes using cached PVGIS data."""
    inp = inp_from_recalc_payload(base_inputs, location, overrides)
    if overrides.get("battery_kwh") is not None:
        inp._battery_override = float(overrides["battery_kwh"])  # noqa: SLF001

    goals = inp.goals or ["lower_bill"]
    annual_kwh = estimate_annual_consumption_kwh(inp)
    specific_yield = (pvgis_data or {}).get("specific_yield_kwh_kwp", 950)
    adjusted_yield = apply_shading_factor(specific_yield, inp.shading)
    system_kwp = recommend_system_size_kwp(annual_kwh, adjusted_yield, goals, roof_area_m2=inp.roof_area_m2)
    upgrade = apply_existing_pv_upgrade(inp, system_kwp)
    system_kwp = upgrade["target_kwp"]
    annual_production = round(system_kwp * adjusted_yield)

    pkg = build_package(inp, package_id, system_kwp, annual_production, adjusted_yield, goals, annual_kwh)
    batt_override = getattr(inp, "_battery_override", None)
    if batt_override is not None:
        pkg["battery_kwh"] = batt_override
        pkg["upfront_cost"] = scale_upfront_for_pv_upgrade(pkg["upfront_cost"], upgrade)
        fin = calculate_financials_with_upfront(
            inp,
            pkg["upfront_cost"],
            pkg["system_kwp"],
            round(pkg["system_kwp"] * adjusted_yield),
            batt_override,
        )
        pkg["annual_savings"] = fin["annual_savings"]
        pkg["payback_years"] = fin["payback_years"]
    else:
        pkg["upfront_cost"] = scale_upfront_for_pv_upgrade(pkg["upfront_cost"], upgrade)

    loan_years = int(overrides.get("loan_years") or 10)
    from financial_model import build_financial_model, calculate_financing

    fin_model = build_financial_model(
        pkg["upfront_cost"],
        pkg.get("annual_savings") or 0,
        pkg.get("monthly_savings") or 0,
        0,
        0,
        pkg.get("battery_kwh") or 0,
        pkg["system_kwp"],
        annual_production,
    )
    monthly_savings = pkg.get("monthly_savings") or (pkg.get("annual_savings") or 0) / 12
    fin_loan = calculate_financing(pkg["upfront_cost"], term_years=loan_years)
    loan_cmp = {
        **fin_loan,
        "monthly_savings_offset": round(monthly_savings, 2),
        "net_monthly_cash": round(monthly_savings - fin_loan["monthly_payment"], 2),
    }

    return {
        "system_kwp": pkg["system_kwp"],
        "annual_savings": pkg.get("annual_savings"),
        "payback_years": pkg.get("payback_years"),
        "upfront_cost": pkg["upfront_cost"],
        "battery_kwh": pkg.get("battery_kwh"),
        "pv_upgrade": upgrade,
        "financials": {
            "annual_savings": pkg.get("annual_savings"),
            "payback_years": pkg.get("payback_years"),
            "system_cost_typical": pkg["upfront_cost"],
            "monthly_savings": pkg.get("monthly_savings"),
        },
        "financing_comparison": {"loan": loan_cmp},
        "financial_model": fin_model,
    }


def _build_why_limitations(inp, goals, system_kwp, annual_production, annual_kwh, sizing_summary) -> list:
    notes = []
    if "ev_charging" in goals and annual_production < annual_kwh * 1.1:
        notes.append(
            "This system may not fully cover all EV charging in winter without grid top-up or a larger battery."
        )
    if sizing_summary and sizing_summary.get("capped_by_roof"):
        notes.append("Roof area limits system size — an on-site survey may find more or less usable area.")
    if inp.shading in ("partial", "heavy", "significant"):
        notes.append("Shading can reduce real-world yield below this estimate until a site survey confirms production.")
    if not inp.has_roof_photos:
        notes.append(
            "No roof photos yet — production and layout assumptions are based on your stated roof type and area."
        )
    if getattr(inp, "has_existing_pv", False):
        up = apply_existing_pv_upgrade(inp, system_kwp)
        notes.append(
            up.get("summary")
            or "Existing PV capacity and inverter limits are not verified — expansion may need hardware upgrades."
        )
    if not notes:
        notes.append(
            "Installer quotes, grid connection rules, and structural checks are not included in this digital estimate."
        )
    return notes[:4]


def _project_path_timeline() -> list:
    return [
        {"step": 1, "title_key": "path.step1_title", "detail_key": "path.step1_detail"},
        {"step": 2, "title_key": "path.step2_title", "detail_key": "path.step2_detail"},
        {"step": 3, "title_key": "path.step3_title", "detail_key": "path.step3_detail"},
        {"step": 4, "title_key": "path.step4_title", "detail_key": "path.step4_detail"},
        {"step": 5, "title_key": "path.step5_title", "detail_key": "path.step5_detail"},
        {"step": 6, "title_key": "path.step6_title", "detail_key": "path.step6_detail"},
        {"step": 7, "title_key": "path.step7_title", "detail_key": "path.step7_detail"},
    ]


def _project_tracker() -> list:
    return [
        {"step": 1, "title_key": "legal.step1_title", "detail_key": "legal.step1_detail", "status": "pending"},
        {"step": 2, "title_key": "legal.step2_title", "detail_key": "legal.step2_detail", "status": "pending"},
        {"step": 3, "title_key": "legal.step3_title", "detail_key": "legal.step3_detail", "status": "pending"},
        {"step": 4, "title_key": "legal.step4_title", "detail_key": "legal.step4_detail", "status": "pending"},
        {"step": 5, "title_key": "legal.step5_title", "detail_key": "legal.step5_detail", "status": "pending"},
        {
            "step": 6,
            "title_key": "legal.step6_title",
            "detail_key": "legal.step6_detail",
            "status": "pending",
            "deadline_key": "legal.step6_deadline",
        },
        {"step": 7, "title_key": "legal.step7_title", "detail_key": "legal.step7_detail", "status": "pending"},
        {
            "step": 8,
            "title_key": "legal.step8_title",
            "detail_key": "legal.step8_detail",
            "status": "pending",
            "warning_key": "legal.step8_warning",
        },
        {"step": 9, "title_key": "legal.step9_title", "detail_key": "legal.step9_detail", "status": "pending"},
        {"step": 10, "title_key": "legal.step10_title", "detail_key": "legal.step10_detail", "status": "pending"},
    ]


def _build_why_recommend(goals, system_kwp, battery_kwh, tech, financials, goal_decisions=None) -> list:
    reasons = []
    if goal_decisions:
        for gd in goal_decisions:
            reasons.append(f"**{gd['goal_label']}** → {gd['primary']}")
    else:
        reasons.append(f"Based on your goal(s), we recommend {tech['primary']} as the primary technology.")

    if "lower_bill" in goals and "backup" not in goals:
        reasons.append(
            "A battery is NOT automatically recommended for bill savings – compare the three packages below."
        )
    elif battery_required_for_goal(goals):
        reasons.append("Battery and backup circuitry are essential for your backup power goal.")

    reasons.append(f"A {system_kwp} kWp system targets your annual usage and daytime consumption pattern.")
    if financials["payback_years"] < 14:
        reasons.append(f"Estimated payback of {financials['payback_years']} years – within typical German range.")
    reasons.append(f"Annual CO₂ reduction of {financials['co2_reduction_tonnes']} tonnes.")
    return reasons
