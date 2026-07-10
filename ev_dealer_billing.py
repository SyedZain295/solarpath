"""EV dealer billing — featured listing checkout via Stripe (or demo invoice)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from database import EvDealer, EvVehicle, db_session

FEATURED_PRICE_EUR = int(os.environ.get("EV_FEATURED_PRICE_EUR", "49"))
FEATURED_DURATION_DAYS = int(os.environ.get("EV_FEATURED_DURATION_DAYS", "30"))


def featured_billing_enabled() -> bool:
    from stripe_checkout import ev_featured_stripe_enabled

    return ev_featured_stripe_enabled()


def demo_billing_allowed() -> bool:
    return os.environ.get("STRIPE_LIVE_ENABLED", "0") != "1" or not featured_billing_enabled()


def _billing_profile(dealer: EvDealer) -> dict:
    profile = dict(dealer.profile or {})
    billing = profile.get("billing")
    if not isinstance(billing, dict):
        billing = {"events": [], "featured_active": {}}
    billing.setdefault("events", [])
    billing.setdefault("featured_active", {})
    profile["billing"] = billing
    return profile


def get_billing_summary(dealer_id: str) -> dict:
    with db_session() as db:
        dealer = db.get(EvDealer, dealer_id)
        if not dealer:
            return {"ok": False, "error": "Dealer not found"}
        profile = _billing_profile(dealer)
        billing = profile["billing"]
        events = billing.get("events") or []
        active = billing.get("featured_active") or {}
        return {
            "ok": True,
            "featured_price_eur": FEATURED_PRICE_EUR,
            "featured_duration_days": FEATURED_DURATION_DAYS,
            "stripe_enabled": featured_billing_enabled(),
            "demo_mode": demo_billing_allowed(),
            "events": events[-20:],
            "featured_active": active,
            "total_spent_eur": sum(int(e.get("amount_eur") or 0) for e in events if e.get("status") == "paid"),
        }


def _append_billing_event(dealer_id: str, event: dict) -> None:
    with db_session() as db:
        dealer = db.get(EvDealer, dealer_id)
        if not dealer:
            return
        profile = _billing_profile(dealer)
        profile["billing"]["events"].append(event)
        dealer.profile = profile
        dealer.updated_at = datetime.now(timezone.utc)


def activate_featured_listing(
    dealer_id: str,
    vehicle_id: str,
    *,
    amount_eur: int,
    stripe_session_id: str = "",
    mode: str = "stripe",
) -> dict:
    with db_session() as db:
        dealer = db.get(EvDealer, dealer_id)
        row = db.get(EvVehicle, vehicle_id)
        if not dealer or not row or row.dealer_id != dealer_id:
            return {"ok": False, "error": "Vehicle not found"}
        row.featured = True
        row.updated_at = datetime.now(timezone.utc)
        profile = _billing_profile(dealer)
        now = datetime.now(timezone.utc).isoformat()
        profile["billing"]["featured_active"][vehicle_id] = {
            "activated_at": now,
            "amount_eur": amount_eur,
            "mode": mode,
            "stripe_session_id": stripe_session_id,
        }
        profile["billing"]["events"].append(
            {
                "id": f"bill-{uuid.uuid4().hex[:8]}",
                "type": "featured_listing",
                "vehicle_id": vehicle_id,
                "amount_eur": amount_eur,
                "status": "paid",
                "mode": mode,
                "stripe_session_id": stripe_session_id,
                "created_at": now,
            }
        )
        dealer.profile = profile
        dealer.updated_at = datetime.now(timezone.utc)
        slug = row.slug
    try:
        from ev_dealer_store import invalidate_vehicle_cache

        invalidate_vehicle_cache()
    except Exception:
        pass
    return {"ok": True, "vehicle_id": vehicle_id, "slug": slug, "featured": True}


def create_featured_checkout(
    dealer_id: str,
    vehicle_id: str,
    *,
    success_url: str,
    cancel_url: str,
    dealer_email: str,
) -> dict:
    with db_session() as db:
        row = db.get(EvVehicle, vehicle_id)
        if not row or row.dealer_id != dealer_id:
            return {"ok": False, "error": "Vehicle not found"}
        if row.status != "published":
            return {"ok": False, "error": "Publish the vehicle before featuring it"}
        if row.featured:
            return {"ok": False, "error": "Already featured"}

    from stripe_checkout import create_ev_featured_checkout_session

    session = create_ev_featured_checkout_session(
        dealer_id=dealer_id,
        vehicle_id=vehicle_id,
        email=dealer_email,
        amount_eur=FEATURED_PRICE_EUR,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    if not session:
        return {"ok": False, "error": "Stripe not configured for featured listings"}
    return {"ok": True, "stripe": True, "checkout_url": session["url"], "session_id": session["id"]}


def demo_featured_invoice(dealer_id: str, vehicle_id: str) -> dict:
    if not demo_billing_allowed():
        return {"ok": False, "error": "Demo billing disabled — use Stripe checkout"}
    result = activate_featured_listing(
        dealer_id,
        vehicle_id,
        amount_eur=FEATURED_PRICE_EUR,
        mode="demo_invoice",
    )
    if result.get("ok"):
        result["invoice"] = {
            "amount_eur": FEATURED_PRICE_EUR,
            "description": f"Featured EV listing ({FEATURED_DURATION_DAYS} days)",
            "status": "paid_demo",
        }
    return result


def handle_stripe_featured_session(session: dict) -> bool:
    meta = session.get("metadata") or {}
    if meta.get("type") != "ev_featured":
        return False
    dealer_id = meta.get("dealer_id") or ""
    vehicle_id = meta.get("vehicle_id") or ""
    if not dealer_id or not vehicle_id:
        return False
    amount = int(meta.get("amount_eur") or FEATURED_PRICE_EUR)
    activate_featured_listing(
        dealer_id,
        vehicle_id,
        amount_eur=amount,
        stripe_session_id=session.get("id") or "",
        mode="stripe",
    )
    return True


def may_set_featured_directly(dealer_id: str) -> bool:
    """Free checkbox only when Stripe featured billing is off (beta/demo)."""
    return not featured_billing_enabled()
