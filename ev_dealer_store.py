"""SQLite-backed EV dealer directory and vehicle inventory."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from database import EvBuyerLead, EvDealer, EvVehicle, db_session

VEHICLE_WRITABLE = {
    "make", "model", "trim", "year", "price_eur", "mileage_km", "battery_kwh",
    "consumption_kwh_100km", "wltp_range_km", "winter_range_km_min", "winter_range_km_max",
    "summer_range_km_min", "summer_range_km_max", "dc_fast_charge_kw", "ac_charge_kw",
    "body_type", "seats", "boot_litres", "family_fit", "priority_tags", "location",
    "battery_warranty_years_remaining", "battery_warranty_km_remaining", "photo_urls",
    "battery_certificate", "featured",
}


def _now():
    return datetime.now(timezone.utc)


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:80] or "vehicle"


def invalidate_vehicle_cache() -> None:
    try:
        from ev_marketplace import clear_vehicle_cache
        clear_vehicle_cache()
    except Exception:
        pass


def dealer_by_email(email: str) -> EvDealer | None:
    email = (email or "").strip().lower()
    if not email:
        return None
    with db_session() as db:
        dealer = db.query(EvDealer).filter(EvDealer.email == email).first()
        if dealer:
            db.expunge(dealer)
        return dealer


def dealer_by_id(dealer_id: str) -> EvDealer | None:
    with db_session() as db:
        dealer = db.get(EvDealer, dealer_id)
        if dealer:
            db.expunge(dealer)
        return dealer


def create_dealer_intake(company_name: str, email: str, phone: str = "", location: str = "") -> EvDealer:
    email = email.strip().lower()
    existing = dealer_by_email(email)
    if existing:
        return existing
    dealer_id = f"evd-{uuid.uuid4().hex[:10]}"
    with db_session() as db:
        dealer = EvDealer(
            id=dealer_id,
            company_name=company_name.strip(),
            email=email,
            phone=(phone or "").strip(),
            location=(location or "").strip(),
            status="pending",
            profile={"source": "intake"},
        )
        db.add(dealer)
        db.flush()
        db.expunge(dealer)
        return dealer


def register_dealer(company_name: str, email: str, password: str, phone: str = "", location: str = "") -> EvDealer:
    from auth_ev_dealer import hash_password

    email = email.strip().lower()
    with db_session() as db:
        dealer = db.query(EvDealer).filter(EvDealer.email == email).first()
        if dealer:
            dealer.company_name = company_name.strip() or dealer.company_name
            dealer.phone = (phone or dealer.phone or "").strip()
            dealer.location = (location or dealer.location or "").strip()
            if password:
                dealer.password_hash = hash_password(password)
            if dealer.status == "pending":
                dealer.profile = {**(dealer.profile or {}), "registered": True}
        else:
            dealer = EvDealer(
                id=f"evd-{uuid.uuid4().hex[:10]}",
                company_name=company_name.strip(),
                email=email,
                password_hash=hash_password(password),
                phone=(phone or "").strip(),
                location=(location or "").strip(),
                status="pending",
                profile={"source": "register"},
            )
            db.add(dealer)
        dealer.updated_at = _now()
        db.flush()
        db.expunge(dealer)
        return dealer


def list_dealers(status: str | None = None) -> list[dict]:
    with db_session() as db:
        q = db.query(EvDealer)
        if status:
            q = q.filter(EvDealer.status == status)
        rows = q.order_by(EvDealer.created_at.desc()).all()
        return [r.to_dict() for r in rows]


def set_dealer_status(dealer_id: str, status: str) -> EvDealer | None:
    with db_session() as db:
        dealer = db.get(EvDealer, dealer_id)
        if not dealer:
            return None
        dealer.status = status
        dealer.updated_at = _now()
        db.flush()
        db.expunge(dealer)
        return dealer


def _normalize_vehicle_payload(data: dict) -> dict:
    cert = data.get("battery_certificate") or {}
    if isinstance(cert, dict):
        uploaded = bool(cert.get("uploaded") or data.get("certificate_uploaded"))
        cert = {
            "uploaded": uploaded,
            "provider": (cert.get("provider") or data.get("cert_provider") or "").strip() or None,
            "test_date": (cert.get("test_date") or data.get("cert_test_date") or "").strip() or None,
            "state_of_health_pct": _float_or_none(cert.get("state_of_health_pct") or data.get("cert_soh")),
            "independent_test_available": bool(cert.get("independent_test_available", True)),
            "document_url": (cert.get("document_url") or data.get("cert_document_url") or "").strip() or None,
        }
        if uploaded and cert["state_of_health_pct"] is None:
            cert["uploaded"] = False
    photos = data.get("photo_urls") or []
    if isinstance(photos, str):
        photos = [u.strip() for u in photos.splitlines() if u.strip()]
    tags = data.get("priority_tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    return {
        "make": (data.get("make") or "").strip(),
        "model": (data.get("model") or "").strip(),
        "trim": (data.get("trim") or "").strip(),
        "year": int(data.get("year") or 0),
        "price_eur": int(float(data.get("price_eur") or 0)),
        "mileage_km": int(float(data.get("mileage_km") or 0)),
        "battery_kwh": float(data.get("battery_kwh") or 0),
        "consumption_kwh_100km": float(data.get("consumption_kwh_100km") or 17),
        "wltp_range_km": int(float(data.get("wltp_range_km") or 0)),
        "winter_range_km_min": int(float(data.get("winter_range_km_min") or 0)),
        "winter_range_km_max": int(float(data.get("winter_range_km_max") or 0)),
        "summer_range_km_min": int(float(data.get("summer_range_km_min") or 0)),
        "summer_range_km_max": int(float(data.get("summer_range_km_max") or 0)),
        "dc_fast_charge_kw": int(float(data.get("dc_fast_charge_kw") or 0)),
        "ac_charge_kw": int(float(data.get("ac_charge_kw") or 11)),
        "body_type": (data.get("body_type") or "compact").strip(),
        "seats": int(data.get("seats") or 5),
        "boot_litres": int(data.get("boot_litres") or 0),
        "family_fit": (data.get("family_fit") or "medium").strip(),
        "priority_tags": tags,
        "location": (data.get("location") or "").strip(),
        "battery_warranty_years_remaining": int(data.get("battery_warranty_years_remaining") or 0),
        "battery_warranty_km_remaining": int(data.get("battery_warranty_km_remaining") or 0),
        "photo_urls": photos[:8],
        "battery_certificate": cert,
    }


def _float_or_none(val):
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _unique_slug(db, base: str) -> str:
    slug = base
    n = 2
    while db.query(EvVehicle).filter(EvVehicle.slug == slug).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


def create_vehicle(dealer_id: str, data: dict) -> dict:
    dealer = dealer_by_id(dealer_id)
    if not dealer or dealer.status != "approved":
        raise PermissionError("Dealer not approved")
    payload = _normalize_vehicle_payload(data)
    if not payload["make"] or not payload["model"]:
        raise ValueError("Make and model required")
    base_slug = _slugify(f"{payload['make']}-{payload['model']}-{payload['year']}")
    vid = f"evv-{uuid.uuid4().hex[:10]}"
    with db_session() as db:
        slug = _unique_slug(db, base_slug)
        row = EvVehicle(
            id=vid,
            dealer_id=dealer_id,
            slug=slug,
            status=(data.get("status") or "draft").strip(),
            featured=bool(data.get("featured")),
            payload=payload,
        )
        db.add(row)
        db.flush()
        result = row.to_public_dict(dealer)
    invalidate_vehicle_cache()
    return result


def update_vehicle(dealer_id: str, vehicle_id: str, data: dict) -> dict | None:
    with db_session() as db:
        row = db.get(EvVehicle, vehicle_id)
        if not row or row.dealer_id != dealer_id:
            return None
        payload = _normalize_vehicle_payload({**(row.payload or {}), **data})
        row.payload = payload
        if "status" in data:
            row.status = (data.get("status") or row.status).strip()
        if "featured" in data:
            row.featured = bool(data.get("featured"))
        row.updated_at = _now()
        dealer = db.get(EvDealer, dealer_id)
        result = row.to_public_dict(dealer)
    invalidate_vehicle_cache()
    return result


def delete_vehicle(dealer_id: str, vehicle_id: str) -> bool:
    with db_session() as db:
        row = db.get(EvVehicle, vehicle_id)
        if not row or row.dealer_id != dealer_id:
            return False
        db.delete(row)
    invalidate_vehicle_cache()
    return True


def list_dealer_vehicles(dealer_id: str) -> list[dict]:
    dealer = dealer_by_id(dealer_id)
    with db_session() as db:
        rows = db.query(EvVehicle).filter(EvVehicle.dealer_id == dealer_id).order_by(EvVehicle.updated_at.desc()).all()
        return [r.to_public_dict(dealer) for r in rows]


def list_published_vehicles() -> list[dict]:
    with db_session() as db:
        rows = (
            db.query(EvVehicle, EvDealer)
            .join(EvDealer, EvVehicle.dealer_id == EvDealer.id)
            .filter(EvVehicle.status == "published", EvDealer.status == "approved")
            .order_by(EvVehicle.featured.desc(), EvVehicle.updated_at.desc())
            .all()
        )
        return [v.to_public_dict(d) for v, d in rows]


def vehicle_by_slug_db(slug: str) -> dict | None:
    slug = (slug or "").strip().lower()
    with db_session() as db:
        row = db.query(EvVehicle).filter(EvVehicle.slug == slug).first()
        if not row:
            return None
        dealer = db.get(EvDealer, row.dealer_id)
        if row.status != "published" or not dealer or dealer.status != "approved":
            return None
        return row.to_public_dict(dealer)


def create_buyer_lead_by_slug(
    vehicle_slug: str,
    *,
    buyer_name: str,
    buyer_email: str,
    buyer_phone: str = "",
    buyer_postcode: str = "",
    buyer_profile: dict | None = None,
    message: str = "",
) -> dict:
    """Create lead for partner inventory or record demo interest."""
    from ev_marketplace import vehicle_by_slug

    vehicle = vehicle_by_slug(vehicle_slug)
    if not vehicle:
        return {"ok": False, "error": "Vehicle not found"}

    profile = buyer_profile or {}
    qualified = bool(
        buyer_email.strip()
        and buyer_name.strip()
        and (buyer_postcode.strip() or profile.get("budget_eur"))
    )

    if vehicle.get("listing_status") == "partner":
        lead = create_buyer_lead(
            vehicle.get("id") or vehicle_slug,
            buyer_name=buyer_name,
            buyer_email=buyer_email,
            buyer_phone=buyer_phone,
            buyer_postcode=buyer_postcode,
            buyer_profile=profile,
            message=message,
        )
        if not lead:
            return {"ok": False, "error": "Could not create lead"}
        return {
            "ok": True,
            "qualified": lead.qualified,
            "lead_id": lead.id,
            "demo": False,
            "message": "Your details were sent to the partner dealer.",
        }

    with db_session() as db:
        lead = EvBuyerLead(
            id=f"evl-{uuid.uuid4().hex[:10]}",
            vehicle_id=vehicle.get("id") or vehicle_slug,
            dealer_id="demo",
            buyer_name=buyer_name.strip(),
            buyer_email=buyer_email.strip().lower(),
            buyer_phone=(buyer_phone or "").strip(),
            buyer_postcode=(buyer_postcode or "").strip(),
            buyer_profile={**profile, "vehicle_slug": vehicle_slug, "vehicle_label": f"{vehicle.get('make')} {vehicle.get('model')}"},
            message=(message or "").strip(),
            qualified=qualified,
            status="new",
        )
        db.add(lead)
    return {
        "ok": True,
        "qualified": qualified,
        "demo": True,
        "message": "Demo listing — interest recorded. Partner dealers will receive real leads when live.",
    }


def create_buyer_lead(
    vehicle_id: str,
    *,
    buyer_name: str,
    buyer_email: str,
    buyer_phone: str = "",
    buyer_postcode: str = "",
    buyer_profile: dict | None = None,
    message: str = "",
) -> EvBuyerLead | None:
    with db_session() as db:
        vehicle = db.get(EvVehicle, vehicle_id)
        if not vehicle:
            vehicle = db.query(EvVehicle).filter(EvVehicle.slug == vehicle_id).first()
        if not vehicle:
            return None
        dealer = db.get(EvDealer, vehicle.dealer_id)
        if not dealer or dealer.status != "approved":
            return None
        if vehicle.status != "published":
            return None
        profile = buyer_profile or {}
        qualified = bool(
            buyer_email.strip()
            and buyer_name.strip()
            and (buyer_postcode.strip() or profile.get("budget_eur"))
        )
        lead = EvBuyerLead(
            id=f"evl-{uuid.uuid4().hex[:10]}",
            vehicle_id=vehicle.id,
            dealer_id=dealer.id,
            buyer_name=buyer_name.strip(),
            buyer_email=buyer_email.strip().lower(),
            buyer_phone=(buyer_phone or "").strip(),
            buyer_postcode=(buyer_postcode or "").strip(),
            buyer_profile=profile,
            message=(message or "").strip(),
            qualified=qualified,
            status="new",
        )
        db.add(lead)
        db.flush()
        payload = vehicle.payload or {}
        vehicle_label = f"{payload.get('make', '')} {payload.get('model', '')}".strip()
        notify_ctx = {
            "id": lead.id,
            "buyer_name": lead.buyer_name,
            "buyer_email": lead.buyer_email,
            "buyer_phone": lead.buyer_phone,
            "buyer_postcode": lead.buyer_postcode,
            "buyer_profile": profile,
            "message": lead.message,
            "qualified": lead.qualified,
        }
        dealer_email = dealer.email
        dealer_name = dealer.company_name or ""
        db.expunge(lead)
    try:
        from email_service import notify_ev_buyer_lead

        notify_ev_buyer_lead(notify_ctx, dealer_email, dealer_name, vehicle_label)
    except Exception:
        pass
    return lead


def list_dealer_leads(dealer_id: str, limit: int = 50) -> list[dict]:
    with db_session() as db:
        rows = (
            db.query(EvBuyerLead)
            .filter(EvBuyerLead.dealer_id == dealer_id)
            .order_by(EvBuyerLead.created_at.desc())
            .limit(limit)
            .all()
        )
        out = []
        for lead in rows:
            item = lead.to_dict()
            vehicle = db.get(EvVehicle, lead.vehicle_id)
            if vehicle:
                p = vehicle.payload or {}
                item["vehicle_label"] = f"{p.get('make', '')} {p.get('model', '')}".strip()
                item["vehicle_slug"] = vehicle.slug
            out.append(item)
        return out


def update_lead_status(dealer_id: str, lead_id: str, status: str) -> bool:
    with db_session() as db:
        lead = db.get(EvBuyerLead, lead_id)
        if not lead or lead.dealer_id != dealer_id:
            return False
        lead.status = status
        return True
