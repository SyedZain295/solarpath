"""EV dealer portal session helpers."""

from __future__ import annotations

from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

from database import EvDealer, db_session


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(dealer: EvDealer, password: str) -> bool:
    if not dealer.password_hash:
        return False
    return check_password_hash(dealer.password_hash, password)


def login_ev_dealer(dealer_id: str) -> None:
    session["ev_dealer_id"] = dealer_id
    session.permanent = True


def logout_ev_dealer() -> None:
    session.pop("ev_dealer_id", None)


def get_current_ev_dealer_id() -> str | None:
    return session.get("ev_dealer_id")


def get_current_ev_dealer() -> EvDealer | None:
    did = get_current_ev_dealer_id()
    if not did:
        return None
    with db_session() as db:
        dealer = db.get(EvDealer, did)
        if dealer:
            db.expunge(dealer)
        return dealer


def ev_dealer_authorized(dealer_id: str, *, admin_ok: bool = False) -> bool:
    if admin_ok and session.get("admin_authenticated"):
        return True
    return session.get("ev_dealer_id") == dealer_id
