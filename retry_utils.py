"""Retry with exponential backoff for external HTTP calls."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

log = logging.getLogger("solarpath.retry")

T = TypeVar("T")


def retry_http(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay_s: float = 0.5,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T | None:
    """Run *fn* up to *attempts* times; return None if all attempts fail."""
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except exceptions as exc:
            last_exc = exc
            if i + 1 >= attempts:
                break
            delay = base_delay_s * (2**i)
            log.warning("retry %s/%s after %s: %s", i + 1, attempts, delay, exc)
            time.sleep(delay)
    if last_exc:
        log.debug("retry exhausted: %s", last_exc)
    return None
