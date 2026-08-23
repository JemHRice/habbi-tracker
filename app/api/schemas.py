"""Request and response bodies that belong to the HTTP layer.

The board *reads* reuse the Phase 1 read models in `app/schemas/views.py`
unchanged. What lives here is the transport-only shapes: login payloads,
settings patches, and the habit/bucket management bodies.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.habit import Habit


def _validate_timezone(value: str) -> str:
    """Reject anything that is not a real IANA zone name."""
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError(f"unknown timezone {value!r}") from error
    return value


# --- Auth & identity ------------------------------------------------------


class UserSummary(BaseModel):
    """The only thing the unauthenticated device-binding call exposes."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str


class LoginRequest(BaseModel):
    user_id: int
    pin: str


class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    """Next local midnight in the user's timezone."""

    must_change_pin: bool
    """True while the PIN is one provisioning issued rather than one chosen."""


class ChangePinRequest(BaseModel):
    current_pin: str
    new_pin: str


# --- Settings -------------------------------------------------------------


class MeResponse(BaseModel):
    display_name: str
    timezone: str
    season_active: bool
    reminders_enabled: bool
    """Dormant: designed-for, not built. Read-only here."""

    must_change_pin: bool


class MeUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    timezone: str | None = None
    season_active: bool | None = None

    _check_timezone = field_validator("timezone")(
        lambda value: value if value is None else _validate_timezone(value)
    )


# --- Completions ----------------------------------------------------------


class CompletionRequest(BaseModel):
    habit_id: int
    date: date_type


# --- Buckets --------------------------------------------------------------


class BucketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color_hex: str
    sort_order: int


class BucketCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color_hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: int = 0


class BucketUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    color_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: int | None = None


# --- Habits ---------------------------------------------------------------


class HabitOut(BaseModel):
    """A habit as the management screens need it, schedule included."""

    id: int
    bucket_id: int
    name: str
    target_per_week: int
    time_cap_minutes: int | None
    season_dependent: bool
    sort_order: int
    anytime: bool
    active: bool
    archived_at: datetime | None
    weekdays: list[int]

    @classmethod
    def from_habit(cls, habit: Habit) -> "HabitOut":
        """Build the response shape from an ORM habit."""
        return cls(
            id=habit.id,
            bucket_id=habit.bucket_id,
            name=habit.name,
            target_per_week=habit.target_per_week,
            time_cap_minutes=habit.time_cap_minutes,
            season_dependent=habit.season_dependent,
            sort_order=habit.sort_order,
            anytime=habit.anytime,
            active=habit.active,
            archived_at=habit.archived_at,
            weekdays=sorted(habit.scheduled_weekdays),
        )


class HabitCreate(BaseModel):
    bucket_id: int
    name: str = Field(min_length=1, max_length=120)
    target_per_week: int = Field(ge=0, le=7)
    weekdays: list[int] = Field(default_factory=list)
    sort_order: int = 0
    time_cap_minutes: int | None = Field(default=None, ge=1)
    season_dependent: bool = False
    anytime: bool = False

    @field_validator("weekdays")
    @classmethod
    def _weekdays_in_range(cls, value: list[int]) -> list[int]:
        if any(weekday not in range(7) for weekday in value):
            raise ValueError("weekdays must be integers 0 (Monday) to 6 (Sunday)")
        return value


class HabitUpdate(BaseModel):
    bucket_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_per_week: int | None = Field(default=None, ge=0, le=7)
    time_cap_minutes: int | None = Field(default=None, ge=1)
    season_dependent: bool | None = None
    sort_order: int | None = None
    anytime: bool | None = None

    clear_time_cap: bool = False
    """Set `time_cap_minutes` to null. A plain null means "leave alone", so
    removing a cap needs its own flag."""


class ScheduleUpdate(BaseModel):
    weekdays: list[int]

    @field_validator("weekdays")
    @classmethod
    def _weekdays_in_range(cls, value: list[int]) -> list[int]:
        if any(weekday not in range(7) for weekday in value):
            raise ValueError("weekdays must be integers 0 (Monday) to 6 (Sunday)")
        return value


class ReorderItem(BaseModel):
    habit_id: int
    sort_order: int
