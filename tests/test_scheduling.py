"""Scheduling, materialisation, backfill, and the season toggle."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import clock
from app.domain.errors import DateOutOfRange
from app.domain.scheduling import (
    backfill,
    ensure_day_materialised,
    is_scheduled,
    last_materialised_date,
    scheduled_habits,
)
from app.models import FactCompletion, Habit, User
from tests.conftest import (
    REFERENCE_MONDAY,
    SATURDAY,
    SEED_MOMENT,
    TUESDAY,
    local_moment,
)


def habit_named(db: Session, user: User, name: str) -> Habit:
    """Fetch one of the user's habits by name."""
    return db.scalars(
        select(Habit).where(Habit.user_id == user.id, Habit.name == name)
    ).one()


def fact_count(db: Session, user: User, day) -> int:
    """Count this user's fact rows on a date."""
    return db.scalar(
        select(func.count())
        .select_from(FactCompletion)
        .where(FactCompletion.user_id == user.id, FactCompletion.date == day)
    )


# --- is_scheduled ---------------------------------------------------------


def test_is_scheduled_follows_the_weekday_set(db: Session, user_a: User) -> None:
    laundry = habit_named(db, user_a, "Laundry")  # Wednesdays and Saturdays

    assert is_scheduled(laundry, REFERENCE_MONDAY + timedelta(days=2), season_active=False)
    assert is_scheduled(laundry, SATURDAY, season_active=False)
    assert not is_scheduled(laundry, REFERENCE_MONDAY, season_active=False)


def test_season_dependent_habits_need_the_season_on(db: Session, user_a: User) -> None:
    training = habit_named(db, user_a, "Team training")  # Tuesdays, season-dependent

    assert not is_scheduled(training, TUESDAY, season_active=False)
    assert is_scheduled(training, TUESDAY, season_active=True)


def test_season_off_does_not_affect_ordinary_habits(db: Session, user_a: User) -> None:
    reading = habit_named(db, user_a, "Reading")

    assert is_scheduled(reading, TUESDAY, season_active=False)
    assert is_scheduled(reading, TUESDAY, season_active=True)


def test_archived_habits_are_never_scheduled(db: Session, user_a: User) -> None:
    reading = habit_named(db, user_a, "Reading")
    reading.active = False
    reading.archived_at = SEED_MOMENT
    db.flush()

    assert not is_scheduled(reading, TUESDAY, season_active=False)


# --- materialisation ------------------------------------------------------


def test_materialising_writes_a_row_per_scheduled_habit(
    db: Session, user_a: User
) -> None:
    expected = len(scheduled_habits(db, user_a, REFERENCE_MONDAY))

    created = ensure_day_materialised(db, user_a, REFERENCE_MONDAY)

    assert created == expected
    assert fact_count(db, user_a, REFERENCE_MONDAY) == expected

    rows = db.scalars(
        select(FactCompletion).where(FactCompletion.date == REFERENCE_MONDAY)
    ).all()
    assert all(row.scheduled for row in rows)
    assert not any(row.completed for row in rows)
    assert not any(row.is_bonus for row in rows)


def test_materialising_is_idempotent(db: Session, user_a: User) -> None:
    first = ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    second = ensure_day_materialised(db, user_a, REFERENCE_MONDAY)

    assert first > 0
    assert second == 0
    assert fact_count(db, user_a, REFERENCE_MONDAY) == first


def test_materialising_respects_the_season_toggle(db: Session, user_a: User) -> None:
    off = len(scheduled_habits(db, user_a, TUESDAY))

    user_a.season_active = True
    db.flush()
    on = len(scheduled_habits(db, user_a, TUESDAY))

    assert on == off + 1  # "Team training" joins the day


def test_flipping_the_season_does_not_rewrite_a_materialised_day(
    db: Session, user_a: User
) -> None:
    """Rule 9: the toggle affects future materialisation and current reads only."""
    ensure_day_materialised(db, user_a, TUESDAY)
    before = fact_count(db, user_a, TUESDAY)

    user_a.season_active = True
    db.flush()

    assert fact_count(db, user_a, TUESDAY) == before


def test_an_empty_board_materialises_nothing(db: Session, user_b: User) -> None:
    assert ensure_day_materialised(db, user_b, REFERENCE_MONDAY) == 0
    assert fact_count(db, user_b, REFERENCE_MONDAY) == 0


def test_materialising_a_date_outside_dim_date_is_refused(
    db: Session, user_a: User
) -> None:
    from datetime import date

    with pytest.raises(DateOutOfRange):
        ensure_day_materialised(db, user_a, date(2031, 1, 1))


# --- backfill -------------------------------------------------------------


def test_backfill_fills_the_gap_since_the_last_materialised_day(
    db: Session, user_a: User
) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    through = REFERENCE_MONDAY + timedelta(days=4)

    backfill(db, user_a, through)

    days = set(
        db.scalars(
            select(FactCompletion.date).where(FactCompletion.user_id == user_a.id)
        ).all()
    )
    assert {REFERENCE_MONDAY + timedelta(days=offset) for offset in range(5)} <= days
    assert last_materialised_date(db, user_a) == through


def test_backfill_is_idempotent(db: Session, user_a: User) -> None:
    through = REFERENCE_MONDAY + timedelta(days=3)

    first = backfill(db, user_a, through)
    second = backfill(db, user_a, through)

    assert first > 0
    assert second == 0


def test_backfill_never_starts_before_the_user_existed(
    db: Session, user_a: User
) -> None:
    backfill(db, user_a, REFERENCE_MONDAY)

    earliest = db.scalar(
        select(func.min(FactCompletion.date)).where(FactCompletion.user_id == user_a.id)
    )
    assert earliest == SEED_MOMENT.date()


def test_backfill_is_capped(db: Session, user_a: User) -> None:
    """A long-dormant account cannot trigger unbounded generation."""
    through = REFERENCE_MONDAY + timedelta(days=200)

    backfill(db, user_a, through, max_days=5)

    days = sorted(
        set(
            db.scalars(
                select(FactCompletion.date).where(FactCompletion.user_id == user_a.id)
            ).all()
        )
    )
    assert days[0] == through - timedelta(days=4)
    assert days[-1] == through
    assert len(days) == 5


def test_backfill_uses_the_configured_cap_by_default() -> None:
    from app.config import get_settings

    assert get_settings().backfill_max_days == 60


def test_backfill_uses_the_clock_when_no_date_is_given(
    db: Session, user_a: User
) -> None:
    """The caller derives "today" from the user's timezone, not the server's."""
    from app.domain.dates import local_today

    with clock.frozen_time(local_moment(TUESDAY, hour=7)):
        today = local_today(user_a)
        backfill(db, user_a, today)

    assert last_materialised_date(db, user_a) == TUESDAY
