"""Application settings, loaded from the environment (and an optional `.env`)."""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Every value can be overridden by an environment variable of the same name
    (case-insensitive), so production injects secrets without a file on disk.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+pysqlite:///./habit_tracker.db"
    """SQLAlchemy URL. SQLite in local dev, Postgres in production."""

    dim_date_start: date = date(2025, 1, 1)
    """First date generated into `dim_date`."""

    dim_date_end: date = date(2030, 12, 31)
    """Last date generated into `dim_date`."""

    backfill_max_days: int = 60
    """Hard cap on how many days a single backfill will materialise."""

    default_timezone: str = "Australia/Sydney"
    """IANA timezone assigned to new users unless one is given."""

    pin_length: int = 6
    """Exact number of digits a PIN must have. Six gives a million combinations
    instead of ten thousand, at the cost of two extra taps each morning."""

    seed_user_a_pin: str = "123456"
    """Development-only PIN for the seeded full board. Override in `.env`."""

    seed_user_b_pin: str = "567890"
    """Development-only PIN for the seeded empty board. Override in `.env`."""


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, read from the environment once."""
    return Settings()
