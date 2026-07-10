from unittest.mock import patch

MOCK_PVGIS = {
    "specific_yield_kwh_kwp": 950,
    "annual_kwh_per_kwp": 950,
    "monthly": [],
}


@patch("app.get_pv_estimate", return_value=MOCK_PVGIS)
@patch("app.get_gsa_yield_estimate", return_value=None)
@patch("pvgis_client._nominatim_search", return_value=None)
@patch("pvgis_client._open_meteo_search", return_value=None)
@patch("pvgis_client._plz_lookup_city", return_value=None)
def test_api_calculate_with_postcode_only(_city, _meteo, _nom, _gsa, _pvgis, client):
    r = client.post(
        "/api/calculate",
        json={
            "postcode": "80331",
            "monthly_kwh": 350,
            "roof_area_m2": 40,
            "goals": ["lower_bill"],
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "system_kwp" in data or "recommendation" in data or "packages" in data


@patch("app.get_pv_estimate", return_value=MOCK_PVGIS)
@patch("app.get_gsa_yield_estimate", return_value=None)
def test_api_calculate_with_coords(_gsa, _pvgis, client):
    r = client.post(
        "/api/calculate",
        json={
            "latitude": 48.1351,
            "longitude": 11.582,
            "location_name": "München",
            "postcode": "80331",
            "monthly_kwh": 350,
            "roof_area_m2": 40,
            "goals": ["lower_bill"],
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "system_kwp" in data or "recommendation" in data or "packages" in data


def test_api_catalog(client):
    r = client.get("/api/catalog")
    assert r.status_code == 200
    data = r.get_json()
    assert "panels" in data
    assert len(data["panels"]) >= 1


def test_api_compatibility_check(client):
    r = client.post(
        "/api/catalog/compatibility-check",
        json={
            "panel_id": "panel-balanced-420",
            "inverter_id": "inv-balanced-6",
            "system_kwp": 5,
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "compatible" in data or "checks" in data or "score" in data


def test_api_suppliers_search(client):
    r = client.get("/api/suppliers?postcode=80331&radius_km=25&limit=5")
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_admin_summary_requires_auth(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "FLASK_DEBUG", False)
    monkeypatch.setattr(app_module, "IS_PRODUCTION", True)
    r = client.get("/api/admin/summary")
    assert r.status_code == 401


def test_api_parse_quote(client):
    text = """SolarTech München GmbH
Photovoltaik Komplettanlage 8,4 kWp
Gesamtpreis: 18.450,00 EUR brutto
Module: 20× Trina Vertex 420 Wp
Jahresertrag ca. 8.900 kWh"""
    r = client.post("/api/quotes/parse-text", json={"text": text})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("kwp") == 8.4
    assert data.get("total_eur") == 18450
    assert data.get("price_per_kwp")
    assert data.get("confidence") in ("medium", "high")


def test_robots_txt(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert b"Disallow: /admin" in r.data


def test_api_report_email_outbox(client, monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    r = client.post(
        "/api/report/email",
        json={"to": "installer@example.com", "recommendation": {"location_name": "München"}},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("ok") is True
    assert data.get("mode") == "outbox"
    assert data.get("path")


def test_api_report_email_invalid(client):
    r = client.post("/api/report/email", json={"to": "not-an-email", "recommendation": {}})
    assert r.status_code == 400
