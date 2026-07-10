"""Lightweight real-time anomaly detection for auth and abuse patterns."""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from compliance import DataClass, compliance_tags
from logging_config import audit


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class AnomalyConfig:
    window_seconds: int = 300
    max_failures: int = 8
    block_seconds: int = 900


class AuthAnomalyTracker:
    """Sliding-window failed auth counter with temporary lockout."""

    def __init__(self, config: AnomalyConfig | None = None) -> None:
        self.config = config or AnomalyConfig(
            window_seconds=_env_int("ANOMALY_WINDOW_SECONDS", 300),
            max_failures=_env_int("ANOMALY_MAX_FAILURES", 8),
            block_seconds=_env_int("ANOMALY_BLOCK_SECONDS", 900),
        )
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._blocked_until: dict[str, float] = {}
        self._lock = threading.Lock()

    def _key(self, identifier: str, ip: str | None) -> str:
        ident = (identifier or "").strip().lower()[:120]
        addr = (ip or "unknown").strip()[:64]
        return f"{ident}|{addr}"

    def is_blocked(self, identifier: str, ip: str | None = None) -> bool:
        key = self._key(identifier, ip)
        now = time.time()
        with self._lock:
            until = self._blocked_until.get(key, 0)
            if until > now:
                return True
            if until:
                del self._blocked_until[key]
            return False

    def record_failure(self, event: str, *, identifier: str, ip: str | None = None, **fields) -> bool:
        """Record failed auth; return True if threshold crossed (lockout applied)."""
        key = self._key(identifier, ip)
        now = time.time()
        cfg = self.config
        with self._lock:
            if self._blocked_until.get(key, 0) > now:
                return True
            q = self._events[key]
            q.append(now)
            cutoff = now - cfg.window_seconds
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) < cfg.max_failures:
                return False
            self._blocked_until[key] = now + cfg.block_seconds
            q.clear()
        tags = compliance_tags(data_class=DataClass.AUDIT)
        audit(
            "anomaly_auth_lockout",
            auth_event=event,
            failures=cfg.max_failures,
            window_seconds=cfg.window_seconds,
            block_seconds=cfg.block_seconds,
            **tags,
            **fields,
        )
        return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._blocked_until.clear()


# Process-wide singleton (in-memory; use Redis for multi-node production).
auth_anomaly = AuthAnomalyTracker()
