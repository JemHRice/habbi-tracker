"""Scheduling and day materialisation.

Materialising a day writes one `fact_completion` row per habit scheduled that
day, with `completed = False`. That is what turns "I didn't do it" into a
recorded fact instead of a gap in the data — and it is why the week and month
views are simple aggregations.

Materialisation only ever looks forward. Changing a habit's schedule, archiving
it, or flipping the season affects days not yet materialised and what current
reads show; it never reshapes a day that has already been written.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.dates import date_range, require_date_in_dimension, to_local_date
from app.models.fact import FactCompletion
from app.models.habit import Habit
from app.models.user import User


def is_scheduled(habit: Habit, day: date, *, season_active: bool) -> bool:
    """Return True if `habit` is expected on `day`.

    A habit is scheduled when it is active, the date's weekday is in its
    schedule, and — for season-dependent habits — the user's season is on.
    A season that is off simply removes those habits; it never penalises.
    """
    if not habit.active:
        return False
    if habit.season_dependent and not season_active:
        return False
    return day.weekday() in habit.scheduled_weekdays


def active_habits(session: Session, user: User) -> list[Habit]:
    """Return the user's non-archived habits, in display order."""
    return list(
        session.scalars(
            select(Habit)
            .where(Habit.user_id == user.id, Habit.active.is_(True))
            .order_by(Habit.anytime, Habit.sort_order, Habit.id)
        ).all()
    )


def scheduled_habits(session: Session, user: User, day: date) -> list[Habit]:
    """Return the user's habits expected on `day`, in display order."""
    return [
        habit
        for habit in active_habits(session, user)
        if is_scheduled(habit, day, season_active=user.season_active)
    ]


def ensure_day_materialised(session: Session, user: User, day: date) -> int:
    """Ensure a scheduled fact row exists for every habit expected on `day`.

    Idempotent: calling it repeatedly creates no duplicates, guarded both by a
    pre-check and by the unique constraint on (user, habit, date). Returns the
    number of rows created.

    Raises:
        DateOutOfRange: if `day` is not present in `dim_date`.
    """
    require_date_in_dimension(session, day)

    already_recorded = set(
        session.scalars(
            select(FactCompletion.habit_id).where(
                FactCompletion.user_id == user.id, FactCompletion.date == day
            )
        ).all()
    )

    created = 0
    for habit in scheduled_habits(session, user, day):
        if habit.id in already_recorded:
            continue
        row = FactCompletion(
            user_id=user.id,
            habit_id=habit.id,
            date=day,
            scheduled=True,
            completed=False,
            is_bonus=False,
        )
        try:
            # A savepoint per row means a concurrent writer that beat us to this
            # habit costs us that one row, not the whole day.
            with session.begin_nested():
                session.add(row)
        except IntegrityError:
            continue
        created += 1

    return created


def last_materialised_date(session: Session, user: User) -> date | None:
    """Return the most recent date this user has any fact row for."""
    return session.scalar(
        select(func.max(FactCompletion.date)).where(FactCompletion.user_id == user.id)
    )


def backfill(
    session: Session, user: User, through_date: date, *, max_days: int | None = None
) -> int:
    """Materialise every day from the user's last materialised day to `through_date`.

    Someone who does not open the app for a week still ends up with correct
    "scheduled but not completed" rows for those days. Idempotent, and capped at
    `max_days` (default `settings.backfill_max_days`) so a long-dormant account
    cannot generate an unbounded amount of work. Returns rows created.

    The window never starts before the user existed, and habits are evaluated
    with their *current* schedule — the honest limit of a forward-only model.
    """
    cap = max_days if max_days is not None else get_settings().backfill_max_days
    created_on = to_local_date(user, user.created_at)
    last = last_materialised_date(session, user)

    start = last + timedelta(days=1) if last is not None else created_on
    start = max(start, created_on, through_date - timedelta(days=cap - 1))

    return sum(
        ensure_day_materialised(session, user, day)
        for day in date_range(start, through_date)
    )
