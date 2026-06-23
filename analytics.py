"""Beta validation event tracking."""

from __future__ import annotations

import uuid

from flask import session

from database import BetaEvent, db_session


def track_event(event_type: str, payload: dict | None = None) -> str:
    eid = f"evt-{uuid.uuid4().hex[:10]}"
    sid = session.get("beta_session_id") or session.get("_id", "")
    if not sid:
        sid = f"sess-{uuid.uuid4().hex[:8]}"
        session["beta_session_id"] = sid
    with db_session() as db:
        db.add(BetaEvent(
            id=eid,
            event_type=event_type,
            payload=payload or {},
            session_id=sid,
        ))
    return eid


def beta_metrics_summary() -> dict:
    with db_session() as db:
        rows = db.query(BetaEvent).all()
    counts: dict[str, int] = {}
    packages: dict[str, int] = {}
    for row in rows:
        counts[row.event_type] = counts.get(row.event_type, 0) + 1
        if row.event_type == "package_select":
            pkg = (row.payload or {}).get("package_id", "unknown")
            packages[pkg] = packages.get(pkg, 0) + 1
    calc_starts = counts.get("calculator_start", 0)
    calc_done = counts.get("calculator_complete", 0)
    quotes = counts.get("quote_request", 0)
    return {
        "events_total": len(rows),
        "by_type": counts,
        "calculator_completion_rate": round(calc_done / calc_starts, 3) if calc_starts else None,
        "quote_conversion_rate": round(quotes / calc_done, 3) if calc_done else None,
        "pdf_downloads": counts.get("pdf_download", 0),
        "package_selections": packages,
    }
