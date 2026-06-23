"""Stripe Checkout — uses test/live keys when set, otherwise demo mode."""

from __future__ import annotations

import os
from typing import Optional

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# Map plan IDs to Stripe Price IDs (create in Stripe Dashboard → Products)
STRIPE_PRICE_IDS = {
    "basic": os.environ.get("STRIPE_PRICE_BASIC", ""),
    "verified": os.environ.get("STRIPE_PRICE_VERIFIED", ""),
    "premium": os.environ.get("STRIPE_PRICE_PREMIUM", ""),
}


def stripe_enabled() -> bool:
    if os.environ.get("STRIPE_LIVE_ENABLED", "0") != "1":
        return False
    return bool(STRIPE_SECRET_KEY and any(STRIPE_PRICE_IDS.values()))


def stripe_plan_enabled(plan_id: str) -> bool:
    if os.environ.get("STRIPE_LIVE_ENABLED", "0") != "1":
        return False
    return bool(STRIPE_SECRET_KEY and STRIPE_PRICE_IDS.get(plan_id))


def create_checkout_session(
    *,
    plan_id: str,
    email: str,
    checkout_id: str,
    amount_eur: int,
    success_url: str,
    cancel_url: str,
) -> Optional[dict]:
    """Return Stripe session dict with id + url, or None if Stripe not configured (beta uses demo)."""
    if os.environ.get("STRIPE_LIVE_ENABLED", "0") != "1":
        return None
    price_id = STRIPE_PRICE_IDS.get(plan_id)
    if not STRIPE_SECRET_KEY or not price_id:
        return None

    import stripe

    stripe.api_key = STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"plan_id": plan_id, "checkout_id": checkout_id},
        )
    except stripe.StripeError as exc:
        raise RuntimeError(str(exc)) from exc
    return {"id": session.id, "url": session.url}


def verify_webhook(payload: bytes, sig_header: str) -> dict:
    import stripe

    stripe.api_key = STRIPE_SECRET_KEY
    event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    return event
