"""Lightweight PIN brute-force protection.

Deliberately in-process and per-user: this is a two-person app, not a bank. A
six-digit PIN is a million combinations, so a short cooldown after a handful of
failures makes guessing hopeless while costing a genuine mistype almost nothing.

State lives in memory, so it resets when the container does. That is an accepted
trade — a restart is not a practical attack vector at this scale, and it avoids
a table, a migration and a cleanup job for a feature two people will trip once a
year. Times come from :mod:`app.clock`, so tests can freeze them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app import clock
from app.api.errors import PIN_THROTTLED, ApiError
from app.config import get_settings


@dataclass
class _Record:
    """One user's recent failure history."""

    failures: int = 0
    blocked_until: datetime | None = None
    first_failure_at: datetime | None = None


_records: dict[int, _Record] = {}


def reset_all() -> None:
    """Forget every recorded failure. Used by tests."""
    _records.clear()


def clear(user_id: int) -> None:
    """Forget this user's failures — called on a successful login."""
    _records.pop(user_id, None)


def check(user_id: int, now: datetime | None = None) -> None:
    """Raise if this user is currently in a cooldown.

    Raises:
        ApiError: 429 `PIN_THROTTLED`, with the remaining seconds in the message.
    """
    record = _records.get(user_id)
    if record is None or record.blocked_until is None:
        return

    moment = clock.resolve_now(now)
    if moment >= record.blocked_until:
        # The cooldown has passed; the slate is clean.
        _records.pop(user_id, None)
        return

    remaining = int((record.blocked_until - moment).total_seconds()) + 1
    raise ApiError(
        429,
        PIN_THROTTLED,
        f"Too many incorrect PIN attempts. Try again in {remaining} seconds.",
    )


def record_failure(user_id: int, now: datetime | None = None) -> None:
    """Count a failed attempt, starting a cooldown once the limit is reached."""
    settings = get_settings()
    moment = clock.resolve_now(now)

    record = _records.setdefault(user_id, _Record())
    if record.first_failure_at is None:
        record.first_failure_at = moment
    record.failures += 1

    if record.failures >= settings.pin_throttle_max_attempts:
        record.blocked_until = moment + timedelta(
            seconds=settings.pin_throttle_cooldown_seconds
        )
        record.failures = 0
        record.first_failure_at = None
