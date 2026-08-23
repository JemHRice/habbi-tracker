"""The board reads: today, one day, one week, one month.

Each of these brings the user up to date first (see
:func:`app.api.deps.bring_up_to_date`), so the frontend never sees a gap caused
by a day that was simply never generated.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Path, Query

from app.api.deps import CurrentUser, DbSession, bring_up_to_date
from app.domain.reads import get_day_detail, get_month, get_today, get_week
from app.schemas.views import DayDetailView, MonthView, TodayView, WeekView

router = APIRouter(tags=["board"])


@router.get("/today", response_model=TodayView)
def read_today(session: DbSession, user: CurrentUser) -> TodayView:
    """The home screen for the user's current local date."""
    bring_up_to_date(session, user)
    return get_today(session, user)


@router.get("/days/{day}", response_model=DayDetailView)
def read_day(
    session: DbSession,
    user: CurrentUser,
    day: date = Path(description="Calendar date as YYYY-MM-DD"),
) -> DayDetailView:
    """One day in detail: what was and was not done, and its final percentage."""
    bring_up_to_date(session, user)
    return get_day_detail(session, user, day)


@router.get("/weeks", response_model=WeekView)
def read_week(
    session: DbSession,
    user: CurrentUser,
    containing_date: date | None = Query(
        default=None, description="Any date in the week. Defaults to today."
    ),
) -> WeekView:
    """The Monday-to-Sunday overview of the week containing a date."""
    today = bring_up_to_date(session, user)
    return get_week(session, user, containing_date or today)


@router.get("/months/{year}/{month}", response_model=MonthView)
def read_month(
    session: DbSession,
    user: CurrentUser,
    year: int = Path(ge=1970, le=9999),
    month: int = Path(ge=1, le=12),
) -> MonthView:
    """Per-habit completion rates for a month, plus the calendar fill values."""
    bring_up_to_date(session, user)
    return get_month(session, user, year, month)
