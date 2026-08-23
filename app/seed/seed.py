"""Load the seed boards.

Guarded so it is safe to run on every deploy: a user whose display name already
exists is left completely alone. Seeding never updates or deletes anything, in
keeping with the forward-only rule.

Run it with `make seed`, or directly:

    python -m app.seed
"""

from __future__ import annotations

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.auth import create_user
from app.domain.dates import populate_dim_date
from app.models.bucket import Bucket
from app.models.habit import Habit, HabitSchedule
from app.models.user import User
from app.seed.data import Board, load_boards, using_local_board


def find_user(session: Session, display_name: str) -> User | None:
    """Return the user with this display name, if one exists."""
    return session.scalar(select(User).where(User.display_name == display_name))


def seed_board(
    session: Session,
    board: Board,
    pin: str,
    timezone: str | None = None,
) -> User:
    """Create one user with their buckets, habits and schedules.

    The PIN is marked provisional: it was issued by provisioning, not chosen by
    the person, so the app can ask them to set their own. Once they do, the
    production environment no longer needs the seed PIN at all.

    Returns the existing user untouched if that display name is already taken,
    which is what makes the seed safe to re-run.
    """
    existing = find_user(session, board.display_name)
    if existing is not None:
        return existing

    user = create_user(
        session,
        display_name=board.display_name,
        pin=pin,
        timezone=timezone,
        pin_is_provisional=True,
    )

    bucket_ids: dict[str, int] = {}
    for bucket_seed in board.buckets:
        bucket = Bucket(
            user_id=user.id,
            name=bucket_seed.name,
            color_hex=bucket_seed.color_hex,
            sort_order=bucket_seed.sort_order,
        )
        session.add(bucket)
        session.flush()
        bucket_ids[bucket_seed.name] = bucket.id

    for habit_seed in board.habits:
        habit = Habit(
            user_id=user.id,
            bucket_id=bucket_ids[habit_seed.bucket],
            name=habit_seed.name,
            target_per_week=habit_seed.target_per_week,
            time_cap_minutes=habit_seed.time_cap_minutes,
            season_dependent=habit_seed.season_dependent,
            sort_order=habit_seed.sort_order,
            anytime=habit_seed.anytime,
            active=True,
        )
        session.add(habit)
        session.flush()
        for weekday in habit_seed.weekdays:
            session.add(HabitSchedule(habit_id=habit.id, weekday=weekday))

    session.flush()
    return user


def seed_all(
    session: Session,
    user_a_pin: str | None = None,
    user_b_pin: str | None = None,
) -> tuple[User, User]:
    """Populate `dim_date` and both boards. Idempotent.

    Board content comes from the private `data_local.py` when it exists, and
    from the public demo board otherwise. PINs default to
    `settings.seed_user_a_pin` / `seed_user_b_pin`, which come from the
    environment — no PIN is written into the repository.
    """
    settings = get_settings()
    populate_dim_date(session, settings.dim_date_start, settings.dim_date_end)

    board_a, board_b = load_boards()
    user_a = seed_board(session, board_a, user_a_pin or settings.seed_user_a_pin)
    user_b = seed_board(session, board_b, user_b_pin or settings.seed_user_b_pin)
    return user_a, user_b


def main() -> int:
    """Entry point for `python -m app.seed`."""
    from app.db import SessionFactory

    source = "private data_local.py" if using_local_board() else "public demo board"

    with SessionFactory() as session:
        user_a, user_b = seed_all(session)
        session.commit()
        # Read the relationships while the session is still open; the User
        # objects are detached once the block exits.
        summary = [
            (user.display_name, len(user.habits)) for user in (user_a, user_b)
        ]

    print(f"Seed source: {source}.")
    for display_name, habit_count in summary:
        print(f"Seeded {display_name!r} with {habit_count} habits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
