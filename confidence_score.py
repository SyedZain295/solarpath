"""Information completeness / digital suitability scoring — not an installation guarantee."""

PVGIS_LIMITATION = (
    "PVGIS terrain-based horizon modelling does not account for nearby trees, chimneys, "
    "or neighbouring buildings. A site survey is needed for final accuracy."
)

SURVEY_DISCLAIMER = (
    "Final feasibility, roof condition, wiring, static load, meter capacity, grid connection "
    "and local requirements must be checked by an installer on site. This score reflects how "
    "complete your online inputs are — not whether installation is guaranteed."
)

# Without roof photos we cap well below 100; with photos still below a perfect score.
_SCORE_CAP_NO_PHOTOS = 78
_SCORE_CAP_WITH_PHOTOS = 88


def calculate_confidence_score(inp, pvgis_available: bool, specific_yield: float) -> dict:
    score = 30
    factors = []
    missing = []

    if inp.location_name:
        score += 10
        factors.append({"item": "Postcode/location", "status": "provided", "points": 10})
    else:
        missing.append("Full address or postcode")

    if inp.monthly_kwh > 0 or inp.monthly_bill_eur > 0:
        score += 15
        factors.append({"item": "Electricity consumption", "status": "provided", "points": 15})
    else:
        missing.append("Electricity bill or kWh data")

    if inp.roof_area_m2 > 0:
        score += 10
        factors.append({"item": "Roof area", "status": "provided", "points": 10})
    else:
        missing.append("Roof dimensions")

    roof = inp.roof_type
    if roof and roof != "unknown":
        score += 8
        factors.append({"item": "Roof orientation", "status": "provided", "points": 8})
    else:
        missing.append("Roof orientation")

    shading = getattr(inp, "shading", "unknown")
    if shading and shading != "unknown":
        score += 10
        factors.append({"item": "Shading assessment", "status": "provided", "points": 10})
    else:
        missing.append("Shading assessment")

    if pvgis_available:
        score += 12
        factors.append({"item": "PVGIS solar resource data", "status": "provided", "points": 12})

    has_photos = getattr(inp, "has_roof_photos", False)
    if has_photos:
        score += 10
        factors.append({"item": "Roof photos", "status": "provided", "points": 10})
    else:
        missing.append("Roof photos")

    housing = getattr(inp, "housing_type", "")
    if housing:
        score += 5
        factors.append({"item": "Property type", "status": "provided", "points": 5})

    cap = _SCORE_CAP_WITH_PHOTOS if has_photos else _SCORE_CAP_NO_PHOTOS
    score = max(0, min(cap, score))

    if score >= 70:
        level, label = "high", "High"
    elif score >= 45:
        level, label = "medium", "Medium"
    else:
        level, label = "low", "Low"

    summary_parts = []
    if inp.location_name:
        summary_parts.append("your postcode and electricity use")
    if not inp.roof_area_m2:
        summary_parts.append("no roof dimensions")
    if shading == "unknown":
        summary_parts.append("no shading assessment yet")
    if not has_photos:
        summary_parts.append("no roof photos yet")

    if summary_parts:
        summary = (
            f"We have {summary_parts[0]}"
            + (f", but {', '.join(summary_parts[1:])}" if len(summary_parts) > 1 else "")
            + "."
        )
    else:
        summary = "Strong online data coverage — an on-site survey is still required before installation."

    return {
        "score": score,
        "level": level,
        "label": label,
        "score_label": "Information completeness index",
        "factors": factors,
        "missing_data": missing,
        "summary": summary,
        "pvgis_limitation": PVGIS_LIMITATION,
        "survey_disclaimer": SURVEY_DISCLAIMER,
        "estimated_accuracy": f"±{20 if level == 'low' else 15 if level == 'medium' else 10}%",
    }
