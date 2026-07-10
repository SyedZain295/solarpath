#!/usr/bin/env python3
"""Validate required secrets before docker compose starts."""

from __future__ import annotations

import os
import sys

REQUIRED_POSTGRES = (
    "SECRET_KEY",
    "ADMIN_TOKEN",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
)

REQUIRED_SQLITE = (
    "SECRET_KEY",
    "ADMIN_TOKEN",
)

DOCS = "docs/CODESPACES.md"


def main() -> int:
    sqlite = os.environ.get("SOLARPATH_SQLITE", "").strip() in ("1", "true", "yes")
    required = REQUIRED_SQLITE if sqlite else REQUIRED_POSTGRES
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    if missing:
        print("Missing required environment variables:", ", ".join(missing), file=sys.stderr)
        print("Set them in GitHub → Settings → Secrets and variables → Codespaces", file=sys.stderr)
        print(f"See {DOCS} for the full list.", file=sys.stderr)
        return 1
    print("Compose secrets OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
