"""The migration produces the schema the model expects, on either engine."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Engine, inspect, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.dates import date_range
from app.models.dim_date import DimDate

EXPECTED_TABLES = {
    "users",
    "buckets",
    "habits",
    "habit_schedules",
    "dim_date",
    "fact_completion",
    "sessions",
}


def test_migration_creates_every_table(engine: Engine) -> None:
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())


def test_fact_completion_has_its_grain_and_indexes(engine: Engine) -> None:
    inspector = inspect(engine)

    unique_columns = [
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("fact_completion")
    ]
    assert ("user_id", "habit_id", "date") in unique_columns

    index_names = {index["name"] for index in inspector.get_indexes("fact_completion")}
    assert {"ix_fact_completion_user_date", "ix_fact_completion_habit_date"} <= index_names


def test_supporting_constraints_and_indexes_exist(engine: Engine) -> None:
    inspector = inspect(engine)

    bucket_uniques = [
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("buckets")
    ]
    assert ("user_id", "name") in bucket_uniques

    schedule_uniques = [
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("habit_schedules")
    ]
    assert ("habit_id", "weekday") in schedule_uniques

    habit_indexes = {index["name"] for index in inspector.get_indexes("habits")}
    assert "ix_habits_user_active" in habit_indexes

    session_indexes = {index["name"] for index in inspector.get_indexes("sessions")}
    assert "ix_sessions_token_hash" in session_indexes


def test_dim_date_covers_the_configured_range(db: Session) -> None:
    settings = get_settings()
    expected = len(date_range(settings.dim_date_start, settings.dim_date_end))

    stored = db.scalars(select(DimDate.date)).all()

    assert len(stored) == expected
    assert min(stored) == settings.dim_date_start
    assert max(stored) == settings.dim_date_end


def test_dim_date_derives_its_attributes_correctly(db: Session) -> None:
    saturday = db.get(DimDate, date(2026, 3, 21))
    assert saturday is not None

    assert saturday.year == 2026
    assert saturday.quarter == 1
    assert saturday.month == 3
    assert saturday.month_name == "March"
    assert saturday.day_of_month == 21
    assert saturday.weekday == 5
    assert saturday.weekday_name == "Saturday"
    assert saturday.iso_week == 12
    assert saturday.week_start_date == date(2026, 3, 16)
    assert saturday.is_weekend is True


def test_dim_date_marks_weekdays_as_not_weekend(db: Session) -> None:
    wednesday = db.get(DimDate, date(2026, 3, 18))
    assert wednesday is not None
    assert wednesday.weekday == 2
    assert wednesday.is_weekend is False
    assert wednesday.week_start_date == date(2026, 3, 16)
