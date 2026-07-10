"""Detailed financial model with scenarios, financing, and lifecycle costs."""

ELECTRICITY_ESCALATION = {"low": 0.02, "expected": 0.04, "high": 0.06}
PRODUCTION_SCENARIO = {"low": 0.88, "expected": 1.0, "high": 1.08}
FINANCING_RATE_APR = 0.049
FINANCING_TERM_YEARS = 10
BATTERY_REPLACEMENT_YEAR = 12
BATTERY_REPLACEMENT_COST_RATIO = 0.65
INVERTER_REPLACEMENT_YEAR = 15
INVERTER_REPLACEMENT_COST_RATIO = 0.35
MAINTENANCE_ANNUAL_PCT = 0.008

DISCLAIMER = (
    "This is an estimate, not a guaranteed return. Your final result depends on roof conditions, "
    "shading, electricity usage, installed equipment, grid approval, and final installer quote."
)


def calculate_financing(
    upfront_cost: float, term_years: int = FINANCING_TERM_YEARS, apr: float = FINANCING_RATE_APR
) -> dict:
    if upfront_cost <= 0:
        return {"monthly_payment": 0, "total_paid": 0, "total_interest": 0}
    monthly_rate = apr / 12
    n = term_years * 12
    if monthly_rate == 0:
        monthly = upfront_cost / n
    else:
        monthly = upfront_cost * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
    total_paid = monthly * n
    return {
        "monthly_payment": round(monthly, 2),
        "total_paid": round(total_paid),
        "total_interest": round(total_paid - upfront_cost),
        "term_years": term_years,
        "apr_pct": round(apr * 100, 1),
    }


def project_savings_over_years(
    annual_savings_year1: float,
    upfront_cost: float,
    years: int,
    escalation: float = 0.04,
    battery_kwh: float = 0,
    system_kwp: float = 0,
    inverter_cost: float = 0,
) -> dict:
    cumulative = -upfront_cost
    yearly = []
    for yr in range(1, years + 1):
        savings = annual_savings_year1 * ((1 + escalation) ** (yr - 1))
        maintenance = upfront_cost * MAINTENANCE_ANNUAL_PCT
        extra_cost = 0
        if battery_kwh > 0 and yr == BATTERY_REPLACEMENT_YEAR:
            extra_cost += battery_kwh * 550 * BATTERY_REPLACEMENT_COST_RATIO
        if yr == INVERTER_REPLACEMENT_YEAR:
            inv_cost = inverter_cost or (system_kwp * 200 + 800)
            extra_cost += inv_cost * INVERTER_REPLACEMENT_COST_RATIO
        net = savings - maintenance - extra_cost
        cumulative += net
        yearly.append(
            {
                "year": yr,
                "savings": round(savings, 2),
                "maintenance": round(maintenance, 2),
                "replacement_cost": round(extra_cost, 2),
                "net": round(net, 2),
                "cumulative": round(cumulative, 2),
            }
        )
    return {"yearly": yearly, "net_benefit": round(cumulative, 2)}


def build_financial_model(
    upfront_cost: float,
    annual_savings: float,
    monthly_savings: float,
    feed_in_income: float,
    self_consumption_savings: float,
    battery_kwh: float,
    system_kwp: float,
    annual_production: float,
) -> dict:
    financing = calculate_financing(upfront_cost)
    proj_10 = project_savings_over_years(
        annual_savings, upfront_cost, 10, battery_kwh=battery_kwh, system_kwp=system_kwp
    )
    proj_20 = project_savings_over_years(
        annual_savings, upfront_cost, 20, battery_kwh=battery_kwh, system_kwp=system_kwp
    )

    scenarios = {}
    for prod_label, prod_factor in PRODUCTION_SCENARIO.items():
        for price_label, price_esc in ELECTRICITY_ESCALATION.items():
            key = f"{prod_label}_prod_{price_label}_price"
            adj_savings = annual_savings * prod_factor * (1 + (price_esc - 0.04))
            scenarios[key] = {
                "production": prod_label,
                "electricity_price": price_label,
                "annual_savings_yr1": round(adj_savings, 2),
                "payback_years": round(upfront_cost / adj_savings, 1) if adj_savings > 0 else 99,
                "net_10yr": project_savings_over_years(
                    adj_savings, upfront_cost, 10, escalation=price_esc, battery_kwh=battery_kwh, system_kwp=system_kwp
                )["net_benefit"],
                "net_20yr": project_savings_over_years(
                    adj_savings, upfront_cost, 20, escalation=price_esc, battery_kwh=battery_kwh, system_kwp=system_kwp
                )["net_benefit"],
            }

    return {
        "upfront_cost": round(upfront_cost),
        "financing": financing,
        "annual_savings": round(annual_savings, 2),
        "monthly_savings": round(monthly_savings, 2),
        "feed_in_income_annual": round(feed_in_income, 2),
        "self_consumption_savings_annual": round(self_consumption_savings, 2),
        "maintenance_annual": round(upfront_cost * MAINTENANCE_ANNUAL_PCT, 2),
        "battery_replacement": {
            "year": BATTERY_REPLACEMENT_YEAR,
            "estimated_cost": round(battery_kwh * 550 * BATTERY_REPLACEMENT_COST_RATIO) if battery_kwh > 0 else 0,
        },
        "inverter_replacement": {
            "year": INVERTER_REPLACEMENT_YEAR,
            "estimated_cost": round((system_kwp * 200 + 800) * INVERTER_REPLACEMENT_COST_RATIO),
        },
        "electricity_escalation_assumptions": {k: f"{v * 100:.0f}%/year" for k, v in ELECTRICITY_ESCALATION.items()},
        "production_scenarios": {k: f"{v * 100:.0f}%" for k, v in PRODUCTION_SCENARIO.items()},
        "projection_10yr": proj_10,
        "projection_20yr": proj_20,
        "scenarios": scenarios,
        "disclaimer": DISCLAIMER,
    }
