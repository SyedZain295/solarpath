def test_quotes_email_bypass_blocked(client):
    r = client.get("/api/quotes?customer_email=anyone@example.com")
    assert r.status_code == 401


def test_quotes_supplier_bypass_blocked(client):
    r = client.get("/api/quotes?supplier_id=sup-fake123")
    assert r.status_code == 401


def test_assessments_email_bypass_blocked(client):
    r = client.get("/api/assessments?email=anyone@example.com")
    assert r.status_code == 401


def test_supplier_register_requires_checkout(client):
    r = client.post("/api/suppliers", json={
        "company_name": "Test GmbH",
        "email": "supplier@example.com",
        "phone": "+49 89 123",
    })
    assert r.status_code == 402


def test_supplier_register_with_demo_checkout(client):
    r1 = client.post("/api/checkout", json={
        "plan": "verified",
        "email": "supplier-demo@example.com",
    })
    assert r1.status_code == 201
    checkout_id = r1.get_json()["checkout_id"]

    r2 = client.post("/api/suppliers", json={
        "checkout_id": checkout_id,
        "company_name": "Demo Solar GmbH",
        "email": "supplier-demo@example.com",
        "phone": "+49 89 123456",
    })
    assert r2.status_code == 201
    data = r2.get_json()
    assert data["plan"] == "verified"
    assert data["verified"] is True

    r3 = client.post("/api/suppliers", json={
        "checkout_id": checkout_id,
        "company_name": "Reuse GmbH",
        "email": "supplier-demo@example.com",
        "phone": "+49 89 999",
    })
    assert r3.status_code == 402


def test_project_page_loads(client):
    r = client.get("/project")
    assert r.status_code == 200
