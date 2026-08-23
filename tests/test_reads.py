"""The read models: today, one day, one week, one month."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.domain.reads import (
    daily_pct,
    get_day_detail,
    get_month,
    get_today,
    get_week,
)
from app.domain.scheduling import ensure_day_materialised, scheduled_habits
from app.domain.tracking import add_bonus, complete_habit
from app.models import FactCompletion, User
from tests.conftest import REFERENCE_MONDAY, SUNDAY, local_moment
from tests.test_scheduling import habit_named

WEDNESDAY = REFERENCE_MONDAY + timedelta(days=2)
SATURDAY = REFERENCE_MONDAY + timedelta(days=5)
NEXT_MONDAY = REFERENCE_MONDAY + timedelta(days=7)


def complete_all_scheduled(db: Session, user: User, day: date) -> int:
    """Tick every scheduled habit on `day`. Returns how many were ticked."""
    facts = db.scalars(
        select(FactCompletion).where(
            FactCompletion.user_id == user.id,
            FactCompletion.date == day,
            FactCompletion.scheduled.is_(True),
        )
    ).all()
    for index, fact in enumerate(facts):
        with clock.frozen_time(local_moment(day, hour=6, minute=index)):
            complete_habit(db, user, fact.habit, day)
    return len(facts)


# --- daily percentage -----------------------------------------------------


def test_an_untouched_day_is_zero_not_null(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)

    assert daily_pct(db, user_a, REFERENCE_MONDAY) == 0.0


def test_a_finished_day_is_exactly_one(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    complete_all_scheduled(db, user_a, REFERENCE_MONDAY)

    assert daily_pct(db, user_a, REFERENCE_MONDAY) == 1.0


def test_the_percentage_caps_at_one_even_with_bonuses(
    db: Session, user_a: User
) -> None:
    """Rule 7: bonuses sit outside the count, so 100% is the ceiling."""
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    complete_all_scheduled(db, user_a, REFERENCE_MONDAY)

    laundry = habit_named(db, user_a, "Laundry")  # not scheduled on a Monday
    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=20)):
        add_bonus(db, user_a, laundry, REFERENCE_MONDAY)

    assert daily_pct(db, user_a, REFERENCE_MONDAY) == 1.0


def test_a_bonus_never_moves_a_partial_percentage(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    scheduled_count = len(scheduled_habits(db, user_a, REFERENCE_MONDAY))
    shower = habit_named(db, user_a, "Shower")
    laundry = habit_named(db, user_a, "Laundry")

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=7)):
        complete_habit(db, user_a, shower, REFERENCE_MONDAY)
    before = daily_pct(db, user_a, REFERENCE_MONDAY)

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=20)):
        add_bonus(db, user_a, laundry, REFERENCE_MONDAY)

    assert before == 1 / scheduled_count
    assert daily_pct(db, user_a, REFERENCE_MONDAY) == before


def test_a_day_with_nothing_scheduled_is_null_not_zero(
    db: Session, user_b: User
) -> None:
    """A rest day is not a failed day, so it has no percentage at all."""
    ensure_day_materialised(db, user_b, REFERENCE_MONDAY)

    assert daily_pct(db, user_b, REFERENCE_MONDAY) is None


# --- get_today ------------------------------------------------------------


def test_today_lists_outstanding_habits_in_display_order(
    db: Session, user_a: User
) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=6)):
        view = get_today(db, user_a)

    keys = [(habit.anytime, habit.sort_order) for habit in view.active]
    assert keys == sorted(keys)
    assert view.active[-2].name == "Water through the day"
    assert view.active[-1].name == "Daily check-in"
    assert all(not habit.anytime for habit in view.active[:-2])


def test_today_stacks_the_completed_pile_in_tick_order(
    db: Session, user_a: User
) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    ticks = ["Full night's sleep", "Shower", "Focused project work"]

    for index, name in enumerate(ticks):
        with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=7, minute=index)):
            complete_habit(db, user_a, habit_named(db, user_a, name), REFERENCE_MONDAY)

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=8)):
        view = get_today(db, user_a)

    assert [entry.habit.name for entry in view.completed] == ticks
    assert [entry.completed_at for entry in view.completed] == sorted(
        entry.completed_at for entry in view.completed
    )


def test_today_counts_done_and_remaining(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    total = len(scheduled_habits(db, user_a, REFERENCE_MONDAY))

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=7)):
        complete_habit(
            db, user_a, habit_named(db, user_a, "Shower"), REFERENCE_MONDAY
        )
        view = get_today(db, user_a)

    assert view.done_count == 1
    assert view.remaining_count == total - 1
    assert len(view.active) == total - 1
    assert view.daily_pct == 1 / total
    assert view.editable is True


def test_today_offers_unscheduled_habits_as_extras(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    scheduled = {habit.name for habit in scheduled_habits(db, user_a, REFERENCE_MONDAY)}

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=6)):
        view = get_today(db, user_a)

    extras = {habit.name for habit in view.available_extras}
    assert extras and extras.isdisjoint(scheduled)
    assert "Laundry" in extras


def test_a_logged_bonus_leaves_the_extras_picker(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    laundry = habit_named(db, user_a, "Laundry")

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=20)):
        add_bonus(db, user_a, laundry, REFERENCE_MONDAY)
        view = get_today(db, user_a)

    assert "Laundry" not in {habit.name for habit in view.available_extras}
    assert [entry.habit.name for entry in view.bonuses] == ["Laundry"]
    assert view.bonuses[0].is_bonus is True
    assert "Laundry" in {entry.habit.name for entry in view.completed}
    assert view.done_count == 0  # the bonus is outside the count


def test_today_on_an_empty_board_is_a_rest_day(db: Session, user_b: User) -> None:
    ensure_day_materialised(db, user_b, REFERENCE_MONDAY)

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=9)):
        view = get_today(db, user_b)

    assert view.daily_pct is None
    assert view.active == []
    assert view.completed == []
    assert view.done_count == 0
    assert view.remaining_count == 0


def test_today_carries_the_bucket_colour_for_rendering(
    db: Session, user_a: User
) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=6)):
        view = get_today(db, user_a)

    shower = next(habit for habit in view.active if habit.name == "Shower")
    assert shower.bucket_name == "Self-care"
    assert shower.bucket_color_hex == "#CA758A"


# --- get_day_detail -------------------------------------------------------


def test_a_locked_empty_day_reads_as_no_data(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)

    with clock.frozen_time(local_moment(REFERENCE_MONDAY + timedelta(days=3), hour=9)):
        view = get_day_detail(db, user_a, REFERENCE_MONDAY)

    assert view.no_data is True
    assert view.final_pct == 0.0
    assert view.editable is False
    assert view.completed == []
    assert len(view.not_completed) == len(
        scheduled_habits(db, user_a, REFERENCE_MONDAY)
    )


def test_an_editable_unfinished_day_is_not_no_data(db: Session, user_a: User) -> None:
    """Rule 8: today is still live, so nothing about it reads as absent."""
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=9)):
        view = get_day_detail(db, user_a, REFERENCE_MONDAY)

    assert view.no_data is False
    assert view.editable is True


def test_a_locked_day_with_only_a_bonus_is_not_no_data(
    db: Session, user_a: User
) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    laundry = habit_named(db, user_a, "Laundry")

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=20)):
        add_bonus(db, user_a, laundry, REFERENCE_MONDAY)

    with clock.frozen_time(local_moment(REFERENCE_MONDAY + timedelta(days=3), hour=9)):
        view = get_day_detail(db, user_a, REFERENCE_MONDAY)

    assert view.no_data is False
    assert view.final_pct == 0.0
    assert [entry.habit.name for entry in view.bonuses] == ["Laundry"]


def test_day_detail_splits_done_from_not_done(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    total = len(scheduled_habits(db, user_a, REFERENCE_MONDAY))

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=7)):
        complete_habit(db, user_a, habit_named(db, user_a, "Shower"), REFERENCE_MONDAY)

    with clock.frozen_time(local_moment(REFERENCE_MONDAY + timedelta(days=3), hour=9)):
        view = get_day_detail(db, user_a, REFERENCE_MONDAY)

    assert [entry.habit.name for entry in view.completed] == ["Shower"]
    assert len(view.not_completed) == total - 1
    assert "Shower" not in {habit.name for habit in view.not_completed}
    assert view.final_pct == 1 / total


# --- get_week -------------------------------------------------------------


def test_a_week_runs_monday_to_sunday(db: Session, user_a: User) -> None:
    with clock.frozen_time(local_moment(WEDNESDAY, hour=9)):
        view = get_week(db, user_a, WEDNESDAY)

    assert view.week_start == REFERENCE_MONDAY
    assert view.week_end == SUNDAY
    assert len(view.days) == 7
    assert [day.weekday for day in view.days] == list(range(7))
    assert [day.date for day in view.days] == [
        REFERENCE_MONDAY + timedelta(days=offset) for offset in range(7)
    ]


def test_the_week_reports_each_days_percentage(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    ensure_day_materialised(db, user_a, WEDNESDAY)
    complete_all_scheduled(db, user_a, REFERENCE_MONDAY)

    with clock.frozen_time(local_moment(NEXT_MONDAY, hour=9)):
        view = get_week(db, user_a, WEDNESDAY)

    by_date = {day.date: day for day in view.days}
    assert by_date[REFERENCE_MONDAY].pct == 1.0
    assert by_date[REFERENCE_MONDAY].locked_empty is False
    assert by_date[WEDNESDAY].pct == 0.0
    assert by_date[WEDNESDAY].locked_empty is True


def test_a_day_never_materialised_reads_as_locked_empty(
    db: Session, user_a: User
) -> None:
    with clock.frozen_time(local_moment(NEXT_MONDAY, hour=9)):
        view = get_week(db, user_a, WEDNESDAY)

    assert all(day.pct is None for day in view.days)
    # Sunday is yesterday, so it is still editable and never reads as absent.
    assert [day.locked_empty for day in view.days] == [True] * 6 + [False]
    assert view.days[-1].date == SUNDAY


def test_the_current_week_marks_editable_days(db: Session, user_a: User) -> None:
    with clock.frozen_time(local_moment(WEDNESDAY, hour=9)):
        view = get_week(db, user_a, WEDNESDAY)

    editable = {day.date for day in view.days if day.editable}
    assert editable == {WEDNESDAY, WEDNESDAY - timedelta(days=1)}
    assert not any(day.locked_empty for day in view.days if day.date >= WEDNESDAY)


# --- get_month ------------------------------------------------------------


def test_a_month_has_a_cell_for_every_day(db: Session, user_a: User) -> None:
    with clock.frozen_time(local_moment(NEXT_MONDAY, hour=9)):
        view = get_month(db, user_a, 2026, 3)

    assert view.year == 2026
    assert view.month == 3
    assert len(view.days) == 31
    assert view.days[0].date == date(2026, 3, 1)
    assert view.days[-1].date == date(2026, 3, 31)


def test_month_rates_are_completed_days_over_scheduled_days(
    db: Session, user_a: User
) -> None:
    for offset in range(7):
        ensure_day_materialised(db, user_a, REFERENCE_MONDAY + timedelta(days=offset))

    laundry = habit_named(db, user_a, "Laundry")  # Wednesday and Saturday
    with clock.frozen_time(local_moment(WEDNESDAY, hour=18)):
        complete_habit(db, user_a, laundry, WEDNESDAY)

    with clock.frozen_time(local_moment(NEXT_MONDAY, hour=9)):
        view = get_month(db, user_a, 2026, 3)

    rate = next(row for row in view.habits if row.name == "Laundry")
    assert rate.scheduled_days == 2
    assert rate.completed_days == 1
    assert rate.rate == 0.5
    assert rate.bucket_name == "Life admin"


def test_month_rates_ignore_bonuses(db: Session, user_a: User) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    laundry = habit_named(db, user_a, "Laundry")

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=20)):
        add_bonus(db, user_a, laundry, REFERENCE_MONDAY)

    with clock.frozen_time(local_moment(NEXT_MONDAY, hour=9)):
        view = get_month(db, user_a, 2026, 3)

    assert "Laundry" not in {row.name for row in view.habits}


def test_an_archived_habit_keeps_its_month_history(db: Session, user_a: User) -> None:
    """Archiving is not deletion: what happened still shows up."""
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    shower = habit_named(db, user_a, "Shower")

    with clock.frozen_time(local_moment(REFERENCE_MONDAY, hour=7)):
        complete_habit(db, user_a, shower, REFERENCE_MONDAY)

    shower.active = False
    shower.archived_at = local_moment(WEDNESDAY, hour=9)
    db.flush()

    with clock.frozen_time(local_moment(NEXT_MONDAY, hour=9)):
        view = get_month(db, user_a, 2026, 3)

    rate = next(row for row in view.habits if row.name == "Shower")
    assert rate.completed_days == 1
    assert rate.scheduled_days == 1


def test_month_calendar_flags_no_data_only_on_locked_empty_days(
    db: Session, user_a: User
) -> None:
    ensure_day_materialised(db, user_a, REFERENCE_MONDAY)
    complete_all_scheduled(db, user_a, REFERENCE_MONDAY)
    today = date(2026, 3, 23)

    with clock.frozen_time(local_moment(today, hour=9)):
        view = get_month(db, user_a, 2026, 3)

    by_date = {day.date: day for day in view.days}
    assert by_date[REFERENCE_MONDAY].pct == 1.0
    assert by_date[REFERENCE_MONDAY].no_data is False
    assert by_date[date(2026, 3, 2)].no_data is True  # locked, nothing recorded
    assert by_date[today].no_data is False  # today is still live
    assert by_date[date(2026, 3, 31)].no_data is False  # the future is not "no data"
