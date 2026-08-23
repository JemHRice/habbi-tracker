"""Ticking habits off, and the edit window that bounds it.

Today and yesterday (in the user's timezone) can be edited; everything older is
locked. That is enough slack to catch up a forgotten evening without letting
history be rewritten — the one rule that makes every past number trustworthy.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.domain.dates import local_today, require_date_in_dimension
from app.domain.errors import (
    EditWindowClosed,
    HabitAlreadyScheduled,
    HabitInactive,
    HabitNotOwned,
    HabitNotScheduled,
)
from app.models.fact import FactCompletion
from app.models.habit import Habit
from app.models.user import User


def can_edit(user: User, day: date, now: datetime | None = None) -> bool:
    """Return True if `day` is today or yesterday in the user's timezone.

    Future dates are not editable either: you cannot tick tomorrow off early.
    """
    today = local_today(user, now)
    return today - timedelta(days=1) <= day <= today


def is_locked(user: User, day: date, now: datetime | None = None) -> bool:
    """Return True if `day` is in the past and beyond the edit window."""
    return day < local_today(user, now) - timedelta(days=1)


def require_editable(user: User, day: date, now: datetime | None = None) -> None:
    """Raise :class:`~app.domain.errors.EditWindowClosed` unless `day` is editable."""
    if not can_edit(user, day, now):
        raise EditWindowClosed(
            f"{day.isoformat()} is outside the edit window for user {user.id}; "
            "only today and yesterday can be changed."
        )


def _require_own_active_habit(user: User, habit: Habit) -> None:
    """Guard that `habit` is this user's and has not been archived."""
    if habit.user_id != user.id:
        raise HabitNotOwned(f"habit {habit.id} does not belong to user {user.id}")
    if not habit.active:
        raise HabitInactive(f"habit {habit.id} is archived and cannot be ticked")


def get_fact(
    session: Session, user: User, habit: Habit, day: date
) -> FactCompletion | None:
    """Return the fact row for this (user, habit, date), or None."""
    return session.scalar(
        select(FactCompletion).where(
            FactCompletion.user_id == user.id,
            FactCompletion.habit_id == habit.id,
            FactCompletion.date == day,
        )
    )


def complete_habit(
    session: Session, user: User, habit: Habit, day: date, now: datetime | None = None
) -> FactCompletion:
    """Tick a habit off for `day`, setting `completed_at`.

    Idempotent: completing something already complete leaves the original
    `completed_at` alone, so the tick order in the completed pile is stable.

    Raises:
        EditWindowClosed: if `day` is not today or yesterday.
        HabitNotOwned / HabitInactive: if the habit is not this user's live habit.
        HabitNotScheduled: if no row exists for that day — use
            :func:`add_bonus` to log something that was not expected.
    """
    moment = clock.resolve_now(now)
    require_editable(user, day, moment)
    _require_own_active_habit(user, habit)

    fact = get_fact(session, user, habit, day)
    if fact is None:
        raise HabitNotScheduled(
            f"habit {habit.id} has no row on {day.isoformat()}; use add_bonus() "
            "to log it as a bonus."
        )

    if not fact.completed:
        fact.completed = True
        fact.completed_at = moment
        session.flush()
    return fact


def uncomplete_habit(
    session: Session, user: User, habit: Habit, day: date, now: datetime | None = None
) -> FactCompletion:
    """Un-tick a habit for `day`, clearing `completed_at`.

    A scheduled row returns to the active list. A bonus row stays on disk as an
    inert `scheduled=False, completed=False` record that no read surfaces;
    logging the bonus again simply re-completes that same row.

    Raises:
        EditWindowClosed, HabitNotOwned, HabitInactive, HabitNotScheduled: as
        for :func:`complete_habit`.
    """
    moment = clock.resolve_now(now)
    require_editable(user, day, moment)
    _require_own_active_habit(user, habit)

    fact = get_fact(session, user, habit, day)
    if fact is None:
        raise HabitNotScheduled(
            f"habit {habit.id} has no row on {day.isoformat()}; nothing to undo."
        )

    if fact.completed:
        fact.completed = False
        fact.completed_at = None
        session.flush()
    return fact


def add_bonus(
    session: Session, user: User, habit: Habit, day: date, now: datetime | None = None
) -> FactCompletion:
    """Log a habit completed on a day it was not scheduled — "something extra".

    Creates a `scheduled=False, is_bonus=True, completed=True` row. Bonuses are
    excluded from the daily percentage on purpose: doing more than the day asked
    for is a bonus *outside* the count, never a way to push past 100%.

    Raises:
        EditWindowClosed: if `day` is not today or yesterday.
        HabitNotOwned / HabitInactive: if the habit is not this user's live habit.
        HabitAlreadyScheduled: if the habit *was* expected that day — that is a
            normal completion, so use :func:`complete_habit`.
        DateOutOfRange: if `day` is not present in `dim_date`.
    """
    moment = clock.resolve_now(now)
    require_editable(user, day, moment)
    _require_own_active_habit(user, habit)
    require_date_in_dimension(session, day)

    fact = get_fact(session, user, habit, day)
    if fact is not None:
        if fact.scheduled:
            raise HabitAlreadyScheduled(
                f"habit {habit.id} was scheduled on {day.isoformat()}; "
                "use complete_habit()."
            )
        if not fact.completed:
            fact.completed = True
            fact.completed_at = moment
            session.flush()
        return fact

    fact = FactCompletion(
        user_id=user.id,
        habit_id=habit.id,
        date=day,
        scheduled=False,
        completed=True,
        completed_at=moment,
        is_bonus=True,
    )
    session.add(fact)
    session.flush()
    return fact
