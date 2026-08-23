"""A single, overridable source of "now".

Every timezone-sensitive rule in the domain (the edit window, session expiry,
day materialisation) reads the current time through :func:`utcnow`, so tests can
freeze it and get deterministic results without touching the system clock.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Iterator

_frozen_now: datetime | None = None


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime.

    Returns the frozen value instead when inside a :func:`frozen_time` block.
    """
    if _frozen_now is not None:
        return _frozen_now
    return datetime.now(UTC)


def resolve_now(now: datetime | None = None) -> datetime:
    """Normalise an optional caller-supplied `now` to an aware UTC datetime.

    Domain functions take an optional `now` argument so a caller can pin the
    moment explicitly; when omitted, the clock is used.

    Raises:
        ValueError: if `now` is given but is naive (no timezone).
    """
    if now is None:
        return utcnow()
    if now.tzinfo is None:
        raise ValueError("`now` must be timezone-aware")
    return now.astimezone(UTC)


@contextmanager
def frozen_time(moment: datetime) -> Iterator[datetime]:
    """Freeze :func:`utcnow` at `moment` for the duration of the block.

    Args:
        moment: A timezone-aware datetime; converted to UTC.

    Raises:
        ValueError: if `moment` is naive.
    """
    global _frozen_now
    if moment.tzinfo is None:
        raise ValueError("frozen_time requires a timezone-aware datetime")
    previous = _frozen_now
    _frozen_now = moment.astimezone(UTC)
    try:
        yield _frozen_now
    finally:
        _frozen_now = previous
