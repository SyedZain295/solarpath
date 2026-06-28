"""Closed-beta access gate — password and invite-token entry."""

from __future__ import annotations

import os
import secrets
from urllib.parse import parse_qs, urlencode, urlparse

from flask import redirect, request, session, url_for

BETA_ACCESS_PASSWORD = os.environ.get("BETA_ACCESS_PASSWORD", "").strip()
BETA_INVITE_TOKENS = {
    t.strip()
    for t in os.environ.get("BETA_INVITE_TOKENS", "").split(",")
    if t.strip()
}
BETA_GATE_ENABLED = os.environ.get("BETA_GATE_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
BETA_DEMO_MODE = os.environ.get("BETA_DEMO_MODE", "0").strip().lower() in ("1", "true", "yes", "on")

PUBLIC_PATH_PREFIXES = (
    "/static/",
    "/health",
    "/robots.txt",
    "/favicon",
)
PUBLIC_EXACT = {"/beta-login", "/demo"}


def default_beta_invite() -> str:
    explicit = os.environ.get("BETA_INVITE_DEFAULT", "").strip()
    if explicit:
        return explicit
    if BETA_INVITE_TOKENS:
        return sorted(BETA_INVITE_TOKENS)[0]
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
    if BETA_DEMO_MODE or not BETA_GATE_ENABLED:
        return False
    return bool(BETA_ACCESS_PASSWORD or BETA_INVITE_TOKENS)


def _path_exempt(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    if path.startswith("/api/incentives") or path.startswith("/api/financing-offers"):
        return True
    return any(path.startswith(p) for p in PUBLIC_PATH_PREFIXES)


def _invite_token_from_request() -> str:
    return (
        (request.args.get("invite") or request.args.get("token") or request.headers.get("X-Beta-Invite") or "")
        .strip()
    )


def _store_beta_session(token: str | None = None) -> None:
    session["beta_authenticated"] = True
    session.permanent = True
    if token:
        session["beta_invite_token"] = token


def persist_beta_invite_session() -> None:
    """Remember invite access for 30 days after first valid invite visit."""
    if not beta_gate_enabled():
        return
    token = _invite_token_from_request()
    if token and token in BETA_INVITE_TOKENS:
        _store_beta_session(token)
        return
    stored = (session.get("beta_invite_token") or "").strip()
    if stored and stored in BETA_INVITE_TOKENS:
        _store_beta_session(stored)


def check_beta_access() -> bool:
    if not beta_gate_enabled():
        return True
    token = _invite_token_from_request()
    if token and token in BETA_INVITE_TOKENS:
        _store_beta_session(token)
        return True
    stored = (session.get("beta_invite_token") or "").strip()
    if stored and stored in BETA_INVITE_TOKENS:
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
        return jsonify({
            "error": "Beta access required. Open your invite link or log in at /beta-login, then try again.",
        }), 401
    nxt = request.full_path if request.query_string else request.path
    if nxt.endswith("?") and not request.query_string:
        nxt = request.path
    return redirect(url_for("beta_login", next=nxt))


def verify_beta_password(password: str) -> bool:
    if not BETA_ACCESS_PASSWORD:
        return False
    return secrets.compare_digest(password, BETA_ACCESS_PASSWORD)
