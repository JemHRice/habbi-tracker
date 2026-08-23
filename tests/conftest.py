"""Shared test fixtures.

Two things make these tests deterministic:

* **A migrated database per session.** The schema under test is the one Alembic
  produces, not `create_all` — so model/migration drift fails the suite.
* **A frozen clock.** Nothing reads the system date. Users are seeded at a fixed
  instant and every timezone-sensitive assertion pins its own moment, so the
  results are the same today and in five years.

Point `TEST_DATABASE_URL` at Postgres to run the identical suite there:

    TEST_DATABASE_URL=postgresql+psycopg://habit:habit@localhost:5433/habit_tracker
"""

from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import create_db_engine
from app.models import Base, User

ROOT = Path(__file__).resolve().parents[1]

SYDNEY = ZoneInfo("Australia/Sydney")
LONDON = ZoneInfo("Europe/London")

REFERENCE_MONDAY = date(2026, 3, 16)
"""A known Monday. Every other test date is expressed relative to it."""

TUESDAY = REFERENCE_MONDAY + timedelta(days=1)
WEDNESDAY = REFERENCE_MONDAY + timedelta(days=2)
SATURDAY = REFERENCE_MONDAY + timedelta(days=5)
SUNDAY = REFERENCE_MONDAY + timedelta(days=6)

SEED_MOMENT = datetime(2026, 3, 1, 8, 0, tzinfo=SYDNEY)
"""When the fixture users are created — a fortnight before REFERENCE_MONDAY, so
backfill has room to work and never trips the "before the user existed" floor."""

PIN_A = "123456"
PIN_B = "567890"


def local_moment(
    day: date, hour: int = 9, minute: int = 0, tz: ZoneInfo = SYDNEY
) -> datetime:
    """Build an aware datetime at a wall-clock time on `day` in `tz`."""
    return datetime.combine(day, time(hour, minute), tzinfo=tz)


def _reset_database(url: str) -> None:
    """Drop every table plus Alembic's bookkeeping, for a guaranteed clean slate."""
    engine = create_db_engine(url)
    try:
        Base.metadata.drop_all(engine)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def database_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    """The database under test: `TEST_DATABASE_URL`, else a temporary SQLite file."""
    override = os.environ.get("TEST_DATABASE_URL")
    if override:
        return override
    path = tmp_path_factory.mktemp("db") / "habit_tracker_test.db"
    return f"sqlite+pysqlite:///{path.as_posix()}"


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    """A migrated database, built by running Alembic exactly as a deploy does."""
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()

    _reset_database(database_url)

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    built = create_db_engine(database_url)
    yield built
    built.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """A session inside a transaction that is rolled back after every test.

    Domain code commits nothing and uses savepoints freely; binding the session
    to an outer transaction lets all of that happen and still leaves the
    database untouched between tests.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def seeded(db: Session) -> tuple[User, User]:
    """Both demo boards, created at the fixed SEED_MOMENT.

    Deliberately seeds the *public demo* boards rather than calling `seed_all`,
    which would pick up a private `data_local.py` if the developer has one. The
    suite must assert the same things on every machine and in CI.
    """
    from app import clock
    from app.seed.data import DEMO_BOARD_A, DEMO_BOARD_B
    from app.seed.seed import seed_board

    with clock.frozen_time(SEED_MOMENT):
        return (
            seed_board(db, DEMO_BOARD_A, PIN_A),
            seed_board(db, DEMO_BOARD_B, PIN_B),
        )


@pytest.fixture
def user_a(seeded: tuple[User, User]) -> User:
    """The full board: 8 buckets, 29 habits."""
    return seeded[0]


@pytest.fixture
def user_b(seeded: tuple[User, User]) -> User:
    """The empty board."""
    return seeded[1]
