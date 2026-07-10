"""Unified security audit + anomaly detection for auth flows."""

from __future__ import annotations

from flask import request

from anomaly_detection import auth_anomaly
from compliance import DataClass, compliance_tags, sanitize_record
from logging_config import audit


def _client_ip() -> str | None:
    return request.headers.get("X-Forwarded-For", request.remote_addr)


def record_auth_failure(event: str, *, identifier: str = "", **fields) -> bool:
    """Audit a failed login; return True if client is temporarily blocked."""
    ip = _client_ip()
    safe = sanitize_record(fields, allow=frozenset(fields.keys()))
    tags = compliance_tags(data_class=DataClass.AUDIT)
    audit(event, identifier=identifier, ip=ip, **safe, **tags)
    return auth_anomaly.record_failure(event, identifier=identifier, ip=ip, **safe)


def auth_blocked(identifier: str = "") -> bool:
    return auth_anomaly.is_blocked(identifier, _client_ip())


def record_auth_success(event: str, **fields) -> None:
    safe = sanitize_record(fields, allow=frozenset(fields.keys()))
    tags = compliance_tags(data_class=DataClass.AUDIT)
    audit(event, ip=_client_ip(), **safe, **tags)
