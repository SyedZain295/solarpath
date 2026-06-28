"""Roof photo storage and installer handoff."""

from __future__ import annotations

import mimetypes
import os
import uuid
from pathlib import Path

from database import RoofPhoto, RoofPhotoSet, db_session

UPLOAD_ROOT = Path(__file__).resolve().parent / "data" / "uploads" / "roof"
MAX_PHOTOS_PER_SET = 5
MAX_BYTES = 8 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


def ensure_upload_dir() -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def _ext_for(content_type: str, filename: str) -> str:
    guessed = mimetypes.guess_extension(content_type or "") or ""
    if guessed in (".jpe", ".jpeg"):
        return ".jpg"
    if guessed:
        return guessed
    name = (filename or "").lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".heic"):
        if name.endswith(ext):
            return ext if ext != ".jpeg" else ".jpg"
    return ".jpg"


def create_photo_set(*, postcode: str = "", customer_email: str = "") -> str:
    set_id = f"rps-{uuid.uuid4().hex[:10]}"
    with db_session() as db:
        db.add(RoofPhotoSet(
            id=set_id,
            postcode=(postcode or "").strip()[:16],
            customer_email=(customer_email or "").strip().lower()[:255],
        ))
    ensure_upload_dir()
    (UPLOAD_ROOT / set_id).mkdir(parents=True, exist_ok=True)
    return set_id


def get_or_create_set(set_id: str | None, *, postcode: str = "", customer_email: str = "") -> str:
    if set_id:
        with db_session() as db:
            if db.get(RoofPhotoSet, set_id):
                return set_id
    return create_photo_set(postcode=postcode, customer_email=customer_email)


def add_photos_to_set(set_id: str, files: list) -> dict:
    """files: werkzeug FileStorage list."""
    ensure_upload_dir()
    set_dir = UPLOAD_ROOT / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    with db_session() as db:
        photo_set = db.get(RoofPhotoSet, set_id)
        if not photo_set:
            return {"ok": False, "error": "Photo set not found"}
        existing = db.query(RoofPhoto).filter(RoofPhoto.set_id == set_id).count()
        if existing >= MAX_PHOTOS_PER_SET:
            return {"ok": False, "error": f"Maximum {MAX_PHOTOS_PER_SET} photos per project"}

        saved = []
        for upload in files:
            if existing + len(saved) >= MAX_PHOTOS_PER_SET:
                break
            if not upload or not upload.filename:
                continue
            raw = upload.read()
            if not raw:
                continue
            if len(raw) > MAX_BYTES:
                return {"ok": False, "error": "Each photo must be under 8 MB"}
            content_type = (upload.content_type or "").split(";")[0].strip().lower()
            if content_type and content_type not in ALLOWED_TYPES:
                return {"ok": False, "error": "Only JPEG, PNG and WebP images are supported"}

            photo_id = f"rph-{uuid.uuid4().hex[:10]}"
            ext = _ext_for(content_type, upload.filename)
            stored_name = f"{photo_id}{ext}"
            path = set_dir / stored_name
            path.write_bytes(raw)

            label = "meter" if "meter" in (upload.filename or "").lower() else "roof"
            row = RoofPhoto(
                id=photo_id,
                set_id=set_id,
                stored_name=stored_name,
                original_name=(upload.filename or "")[:255],
                content_type=content_type or "image/jpeg",
                size_bytes=len(raw),
                label=label,
            )
            db.add(row)
            saved.append(row.to_public_dict())

        if not saved:
            return {"ok": False, "error": "No valid images uploaded"}

        return {"ok": True, "set_id": set_id, "photos": saved, "count": existing + len(saved)}


def get_photo(photo_id: str) -> dict | None:
    with db_session() as db:
        row = db.get(RoofPhoto, photo_id)
        if not row:
            return None
        return {
            "id": row.id,
            "set_id": row.set_id,
            "stored_name": row.stored_name,
            "content_type": row.content_type or "image/jpeg",
        }


def photo_file_path(photo: dict) -> Path | None:
    path = UPLOAD_ROOT / photo["set_id"] / photo["stored_name"]
    return path if path.is_file() else None


def get_set_summary(set_id: str) -> dict | None:
    if not set_id:
        return None
    with db_session() as db:
        photo_set = db.get(RoofPhotoSet, set_id)
        if not photo_set:
            return None
        photos = (
            db.query(RoofPhoto)
            .filter(RoofPhoto.set_id == set_id)
            .order_by(RoofPhoto.created_at.asc())
            .all()
        )
        return {
            "set_id": set_id,
            "quote_id": photo_set.quote_id or "",
            "postcode": photo_set.postcode or "",
            "count": len(photos),
            "photos": [p.to_public_dict() for p in photos],
        }


def link_set_to_quote(set_id: str, quote_id: str, customer_email: str = "") -> None:
    if not set_id or not quote_id:
        return
    with db_session() as db:
        photo_set = db.get(RoofPhotoSet, set_id)
        if not photo_set:
            return
        photo_set.quote_id = quote_id
        if customer_email:
            photo_set.customer_email = customer_email.strip().lower()[:255]


def analyze_roof_set(set_id: str, hints: dict | None = None) -> dict:
    """Heuristic roof-photo analysis — improves confidence hints for calculator."""
    summary = get_set_summary(set_id)
    if not summary:
        return {"ok": False, "error": "Photo set not found"}
    hints = hints or {}
    count = int(summary.get("count") or 0)
    labels = [p.get("label") or "roof" for p in summary.get("photos") or []]
    has_meter = any(lbl == "meter" for lbl in labels)
    shading_in = (hints.get("shading") or "unknown").lower()
    if count >= 3:
        shading_suggestion = "partial" if shading_in == "unknown" else shading_in
        confidence = "medium"
    elif count >= 1:
        shading_suggestion = shading_in
        confidence = "low"
    else:
        shading_suggestion = "unknown"
        confidence = "low"
    notes = []
    if count < 2:
        notes.append("Add at least two roof angles (south + east/west) for better layout confidence.")
    if not has_meter:
        notes.append("A meter-cabinet photo helps installers plan inverter placement.")
    if hints.get("roof_area_m2"):
        notes.append(f"Usable roof area stated: ~{hints['roof_area_m2']} m² — verify against photos on site.")
    result = {
        "ok": True,
        "stub": False,
        "set_id": set_id,
        "photo_count": count,
        "shading_suggestion": shading_suggestion,
        "roof_area_hint_m2": hints.get("roof_area_m2"),
        "has_meter_photo": has_meter,
        "notes": notes,
        "confidence": confidence,
    }
    lat = hints.get("latitude") if hints.get("latitude") is not None else hints.get("lat")
    lon = hints.get("longitude") if hints.get("longitude") is not None else hints.get("lon")
    if lat is not None and lon is not None:
        from google_solar_client import merge_solar_insights

        return merge_solar_insights(result, float(lat), float(lon))
    return result


def can_view_photo(
    photo_id: str,
    *,
    quote_id: str = "",
    supplier_id: str = "",
    customer_email: str = "",
    set_id: str = "",
    admin: bool = False,
) -> bool:
    if admin:
        return True
    photo = get_photo(photo_id)
    if not photo:
        return False
    from database import Quote

    set_id_val = photo["set_id"]
    with db_session() as db:
        photo_set = db.get(RoofPhotoSet, set_id_val)
        if not photo_set:
            return False
        if customer_email and photo_set.customer_email and photo_set.customer_email == customer_email.strip().lower():
            return True
        if not quote_id and photo_set.quote_id:
            quote_id = photo_set.quote_id
        if not quote_id:
            if set_id and set_id_val == set_id:
                return True
            return False
        quote = db.get(Quote, quote_id)
        if not quote:
            return False
        payload = quote.payload or {}
        if payload.get("roof_photo_set_id") != set_id_val:
            return False
        if supplier_id and supplier_id in (payload.get("supplier_ids") or []):
            return True
    return False
