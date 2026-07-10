"""Tests for compliance PII classification and redaction."""

from compliance import DataClass, RETENTION, classify_field, redact_value, sanitize_record


def test_classify_pii_and_credentials():
    assert classify_field("email") == DataClass.PII
    assert classify_field("customer_email") == DataClass.PII
    assert classify_field("password") == DataClass.CREDENTIAL
    assert classify_field("admin_token") == DataClass.CREDENTIAL
    assert classify_field("title") == DataClass.INTERNAL


def test_redact_email_and_phone():
    assert "***@***" in redact_value("user@example.com")
    assert "***-***-****" in redact_value("+49 89 12345678")


def test_sanitize_record_redacts_sensitive_keys():
    out = sanitize_record({"email": "a@b.com", "plan": "verified"})
    assert out["email"] == "***@***"
    assert out["plan"] == "verified"


def test_retention_defaults():
    assert RETENTION.audit_days >= RETENTION.pii_days
