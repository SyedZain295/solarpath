"""Closed-beta access gate — password and invite-token entry."""

from __future__ import annotations

import os
import secrets
from urllib.parse import parse_qs, urlencode, urlparse

from flask import redirect, request, session, url_for

PUBLIC_PATH_PREFIXES = (
    "/static/",
    "/health",
    "/robots.txt",
    "/favicon",
)
PUBLIC_EXACT = {"/beta-login", "/demo"}


def _is_production() -> bool:
    env = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "development")).strip().lower()
    return env == "production"


def _env_flag(name: str, *, default: str) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        raw = default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _gate_env_default() -> str:
    """Production deploys default to public demo; local dev defaults to gate on."""
    return "0" if _is_production() else "1"


def _demo_env_default() -> str:
    return "1" if _is_production() else "0"


def _beta_demo_mode() -> bool:
    return _env_flag("BETA_DEMO_MODE", default=_demo_env_default())


def _beta_gate_env_enabled() -> bool:
    return _env_flag("BETA_GATE_ENABLED", default=_gate_env_default())


def _beta_access_password() -> str:
    return os.environ.get("BETA_ACCESS_PASSWORD", "").strip()


def _beta_invite_tokens() -> set[str]:
    return {t.strip() for t in os.environ.get("BETA_INVITE_TOKENS", "").split(",") if t.strip()}


def default_beta_invite() -> str:
    explicit = os.environ.get("BETA_INVITE_DEFAULT", "").strip()
    if explicit:
        return explicit
    tokens = _beta_invite_tokens()
    if tokens:
        return sorted(tokens)[0]
    return ""


def invite_href(path: str, invite: str | None = None) -> str:
    """Append ?invite=… to internal paths when a default invite is configured."""
    token = (invite or default_beta_invite()).strip()
    if not token or not path.startswith("/"):
        return path
    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc:
        return path
    query = parse_qs(parsed.query, keep_blank_values=True)
    if "invite" in query or "token" in query:
        return path
    query["invite"] = [token]
    new_query = urlencode(query, doseq=True)
    rebuilt = f"{parsed.path}?{new_query}"
    if parsed.fragment:
        rebuilt = f"{rebuilt}#{parsed.fragment}"
    return rebuilt


def _api_calculate_post() -> bool:
    if request.path in ("/api/calculate", "/api/calculate/recalc", "/api/bill-upload") and request.method == "POST":
        return True
    return False


def beta_gate_enabled() -> bool:
    if _beta_demo_mode() or not _beta_gate_env_enabled():
        return False
    return bool(_beta_access_password() or _beta_invite_tokens())


def beta_gate_status() -> dict[str, str | bool]:
    """Snapshot for /health and ops checks."""
    return {
        "beta_gate": beta_gate_enabled(),
        "demo_mode": _beta_demo_mode(),
        "beta_gate_env": os.environ.get("BETA_GATE_ENABLED", _gate_env_default()),
        "beta_demo_env": os.environ.get("BETA_DEMO_MODE", _demo_env_default()),
    }


def _path_exempt(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    if path.startswith("/api/incentives") or path.startswith("/api/financing-offers"):
        return True
    return any(path.startswith(p) for p in PUBLIC_PATH_PREFIXES)


def _invite_token_from_request() -> str:
    return (
        request.args.get("invite") or request.args.get("token") or request.headers.get("X-Beta-Invite") or ""
    ).strip()


def _store_beta_session(token: str | None = None) -> None:
    session["beta_authenticated"] = True
    session.permanent = True
    if token:
        session["beta_invite_token"] = token


def persist_beta_invite_session() -> None:
    """Remember invite access for 30 days after first valid invite visit."""
    if not beta_gate_enabled():
        return
    tokens = _beta_invite_tokens()
    token = _invite_token_from_request()
    if token and token in tokens:
        _store_beta_session(token)
        return
    stored = (session.get("beta_invite_token") or "").strip()
    if stored and stored in tokens:
        _store_beta_session(stored)


def check_beta_access() -> bool:
    if not beta_gate_enabled():
        return True
    tokens = _beta_invite_tokens()
    token = _invite_token_from_request()
    if token and token in tokens:
        _store_beta_session(token)
        return True
    stored = (session.get("beta_invite_token") or "").strip()
    if stored and stored in tokens:
        _store_beta_session(stored)
        return True
    if session.get("beta_authenticated"):
        return True
    return False


def beta_gate_before_request():
    persist_beta_invite_session()
    if not beta_gate_enabled():
        return None
    if _api_calculate_post():
        return None
    if _path_exempt(request.path):
        return None
    if request.path == "/beta-login" and request.method == "POST":
        return None
    if check_beta_access():
        return None
    if request.path.startswith("/api/"):
        from flask import jsonify

        return jsonify(
            {
                "error": "Beta access required. Open your invite link or log in at /beta-login, then try again.",
            }
        ), 401
    nxt = request.full_path if request.query_string else request.path
    if nxt.endswith("?") and not request.query_string:
        nxt = request.path
    return redirect(url_for("beta_login", next=nxt))


def verify_beta_password(password: str) -> bool:
    pwd = _beta_access_password()
    if not pwd:
        return False
    return secrets.compare_digest(password, pwd)
