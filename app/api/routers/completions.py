"""Ticking, un-ticking and bonuses.

All three return the live view of the date they changed, so the client can
settle an optimistic update without a second round trip: a `TodayView` when the
date is the user's today, a `DayDetailView` when it is yesterday being caught
up. Clients discriminate on the `kind` field.

The edit window is not re-checked here. The domain function raises
`EditWindowClosed` and the handler in `app/api/errors.py` turns it into
`403 EDIT_WINDOW_LOCKED` — one rule, one place.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession, bring_up_to_date
from app.api.schemas import CompletionRequest
from app.domain.habits import get_habit
from app.domain.reads import get_day_detail, get_today
from app.domain.tracking import add_bonus, complete_habit, uncomplete_habit
from app.models.user import User
from app.schemas.views import DayView

router = APIRouter(prefix="/completions", tags=["completions"])


def _view_of(session: Session, user: User, day: date, today: date) -> DayView:
    """Return the freshest view of `day` for the client to render."""
    if day == today:
        return get_today(session, user)
    return get_day_detail(session, user, day)


@router.post("", response_model=DayView)
def complete(
    payload: CompletionRequest, session: DbSession, user: CurrentUser
) -> DayView:
    """Tick a scheduled habit off for a date.

    Completing a habit that was *not* scheduled that day is a bonus, not a
    completion, and is refused here — use `POST /completions/bonus`.
    """
    today = bring_up_to_date(session, user)
    habit = get_habit(session, user, payload.habit_id, include_archived=False)
    complete_habit(session, user, habit, payload.date)
    return _view_of(session, user, payload.date, today)


@router.delete("", response_model=DayView)
def uncomplete(
    payload: CompletionRequest, session: DbSession, user: CurrentUser
) -> DayView:
    """Un-tick a habit, returning it to the active list."""
    today = bring_up_to_date(session, user)
    habit = get_habit(session, user, payload.habit_id, include_archived=False)
    uncomplete_habit(session, user, habit, payload.date)
    return _view_of(session, user, payload.date, today)


@router.post("/bonus", response_model=DayView)
def bonus(
    payload: CompletionRequest, session: DbSession, user: CurrentUser
) -> DayView:
    """Log "something extra": a habit completed on a day it was not scheduled.

    Bonuses join the completed pile but are excluded from the daily percentage —
    doing more than the day asked for is a bonus outside the count, never a way
    past 100%.
    """
    today = bring_up_to_date(session, user)
    habit = get_habit(session, user, payload.habit_id, include_archived=False)
    add_bonus(session, user, habit, payload.date)
    return _view_of(session, user, payload.date, today)
