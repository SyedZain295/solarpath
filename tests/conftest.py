import json
import os
from pathlib import Path

# Use isolated test database before app import
os.environ["DATABASE_URL"] = "sqlite:///data/test_solarpath.db"
os.environ.pop("BETA_ACCESS_PASSWORD", None)
os.environ.pop("BETA_INVITE_TOKENS", None)

import pytest

import supplier_store
from app import app as flask_app
from database import init_db

# Developer .env may configure SMTP; tests must not send mail or require credentials.
for _smtp_key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_USE_TLS", "SMTP_USE_SSL"):
    os.environ.pop(_smtp_key, None)

FIXTURES = Path(__file__).parent / "fixtures"
SUPPLIERS_FIXTURE = FIXTURES / "suppliers_fixture.json"


@pytest.fixture(autouse=True)
def isolated_suppliers_db():
    """Load fixture suppliers into test DB — never touch production suppliers.json."""
    supplier_store.clear_all()
    with open(SUPPLIERS_FIXTURE, encoding="utf-8") as fh:
        rows = json.load(fh)
    for row in rows:
        supplier_store.upsert(row, invalidate=False)
    supplier_store._invalidate_cache()


@pytest.fixture
def client():
    init_db()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client
