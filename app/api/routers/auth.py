"""Device binding, login and logout.

There is no public sign-up: users are provisioned by the seed. A device asks
`GET /users` once to learn whose it is, then only ever posts a PIN.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

from app.api import throttle
from app.api.deps import CurrentUser, DbSession, bearer_scheme
from app.api.errors import NOT_FOUND, PIN_INVALID, ApiError
from app.api.schemas import LoginRequest, LoginResponse, UserSummary
from app.domain.auth import create_session, expire_session, verify_pin
from app.models.user import User

router = APIRouter(tags=["auth"])


@router.get("/users", response_model=list[UserSummary])
def list_users(session: DbSession) -> list[User]:
    """List who this app belongs to, for first-run device binding.

    Deliberately unauthenticated and deliberately minimal: display names only,
    which is exactly what the "who are you?" picker needs and nothing more.
    """
    return list(session.scalars(select(User).order_by(User.id)).all())


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: DbSession) -> LoginResponse:
    """Exchange a PIN for a session token that lasts until the next local midnight.

    Raises:
        ApiError: 404 if the user does not exist, 401 `PIN_INVALID` for a wrong
            PIN, or 429 `PIN_THROTTLED` while a cooldown is in force.
    """
    user = session.get(User, payload.user_id)
    if user is None:
        raise ApiError(404, NOT_FOUND, f"No user {payload.user_id}.")

    throttle.check(user.id)

    if not verify_pin(user, payload.pin):
        throttle.record_failure(user.id)
        raise ApiError(401, PIN_INVALID, "That PIN is not correct.")

    throttle.clear(user.id)
    token, expires_at = create_session(session, user)
    return LoginResponse(
        token=token,
        expires_at=expires_at,
        must_change_pin=user.pin_is_provisional,
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    session: DbSession,
    _user: CurrentUser,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Response:
    """End the current session. Logging out twice is not an error."""
    expire_session(session, credentials.credentials)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
