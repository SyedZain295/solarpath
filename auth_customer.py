"""Customer auth helpers."""

from __future__ import annotations

from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

from database import Customer, db_session


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(customer: Customer, password: str) -> bool:
    return check_password_hash(customer.password_hash, password)


def login_customer(customer_id: str) -> None:
    session["customer_id"] = customer_id
    session.permanent = True


def logout_customer() -> None:
    session.pop("customer_id", None)


def get_current_customer() -> Customer | None:
    cid = session.get("customer_id")
    if not cid:
        return None
    with db_session() as db:
        customer = db.get(Customer, cid)
        if customer:
            db.expunge(customer)
        return customer


def customer_by_email(email: str) -> Customer | None:
    with db_session() as db:
        customer = db.query(Customer).filter(Customer.email == email.strip().lower()).first()
        if customer:
            db.expunge(customer)
        return customer
