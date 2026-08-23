"""Ticking, un-ticking, and bonuses."""

from __future__ import annotations

from datetime import UTC, timedelta

import pytest
from sqlalchemy.orm import Session

from app import clock
from app.domain.errors import (
    EditWindowClosed,
    HabitAlreadyScheduled,
    HabitInactive,
    HabitNotOwned,
    HabitNotScheduled,
)
from app.domain.scheduling import ensure_day_materialised
from app.domain.tracking import add_bonus, complete_habit, get_fact, uncomplete_habit
from app.models import User
from tests.conftest import REFERENCE_MONDAY, TUESDAY, local_moment
from tests.test_scheduling import habit_named

TWO_DAYS_BEFORE = REFERENCE_MONDAY - timedelta(days=2)


def test_completing_sets_the_flag_and_the_timestamp(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    shower = habit_named(db, user_a, "Shower")
    moment = local_moment(REFERENCE_MONDAY, hour=7, minute=30)

    with clock.frozen_time(moment):
        fact = complete_habit(db, user_a, shower, REFERENCE_MONDAY)

    assert fact.completed is True
    assert fact.completed_at == moment.astimezone(UTC)
    assert fact.scheduled is True
    assert fact.is_bonus is False


def test_uncompleting_clears_the_flag_and_the_timestamp(
    db: Session, user_a: User
) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    shower = habit_named(db, user_a, "Shower")

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=7)):
        complete_habit(db, user_a, shower, REFERENCE_MONDAY)
        fact = uncomplete_habit(db, user_a, shower, REFERENCE_MONDAY)

    assert fact.completed is False
    assert fact.completed_at is None
    assert fact.scheduled is True


def test_completing_twice_keeps_the_first_timestamp(db: Session, user_a: User) -> None:
    """Tick order in the completed pile must not shuffle on a repeat tap."""
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    shower = habit_named(db, user_a, "Shower")
    first = local_moment(REFERENCE_MONDAY, hour=7)

    with clock.frozen_time(first):
        complete_habit(db, user_a, shower, REFERENCE_MONDAY)
    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=9)):
        fact = complete_habit(db, user_a, shower, REFERENCE_MONDAY)

    assert fact.completed_at == first.astimezone(UTC)


def test_mutations_are_refused_outside_the_edit_window(
    db: Session, user_a: User
) -> None:
    ensure_day_materialised(db, user_a, TWO_DAYS_BEFORE)
    shower = habit_named(db, user_a, "Shower")

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=10)):
        with pytest.raises(EditWindowClosed):
            complete_habit(db, user_a, shower, TWO_DAYS_BEFORE)
        with pytest.raises(EditWindowClosed):
            uncomplete_habit(db, user_a, shower, TWO_DAYS_BEFORE)
        with pytest.raises(EditWindowClosed):
            add_bonus(db, user_a, shower, TWO_DAYS_BEFORE)


def test_yesterday_can_still_be_caught_up(db: Session, user_a: User) -> None:
    yesterday = REFERENCE_MONDAY - timedelta(days=1)
    ensure_day_materialised(db, user_a, yesterday)
    reading = habit_named(db, user_a, "Reading")

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=8)):
        fact = complete_habit(db, user_a, reading, yesterday)

    assert fact.completed is True


def test_completing_an_unscheduled_habit_points_at_add_bonus(
    db: Session, user_a: User
) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    laundry = habit_named(db, user_a, "Laundry")  # Wednesdays and Saturdays only

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=10)):
        with pytest.raises(HabitNotScheduled):
            complete_habit(db, user_a, laundry, REFERENCE_MONDAY)


def test_a_bonus_creates_an_unscheduled_completed_row(
    db: Session, user_a: User
) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    laundry = habit_named(db, user_a, "Laundry")
    moment = local_moment(REFERENCE_MONDAY, hour=19)

    with clock.frozen_time(moment):
        fact = add_bonus(db, user_a, laundry, REFERENCE_MONDAY)

    assert fact.scheduled is False
    assert fact.is_bonus is True
    assert fact.completed is True
    assert fact.completed_at == moment.astimezone(UTC)


def test_a_bonus_on_a_scheduled_habit_is_refused(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    shower = habit_named(db, user_a, "Shower")

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=10)):
        with pytest.raises(HabitAlreadyScheduled):
            add_bonus(db, user_a, shower, REFERENCE_MONDAY)


def test_a_bonus_can_be_undone_and_relogged(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    laundry = habit_named(db, user_a, "Laundry")

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=19)):
        add_bonus(db, user_a, laundry, REFERENCE_MONDAY)
        undone = uncomplete_habit(db, user_a, laundry, REFERENCE_MONDAY)
        assert undone.completed is False
        assert undone.is_bonus is True

        relogged = add_bonus(db, user_a, laundry, REFERENCE_MONDAY)

    assert relogged.id == undone.id
    assert relogged.completed is True


def test_boards_stay_separate(db: Session, user_a: User, user_b: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    shower = habit_named(db, user_a, "Shower")

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=10)):
        with pytest.raises(HabitNotOwned):
            complete_habit(db, user_b, shower, REFERENCE_MONDAY)


def test_archived_habits_cannot_be_ticked(db: Session, user_a: User) -> None:
    """Archiving stops future ticking; it never deletes what came before."""
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    shower = habit_named(db, user_a, "Shower")

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=7)):
        complete_habit(db, user_a, shower, REFERENCE_MONDAY)

    shower.active = False
    shower.archived_at = local_moment(TUESDAY, hour=9)
    db.flush()

    with clock.frozen_time(local_moment(TUESDAY, hour=10)):
        with pytest.raises(HabitInactive):
            complete_habit(db, user_a, shower, TUESDAY)

    preserved = get_fact(db, user_a, shower, REFERENCE_MONDAY)
    assert preserved is not None
    assert preserved.completed is True
