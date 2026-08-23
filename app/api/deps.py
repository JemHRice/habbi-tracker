"""Shared request dependencies: the database session and the current user."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Iterator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.errors import UNAUTHENTICATED, ApiError
from app.db import SessionFactory
from app.domain.auth import validate_session
from app.domain.dates import local_today
from app.domain.scheduling import backfill
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False, description="Session token from /auth/login")


def get_db() -> Iterator[Session]:
    """Yield a session, committing on success and rolling back on failure.

    Endpoints therefore never call `commit()` themselves; a request either
    applies fully or not at all.
    """
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    session: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> User:
    """Resolve the Bearer token to a user.

    Raises:
        ApiError: 401 `UNAUTHENTICATED` if the header is missing, malformed, or
            the token is unknown or past its day-boundary expiry.
    """
    if credentials is None or not credentials.credentials:
        raise ApiError(401, UNAUTHENTICATED, "A session token is required.")

    user = validate_session(session, credentials.credentials)
    if user is None:
        raise ApiError(401, UNAUTHENTICATED, "Session token is invalid or has expired.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def bring_up_to_date(
    session: Session, user: User, now: datetime | None = None
) -> date:
    """Materialise everything up to the user's local today, and return that date.

    Reads in the domain layer are pure, so this is where the API fills the gap:
    someone who did not open the app for three days still gets correct
    "scheduled but not completed" rows for those days before anything is read.

    It only ever fills *up to today*. It never reaches back to materialise a
    month that was never generated, because doing so would write history using
    today's schedule — exactly the retroactive reshaping the model forbids.
    """
    today = local_today(user, now)
    backfill(session, user, today)
    return today
