"""Production logging configuration."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT, "data")


def setup_logging(*, production: bool = False) -> None:
    level = logging.INFO if production else logging.DEBUG
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(sh)
    if production:
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.environ.get("LOG_FILE", os.path.join(LOG_DIR, "solarpath.log"))
        if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
            fh = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=5)
            fh.setFormatter(fmt)
            root.addHandler(fh)
