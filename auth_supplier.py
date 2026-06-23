"""Supplier portal session helpers."""

from __future__ import annotations

from flask import session


def login_supplier(supplier_id: str) -> None:
    session["supplier_id"] = supplier_id
    session.permanent = True


def logout_supplier() -> None:
    session.pop("supplier_id", None)


def get_current_supplier_id() -> str | None:
    return session.get("supplier_id")


def supplier_authorized(supplier_id: str, *, admin_ok: bool = False) -> bool:
    if admin_ok and session.get("admin_authenticated"):
        return True
    return session.get("supplier_id") == supplier_id
