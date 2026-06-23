"""Print live production URLs for Solar Path on Render."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE = os.environ.get("PRODUCTION_URL", "https://solar-path.onrender.com").rstrip("/")
invite = (os.environ.get("BETA_INVITE_TOKENS") or "solarpath-beta-2026").split(",")[0].strip()
password = os.environ.get("BETA_ACCESS_PASSWORD", "")

print()
print("=" * 56)
print("  Solar Path — LIVE (Render)")
print("=" * 56)
print()
print(f"  Health:     {BASE}/health")
print(f"  Invite QR:  {BASE}/?invite={invite}")
print(f"  Calculator: {BASE}/calculator")
print(f"  Admin:      {BASE}/admin")
print()
if password:
    print(f"  Beta password (backup): {password}")
print()
print("  Note: free tier sleeps after ~15 min idle — first visit may be slow.")
print()
