#!/usr/bin/env python3
"""Quick UI smoke checks — pages, static assets, duplicate IDs."""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class IdChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: dict[str, int] = defaultdict(int)

    def handle_starttag(self, tag: str, attrs: list) -> None:
        d = dict(attrs)
        if "id" in d:
            self.ids[d["id"]] += 1


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from app import app

    app.config["TESTING"] = True
    client = app.test_client()
    pages = [
        "/",
        "/calculator",
        "/suppliers",
        "/compare-quotes",
        "/demo",
        "/compatibility",
        "/ev",
        "/results",
        "/estimate",
        "/survey",
        "/energy-advisor",
        "/login",
        "/register",
        "/privacy",
        "/terms",
    ]
    errors: list[str] = []
    for path in pages:
        r = client.get(path)
        if r.status_code != 200:
            errors.append(f"{path} returned {r.status_code}")
            continue
        html = r.data.decode("utf-8", "replace")
        checker = IdChecker()
        checker.feed(html)
        dups = [i for i, n in checker.ids.items() if n > 1]
        if dups:
            errors.append(f"{path} duplicate ids: {', '.join(dups[:8])}")
        refs = re.findall(r'(?:href|src)="(/static/[^"]+)"', html)
        for ref in set(refs):
            rel = ref.split("/static/", 1)[1].split("?", 1)[0]
            if not (ROOT / "static" / rel).is_file():
                errors.append(f"{path} missing static: {ref}")

    if errors:
        for e in errors:
            print("ERROR:", e)
        return 1
    print(f"UI smoke OK — {len(pages)} pages, no duplicate ids, static assets found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
