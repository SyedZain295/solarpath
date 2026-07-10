"""Fixed sample recommendation for the public /demo route."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DEMO_FILE = Path(__file__).resolve().parent / "data" / "demo_recommendation.json"


@lru_cache(maxsize=1)
def load_demo_recommendation() -> dict:
    with open(_DEMO_FILE, encoding="utf-8") as f:
        return json.load(f)
