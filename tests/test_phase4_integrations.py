"""Phase 4 integration tests."""

from bill_ocr import parse_bill_text
from financing_offers import financing_offers
from incentives_lookup import incentives_lookup
from roof_analysis import analyze_roof_request
from ev_dealer_billing import demo_featured_invoice, get_billing_summary


def test_bill_ocr_parses_german_text():
    text = """
    Stromrechnung Januar 2026
    Verbrauch: 420 kWh
    Gesamt zu zahlen: 142,50 €
    """
    result = parse_bill_text(text)
    assert result["ok"] is True
    assert result["stub"] is False
    assert result["parsed"]["monthly_kwh"] == 420
    assert result["parsed"]["monthly_bill_eur"] == 142.5


def test_financing_offers_not_stub():
    result = financing_offers(15000, 10)
    assert result["ok"] is True
    assert result["stub"] is False
    assert len(result["offers"]) >= 2


def test_incentives_bavaria():
    result = incentives_lookup("80331")
    assert result["ok"] is True
    assert result["stub"] is False
    assert result["region"] == "Bayern"
    assert result["count"] >= 4


def test_roof_analysis_requires_input():
    result = analyze_roof_request({})
    assert result.get("ok") is False


def test_roof_analysis_location_only():
    result = analyze_roof_request({"latitude": 48.13, "longitude": 11.58})
    assert result.get("ok") is True
    assert "google_solar" in result


def test_api_bill_upload(client):
    resp = client.post(
        "/api/bill-upload",
        json={"text": "Verbrauch 350 kWh\nGesamt 98,00 €"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["parsed"]["monthly_kwh"] == 350


def test_api_financing_offers(client):
    resp = client.get("/api/financing-offers?amount=12000&term_years=10")
    assert resp.status_code == 200
    assert resp.get_json()["stub"] is False


def test_api_incentives(client):
    resp = client.get("/api/incentives?postcode=80331")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["region"] == "Bayern"


def test_ev_dealer_billing_demo(client):
    from database import EvDealer, EvVehicle, db_session
    from auth_ev_dealer import hash_password

    dealer_id = "evd-test-bill"
    veh_id = "evv-test-bill"
    with db_session() as db:
        if not db.get(EvDealer, dealer_id):
            db.add(EvDealer(
                id=dealer_id,
                company_name="Test Motors",
                email="billing-test@example.com",
                password_hash=hash_password("testpass12"),
                status="approved",
            ))
        if not db.get(EvVehicle, veh_id):
            db.add(EvVehicle(
                id=veh_id,
                dealer_id=dealer_id,
                slug="test-billing-vehicle",
                status="published",
                featured=False,
                payload={"make": "VW", "model": "ID.3", "price_eur": 25000},
            ))
    result = demo_featured_invoice(dealer_id, veh_id)
    assert result.get("ok") is True
    summary = get_billing_summary(dealer_id)
    assert summary["total_spent_eur"] >= 0
