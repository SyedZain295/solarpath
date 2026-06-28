"""Solar Path EV Phase 2 — dealer portal, inventory, leads."""

import uuid

import pytest

from ev_marketplace import clear_vehicle_cache


def _admin_session(client):
    with client.session_transaction() as sess:
        sess["admin_authenticated"] = True


def _register_and_approve(client, email=None):
    email = email or f"dealer-{uuid.uuid4().hex[:8]}@test.de"
    resp = client.post("/api/ev-dealer/register", json={
        "company_name": "Test EV Bayern",
        "email": email,
        "password": "testpass123",
        "location": "München",
        "phone": "+49 89 000",
    })
    assert resp.status_code == 200
    dealer_id = resp.get_json()["dealer"]["id"]
    _admin_session(client)
    approve = client.patch(f"/api/admin/ev-dealers/{dealer_id}", json={"status": "approved"})
    assert approve.status_code == 200
    login = client.post("/api/ev-dealer/login", json={"email": email, "password": "testpass123"})
    assert login.status_code == 200
    return dealer_id, email


def test_dealer_intake_creates_pending(client):
    email = f"intake-{uuid.uuid4().hex[:6]}@test.de"
    resp = client.post("/api/ev-dealer-intake", json={
        "company_name": "Intake Motors",
        "email": email,
        "location": "Augsburg",
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "pending"


def test_dealer_vehicle_publish_and_list(client):
    _register_and_approve(client)
    create = client.post("/api/ev-dealer/vehicles", json={
        "make": "Volkswagen",
        "model": "ID.3",
        "year": 2021,
        "price_eur": 24000,
        "mileage_km": 35000,
        "battery_kwh": 58,
        "consumption_kwh_100km": 16.5,
        "winter_range_km_min": 220,
        "winter_range_km_max": 260,
        "dc_fast_charge_kw": 120,
        "status": "published",
        "certificate_uploaded": True,
        "cert_provider": "TÜV SÜD",
        "cert_test_date": "2026-01",
        "cert_soh": 90,
    })
    assert create.status_code == 201
    vehicle = create.get_json()
    clear_vehicle_cache()
    listing = client.get("/api/ev-vehicles")
    slugs = [v["slug"] for v in listing.get_json()["vehicles"]]
    assert vehicle["slug"] in slugs
    assert vehicle["listing_status"] == "partner"


def test_buyer_lead_partner_vehicle(client):
    _register_and_approve(client)
    create = client.post("/api/ev-dealer/vehicles", json={
        "make": "Hyundai",
        "model": "Kona",
        "year": 2022,
        "price_eur": 26000,
        "battery_kwh": 64,
        "status": "published",
    })
    slug = create.get_json()["slug"]
    clear_vehicle_cache()
    lead = client.post("/api/ev-buyer-lead", json={
        "vehicle_slug": slug,
        "buyer_name": "Anna Test",
        "buyer_email": "anna@test.de",
        "buyer_postcode": "80331",
        "buyer_profile": {"budget_eur": 28000},
    })
    assert lead.status_code == 200
    assert lead.get_json()["qualified"] is True
    assert lead.get_json()["demo"] is False

    leads = client.get("/api/ev-dealer/leads")
    assert leads.status_code == 200
    assert len(leads.get_json()["leads"]) >= 1


def test_buyer_lead_demo_vehicle(client):
    lead = client.post("/api/ev-buyer-lead", json={
        "vehicle_slug": "vw-id3-pro-58",
        "buyer_name": "Demo Buyer",
        "buyer_email": "demo@test.de",
        "buyer_postcode": "80331",
    })
    assert lead.status_code == 200
    data = lead.get_json()
    assert data["demo"] is True


def test_pending_dealer_cannot_publish(client):
    email = f"pending-{uuid.uuid4().hex[:6]}@test.de"
    client.post("/api/ev-dealer/register", json={
        "company_name": "Pending Co",
        "email": email,
        "password": "testpass123",
        "location": "Nürnberg",
    })
    client.post("/api/ev-dealer/login", json={"email": email, "password": "testpass123"})
    resp = client.post("/api/ev-dealer/vehicles", json={
        "make": "Fiat",
        "model": "500e",
        "price_eur": 15000,
    })
    assert resp.status_code == 403
