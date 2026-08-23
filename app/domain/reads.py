"""Read models: today, one day, one week, one month.

Every percentage here is `completed_scheduled / total_scheduled` over rows where
`scheduled = True`. Completed-scheduled is a subset of scheduled, so the value
cannot exceed 1.0 — no clamping is needed, and none is done. When nothing was
scheduled the answer is `None` (a rest day), not zero: a day off is not a
failure, and the UI should not draw it as one.

These functions are pure reads. Callers that need today's rows to exist should
run :func:`app.domain.scheduling.backfill` first; Phase 2's API layer does that
on the way in.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.domain.dates import date_range, local_today, month_bounds, week_start
from app.domain.scheduling import active_habits
from app.domain.tracking import can_edit, is_locked
from app.models.fact import FactCompletion
from app.models.habit import Habit
from app.models.user import User
from app.schemas.views import (
    CompletedEntry,
    DayDetailView,
    HabitRef,
    MonthDayView,
    MonthHabitRate,
    MonthView,
    TodayView,
    WeekDayView,
    WeekView,
)


@dataclass(frozen=True)
class DayStats:
    """The three numbers every day-shaped view needs."""

    scheduled_count: int
    done_count: int
    completed_any: bool
    """True if anything at all was ticked, bonuses included. Drives `no_data`."""

    @property
    def pct(self) -> float | None:
        """Completed scheduled over total scheduled; `None` on a rest day."""
        if self.scheduled_count == 0:
            return None
        return self.done_count / self.scheduled_count


def _habit_ref(habit: Habit) -> HabitRef:
    """Flatten a habit and its bucket into the shape the UI consumes."""
    return HabitRef(
        id=habit.id,
        name=habit.name,
        bucket_id=habit.bucket_id,
        bucket_name=habit.bucket.name,
        bucket_color_hex=habit.bucket.color_hex,
        sort_order=habit.sort_order,
        anytime=habit.anytime,
        time_cap_minutes=habit.time_cap_minutes,
        season_dependent=habit.season_dependent,
    )


def _entry(fact: FactCompletion) -> CompletedEntry:
    """Build a completed-pile entry from a ticked fact row."""
    return CompletedEntry(
        habit=_habit_ref(fact.habit),
        completed_at=fact.completed_at,
        is_bonus=fact.is_bonus,
    )


def _display_key(habit: Habit) -> tuple[bool, int, int]:
    """Sort key for the active list: timed habits first, then hand-set order."""
    return (habit.anytime, habit.sort_order, habit.id)


def _facts_between(
    session: Session, user: User, start: date, end: date
) -> list[FactCompletion]:
    """Fetch this user's fact rows in [start, end], with habit and bucket loaded."""
    return list(
        session.scalars(
            select(FactCompletion)
            .options(joinedload(FactCompletion.habit).joinedload(Habit.bucket))
            .where(
                FactCompletion.user_id == user.id,
                FactCompletion.date >= start,
                FactCompletion.date <= end,
            )
            .order_by(FactCompletion.date, FactCompletion.id)
        )
        .unique()
        .all()
    )


def _stats(facts: list[FactCompletion]) -> DayStats:
    """Reduce one day's fact rows to its counts."""
    scheduled = [fact for fact in facts if fact.scheduled]
    return DayStats(
        scheduled_count=len(scheduled),
        done_count=sum(1 for fact in scheduled if fact.completed),
        completed_any=any(fact.completed for fact in facts),
    )


def _by_date(facts: list[FactCompletion]) -> dict[date, list[FactCompletion]]:
    """Group fact rows by their date."""
    grouped: dict[date, list[FactCompletion]] = defaultdict(list)
    for fact in facts:
        grouped[fact.date].append(fact)
    return grouped


def daily_pct(session: Session, user: User, day: date) -> float | None:
    """Return the day's completion fraction (0.0-1.0), or `None` if nothing was
    scheduled.

    Counts only `scheduled = True` rows, so bonuses are excluded and the value
    can never exceed 1.0.
    """
    return _stats(_facts_between(session, user, day, day)).pct


def get_today(session: Session, user: User, now: datetime | None = None) -> TodayView:
    """Build the home screen for the user's current local date.

    The active list is ordered by `(anytime, sort_order)` — timed habits in
    morning-to-night order, then the ones with no natural time. The completed
    pile is ordered by `completed_at`, so it stacks in the order things were
    actually ticked.
    """
    day = local_today(user, now)
    facts = _facts_between(session, user, day, day)
    stats = _stats(facts)

    outstanding = [fact.habit for fact in facts if fact.scheduled and not fact.completed]
    completed = sorted(
        (fact for fact in facts if fact.completed), key=lambda fact: fact.completed_at
    )

    recorded_habit_ids = {fact.habit_id for fact in facts}
    extras = [
        habit
        for habit in active_habits(session, user)
        if habit.id not in recorded_habit_ids
    ]

    return TodayView(
        date=day,
        editable=can_edit(user, day, now),
        active=[_habit_ref(habit) for habit in sorted(outstanding, key=_display_key)],
        completed=[_entry(fact) for fact in completed],
        daily_pct=stats.pct,
        done_count=stats.done_count,
        remaining_count=stats.scheduled_count - stats.done_count,
        available_extras=[_habit_ref(habit) for habit in extras],
        bonuses=[_entry(fact) for fact in completed if fact.is_bonus],
    )


def get_day_detail(
    session: Session, user: User, day: date, now: datetime | None = None
) -> DayDetailView:
    """Build the read-back view of a single day.

    `no_data` is True only when the day is locked *and* nothing was completed —
    the state the UI renders with the mascot. A locked 0% day is "no data"; an
    editable day that is merely unfinished is not, because it is still live.
    """
    facts = _facts_between(session, user, day, day)
    stats = _stats(facts)

    completed = sorted(
        (fact for fact in facts if fact.completed), key=lambda fact: fact.completed_at
    )
    missed = [fact.habit for fact in facts if fact.scheduled and not fact.completed]

    return DayDetailView(
        date=day,
        editable=can_edit(user, day, now),
        completed=[_entry(fact) for fact in completed],
        not_completed=[_habit_ref(habit) for habit in sorted(missed, key=_display_key)],
        bonuses=[_entry(fact) for fact in completed if fact.is_bonus],
        final_pct=stats.pct,
        no_data=is_locked(user, day, now) and not stats.completed_any,
    )


def get_week(
    session: Session, user: User, containing_date: date, now: datetime | None = None
) -> WeekView:
    """Build the Monday-to-Sunday overview of the week containing `containing_date`."""
    start = week_start(containing_date)
    end = start + timedelta(days=6)
    grouped = _by_date(_facts_between(session, user, start, end))

    days = []
    for day in date_range(start, end):
        stats = _stats(grouped.get(day, []))
        days.append(
            WeekDayView(
                date=day,
                weekday=day.weekday(),
                pct=stats.pct,
                scheduled_count=stats.scheduled_count,
                done_count=stats.done_count,
                editable=can_edit(user, day, now),
                locked_empty=is_locked(user, day, now) and not stats.completed_any,
            )
        )

    return WeekView(week_start=start, week_end=end, days=days)


def get_month(
    session: Session,
    user: User,
    year: int,
    month: int,
    now: datetime | None = None,
) -> MonthView:
    """Build the monthly view: per-habit completion rates plus calendar fills.

    Rates are derived from the fact rows themselves rather than from the user's
    current habit list, so a habit archived mid-month still reports the days it
    was actually scheduled. History stays honest.
    """
    first, last = month_bounds(year, month)
    facts = _facts_between(session, user, first, last)

    scheduled_totals: dict[int, int] = defaultdict(int)
    completed_totals: dict[int, int] = defaultdict(int)
    habits_seen: dict[int, Habit] = {}

    for fact in facts:
        if not fact.scheduled:
            continue
        habits_seen[fact.habit_id] = fact.habit
        scheduled_totals[fact.habit_id] += 1
        if fact.completed:
            completed_totals[fact.habit_id] += 1

    habit_rates = [
        MonthHabitRate(
            habit_id=habit.id,
            name=habit.name,
            bucket_name=habit.bucket.name,
            bucket_color_hex=habit.bucket.color_hex,
            scheduled_days=scheduled_totals[habit.id],
            completed_days=completed_totals[habit.id],
            rate=(
                completed_totals[habit.id] / scheduled_totals[habit.id]
                if scheduled_totals[habit.id]
                else None
            ),
        )
        for habit in sorted(habits_seen.values(), key=_display_key)
    ]

    grouped = _by_date(facts)
    days = []
    for day in date_range(first, last):
        stats = _stats(grouped.get(day, []))
        days.append(
            MonthDayView(
                date=day,
                pct=stats.pct,
                no_data=is_locked(user, day, now) and not stats.completed_any,
            )
        )

    return MonthView(year=year, month=month, habits=habit_rates, days=days)
