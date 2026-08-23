"""PIN hashing and session issuing.

Two facts shape this module:

* PINs are short, so they are hashed with argon2 — a deliberately slow,
  memory-hard function — rather than a fast general-purpose digest.
* Session tokens are 256 bits of randomness, so guessing them is not a threat
  and a plain SHA-256 of the token is enough to avoid storing it in the clear.

There are no HTTP endpoints here; Phase 2 builds the login route on top.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import clock
from app.config import get_settings
from app.domain.dates import next_local_midnight
from app.domain.errors import InvalidPin
from app.models.auth_session import AuthSession
from app.models.user import User

_hasher = PasswordHasher()

TOKEN_BYTES = 32
"""Entropy per session token. 32 bytes = 256 bits."""


def validate_pin_format(pin: str) -> None:
    """Raise :class:`~app.domain.errors.InvalidPin` unless `pin` fits the policy.

    A PIN is exactly `settings.pin_length` digits (six by default). Checked when
    setting a PIN, never when verifying one.
    """
    expected = get_settings().pin_length
    if len(pin) != expected or not pin.isdigit():
        raise InvalidPin(f"PIN must be exactly {expected} digits")


def hash_pin(pin: str) -> str:
    """Return an argon2 hash of `pin`, salt included in the encoded string.

    Raises:
        InvalidPin: if the PIN does not fit the configured format.
    """
    validate_pin_format(pin)
    return _hasher.hash(pin)


def set_pin(session: Session, user: User, pin: str) -> User:
    """Replace a user's PIN with one the person chose. Sessions are left alone.

    Clears `pin_is_provisional`: whatever the PIN was before, it is now a
    deliberate choice rather than something the seed issued.

    Raises:
        InvalidPin: if the PIN does not fit the configured format.
    """
    user.pin_hash = hash_pin(pin)
    user.pin_is_provisional = False
    session.flush()
    return user


def verify_pin(user: User, pin: str) -> bool:
    """Return True if `pin` matches the user's stored hash.

    Never raises on a wrong PIN — a bad guess is an expected outcome, not an
    error. Brute-force throttling is an API concern and lands in Phase 2.
    """
    try:
        return _hasher.verify(user.pin_hash, pin)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest stored in place of a session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user(
    session: Session,
    display_name: str,
    pin: str,
    timezone: str | None = None,
    email: str | None = None,
    pin_is_provisional: bool = False,
) -> User:
    """Create a user with a hashed PIN. The PIN itself is never stored.

    Args:
        timezone: IANA zone name; defaults to `settings.default_timezone`.
        pin_is_provisional: True when the PIN was issued rather than chosen —
            the seed sets this, so the person is asked to pick their own.

    Raises:
        InvalidPin: if the PIN does not fit the configured format.
    """
    user = User(
        display_name=display_name,
        email=email,
        pin_hash=hash_pin(pin),
        timezone=timezone or get_settings().default_timezone,
        pin_is_provisional=pin_is_provisional,
    )
    session.add(user)
    session.flush()
    return user


def create_session(
    session: Session, user: User, now: datetime | None = None
) -> tuple[str, datetime]:
    """Issue a session token for `user`, expiring at the next local midnight.

    That boundary is the same one the edit window uses, so a session lasts
    exactly one local day: roughly one PIN entry each morning.

    Returns:
        The plaintext token (shown to the caller once, never stored) and its
        expiry as an aware UTC datetime.
    """
    moment = clock.resolve_now(now)
    token = secrets.token_urlsafe(TOKEN_BYTES)
    expires_at = next_local_midnight(user, moment)

    session.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=expires_at,
            created_at=moment,
        )
    )
    session.flush()
    return token, expires_at


def validate_session(
    session: Session, token: str, now: datetime | None = None
) -> User | None:
    """Return the token's user, or None if the token is unknown or expired.

    Expiry is exclusive at the boundary: a token whose `expires_at` is exactly
    `now` has expired, which keeps the day boundary unambiguous.
    """
    moment = clock.resolve_now(now)
    record = session.scalar(
        select(AuthSession).where(AuthSession.token_hash == hash_token(token))
    )
    if record is None or record.expires_at <= moment:
        return None
    return record.user


def expire_session(session: Session, token: str) -> None:
    """Delete the session for `token`, if any. Logging out is idempotent."""
    session.execute(
        delete(AuthSession).where(AuthSession.token_hash == hash_token(token))
    )
    session.flush()


def purge_expired_sessions(session: Session, now: datetime | None = None) -> int:
    """Delete every session that has passed its expiry. Returns rows removed."""
    moment = clock.resolve_now(now)
    result = session.execute(delete(AuthSession).where(AuthSession.expires_at <= moment))
    session.flush()
    return result.rowcount or 0
