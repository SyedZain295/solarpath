def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "solar-path"


def test_homepage(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Solar Path" in r.data


def test_calculator_page(client):
    r = client.get("/calculator")
    assert r.status_code == 200
    assert b"goal-card" in r.data or b"calc-step" in r.data
