"""SQLite-backed supplier directory — replaces suppliers.json at runtime."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from database import Supplier, db_session
from supplier_utils import ensure_intake_slug

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_JSON = os.path.join(ROOT, "data", "suppliers.json")

_CACHE: list[dict] | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _infer_listing_status(row: dict) -> str:
    if row.get("listing_status"):
        return row["listing_status"]
    if row.get("checkout_id"):
        return "verified" if row.get("verified") else "unverified"
    src = (row.get("source") or "").lower()
    if src in ("openstreetmap", "photovoltaik-vergleichsrechner", "pvr"):
        return "unverified"
    return "demo"


def _normalize_import_row(row: dict) -> dict:
    data = dict(row)
    status = _infer_listing_status(data)
    data["listing_status"] = status
    if status == "demo":
        data["verified"] = False
        data["contact_verified"] = False
        data["source"] = data.get("source") or "installer_seed"
        if int(data.get("reviews_count") or 0) <= 0:
            data["rating"] = None
    if not data.get("service_area"):
        data["service_area"] = list(data.get("regions") or data.get("locations_served") or [])
    if not data.get("specialisms"):
        specs = []
        if data.get("battery_capable"):
            specs.append("battery")
        if data.get("ev_charger_capable"):
            specs.append("ev_charger")
        if data.get("heat_pump_capable"):
            specs.append("heat_pump")
        if data.get("commercial_available"):
            specs.append("commercial")
        if data.get("residential_available", True):
            specs.append("residential")
        data["specialisms"] = specs
    if data.get("claim_profile") is None:
        data["claim_profile"] = {}
    return data


def _model_to_dict(model: Supplier) -> dict:
    data = dict(model.profile or {})
    data.update({
        "id": model.id,
        "company_name": model.company_name,
        "email": model.email or "",
        "phone": model.phone or "",
        "website": model.website or "",
        "intake_slug": model.intake_slug or "",
        "latitude": model.latitude,
        "longitude": model.longitude,
        "plan": model.plan or "basic",
        "verified": bool(model.verified),
        "source": model.source or "",
        "last_verified": model.last_verified.isoformat() if model.last_verified else None,
        "contact_verified": bool(model.contact_verified),
        "service_area": model.service_area or [],
        "specialisms": model.specialisms or [],
        "listing_status": model.listing_status or "demo",
        "claim_profile": model.claim_profile or {},
    })
    return data


def _dict_to_model(data: dict, model: Supplier | None = None) -> Supplier:
    normalized = _normalize_import_row(data)
    sid = normalized.get("id") or f"sup-{uuid.uuid4().hex[:8]}"
    normalized["id"] = sid
    if model is None:
        model = Supplier(id=sid)
    model.company_name = normalized.get("company_name", "") or "Installer"
    model.email = (normalized.get("email") or "").strip().lower()
    model.phone = normalized.get("phone") or ""
    model.website = normalized.get("website") or ""
    model.intake_slug = normalized.get("intake_slug") or None
    lat, lon = normalized.get("latitude"), normalized.get("longitude")
    model.latitude = float(lat) if lat is not None else None
    model.longitude = float(lon) if lon is not None else None
    model.plan = normalized.get("plan") or "basic"
    model.verified = bool(normalized.get("verified"))
    model.source = normalized.get("source") or ""
    lv = normalized.get("last_verified")
    if isinstance(lv, str) and lv:
        try:
            model.last_verified = datetime.fromisoformat(lv.replace("Z", "+00:00"))
        except ValueError:
            model.last_verified = None
    elif lv is None:
        model.last_verified = None
    else:
        model.last_verified = lv
    model.contact_verified = bool(normalized.get("contact_verified"))
    model.service_area = normalized.get("service_area") or []
    model.specialisms = normalized.get("specialisms") or []
    model.listing_status = normalized.get("listing_status") or "demo"
    model.claim_profile = normalized.get("claim_profile") or {}
    model.profile = normalized
    if not model.created_at:
        model.created_at = _now()
    model.updated_at = _now()
    return model


def _invalidate_cache() -> None:
    global _CACHE
    _CACHE = None


def ensure_intake_slugs(rows: list[dict]) -> list[dict]:
    taken = {s.get("intake_slug") for s in rows if s.get("intake_slug")}
    changed: list[dict] = []
    for s in rows:
        if not s.get("intake_slug"):
            s["intake_slug"] = ensure_intake_slug(s, taken)
            taken.add(s["intake_slug"])
            changed.append(s)
    if changed:
        with db_session() as db:
            for s in changed:
                model = db.get(Supplier, s["id"])
                if model:
                    db.merge(_dict_to_model(s, model))
        _invalidate_cache()
    return rows


def get_all() -> list[dict]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    with db_session() as db:
        models = db.query(Supplier).all()
        rows = [_model_to_dict(m) for m in models]
    rows = ensure_intake_slugs(rows)
    _CACHE = rows
    return _CACHE


def count() -> int:
    with db_session() as db:
        return db.query(Supplier).count()


def get_by_id(supplier_id: str) -> dict | None:
    with db_session() as db:
        model = db.get(Supplier, supplier_id)
        return _model_to_dict(model) if model else None


def get_by_slug(slug: str) -> dict | None:
    slug = slug.strip().lower()
    with db_session() as db:
        for model in db.query(Supplier).all():
            if (model.intake_slug or "").lower() == slug:
                return _model_to_dict(model)
    return None


def upsert(data: dict, *, invalidate: bool = True) -> dict:
    sid = data.get("id") or f"sup-{uuid.uuid4().hex[:8]}"
    with db_session() as db:
        model = db.get(Supplier, sid)
        model = _dict_to_model({**data, "id": sid}, model)
        db.merge(model)
    if invalidate:
        _invalidate_cache()
    return get_by_id(sid) or _normalize_import_row({**data, "id": sid})


def replace_all(rows: list[dict]) -> None:
    with db_session() as db:
        db.query(Supplier).delete()
        for row in rows:
            db.add(_dict_to_model(row))
    _invalidate_cache()


def import_json_file(path: str = DEFAULT_JSON) -> int:
    if not os.path.isfile(path):
        return 0
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    if not isinstance(rows, list):
        return 0
    with db_session() as db:
        existing = {m.id for m in db.query(Supplier.id).all()}
        added = 0
        for row in rows:
            sid = row.get("id") or f"sup-{uuid.uuid4().hex[:8]}"
            if sid in existing:
                model = db.get(Supplier, sid)
                db.merge(_dict_to_model({**row, "id": sid}, model))
            else:
                db.add(_dict_to_model({**row, "id": sid}))
                added += 1
    _invalidate_cache()
    ensure_intake_slugs(get_all())
    return added


def migrate_from_json_if_empty() -> int:
    with db_session() as db:
        if db.query(Supplier).count() > 0:
            return 0
    return import_json_file(DEFAULT_JSON)


def clear_all() -> None:
    with db_session() as db:
        db.query(Supplier).delete()
    _invalidate_cache()
