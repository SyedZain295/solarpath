"""SQLAlchemy database layer — SQLite by default, Postgres via DATABASE_URL."""

from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text, create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
DEFAULT_DB = f"sqlite:///{os.path.join(DATA_DIR, 'solarpath.db')}"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB)

# Render/Heroku-style postgres URLs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(32), primary_key=True)
    name = Column(String(200), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(64), default="")
    postcode = Column(String(16), default="")
    housing_type = Column(String(64), default="")
    interests = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "postcode": self.postcode,
            "housing_type": self.housing_type or "",
            "interests": self.interests or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(40), primary_key=True)
    plan = Column(String(32), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    amount_eur = Column(Integer, default=0)
    status = Column(String(32), default="pending")
    stripe_session_id = Column(String(255), nullable=True, index=True)
    disclaimer = Column(String(500), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "plan": self.plan,
            "email": self.email,
            "amount_eur": self.amount_eur,
            "status": self.status,
            "stripe_session_id": self.stripe_session_id,
            "disclaimer": self.disclaimer or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(String(32), primary_key=True)
    customer_id = Column(String(32), default="", index=True)
    customer_email = Column(String(255), default="", index=True)
    payload = Column(JSON, nullable=False)
    status = Column(String(32), default="matched")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        data = dict(self.payload or {})
        data.setdefault("id", self.id)
        data.setdefault("customer_id", self.customer_id)
        data.setdefault("customer_email", self.customer_email)
        data.setdefault("status", self.status)
        data.setdefault("created_at", self.created_at.isoformat() if self.created_at else None)
        return data


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(32), primary_key=True)
    customer_id = Column(String(32), default="", index=True)
    customer_email = Column(String(255), default="", index=True)
    recommendation = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer_email": self.customer_email,
            "recommendation": self.recommendation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(32), primary_key=True)
    customer_id = Column(String(32), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    doc_type = Column(String(64), default="other")
    notes = Column(String(500), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "title": self.title,
            "doc_type": self.doc_type,
            "notes": self.notes or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(String(40), primary_key=True)
    company_name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), default="", index=True)
    phone = Column(String(64), default="")
    website = Column(String(500), default="")
    intake_slug = Column(String(64), unique=True, nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    plan = Column(String(32), default="basic")
    verified = Column(Boolean, default=False)
    source = Column(String(64), default="")
    last_verified = Column(DateTime, nullable=True)
    contact_verified = Column(Boolean, default=False)
    service_area = Column(JSON, default=list)
    specialisms = Column(JSON, default=list)
    listing_status = Column(String(32), default="demo", index=True)
    claim_profile = Column(JSON, default=dict)
    profile = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class BetaEvent(Base):
    __tablename__ = "beta_events"

    id = Column(String(32), primary_key=True)
    event_type = Column(String(64), nullable=False, index=True)
    payload = Column(JSON, default=dict)
    session_id = Column(String(64), default="", index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EvDealer(Base):
    """Solar Path EV partner dealer (Phase 2)."""

    __tablename__ = "ev_dealers"

    id = Column(String(40), primary_key=True)
    company_name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), default="")
    phone = Column(String(64), default="")
    location = Column(String(255), default="")
    status = Column(String(32), default="pending", index=True)  # pending | approved | suspended
    profile = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_name": self.company_name,
            "email": self.email,
            "phone": self.phone or "",
            "location": self.location or "",
            "status": self.status or "pending",
            "profile": self.profile or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EvVehicle(Base):
    """Dealer-listed used EV."""

    __tablename__ = "ev_vehicles"

    id = Column(String(40), primary_key=True)
    dealer_id = Column(String(40), nullable=False, index=True)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    status = Column(String(32), default="draft", index=True)  # draft | published | sold
    featured = Column(Boolean, default=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_public_dict(self, dealer: EvDealer | None = None) -> dict:
        data = dict(self.payload or {})
        data["id"] = self.id
        data["slug"] = self.slug
        data["dealer_id"] = self.dealer_id
        data["listing_status"] = "partner"
        data["featured"] = bool(self.featured)
        data["vehicle_status"] = self.status
        if dealer:
            data["dealer_name"] = dealer.company_name
            data["location"] = data.get("location") or dealer.location
        return data


class EvBuyerLead(Base):
    """Qualified EV buyer lead sent to a partner dealer."""

    __tablename__ = "ev_buyer_leads"

    id = Column(String(32), primary_key=True)
    vehicle_id = Column(String(40), nullable=False, index=True)
    dealer_id = Column(String(40), nullable=False, index=True)
    buyer_name = Column(String(200), default="")
    buyer_email = Column(String(255), default="", index=True)
    buyer_phone = Column(String(64), default="")
    buyer_postcode = Column(String(16), default="")
    buyer_profile = Column(JSON, default=dict)
    message = Column(Text, default="")
    qualified = Column(Boolean, default=False)
    status = Column(String(32), default="new", index=True)  # new | contacted | closed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "dealer_id": self.dealer_id,
            "buyer_name": self.buyer_name,
            "buyer_email": self.buyer_email,
            "buyer_phone": self.buyer_phone,
            "buyer_postcode": self.buyer_postcode,
            "buyer_profile": self.buyer_profile or {},
            "message": self.message or "",
            "qualified": bool(self.qualified),
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class InstallerQuote(Base):
    """Structured quote submitted by an installer for a homeowner lead."""

    __tablename__ = "installer_quotes"

    id = Column(String(32), primary_key=True)
    supplier_id = Column(String(40), nullable=False, index=True)
    quote_request_id = Column(String(32), default="", index=True)
    system_kwp = Column(Float, nullable=True)
    panel_model = Column(String(255), default="")
    inverter_model = Column(String(255), default="")
    battery_model = Column(String(255), default="")
    warranty_years = Column(Integer, nullable=True)
    install_weeks = Column(Integer, nullable=True)
    exclusions = Column(Text, default="")
    total_eur = Column(Integer, nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "supplier_id": self.supplier_id,
            "quote_request_id": self.quote_request_id,
            "system_kwp": self.system_kwp,
            "panel_model": self.panel_model,
            "inverter_model": self.inverter_model,
            "battery_model": self.battery_model,
            "warranty_years": self.warranty_years,
            "install_weeks": self.install_weeks,
            "exclusions": self.exclusions or "",
            "total_eur": self.total_eur,
            "notes": self.notes or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@contextmanager
def db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _migrate_json_if_empty()
    try:
        from supplier_store import migrate_from_json_if_empty
        migrate_from_json_if_empty()
    except Exception:
        pass


def _load_json_file(name: str, default):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        raw = fh.read().strip()
        if not raw:
            return default
        return json.loads(raw)


def _migrate_json_if_empty() -> None:
    """One-time import from legacy JSON files when DB tables are empty."""
    from werkzeug.security import generate_password_hash

    with db_session() as session:
        if session.query(Customer).count() == 0:
            for row in _load_json_file("customers.json", []):
                email = (row.get("email") or "").strip().lower()
                if not email:
                    continue
                session.add(Customer(
                    id=row.get("id") or f"cust-{uuid.uuid4().hex[:8]}",
                    name=row.get("name", ""),
                    email=email,
                    password_hash=generate_password_hash(uuid.uuid4().hex),
                    phone=row.get("phone", ""),
                    postcode=row.get("postcode", ""),
                    housing_type=row.get("housing_type", ""),
                    interests=row.get("interests") or [],
                ))

        if session.query(Subscription).count() == 0:
            for row in _load_json_file("subscriptions.json", []):
                session.add(Subscription(
                    id=row.get("id") or f"chk-{uuid.uuid4().hex[:10]}",
                    plan=row.get("plan", "verified"),
                    email=row.get("email", ""),
                    amount_eur=int(row.get("amount_eur") or 0),
                    status=row.get("status", "paid_demo"),
                    disclaimer=row.get("disclaimer", ""),
                ))

        if session.query(Quote).count() == 0:
            for row in _load_json_file("quotes.json", []):
                qid = row.get("id") or f"quote-{uuid.uuid4().hex[:8]}"
                session.add(Quote(
                    id=qid,
                    customer_id=row.get("customer_id", ""),
                    customer_email=(row.get("customer_email") or "").lower(),
                    payload=row,
                    status=row.get("status", "matched"),
                ))

        if session.query(Assessment).count() == 0:
            for row in _load_json_file("assessments.json", []):
                session.add(Assessment(
                    id=row.get("id") or f"assess-{uuid.uuid4().hex[:8]}",
                    customer_id=row.get("customer_id", ""),
                    customer_email=(row.get("customer_email") or "").lower(),
                    recommendation=row.get("recommendation") or {},
                ))

        if session.query(Document).count() == 0:
            for row in _load_json_file("documents.json", []):
                session.add(Document(
                    id=row.get("id") or f"doc-{uuid.uuid4().hex[:8]}",
                    customer_id=row.get("customer_id", ""),
                    title=row.get("title", ""),
                    doc_type=row.get("doc_type", "other"),
                    notes=row.get("notes", ""),
                ))


def db_health() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "sqlite"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
