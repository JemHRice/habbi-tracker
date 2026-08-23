"""Declarative base and shared column types."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app import clock


class Base(DeclarativeBase):
    """Base class for every ORM model."""


class UtcDateTime(TypeDecorator):
    """A timestamp that is always timezone-aware UTC in Python.

    Postgres round-trips `timestamptz` faithfully; SQLite has no timezone type
    and hands back naive values. This decorator normalises both engines to the
    same thing, so `completed_at` and session expiry compare identically in dev
    and in production.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> datetime | None:
        """Store aware datetimes as UTC; reject naive ones outright."""
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError(f"expected datetime, got {type(value).__name__}")
        if value.tzinfo is None:
            raise ValueError("naive datetimes are not accepted; use aware UTC")
        return value.astimezone(UTC)

    def process_result_value(self, value: Any, dialect: Any) -> datetime | None:
        """Return values as aware UTC, tagging SQLite's naive results."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class TimestampMixin:
    """`created_at` / `updated_at` columns maintained in Python.

    Defaults come from :mod:`app.clock` rather than the database so a frozen
    clock in tests governs these too.
    """

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=clock.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=clock.utcnow, onupdate=clock.utcnow
    )
