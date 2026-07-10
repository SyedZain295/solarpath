"""Enterprise privacy/compliance helpers (GDPR + HIPAA-adjacent patterns for PII).

Solar Path stores lead/contact PII (email, phone, postcode), not clinical PHI.
These utilities apply the same engineering controls: classification, minimization,
retention metadata, and audit tagging for regulated-style deployments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

# Fields treated as sensitive PII in logs, exports, and audit trails.
PII_FIELD_NAMES = frozenset(
    {
        "email",
        "phone",
        "postcode",
        "address",
        "customer_email",
        "password",
        "token",
        "authorization",
        "secret",
        "bill_text",
        "raw_bill",
    }
)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s\-().]{7,}\d")


class DataClass(str, Enum):
    """Rough mapping to HIPAA/GDPR handling tiers for non-clinical PII."""

    PUBLIC = "public"
    INTERNAL = "internal"
    PII = "pii"  # contact / lead data
    CREDENTIAL = "credential"  # passwords, tokens, API keys
    AUDIT = "audit"  # security events — retain longer, never export casually


@dataclass(frozen=True)
class RetentionPolicy:
    """Default retention windows (days) — enforced by ops/cron, documented here."""

    pii_days: int = 730
    audit_days: int = 2555  # ~7 years, common audit retention
    session_days: int = 30


RETENTION = RetentionPolicy()


def classify_field(name: str) -> DataClass:
    key = name.lower().replace("-", "_")
    if key in {"password", "token", "secret", "authorization", "admin_token"}:
        return DataClass.CREDENTIAL
    if key in PII_FIELD_NAMES or "email" in key or "phone" in key:
        return DataClass.PII
    if key.startswith("audit_") or key in {"event", "request_id"}:
        return DataClass.AUDIT
    return DataClass.INTERNAL


def redact_value(value: Any) -> str:
    """Minimize PII in log/audit payloads."""
    if value is None:
        return ""
    text = str(value)
    text = _EMAIL_RE.sub("***@***", text)
    text = _PHONE_RE.sub("***-***-****", text)
    if len(text) > 120:
        return text[:40] + "…[truncated]"
    return text


def sanitize_record(data: dict[str, Any], *, allow: frozenset[str] | None = None) -> dict[str, str]:
    """Return a log-safe copy of a dict with PII redacted."""
    out: dict[str, str] = {}
    for key, val in data.items():
        if allow and key not in allow:
            continue
        dc = classify_field(key)
        if dc in (DataClass.PII, DataClass.CREDENTIAL):
            out[key] = redact_value(val)
        else:
            out[key] = str(val)
    return out


def compliance_tags(*, data_class: DataClass = DataClass.AUDIT) -> dict[str, str]:
    """Structured fields appended to audit/security log lines."""
    return {
        "data_class": data_class.value,
        "retention_days": str(
            RETENTION.audit_days if data_class == DataClass.AUDIT else RETENTION.pii_days
        ),
    }
