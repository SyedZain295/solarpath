"""Centralized environment configuration and startup validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

_DEV_SECRET = "dev-solar-key-change-in-production"
_DEV_ADMIN = "dev-admin"


@dataclass(frozen=True)
class Settings:
    app_env: str
    secret_key: str
    admin_token: str
    region_focus: str
    database_url: str
    # Optional previous secret for rotation window (comma-separated)
    previous_secret_keys: tuple[str, ...]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    def validate(self) -> None:
        if self.is_production:
            if self.secret_key == _DEV_SECRET or len(self.secret_key) < 16:
                raise ValueError("SECRET_KEY must be set to a strong value in production")
            if self.admin_token == _DEV_ADMIN or len(self.admin_token) < 12:
                raise ValueError("ADMIN_TOKEN must be set in production")


@lru_cache
def get_settings() -> Settings:
    prev = os.environ.get("SECRET_KEY_PREVIOUS", "")
    keys = tuple(k.strip() for k in prev.split(",") if k.strip())
    settings = Settings(
        app_env=os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "development")),
        secret_key=os.environ.get("SECRET_KEY", _DEV_SECRET),
        admin_token=os.environ.get("ADMIN_TOKEN", _DEV_ADMIN),
        region_focus=os.environ.get("REGION_FOCUS", "Bayern"),
        database_url=os.environ.get("DATABASE_URL", "sqlite:///data/solarpath.db"),
        previous_secret_keys=keys,
    )
    settings.validate()
    return settings
