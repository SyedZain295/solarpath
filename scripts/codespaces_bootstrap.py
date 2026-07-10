#!/usr/bin/env python3
"""Bootstrap data + DB for Docker / Codespaces so the app is usable on first open."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_database_module() -> ModuleType:
    """Import database.py even when PYTHONPATH/cwd are misconfigured in containers."""
    try:
        import database as db_module

        return db_module
    except ModuleNotFoundError:
        db_file = ROOT / "database.py"
        if not db_file.is_file():
            raise ModuleNotFoundError(
                f"database.py not found at {db_file} (cwd={Path.cwd()}, PYTHONPATH={sys.path[:4]})"
            ) from None
        spec = importlib.util.spec_from_file_location("database", db_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load database module from {db_file}") from None
        module = importlib.util.module_from_spec(spec)
        sys.modules["database"] = module
        spec.loader.exec_module(module)
        return module


def main() -> int:
    suppliers = ROOT / "data" / "suppliers.json"
    if not suppliers.is_file() or suppliers.stat().st_size < 100:
        print("Seeding installer directory...")
        subprocess.run(
            [sys.executable, "scripts/seed_german_installers.py"],
            cwd=ROOT,
            check=True,
        )

    database = _load_database_module()
    database.init_db()

    subprocess.run([sys.executable, "scripts/ensure_ready.py"], cwd=ROOT, check=False)
    print("Bootstrap OK — open http://localhost:5000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
