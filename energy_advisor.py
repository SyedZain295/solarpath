"""Energy advisor for non-solar users, household usage breakdown, and meter estimates."""

HOUSING_PATHS = {
    "detached": {"solar_viable": True, "label": "Detached house"},
    "semi_detached": {"solar_viable": True, "label": "Semi-detached house"},
    "terraced": {"solar_viable": True, "label": "Terraced house"},
    "apartment_renter": {"solar_viable": False, "label": "Apartment (renter)"},
    "apartment_owner": {"solar_viable": False, "label": "Apartment (owner)"},
    "landlord": {"solar_viable": True, "label": "Landlord / multi-unit building"},
    "housing_association": {"solar_viable": True, "label": "Housing association (WEG)"},
}

APARTMENT_OPTIONS = [
    {
        "name": "Balcony solar (Balkonkraftwerk)",
        "description": "Plug-in micro-PV (up to 800 W) for balcony or terrace. Lower savings but no landlord permission needed in many cases.",
        "typical_cost_eur": 600,
        "annual_savings_eur": 150,
        "suitable_for": ["apartment_renter", "apartment_owner"],
    },
    {
        "name": "Portable solar panel + battery",
        "description": "Flexible panels for sunny windowsills or balconies. Charge devices and small appliances.",
        "typical_cost_eur": 400,
        "annual_savings_eur": 80,
        "suitable_for": ["apartment_renter", "apartment_owner"],
    },
    {
        "name": "Energy efficiency audit",
        "description": "Identify which rooms and appliances use the most electricity – often the fastest way to cut bills.",
        "typical_cost_eur": 0,
        "annual_savings_eur": 200,
        "suitable_for": ["apartment_renter", "apartment_owner", "detached"],
    },
    {
        "name": "Dynamic tariff + smart plug scheduling",
        "description": "Shift washing, dishwasher, and heating to cheaper hours using a dynamic electricity tariff.",
        "typical_cost_eur": 50,
        "annual_savings_eur": 120,
        "suitable_for": ["apartment_renter", "apartment_owner"],
    },
    {
        "name": "Landlord rooftop PV (Mieterstrom)",
        "description": "Landlord installs rooftop PV and sells electricity directly to tenants at below-grid rates.",
        "typical_cost_eur": 0,
        "annual_savings_eur": 300,
        "suitable_for": ["apartment_renter", "landlord"],
    },
]

# Typical household electricity breakdown (% of total) – German averages
USAGE_BREAKDOWN = {
    "heating_hot_water": {"pct": 35, "label": "Heating & hot water", "icon": "🔥", "tips": [
        "Lower thermostat by 1°C – saves ~6%",
        "Insulate pipes and use timer on water heater",
        "Shorter showers save hot water energy",
    ]},
    "kitchen": {"pct": 18, "label": "Kitchen (cooking, fridge, dishwasher)", "icon": "🍳", "tips": [
        "Use lid on pots – cooks faster, uses less energy",
        "Defrost fridge regularly",
        "Run dishwasher only when full",
    ]},
    "lighting": {"pct": 8, "label": "Lighting", "icon": "💡", "tips": [
        "Switch to LED bulbs – 80% less energy",
        "Turn off lights in unused rooms",
    ]},
    "electronics": {"pct": 12, "label": "Electronics & standby", "icon": "📺", "tips": [
        "Unplug devices on standby – can save €50–100/year",
        "Use power strips with switches",
    ]},
    "laundry": {"pct": 8, "label": "Washing & drying", "icon": "👕", "tips": [
        "Wash at 30°C instead of 60°C",
        "Air-dry instead of tumble dryer when possible",
    ]},
    "cooling": {"pct": 5, "label": "Cooling & ventilation", "icon": "❄️", "tips": [
        "Close blinds during hot days",
        "Use fans instead of AC where possible",
    ]},
    "ev_mobility": {"pct": 10, "label": "EV charging & mobility", "icon": "⚡", "tips": [
        "Charge during off-peak hours",
        "Consider solar-compatible charger if you move to a house",
    ]},
    "other": {"pct": 4, "label": "Other", "icon": "📦", "tips": ["Review all appliances for energy rating"]},
}


def analyze_household_usage(annual_kwh: float, has_ev: bool = False, has_heat_pump: bool = False) -> list:
    """Break down electricity by area of home with savings tips."""
    breakdown = []
    for key, info in USAGE_BREAKDOWN.items():
        pct = info["pct"]
        if key == "ev_mobility" and not has_ev:
            pct = 2
        if key == "heating_hot_water" and has_heat_pump:
            pct = 45
        kwh = annual_kwh * pct / 100
        cost_eur = kwh * 0.32
        breakdown.append({
            "area": key,
            "label": info["label"],
            "icon": info["icon"],
            "pct": pct,
            "annual_kwh": round(kwh),
            "annual_cost_eur": round(cost_eur, 2),
            "tips": info["tips"],
        })
    breakdown.sort(key=lambda x: x["annual_cost_eur"], reverse=True)
    return breakdown


def estimate_meter_timeline(monthly_bill: float, monthly_kwh: float, electricity_price_ct: float, annual_savings_with_solar: float = 0) -> dict:
    """Past, current, and projected future electricity costs."""
    price = electricity_price_ct / 100
    if monthly_kwh > 0:
        monthly_cost = monthly_kwh * price
    elif monthly_bill > 0:
        monthly_cost = monthly_bill
    else:
        monthly_cost = 120
        monthly_kwh = monthly_cost / price

    annual_cost = monthly_cost * 12
    escalation = 0.04

    past = [{"year": f"Year -{i}", "annual_cost": round(annual_cost / ((1 + escalation) ** i)), "note": "Estimated from current usage"} for i in range(3, 0, -1)]
    current = {"year": "Current year", "annual_cost": round(annual_cost), "monthly_cost": round(monthly_cost, 2), "monthly_kwh": round(monthly_kwh)}

    future_without = []
    future_with = []
    for i in range(1, 11):
        cost_no_solar = annual_cost * ((1 + escalation) ** i)
        cost_with_solar = max(0, cost_no_solar - annual_savings_with_solar * ((1 + escalation) ** (i - 1)))
        future_without.append({"year": f"Year +{i}", "annual_cost": round(cost_no_solar)})
        future_with.append({"year": f"Year +{i}", "annual_cost": round(cost_with_solar), "savings": round(cost_no_solar - cost_with_solar)})

    return {
        "past": past,
        "current": current,
        "future_without_solar": future_without,
        "future_with_solar": future_with,
        "ten_year_cost_without": sum(f["annual_cost"] for f in future_without),
        "ten_year_cost_with": sum(f["annual_cost"] for f in future_with),
        "ten_year_savings": sum(f["savings"] for f in future_with),
        "note": "Connect your smart meter for actual half-hourly data. These projections use 4%/year electricity price escalation.",
    }


def get_apartment_recommendations(housing_type: str, annual_kwh: float) -> list:
    """Options for renters/apartment dwellers who cannot install rooftop solar."""
    options = []
    for opt in APARTMENT_OPTIONS:
        if housing_type in opt["suitable_for"]:
            options.append(opt)
    usage = analyze_household_usage(annual_kwh)
    top_drain = usage[0] if usage else None
    return {
        "options": options,
        "top_cost_area": top_drain,
        "message": "You don't need rooftop solar to save money. Focus on your highest-cost areas first.",
    }


def build_quote_ready_profile(inp, recommendation: dict) -> dict:
    """Structured project pack for installers."""
    return {
        "location": {
            "address_or_postcode": inp.location_name,
            "latitude": inp.latitude,
            "longitude": inp.longitude,
        },
        "property": {
            "type": getattr(inp, "housing_type", "detached"),
            "owner_status": getattr(inp, "owner_status", "owner"),
            "roof_type": inp.roof_type,
            "roof_area_m2": inp.roof_area_m2,
            "shading": getattr(inp, "shading", "unknown"),
        },
        "consumption": {
            "annual_kwh": recommendation.get("financials", {}).get("annual_consumption_kwh"),
            "monthly_bill_eur": inp.monthly_bill_eur,
            "electricity_price_ct": inp.electricity_price_ct,
        },
        "existing_equipment": {
            "heat_pump": getattr(inp, "has_heat_pump", False),
            "ev": getattr(inp, "has_ev", False),
            "electric_water_heater": getattr(inp, "has_electric_water_heater", False),
            "pool": getattr(inp, "has_pool", False),
        },
        "project": {
            "goals": inp.goals,
            "backup_priority": "backup" in (inp.goals or []),
            "timeframe": getattr(inp, "installation_timeframe", "not_sure"),
            "budget_eur": inp.budget_eur,
            "selected_package": getattr(inp, "selected_package", None),
        },
        "recommendation_summary": {
            "primary_technology": recommendation.get("primary_technology", {}).get("primary"),
            "system_kwp": recommendation.get("system_kwp"),
            "battery_kwh": recommendation.get("battery_kwh"),
            "estimated_cost": recommendation.get("financials", {}).get("system_cost_typical"),
            "confidence": recommendation.get("confidence", {}).get("level"),
        },
        "documents_needed": [
            "Roof photos (all sides)",
            "Electricity bill (last 12 months)",
            "Meter number (Zählernummer)",
            "Property ownership proof (if owner)",
        ],
        "consent_required": True,
    }
