"""Tests for security headers and auth lockout integration."""

from anomaly_detection import auth_anomaly


def test_security_headers_present(client):
    auth_anomaly.reset()
    r = client.get("/")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("X-Request-ID")


def test_customer_login_lockout(client):
    auth_anomaly.reset()
    auth_anomaly.config = auth_anomaly.config.__class__(window_seconds=300, max_failures=3, block_seconds=900)
    payload = {"email": "nobody@example.com", "password": "wrong"}
    for _ in range(3):
        client.post("/api/login", json=payload)
    r = client.post("/api/login", json=payload)
    assert r.status_code == 429
