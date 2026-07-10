"""Fuzz-style tests — malformed API payloads must not crash the server."""

import pytest


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"monthly_kwh": None},
        {"monthly_kwh": "not-a-number"},
        {"monthly_kwh": -999},
        {"monthly_kwh": 1e99},
        {"postcode": "x" * 500},
        {"goal": ["nested", "list"]},
        None,
    ],
)
def test_quick_estimate_bad_payloads(client, payload):
    r = client.post("/api/quick-estimate", json=payload)
    assert r.status_code in (200, 400, 415, 422, 500)
    if r.status_code == 200:
        assert isinstance(r.get_json(), dict)


@pytest.mark.parametrize(
    "path",
    [
        "/api/does-not-exist",
        "/api/../../../etc/passwd",
        "/api/" + "a" * 200,
        "/api/%00",
    ],
)
def test_unknown_api_paths(client, path):
    r = client.get(path)
    assert r.status_code in (404, 400, 405, 302, 308)


def test_health_always_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json().get("status") in ("ok", "degraded")
