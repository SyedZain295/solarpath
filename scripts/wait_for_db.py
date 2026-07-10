#!/usr/bin/env python3
"""Wait until Postgres accepts connections (docker compose / Codespaces)."""

from __future__ import annotations

import os
import sys
import time

from sqlalchemy import create_engine, text


def main() -> int:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        user = os.environ.get("POSTGRES_USER", "")
        password = os.environ.get("POSTGRES_PASSWORD", "")
        host = os.environ.get("POSTGRES_HOST", "db")
        port = os.environ.get("POSTGRES_PORT", "5432")
        db = os.environ.get("POSTGRES_DB", "solarpath")
        if user and password:
            url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    if not url.startswith("postgresql"):
        return 0

    for attempt in range(1, 31):
        try:
            engine = create_engine(url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database ready")
            return 0
        except Exception:
            print(f"Waiting for database... ({attempt}/30)")
            time.sleep(2)
    print("Database did not become ready in time", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
