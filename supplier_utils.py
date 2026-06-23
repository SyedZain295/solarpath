"""Installer intake slugs and branded link helpers."""

import re
import unicodedata

PLACEHOLDER_PHONES = {"—", "-", "---", "–", "n/a", "N/A", "none", "None"}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "installer"


def ensure_intake_slug(supplier: dict, taken: set[str] | None = None) -> str:
    if supplier.get("intake_slug"):
        return supplier["intake_slug"]
    base = slugify(supplier.get("company_name", supplier.get("id", "installer")))[:48]
    slug = base
    n = 2
    taken = taken or set()
    while slug in taken:
        slug = f"{base}-{n}"
        n += 1
    return slug


def public_installer_brand(supplier: dict, request_root: str = "") -> dict:
    slug = supplier.get("intake_slug", "")
    intake_url = f"{request_root.rstrip('/')}/i/{slug}" if slug else ""
    return {
        "id": supplier.get("id"),
        "company_name": supplier.get("company_name"),
        "description": supplier.get("description", ""),
        "certifications": supplier.get("certifications", []),
        "regions": supplier.get("regions", []),
        "verified": supplier.get("verified", False),
        "plan": supplier.get("plan", "basic"),
        "intake_slug": slug,
        "intake_url": intake_url,
        "residential_available": supplier.get("residential_available", True),
        "battery_capable": supplier.get("battery_capable", True),
    }


def is_placeholder_phone(phone: str | None) -> bool:
    if phone is None:
        return True
    text = str(phone).strip()
    if not text or text in PLACEHOLDER_PHONES:
        return True
    digits = re.sub(r"\D", "", text)
    return len(digits) < 6


def is_placeholder_email(email: str | None, company: str = "") -> bool:
    if not email:
        return True
    e = email.strip().lower()
    if e.endswith(".solarpath.local"):
        return True
    if e.startswith("kontakt@") and e.endswith(".de"):
        return True
    if e.startswith("contact@") and e.endswith(".solarpath.local"):
        return True
    slug = slugify(company or "")
    if slug and e.startswith("info@") and slug.replace("-", "") in e.replace(".", "").replace("-", ""):
        return True
    return False


def is_directory_listing(supplier: dict) -> bool:
    if supplier.get("verified"):
        return False
    has_real_contact = (
        not is_placeholder_phone(supplier.get("phone"))
        or not is_placeholder_email(supplier.get("email"), supplier.get("company_name", ""))
        or bool((supplier.get("website") or "").strip())
    )
    if has_real_contact:
        return False
    src = supplier.get("source") or ""
    if "photovoltaik-vergleichsrechner" in src:
        return True
    return (
        is_placeholder_phone(supplier.get("phone"))
        and is_placeholder_email(supplier.get("email"), supplier.get("company_name", ""))
        and not (supplier.get("website") or "").strip()
    )


def prepare_supplier_for_public_listing(supplier: dict, *, quality_score: int | None = None) -> dict:
    """Strip placeholder contact/ratings from public API responses."""
    row = dict(supplier)
    listing_status = supplier.get("listing_status") or ("demo" if not supplier.get("checkout_id") else "unverified")
    row["listing_status"] = listing_status
    row["is_demo_listing"] = listing_status == "demo"
    if row["is_demo_listing"]:
        row["listing_label"] = "Demo listing (beta sample)"
        row["verified"] = False
        row["display_rating"] = None
        row["display_reviews"] = 0
    directory = is_directory_listing(supplier) and not row["is_demo_listing"]
    reviews = int(supplier.get("reviews_count") or 0)
    rating = supplier.get("rating")

    row["is_directory_listing"] = directory or row["is_demo_listing"]
    row["display_phone"] = None if is_placeholder_phone(supplier.get("phone")) or row["is_demo_listing"] else supplier.get("phone")
    row["display_email"] = None if is_placeholder_email(supplier.get("email"), supplier.get("company_name", "")) or row["is_demo_listing"] else supplier.get("email")
    website = (supplier.get("website") or "").strip()
    row["display_website"] = None if row["is_demo_listing"] else (website or None)

    if not row["is_demo_listing"] and reviews > 0 and rating is not None:
        row["display_rating"] = round(float(rating), 1)
        row["display_reviews"] = reviews
    else:
        row["display_rating"] = None
        row["display_reviews"] = 0

    if directory or row["is_demo_listing"]:
        row["quality_score"] = None
    elif quality_score is not None:
        row["quality_score"] = quality_score

    return row
