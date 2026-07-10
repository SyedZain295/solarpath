"""Validate Neon Postgres and push DATABASE_URL to Render."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Reuse Render API helpers
sys.path.insert(0, str(ROOT / "scripts"))
from configure_render import find_service_id, set_env, trigger_deploy  # noqa: E402


def test_database(url: str) -> None:
    from sqlalchemy import create_engine, text

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("  database connection OK")


def main() -> int:
    db_url = os.environ.get("DATABASE_URL", "").strip()
    api_key = os.environ.get("RENDER_API_KEY", "").strip()

    if not db_url:
        print("DATABASE_URL is not set in .env")
        print()
        print("Steps:")
        print("  1. Create a free Postgres database at https://neon.tech")
        print("  2. Copy the connection string (pooled recommended)")
        print("  3. Add to .env:  DATABASE_URL=postgresql://...")
        print("  4. Re-run:  python scripts/setup_neon_render.py")
        print()
        print("See docs/DEPLOYMENT.md for full instructions.")
        return 1

    if not (db_url.startswith("postgresql://") or db_url.startswith("postgres://")):
        print("DATABASE_URL must be a PostgreSQL connection string (postgresql://...)")
        return 1

    print("Testing Neon/Postgres connection...")
    try:
        test_database(db_url)
    except Exception as exc:
        print(f"  connection FAILED: {exc}")
        return 1

    if not api_key:
        print()
        print("RENDER_API_KEY is not set in .env — cannot push to Render automatically.")
        print("Set DATABASE_URL manually in Render dashboard → solar-path → Environment.")
        print("See docs/DEPLOYMENT.md")
        return 1

    print("Pushing DATABASE_URL to Render service solar-path...")
    sid = find_service_id()
    set_env(sid, "DATABASE_URL", db_url)
    trigger_deploy(sid)
    print()
    print("Done. After redeploy, verify:")
    print("  curl https://solar-path.onrender.com/health")
    print('  Expect database.url to show your Neon host (not "sqlite").')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
