"""Email notifications – logs in dev; set SMTP env vars for production."""

import os
import smtplib
import uuid
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _data_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "data")


def _from_addr() -> str:
    return os.environ.get("SMTP_FROM") or os.environ.get("SUPPORT_EMAIL") or "noreply@solarpath.local"


def _smtp_port() -> int:
    raw = (os.environ.get("SMTP_PORT") or "587").strip()
    try:
        return int(raw)
    except ValueError:
        return 587


def _use_ssl(port: int | None = None) -> bool:
    if os.environ.get("SMTP_USE_SSL", "").strip().lower() in ("1", "true", "yes"):
        return True
    return (port if port is not None else _smtp_port()) == 465


def _use_tls() -> bool:
    return os.environ.get("SMTP_USE_TLS", "1").strip().lower() not in ("0", "false", "no")


def _smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST", "").strip() and os.environ.get("SMTP_USER", "").strip())


def smtp_status() -> dict:
    """Report SMTP configuration for health checks (never exposes secrets)."""
    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    password_set = bool(os.environ.get("SMTP_PASSWORD", "").strip())
    port = _smtp_port()
    from_addr = _from_addr()

    if not host or not user:
        missing = []
        if not host:
            missing.append("SMTP_HOST")
        if not user:
            missing.append("SMTP_USER")
        return {
            "configured": False,
            "ready": False,
            "mode": "file_log",
            "from": from_addr,
            "missing": missing,
        }

    return {
        "configured": True,
        "ready": password_set,
        "mode": "smtp",
        "from": from_addr,
        "host": host,
        "port": port,
        "user": user,
        "password_set": password_set,
        "use_ssl": _use_ssl(port),
        "use_tls": _use_tls(),
        "missing": [] if password_set else ["SMTP_PASSWORD"],
    }


def test_smtp_connection() -> dict:
    """Verify SMTP login without sending mail."""
    status = smtp_status()
    if not status["configured"]:
        return {"ok": False, "error": "not_configured", **status}
    if not status["ready"]:
        return {"ok": False, "error": "missing_password", **status}

    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    port = _smtp_port()
    try:
        with _smtp_session(host, port, user, password) as server:
            server.noop()
        return {"ok": True, **status}
    except smtplib.SMTPAuthenticationError:
        return {"ok": False, "error": "authentication_failed", **status}
    except (smtplib.SMTPException, OSError) as exc:
        return {"ok": False, "error": str(exc), **status}


def _smtp_session(host: str, port: int, user: str, password: str):
    if _use_ssl(port):
        server = smtplib.SMTP_SSL(host, port or 465, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        if _use_tls():
            server.starttls()
    if password:
        server.login(user, password)
    return server


def _send_message(msg: MIMEText | MIMEMultipart) -> bool:
    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    port = _smtp_port()

    if not host or not user:
        return False
    if not password:
        raise smtplib.SMTPException("SMTP_PASSWORD is not set")

    with _smtp_session(host, port, user, password) as server:
        server.send_message(msg)
    return True


def _log_email(to: str, subject: str, body: str, from_addr: str, attachment_note: str = "") -> None:
    log_path = os.path.join(_data_dir(), "email_log.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n---\nFrom: {from_addr}\nTo: {to}\nSubject: {subject}\n{body}\n{attachment_note}")


def send_email(to: str, subject: str, body: str) -> bool:
    if not to:
        return False
    from_addr = _from_addr()

    if not _smtp_configured():
        _log_email(to, subject, body, from_addr)
        return True

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    try:
        return _send_message(msg)
    except (smtplib.SMTPException, OSError):
        _log_email(to, subject, body, from_addr, "SMTP send failed — logged locally.\n")
        return False


def send_email_with_attachment(
    to: str,
    subject: str,
    body: str,
    attachment_bytes: bytes,
    filename: str,
) -> dict:
    """Send email with PDF attachment. Without SMTP, saves to data/email_outbox/."""
    if not to:
        return {"ok": False, "error": "missing_email"}

    from_addr = _from_addr()

    if not _smtp_configured() or not os.environ.get("SMTP_PASSWORD", "").strip():
        outbox = os.path.join(_data_dir(), "email_outbox")
        os.makedirs(outbox, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        pdf_path = os.path.join(outbox, safe_name)
        with open(pdf_path, "wb") as fh:
            fh.write(attachment_bytes)
        _log_email(to, subject, body, from_addr, f"Attachment saved: {pdf_path}\n")
        return {"ok": True, "mode": "outbox", "path": pdf_path}

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg.attach(MIMEText(body))
    part = MIMEApplication(attachment_bytes, _subtype="pdf")
    part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(part)

    try:
        _send_message(msg)
        return {"ok": True, "mode": "smtp"}
    except (smtplib.SMTPException, OSError) as exc:
        outbox = os.path.join(_data_dir(), "email_outbox")
        os.makedirs(outbox, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        pdf_path = os.path.join(outbox, safe_name)
        with open(pdf_path, "wb") as fh:
            fh.write(attachment_bytes)
        _log_email(to, subject, body, from_addr, f"SMTP failed ({exc}); attachment saved: {pdf_path}\n")
        return {"ok": True, "mode": "outbox", "path": pdf_path, "smtp_error": str(exc)}


def notify_quote_request(quote: dict, supplier_emails: list) -> None:
    customer = quote.get("customer_name", "Customer")
    subject = f"New Solar Path lead: {customer}"
    lp = quote.get("lead_profile") or {}
    energy = lp.get("energy") or {}
    prefs = lp.get("preferences") or {}
    body = (
        f"A new qualified quote request was submitted.\n\n"
        f"Customer: {quote.get('customer_first_name') or customer}\n"
        f"Email: {quote.get('customer_email')}\n"
        f"Phone: {quote.get('customer_phone')}\n"
        f"Postcode: {quote.get('customer_postcode')} {quote.get('customer_town', '')}\n"
        f"Preferred contact: {quote.get('preferred_contact_time', 'any')}\n"
        f"Lead tier: {quote.get('lead_tier', 'basic')}\n"
        f"Annual use: ~{energy.get('annual_kwh', '—')} kWh\n"
        f"Recommended system: {prefs.get('system_kwp', '—')} kWp\n"
        f"Battery interest: {quote.get('battery_interest', '—')}\n"
        f"Timeframe: {quote.get('installation_timeframe', '—')}\n"
        f"Roof photos: {(lp.get('roof') or {}).get('roof_photo_count', 0)} attached\n"
        f"Quote ID: {quote.get('id')}\n"
    )
    for email in supplier_emails:
        if email:
            send_email(email, subject, body)
    send_email(
        quote.get("customer_email", ""),
        "Solar Path – quote request received",
        "We received your quote request. Matched suppliers will contact you within 1–2 business days.",
    )


def notify_ev_buyer_lead(lead: dict, dealer_email: str, dealer_name: str, vehicle_label: str) -> None:
    if not dealer_email:
        return
    subject = f"New EV buyer lead: {vehicle_label or 'listing'}"
    profile = lead.get("buyer_profile") or {}
    body = (
        f"A new buyer enquiry was submitted on Solar Path.\n\n"
        f"Vehicle: {vehicle_label or '—'}\n"
        f"Buyer: {lead.get('buyer_name', '—')}\n"
        f"Email: {lead.get('buyer_email', '—')}\n"
        f"Phone: {lead.get('buyer_phone') or '—'}\n"
        f"Postcode: {lead.get('buyer_postcode') or '—'}\n"
        f"Qualified: {'yes' if lead.get('qualified') else 'no'}\n"
        f"Budget: {profile.get('budget_eur') or '—'}\n"
        f"Message: {lead.get('message') or '—'}\n"
        f"Lead ID: {lead.get('id', '—')}\n\n"
        f"Sign in to your dealer dashboard to respond.\n"
    )
    send_email(dealer_email, subject, body)
    buyer_email = (lead.get("buyer_email") or "").strip()
    if buyer_email:
        send_email(
            buyer_email,
            "Solar Path – your EV enquiry was sent",
            f"Thanks {lead.get('buyer_name', '')} — your interest in {vehicle_label or 'this vehicle'} "
            f"was forwarded to {dealer_name or 'the dealer'}. Expect contact within 1–2 business days.",
        )
