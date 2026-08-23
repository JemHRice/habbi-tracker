"""The edit window: today and yesterday, in the user's own timezone."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app import clock
from app.domain.tracking import can_edit, is_locked
from app.models import User
from tests.conftest import LONDON, SYDNEY, TUESDAY, local_moment

YESTERDAY = TUESDAY - timedelta(days=1)
TWO_DAYS_AGO = TUESDAY - timedelta(days=2)
TOMORROW = TUESDAY + timedelta(days=1)


def test_today_and_yesterday_are_editable(db: Session, user_a: User) -> None:
    with clock.frozen_time(local_moment(TUESDAY, hour=10)):
        assert can_edit(user_a, TUESDAY)
        assert can_edit(user_a, YESTERDAY)


def test_two_days_ago_is_locked(db: Session, user_a: User) -> None:
    with clock.frozen_time(local_moment(TUESDAY, hour=10)):
        assert not can_edit(user_a, TWO_DAYS_AGO)
        assert is_locked(user_a, TWO_DAYS_AGO)


def test_tomorrow_is_not_editable(db: Session, user_a: User) -> None:
    """You cannot tick a day off before living it — but it is not locked either."""
    with clock.frozen_time(local_moment(TUESDAY, hour=10)):
        assert not can_edit(user_a, TOMORROW)
        assert not is_locked(user_a, TOMORROW)


def test_the_window_rolls_at_local_midnight(db: Session, user_a: User) -> None:
    just_before = local_moment(TUESDAY, hour=23, minute=59)
    just_after = local_moment(TOMORROW, hour=0, minute=1)

    with clock.frozen_time(just_before):
        assert can_edit(user_a, YESTERDAY)

    with clock.frozen_time(just_after):
        assert not can_edit(user_a, YESTERDAY)
        assert can_edit(user_a, TUESDAY)


def test_the_window_follows_the_user_timezone(db: Session, user_a: User) -> None:
    """At one instant, two users in different zones are on different dates."""
    user_a.timezone = "Australia/Sydney"
    londoner = User(
        display_name="Elsewhere",
        pin_hash=user_a.pin_hash,
        timezone="Europe/London",
    )
    db.add(londoner)
    db.flush()

    # 14:00 UTC: already Wednesday in Sydney (UTC+11), still Tuesday in London.
    moment = local_moment(TUESDAY, hour=14, tz=LONDON)

    with clock.frozen_time(moment):
        assert moment.astimezone(SYDNEY).date() == TOMORROW
        assert can_edit(user_a, TOMORROW)
        assert not can_edit(londoner, TOMORROW)
        assert can_edit(londoner, TUESDAY)


def test_an_explicit_now_overrides_the_clock(db: Session, user_a: User) -> None:
    """Domain functions accept `now` so callers can pin the moment themselves."""
    with clock.frozen_time(local_moment(TUESDAY, hour=10)):
        assert not can_edit(user_a, TWO_DAYS_AGO)
        assert can_edit(user_a, TWO_DAYS_AGO, now=local_moment(YESTERDAY, hour=10))
