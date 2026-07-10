"""Backup SQLite database to data/backups/."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BACKUP_DIR = os.path.join(DATA, "backups")
DB_FILE = os.path.join(DATA, "solarpath.db")


def main() -> int:
    if not os.path.isfile(DB_FILE):
        print("No database file at", DB_FILE)
        return 1
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = os.path.join(BACKUP_DIR, f"solarpath-{stamp}.db")
    shutil.copy2(DB_FILE, dest)
    print("Backed up to", dest)
    backups = sorted(f for f in os.listdir(BACKUP_DIR) if f.endswith(".db"))
    while len(backups) > 14:
        old = backups.pop(0)
        os.remove(os.path.join(BACKUP_DIR, old))
        print("Removed old backup", old)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
