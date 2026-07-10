"""HTTP middleware: request IDs, security headers, CSP, compliance hooks."""

from __future__ import annotations

import logging
import time
import uuid

from flask import Flask, g, request

from logging_config import request_id_ctx

log = logging.getLogger("solarpath")

# Baseline CSP — allows inline scripts/styles used by Jinja templates today.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https:; "
    "connect-src 'self' https://re.jrc.ec.europa.eu; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


def register_http_middleware(app: Flask, *, production: bool) -> None:
    """Attach request logging, correlation IDs, and security headers."""

    @app.before_request
    def log_request_start():
        rid = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
        g.request_id = rid
        request_id_ctx.set(rid)
        if app.config.get("TESTING"):
            return None
        g._req_start = time.perf_counter()
        log.info("--> %s %s", request.method, request.path)

    @app.after_request
    def log_request_end(response):
        if hasattr(g, "request_id"):
            response.headers["X-Request-ID"] = g.request_id
        if not app.config.get("TESTING") and hasattr(g, "_req_start"):
            elapsed_ms = round((time.perf_counter() - g._req_start) * 1000, 1)
            log.info("<-- %s %s %s %sms", request.method, request.path, response.status_code, elapsed_ms)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
            response.headers.setdefault("Content-Security-Policy", _CSP)
        return response
