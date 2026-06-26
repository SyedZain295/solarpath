"""Closed-beta access gate — password and invite-token entry."""

from __future__ import annotations

import os
import secrets
from urllib.parse import urlparse, urlunparse

from flask import redirect, request, session, url_for

BETA_ACCESS_PASSWORD = os.environ.get("BETA_ACCESS_PASSWORD", "").strip()
BETA_INVITE_TOKENS = {
    t.strip()
    for t in os.environ.get("BETA_INVITE_TOKENS", "").split(",")
    if t.strip()
}

PUBLIC_PATH_PREFIXES = (
    "/static/",
    "/health",
    "/robots.txt",
    "/favicon",
)
PUBLIC_EXACT = {"/beta-login"}


def beta_gate_enabled() -> bool:
    return bool(BETA_ACCESS_PASSWORD or BETA_INVITE_TOKENS)


def _path_exempt(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path.startswith(p) for p in PUBLIC_PATH_PREFIXES)


def _invite_token_from_request() -> str:
    return (
        (request.args.get("invite") or request.args.get("token") or request.headers.get("X-Beta-Invite") or "")
        .strip()
    )


def check_beta_access() -> bool:
    if not beta_gate_enabled():
        return True
    if session.get("beta_authenticated"):
        return True
    token = _invite_token_from_request()
    if token and token in BETA_INVITE_TOKENS:
        session["beta_authenticated"] = True
        session.permanent = True
        return True
    return False


def beta_gate_before_request():
    if not beta_gate_enabled():
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
