#!/usr/bin/env python3
"""Validate local dev environment — used by SETUP_DEV.bat and CI."""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 10)

REQUIRED_PACKAGES = (
    "flask",
    "requests",
    "sqlalchemy",
    "pytest",
    "dotenv",
)

WARN_IF_EMPTY = (
    "SECRET_KEY",
    "ADMIN_TOKEN",
)


def check_python() -> list[str]:
    errors = []
    if sys.version_info < MIN_PYTHON:
        errors.append(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required; got {sys.version.split()[0]}")
    return errors


def check_imports() -> list[str]:
    errors = []
    for name in REQUIRED_PACKAGES:
        mod = "dotenv" if name == "dotenv" else name
        try:
            importlib.import_module(mod)
        except ImportError:
            errors.append(f"Missing package: {name} (pip install -r requirements-dev.txt)")
    return errors


def check_env_file(ci: bool) -> list[str]:
    warnings: list[str] = []
    env_path = ROOT / ".env"
    example = ROOT / ".env.example"
    if not env_path.exists():
        if example.exists() and not ci:
            warnings.append(".env missing — copy from .env.example (START.bat does this automatically)")
        elif ci:
            # CI uses env vars only
            pass
        else:
            warnings.append(".env missing and no .env.example found")
        return warnings
    if ci:
        return warnings
    text = env_path.read_text(encoding="utf-8", errors="replace")
    for key in WARN_IF_EMPTY:
        for line in text.splitlines():
            if line.startswith(f"{key}=") and not line.split("=", 1)[1].strip():
                warnings.append(f"{key} is empty in .env (OK for local dev, set for production)")
    return warnings


def check_data(ci: bool) -> list[str]:
    errors: list[str] = []
    if ci:
        return errors
    suppliers = ROOT / "data" / "suppliers.json"
    if not suppliers.is_file():
        errors.append("data/suppliers.json missing — run: python scripts/import_pvr_directory.py --skip-geocode")
    elif suppliers.stat().st_size < 10:
        errors.append("data/suppliers.json is empty — run supplier import script")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Solar Website environment")
    parser.add_argument("--ci", action="store_true", help="CI mode: skip local-only data checks")
    args = parser.parse_args()

    errors = []
    errors.extend(check_python())
    errors.extend(check_imports())
    errors.extend(check_env_file(args.ci))
    errors.extend(check_data(args.ci))

    warnings = [e for e in errors if e.startswith(".env") or "empty in .env" in e]
    hard_errors = [e for e in errors if e not in warnings]

    for w in warnings:
        print(f"WARN: {w}")
    for e in hard_errors:
        print(f"ERROR: {e}")

    if hard_errors:
        return 1
    print("Environment OK" + (" (CI)" if args.ci else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
