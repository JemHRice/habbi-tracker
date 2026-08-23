"""Calendar helpers: local day boundaries and the `dim_date` dimension.

Timestamps are stored as UTC. A user's *day* is a local concept, so every rule
that turns a moment into a date (the edit window, session expiry, "today")
routes through here.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.models.dim_date import DimDate, build_row
from app.models.user import User


def user_zone(user: User) -> ZoneInfo:
    """Return the user's timezone as a :class:`~zoneinfo.ZoneInfo`."""
    return ZoneInfo(user.timezone)


def to_local_date(user: User, moment: datetime) -> date:
    """Convert an aware UTC moment into the calendar date the user was living."""
    return moment.astimezone(user_zone(user)).date()


def local_today(user: User, now: datetime | None = None) -> date:
    """Return today's date in the user's timezone."""
    return to_local_date(user, clock.resolve_now(now))


def next_local_midnight(user: User, now: datetime | None = None) -> datetime:
    """Return the next local midnight after `now`, as an aware UTC datetime.

    This is the single day boundary the app uses: sessions expire on it and the
    edit window rolls over on it. On the rare zone where a DST jump means local
    midnight does not exist, :class:`~zoneinfo.ZoneInfo` resolves the wall time
    to a real instant, which is close enough for a day boundary.
    """
    zone = user_zone(user)
    local_now = clock.resolve_now(now).astimezone(zone)
    tomorrow = local_now.date() + timedelta(days=1)
    midnight = datetime.combine(tomorrow, time.min, tzinfo=zone)
    return midnight.astimezone(UTC)


def week_start(day: date) -> date:
    """Return the Monday of the week containing `day`."""
    return day - timedelta(days=day.weekday())


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """Return the first and last dates of `month` in `year`."""
    first = date(year, month, 1)
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last


def date_range(start: date, end: date) -> list[date]:
    """Return every date from `start` to `end` inclusive (empty if start > end)."""
    if start > end:
        return []
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def populate_dim_date(session: Session, start: date, end: date) -> int:
    """Fill `dim_date` for [start, end], skipping dates already present.

    Idempotent: safe to run on every migration and every seed. Returns the
    number of rows inserted.
    """
    if start > end:
        return 0

    existing = set(
        session.scalars(
            select(DimDate.date).where(DimDate.date >= start, DimDate.date <= end)
        ).all()
    )
    missing = [day for day in date_range(start, end) if day not in existing]
    if not missing:
        return 0

    session.execute(DimDate.__table__.insert(), [build_row(day) for day in missing])
    return len(missing)


def require_date_in_dimension(session: Session, day: date) -> None:
    """Raise :class:`~app.domain.errors.DateOutOfRange` if `day` is not in `dim_date`.

    Fact rows carry a foreign key to `dim_date`, so this turns what would be an
    opaque integrity error into a clear, actionable one.
    """
    from app.domain.errors import DateOutOfRange

    if session.get(DimDate, day) is None:
        raise DateOutOfRange(
            f"{day.isoformat()} is not in dim_date; extend DIM_DATE_START/DIM_DATE_END "
            "and re-run the date dimension population."
        )
