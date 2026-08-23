"""Habit management: creating, editing, rescheduling, reordering, archiving.

Two rules govern everything here, and they are the same two that govern the
rest of the app:

* **Archive, never delete.** Removing a habit sets `active = False` and
  `archived_at`. Every `fact_completion` row it ever produced survives, so past
  weeks and months keep telling the truth.
* **Edits are forward-only.** Changing a habit's schedule or attributes affects
  future materialisation and current reads. Days already materialised keep
  exactly the rows they had — a week in progress is never reshaped underneath
  the person living it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.domain.buckets import get_bucket
from app.domain.errors import DomainError, HabitNotFound
from app.models.habit import Habit, HabitSchedule
from app.models.user import User

VALID_WEEKDAYS = frozenset(range(7))


class InvalidSchedule(DomainError):
    """The weekday set is not a subset of 0-6 (Monday to Sunday)."""


def _clean_weekdays(weekdays: Iterable[int]) -> list[int]:
    """Validate and normalise a weekday set to a sorted, de-duplicated list."""
    unique = set(weekdays)
    if not unique <= VALID_WEEKDAYS:
        raise InvalidSchedule("weekdays must be integers 0 (Monday) to 6 (Sunday)")
    return sorted(unique)


def list_habits(
    session: Session, user: User, *, include_archived: bool = False
) -> list[Habit]:
    """Return the user's habits in display order.

    Archived habits are excluded unless asked for; they no longer belong on a
    board, even though their history does.
    """
    statement = select(Habit).where(Habit.user_id == user.id)
    if not include_archived:
        statement = statement.where(Habit.active.is_(True))
    return list(
        session.scalars(
            statement.order_by(Habit.anytime, Habit.sort_order, Habit.id)
        ).all()
    )


def get_habit(
    session: Session, user: User, habit_id: int, *, include_archived: bool = True
) -> Habit:
    """Return one of the user's habits.

    Raises:
        HabitNotFound: if it does not exist *or* belongs to someone else — the
            two are deliberately indistinguishable, so one board cannot probe
            for the existence of rows on the other.
    """
    statement = select(Habit).where(Habit.id == habit_id, Habit.user_id == user.id)
    if not include_archived:
        statement = statement.where(Habit.active.is_(True))
    habit = session.scalar(statement)
    if habit is None:
        raise HabitNotFound(f"no habit {habit_id} on this board")
    return habit


def create_habit(
    session: Session,
    user: User,
    *,
    bucket_id: int,
    name: str,
    target_per_week: int,
    weekdays: Iterable[int],
    sort_order: int,
    time_cap_minutes: int | None = None,
    season_dependent: bool = False,
    anytime: bool = False,
) -> Habit:
    """Add a habit to the user's board, with its scheduled weekdays.

    The habit starts being materialised from the next day materialisation
    onward; it does not appear on days already written.

    Raises:
        BucketNotFound: if the bucket is not this user's.
        InvalidSchedule: if the weekday set is out of range.
    """
    bucket = get_bucket(session, user, bucket_id)
    days = _clean_weekdays(weekdays)

    habit = Habit(
        user_id=user.id,
        bucket_id=bucket.id,
        name=name,
        target_per_week=target_per_week,
        time_cap_minutes=time_cap_minutes,
        season_dependent=season_dependent,
        sort_order=sort_order,
        anytime=anytime,
        active=True,
    )
    session.add(habit)
    session.flush()

    for weekday in days:
        session.add(HabitSchedule(habit_id=habit.id, weekday=weekday))
    session.flush()
    return habit


def update_habit(
    session: Session,
    user: User,
    habit_id: int,
    *,
    bucket_id: int | None = None,
    name: str | None = None,
    target_per_week: int | None = None,
    time_cap_minutes: int | None = None,
    season_dependent: bool | None = None,
    sort_order: int | None = None,
    anytime: bool | None = None,
    clear_time_cap: bool = False,
) -> Habit:
    """Edit a habit's attributes. Only the given fields change.

    Forward-only: this changes what gets materialised from now on and what
    current reads show. Days already materialised are untouched.

    Args:
        clear_time_cap: explicitly set `time_cap_minutes` to null, which a
            plain `None` cannot express (it means "leave alone").

    Raises:
        HabitNotFound: if it is not this user's habit.
        BucketNotFound: if moving it to a bucket that is not this user's.
    """
    habit = get_habit(session, user, habit_id)

    if bucket_id is not None:
        habit.bucket_id = get_bucket(session, user, bucket_id).id
    if name is not None:
        habit.name = name
    if target_per_week is not None:
        habit.target_per_week = target_per_week
    if clear_time_cap:
        habit.time_cap_minutes = None
    elif time_cap_minutes is not None:
        habit.time_cap_minutes = time_cap_minutes
    if season_dependent is not None:
        habit.season_dependent = season_dependent
    if sort_order is not None:
        habit.sort_order = sort_order
    if anytime is not None:
        habit.anytime = anytime

    session.flush()
    return habit


def set_schedule(
    session: Session, user: User, habit_id: int, weekdays: Iterable[int]
) -> Habit:
    """Replace a habit's scheduled weekdays.

    Forward-only, like every other habit edit: an already-materialised day keeps
    the rows it had, even if the habit is no longer scheduled on that weekday.

    Raises:
        HabitNotFound: if it is not this user's habit.
        InvalidSchedule: if the weekday set is out of range.
    """
    habit = get_habit(session, user, habit_id)
    days = _clean_weekdays(weekdays)

    habit.schedules.clear()
    session.flush()
    for weekday in days:
        session.add(HabitSchedule(habit_id=habit.id, weekday=weekday))
    session.flush()
    session.refresh(habit)
    return habit


def archive_habit(
    session: Session, user: User, habit_id: int, now: datetime | None = None
) -> Habit:
    """Archive a habit: a soft delete that preserves every past fact row.

    The habit stops being scheduled and materialised from here on and drops off
    the board, but week and month views still show what it recorded. There is no
    hard delete anywhere in this app. Archiving twice is harmless.

    Raises:
        HabitNotFound: if it is not this user's habit.
    """
    habit = get_habit(session, user, habit_id)
    if habit.active:
        habit.active = False
        habit.archived_at = clock.resolve_now(now)
        session.flush()
    return habit


def reorder_habits(
    session: Session, user: User, ordering: Sequence[tuple[int, int]]
) -> list[Habit]:
    """Apply new `sort_order` values in one batch.

    `sort_order` is display-only — it never touches `fact_completion` — so
    reordering cannot distort any past percentage.

    Args:
        ordering: `(habit_id, sort_order)` pairs.

    Returns:
        The user's active habits in their new order.

    Raises:
        HabitNotFound: if any id is not this user's habit; nothing is applied.
    """
    habits = [(get_habit(session, user, habit_id), order) for habit_id, order in ordering]
    for habit, order in habits:
        habit.sort_order = order
    session.flush()
    return list_habits(session, user)
