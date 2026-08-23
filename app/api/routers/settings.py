"""The `/me` settings surface: display name, timezone, season toggle, PIN."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.api.errors import PIN_INVALID, ApiError
from app.api.schemas import ChangePinRequest, MeResponse, MeUpdate
from app.domain.auth import set_pin, verify_pin
from app.models.user import User

router = APIRouter(prefix="/me", tags=["settings"])


def _me(user: User) -> MeResponse:
    """Shape a user as the settings screen sees them."""
    return MeResponse(
        display_name=user.display_name,
        timezone=user.timezone,
        season_active=user.season_active,
        reminders_enabled=user.reminders_enabled,
        must_change_pin=user.pin_is_provisional,
    )


@router.get("", response_model=MeResponse)
def read_me(user: CurrentUser) -> MeResponse:
    """The current user's settings."""
    return _me(user)


@router.patch("", response_model=MeResponse)
def update_me(payload: MeUpdate, session: DbSession, user: CurrentUser) -> MeResponse:
    """Change display name, timezone, or the season toggle. Partial update.

    `reminders_enabled` is deliberately absent: the field is dormant, so there
    is nothing meaningful to set it to and no behaviour wired to it.

    Flipping the season affects future materialisation and current reads only;
    days already materialised keep the rows they had.
    """
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.timezone is not None:
        user.timezone = payload.timezone
    if payload.season_active is not None:
        user.season_active = payload.season_active

    session.flush()
    return _me(user)


@router.put("/pin", response_model=MeResponse)
def change_pin(
    payload: ChangePinRequest, session: DbSession, user: CurrentUser
) -> MeResponse:
    """Replace the PIN with one the person chose.

    Clears `must_change_pin`, which is how a provisioned account stops being one.
    Existing sessions stay valid — changing your own PIN should not log you out
    of the device you are holding.

    Raises:
        ApiError: 401 `PIN_INVALID` if the current PIN is wrong.
        InvalidPin: (400 `VALIDATION`) if the new PIN is not six digits.
    """
    if not verify_pin(user, payload.current_pin):
        raise ApiError(401, PIN_INVALID, "Your current PIN is not correct.")

    set_pin(session, user, payload.new_pin)
    return _me(user)
