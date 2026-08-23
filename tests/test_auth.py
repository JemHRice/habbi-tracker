"""PIN verification and day-bounded sessions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app import clock
from app.config import get_settings
from app.domain.auth import (
    create_session,
    create_user,
    expire_session,
    hash_token,
    purge_expired_sessions,
    set_pin,
    validate_session,
    verify_pin,
)
from app.domain.errors import InvalidPin
from app.models import User
from tests.conftest import LONDON, PIN_A, SYDNEY, TUESDAY, local_moment

# Sydney is UTC+11 in March, so Wednesday 00:00 local is Tuesday 13:00 UTC.
NEXT_LOCAL_MIDNIGHT_UTC = datetime(2026, 3, 17, 13, 0, tzinfo=UTC)


def test_the_pin_is_hashed_not_stored(db: Session) -> None:
    user = create_user(db, display_name="Someone", pin="918273")

    assert user.pin_hash != "918273"
    assert "918273" not in user.pin_hash
    assert user.pin_hash.startswith("$argon2")


def test_verify_pin_accepts_the_right_pin_and_rejects_others(
    db: Session, user_a: User
) -> None:
    assert verify_pin(user_a, PIN_A) is True
    assert verify_pin(user_a, "000000") is False
    assert verify_pin(user_a, "") is False


def test_a_pin_must_be_six_digits(db: Session) -> None:
    assert get_settings().pin_length == 6

    with pytest.raises(InvalidPin):
        create_user(db, display_name="Too short", pin="1234")
    with pytest.raises(InvalidPin):
        create_user(db, display_name="Too long", pin="1234567")
    with pytest.raises(InvalidPin):
        create_user(db, display_name="Not digits", pin="12ab56")
    with pytest.raises(InvalidPin):
        create_user(db, display_name="Empty", pin="")


def test_a_wrong_pin_is_rejected_not_raised(db: Session, user_a: User) -> None:
    """A bad guess at login is an expected outcome, not an error — even when it
    is the wrong length. Only *setting* a PIN validates the format."""
    assert verify_pin(user_a, "1234") is False
    assert verify_pin(user_a, "not-a-pin") is False


def test_changing_a_pin_replaces_the_hash(db: Session, user_a: User) -> None:
    original = user_a.pin_hash

    set_pin(db, user_a, "246813")

    assert user_a.pin_hash != original
    assert verify_pin(user_a, "246813") is True
    assert verify_pin(user_a, PIN_A) is False


def test_a_seeded_pin_is_marked_provisional(db: Session, user_a: User) -> None:
    """Provisioning issued this PIN; nobody chose it."""
    assert user_a.pin_is_provisional is True


def test_choosing_a_pin_clears_the_provisional_flag(
    db: Session, user_a: User
) -> None:
    set_pin(db, user_a, "246813")

    assert user_a.pin_is_provisional is False


def test_deliberately_choosing_the_seed_pin_is_not_provisional(
    db: Session, user_a: User
) -> None:
    """The flag records where a PIN came from, not what it is.

    Someone who picks the same digits the seed happened to use has still made a
    choice, so they are never asked to change it.
    """
    set_pin(db, user_a, PIN_A)

    assert verify_pin(user_a, PIN_A) is True
    assert user_a.pin_is_provisional is False


def test_a_directly_created_user_is_not_provisional(db: Session) -> None:
    user = create_user(db, display_name="Chose their own", pin="918273")

    assert user.pin_is_provisional is False


def test_changing_to_an_invalid_pin_leaves_the_old_one(
    db: Session, user_a: User
) -> None:
    original = user_a.pin_hash

    with pytest.raises(InvalidPin):
        set_pin(db, user_a, "12")

    assert user_a.pin_hash == original
    assert verify_pin(user_a, PIN_A) is True


def test_new_users_get_the_default_timezone(db: Session) -> None:
    user = create_user(db, display_name="Someone", pin="918273")

    assert user.timezone == get_settings().default_timezone == "Australia/Sydney"


def test_a_session_expires_at_the_next_local_midnight(
    db: Session, user_a: User
) -> None:
    with clock.frozen_time(local_moment(TUESDAY, hour=10)):
        _token, expires_at = create_session(db, user_a)

    assert expires_at == NEXT_LOCAL_MIDNIGHT_UTC
    assert expires_at.astimezone(SYDNEY).hour == 0
    assert expires_at.astimezone(SYDNEY).date() == TUESDAY + timedelta(days=1)


def test_a_late_night_session_still_expires_the_same_night(
    db: Session, user_a: User
) -> None:
    """Signing in at 23:59 buys a minute, not another day. That is the trade-off
    of a day-boundary session, and it keeps the boundary unambiguous."""
    with clock.frozen_time(local_moment(TUESDAY, hour=23, minute=59)):
        _token, expires_at = create_session(db, user_a)

    assert expires_at == NEXT_LOCAL_MIDNIGHT_UTC


def test_expiry_follows_the_users_own_timezone(db: Session, user_a: User) -> None:
    user_a.timezone = "Europe/London"
    db.flush()

    with clock.frozen_time(local_moment(TUESDAY, hour=10, tz=LONDON)):
        _token, expires_at = create_session(db, user_a)

    # London is on GMT until late March, so midnight local is midnight UTC —
    # a different instant from the Sydney user's boundary above.
    assert expires_at == datetime(2026, 3, 18, 0, 0, tzinfo=UTC)
    assert expires_at != NEXT_LOCAL_MIDNIGHT_UTC


def test_a_token_validates_until_the_boundary_and_not_after(
    db: Session, user_a: User
) -> None:
    with clock.frozen_time(local_moment(TUESDAY, hour=10)):
        token, expires_at = create_session(db, user_a)

    assert validate_session(db, token, now=expires_at - timedelta(seconds=1)) is user_a
    assert validate_session(db, token, now=expires_at) is None
    assert validate_session(db, token, now=expires_at + timedelta(hours=1)) is None


def test_only_the_token_hash_is_stored(db: Session, user_a: User) -> None:
    from sqlalchemy import select

    from app.models import AuthSession

    with clock.frozen_time(local_moment(TUESDAY, hour=10)):
        token, _expires_at = create_session(db, user_a)

    record = db.scalars(select(AuthSession)).one()
    assert record.token_hash != token
    assert record.token_hash == hash_token(token)


def test_an_unknown_token_never_validates(db: Session, user_a: User) -> None:
    with clock.frozen_time(local_moment(TUESDAY, hour=10)):
        create_session(db, user_a)

        assert validate_session(db, "not-a-real-token") is None


def test_tokens_are_unique_per_session(db: Session, user_a: User) -> None:
    with clock.frozen_time(local_moment(TUESDAY, hour=10)):
        first, _ = create_session(db, user_a)
        second, _ = create_session(db, user_a)

    assert first != second


def test_expiring_a_session_revokes_it_and_is_idempotent(
    db: Session, user_a: User
) -> None:
    with clock.frozen_time(local_moment(TUESDAY, hour=10)):
        token, _expires_at = create_session(db, user_a)

        expire_session(db, token)
        assert validate_session(db, token) is None

        expire_session(db, token)  # logging out twice is not an error


def test_purging_removes_only_expired_sessions(db: Session, user_a: User) -> None:
    with clock.frozen_time(local_moment(TUESDAY, hour=10)):
        stale, _ = create_session(db, user_a)

    with clock.frozen_time(local_moment(TUESDAY + timedelta(days=1), hour=10)):
        fresh, _ = create_session(db, user_a)
        removed = purge_expired_sessions(db)

        assert removed == 1
        assert validate_session(db, stale) is None
        assert validate_session(db, fresh) is user_a
