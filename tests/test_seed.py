"""The seed loads the documented boards, and re-running it changes nothing.

These assertions are all against the **public demo board** in `app/seed/data.py`.
Real habit names live in a gitignored `data_local.py`, so the suite must never
depend on them — see the `seeded` fixture.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Bucket, Habit, HabitSchedule, User
from app.seed import data
from app.seed.data import DEMO_BOARD_A, DEMO_BUCKETS, DEMO_HABITS, load_boards
from app.seed.seed import seed_board
from tests.conftest import PIN_A, PIN_B


def test_user_a_has_the_full_board(db: Session, user_a: User) -> None:
    buckets = db.scalars(select(Bucket).where(Bucket.user_id == user_a.id)).all()
    habits = db.scalars(select(Habit).where(Habit.user_id == user_a.id)).all()

    assert len(buckets) == 8
    assert len(habits) == 29
    assert all(habit.active for habit in habits)


def test_bucket_colours_match_the_palette(db: Session, user_a: User) -> None:
    stored = {
        bucket.name: bucket.color_hex
        for bucket in db.scalars(select(Bucket).where(Bucket.user_id == user_a.id))
    }

    assert stored == {seed.name: seed.color_hex for seed in DEMO_BUCKETS}
    assert stored["Self-care"] == "#CA758A"
    assert stored["Study"] == "#6C6C2C"


def test_three_bucket_colours_are_flagged_provisional() -> None:
    """The core palette has five colours; three buckets use stand-ins."""
    provisional = {seed.name for seed in DEMO_BUCKETS if seed.provisional_color}

    assert provisional == {"Life admin", "Social", "Team sport"}


def test_every_habit_gets_its_scheduled_weekdays(db: Session, user_a: User) -> None:
    habits = {
        habit.name: habit
        for habit in db.scalars(select(Habit).where(Habit.user_id == user_a.id))
    }

    for seed in DEMO_HABITS:
        assert habits[seed.name].scheduled_weekdays == set(seed.weekdays)

    assert habits["Laundry"].scheduled_weekdays == {2, 5}
    assert habits["Training prep"].scheduled_weekdays == {0}
    assert habits["Morning water"].scheduled_weekdays == set(range(7))


def test_habit_attributes_survive_the_seed(db: Session, user_a: User) -> None:
    habits = {
        habit.name: habit
        for habit in db.scalars(select(Habit).where(Habit.user_id == user_a.id))
    }

    assert habits["Focused project work"].time_cap_minutes == 30
    assert habits["Coursework"].time_cap_minutes == 60
    assert habits["Shower"].time_cap_minutes is None

    season = {name for name, habit in habits.items() if habit.season_dependent}
    assert season == {"Team training", "Weekend fixture"}

    anytime = {name for name, habit in habits.items() if habit.anytime}
    assert anytime == {"Water through the day", "Daily check-in", "Small kind gesture"}


def test_dormant_fields_are_present_but_unset(db: Session, user_a: User) -> None:
    """Notifications are designed-for, not built: the shape exists, empty."""
    assert user_a.reminders_enabled is False
    habits = db.scalars(select(Habit).where(Habit.user_id == user_a.id)).all()
    assert all(habit.reminder_time is None for habit in habits)


def test_user_b_starts_empty(db: Session, user_b: User) -> None:
    buckets = db.scalars(select(Bucket).where(Bucket.user_id == user_b.id)).all()
    habits = db.scalars(select(Habit).where(Habit.user_id == user_b.id)).all()

    assert buckets == []
    assert habits == []
    assert user_b.season_active is False


def test_users_get_distinct_pin_hashes(db: Session, user_a: User, user_b: User) -> None:
    """Hashes are salted, so identical PINs would still differ — and these differ."""
    assert user_a.pin_hash != user_b.pin_hash
    assert PIN_A not in user_a.pin_hash
    assert PIN_B not in user_b.pin_hash


def test_seeding_twice_is_a_no_op(db: Session, user_a: User) -> None:
    seed_board(db, DEMO_BOARD_A, PIN_A)

    assert db.scalar(select(func.count()).select_from(User)) == 2
    assert db.scalar(select(func.count()).select_from(Bucket)) == 8
    assert db.scalar(select(func.count()).select_from(Habit)) == 29
    assert db.scalar(select(func.count()).select_from(HabitSchedule)) == sum(
        len(seed.weekdays) for seed in DEMO_HABITS
    )


def test_load_boards_always_returns_both_boards() -> None:
    """Whether or not a private data_local.py exists, two boards come back."""
    board_a, board_b = load_boards()

    assert board_a.display_name == "User A"
    assert board_b.display_name == "User B"


def test_load_boards_falls_back_to_the_demo_board(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """What a fresh clone and CI get, tested regardless of the local machine."""
    monkeypatch.setattr(data, "_local_module", lambda: None)

    assert data.using_local_board() is False
    assert data.load_boards() == (data.DEMO_BOARD_A, data.DEMO_BOARD_B)


def test_a_broken_local_board_is_not_silently_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A typo in data_local.py must fail loudly, not quietly seed the demo board."""

    def explode(_name: str) -> None:
        raise ImportError("data_local.py is broken")

    monkeypatch.setattr(data.importlib, "import_module", explode)
    monkeypatch.setattr(data.importlib.util, "find_spec", lambda _name: object())

    with pytest.raises(ImportError):
        data.load_boards()


def test_the_public_demo_board_is_exactly_the_expected_generic_set() -> None:
    """A guard against private habit names drifting into the public seed file.

    Asserted as a positive snapshot rather than a list of names to avoid — that
    would put the private names back into a tracked file, which is the thing
    this test exists to prevent.
    """
    assert {seed.name for seed in DEMO_HABITS} == {
        "Morning water",
        "Morning skincare",
        "Brush teeth (AM)",
        "Shower",
        "Meal prep",
        "Focused project work",
        "Career admin",
        "Coursework",
        "Deep study block",
        "Certification study",
        "Movement / gym",
        "Training prep",
        "Team training",
        "Midweek match",
        "Weekend fixture",
        "Reading",
        "Evening skincare",
        "Brush teeth (PM)",
        "Put clothes away",
        "Tidy desk",
        "Laundry",
        "Finance review",
        "See a friend",
        "Quality time",
        "Wind down early",
        "Full night's sleep",
        "Water through the day",
        "Daily check-in",
        "Small kind gesture",
    }
    assert {seed.name for seed in DEMO_BUCKETS} == {
        "Self-care",
        "Health",
        "Study",
        "Career",
        "Relationship",
        "Life admin",
        "Social",
        "Team sport",
    }
