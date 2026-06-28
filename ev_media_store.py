"""EV dealer vehicle photo and certificate file storage."""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

UPLOAD_ROOT = Path(__file__).resolve().parent / "data" / "uploads" / "ev"
MAX_PHOTO_BYTES = 8 * 1024 * 1024
MAX_CERT_BYTES = 12 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
CERT_TYPES = PHOTO_TYPES | {"application/pdf"}


def ensure_upload_dir(dealer_id: str) -> Path:
    path = UPLOAD_ROOT / dealer_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_dealer_photos(dealer_id: str, files: list) -> list[str]:
    urls = []
    dest = ensure_upload_dir(dealer_id)
    for upload in files[:8]:
        if not upload or not upload.filename:
            continue
        raw = upload.read()
        if not raw or len(raw) > MAX_PHOTO_BYTES:
            continue
        ctype = (upload.content_type or "").split(";")[0].strip().lower()
        if ctype and ctype not in PHOTO_TYPES:
            continue
        ext = mimetypes.guess_extension(ctype) or ".jpg"
        if ext == ".jpe":
            ext = ".jpg"
        name = f"photo-{uuid.uuid4().hex[:10]}{ext}"
        (dest / name).write_bytes(raw)
        urls.append(f"/api/ev-dealer/media/{dealer_id}/{name}")
    return urls


def save_dealer_cert(dealer_id: str, upload) -> str | None:
    if not upload or not upload.filename:
        return None
    raw = upload.read()
    if not raw or len(raw) > MAX_CERT_BYTES:
        return None
    ctype = (upload.content_type or "").split(";")[0].strip().lower()
    if ctype and ctype not in CERT_TYPES:
        return None
    ext = ".pdf" if ctype == "application/pdf" else (mimetypes.guess_extension(ctype) or ".jpg")
    dest = ensure_upload_dir(dealer_id)
    name = f"cert-{uuid.uuid4().hex[:10]}{ext}"
    (dest / name).write_bytes(raw)
    return f"/api/ev-dealer/media/{dealer_id}/{name}"


def media_file_path(dealer_id: str, filename: str) -> Path | None:
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return None
    path = UPLOAD_ROOT / dealer_id / filename
    return path if path.is_file() else None
