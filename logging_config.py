"""Structured logging, request correlation IDs, audit trail, PII redaction."""

from __future__ import annotations

import contextvars
import json
import logging
import os
import re
import sys
import time
from logging.handlers import RotatingFileHandler

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_REDACT = [
    (re.compile(r'("?password"?\s*[:=]\s*)"?[^",}\s]+', re.I), r"\1***"),
    (re.compile(r'("?(?:token|authorization|secret)"?\s*[:=]\s*)"?[^",}\s]+', re.I), r"\1***"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "***@***"),
]


def _redact(msg: str) -> str:
    for pat, repl in _REDACT:
        msg = pat.sub(repl, msg)
    return msg


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": _redact(record.getMessage()),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logging(*, production: bool = False) -> None:
    level = logging.INFO if production else logging.DEBUG
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addFilter(RequestIdFilter())

    if production:
        handler: logging.Handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(RequestIdFilter())
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.environ.get("LOG_FILE", os.path.join(log_dir, "solarpath.log"))
        fh = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=5)
        fh.addFilter(RequestIdFilter())
        fh.setFormatter(JsonFormatter())
        root.addHandler(fh)
    else:
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] rid=%(request_id)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        sh = logging.StreamHandler()
        sh.addFilter(RequestIdFilter())
        sh.setFormatter(fmt)
        root.addHandler(sh)

    logging.getLogger("solarpath.audit").setLevel(logging.INFO)


def audit(event: str, **fields) -> None:
    """Security / auth audit line (JSON in production)."""
    logger = logging.getLogger("solarpath.audit")
    payload = {"event": event, **{k: _redact(str(v)) for k, v in fields.items()}}
    logger.info(json.dumps(payload) if os.environ.get("APP_ENV") == "production" else str(payload))
