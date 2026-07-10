def test_register_and_login(client):
    import uuid

    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/customers",
        json={
            "name": "Test User",
            "email": email,
            "phone": "+49 89 123456",
            "postcode": "80331",
            "password": "testpass123",
            "housing_type": "detached",
            "interests": ["quotes"],
        },
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["email"] == email

    client.post("/api/logout")
    r2 = client.post("/api/login", json={"email": email, "password": "testpass123"})
    assert r2.status_code == 200
    assert r2.get_json()["customer"]["email"] == email

    r3 = client.get("/api/me")
    assert r3.status_code == 200
    assert r3.get_json()["authenticated"] is True


def test_quotes_requires_auth(client):
    r = client.get("/api/quotes")
    assert r.status_code == 401
