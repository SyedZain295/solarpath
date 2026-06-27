from unittest.mock import patch

from flask import Flask

import beta_access


def test_beta_gate_returns_json_for_api():
  app = Flask(__name__)
  with app.test_request_context("/api/other", method="POST"):
    with patch.object(beta_access, "beta_gate_enabled", return_value=True), patch.object(
      beta_access, "check_beta_access", return_value=False
    ):
      resp = beta_access.beta_gate_before_request()
    assert resp is not None
    body, status = resp
    assert status == 401
    assert body.json["error"]


def test_beta_gate_exempts_calculate_post():
  app = Flask(__name__)
  with app.test_request_context("/api/calculate", method="POST"):
    with patch.object(beta_access, "beta_gate_enabled", return_value=True), patch.object(
      beta_access, "check_beta_access", return_value=False
    ):
      assert beta_access.beta_gate_before_request() is None


def test_beta_gate_disabled_via_env(monkeypatch):
  monkeypatch.setattr(beta_access, "BETA_GATE_ENABLED", False)
  monkeypatch.setattr(beta_access, "BETA_DEMO_MODE", True)
  assert beta_access.beta_gate_enabled() is False


def test_invite_href_appends_token():
  with patch.object(beta_access, "default_beta_invite", return_value="solarpath-beta-2026"):
    assert beta_access.invite_href("/calculator") == "/calculator?invite=solarpath-beta-2026"
    assert beta_access.invite_href("/calculator?lang=de") == "/calculator?lang=de&invite=solarpath-beta-2026"
    assert beta_access.invite_href("/calculator?invite=other") == "/calculator?invite=other"


def test_persist_invite_session():
  app = Flask(__name__)
  app.secret_key = "test"
  with app.test_request_context("/?invite=tok"):
    with patch.object(beta_access, "BETA_INVITE_TOKENS", {"tok"}), patch.object(
      beta_access, "beta_gate_enabled", return_value=True
    ):
      beta_access.persist_beta_invite_session()
      assert beta_access.check_beta_access() is True


def test_check_beta_access_accepts_invite_header():
  app = Flask(__name__)
  app.secret_key = "test"
  with app.test_request_context("/api/calculate", method="POST", headers={"X-Beta-Invite": "tok"}):
    with patch.object(beta_access, "BETA_INVITE_TOKENS", {"tok"}), patch.object(
      beta_access, "BETA_ACCESS_PASSWORD", ""
    ):
      assert beta_access.check_beta_access() is True


@patch("beta_access.beta_gate_enabled", return_value=True)
@patch("beta_access.check_beta_access", return_value=True)
@patch("app.get_pv_estimate", return_value={"specific_yield_kwh_kwp": 950, "monthly": []})
@patch("app.get_gsa_yield_estimate", return_value=None)
def test_api_calculate_ok_when_beta_session(_gsa, _pvgis, _access, _enabled, client):
    r = client.post(
        "/api/calculate",
        json={
            "latitude": 48.1351,
            "longitude": 11.582,
            "location_name": "München",
            "monthly_kwh": 350,
            "goals": ["lower_bill"],
        },
    )
    assert r.status_code == 200
    assert "system_kwp" in r.get_json()


def test_demo_route_public(client):
    r = client.get("/demo")
    assert r.status_code == 200
    assert b"Demo mode" in r.data or b"demo-banner" in r.data
    assert b"M" in r.data  # München sample embedded in page JSON
