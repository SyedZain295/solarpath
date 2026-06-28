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
    return (
        os.environ.get("SMTP_FROM")
        or os.environ.get("SUPPORT_EMAIL")
        or "noreply@solarpath.local"
    )


def _smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER"))


def send_email(to: str, subject: str, body: str) -> bool:
    if not to:
        return False
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    from_addr = _from_addr()

    if not host or not user:
        log_path = os.path.join(_data_dir(), "email_log.txt")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n---\nFrom: {from_addr}\nTo: {to}\nSubject: {subject}\n{body}\n")
        return True

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
    return True


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

    if not _smtp_configured():
        outbox = os.path.join(_data_dir(), "email_outbox")
        os.makedirs(outbox, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        pdf_path = os.path.join(outbox, safe_name)
        with open(pdf_path, "wb") as fh:
            fh.write(attachment_bytes)
        log_path = os.path.join(_data_dir(), "email_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                f"\n---\nFrom: {from_addr}\nTo: {to}\nSubject: {subject}\n{body}\n"
                f"Attachment saved: {pdf_path}\n"
            )
        return {"ok": True, "mode": "outbox", "path": pdf_path}

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg.attach(MIMEText(body))
    part = MIMEApplication(attachment_bytes, _subtype="pdf")
    part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(part)

    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
    return {"ok": True, "mode": "smtp"}


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
    send_email(quote.get("customer_email", ""), "Solar Path – quote request received",
               "We received your quote request. Matched suppliers will contact you within 1–2 business days.")
