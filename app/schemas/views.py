"""Read model definitions.

Percentages are fractions in the range 0.0-1.0, or `None` for "nothing was
scheduled" (a rest day). They cannot exceed 1.0: completed-scheduled is always a
subset of scheduled, so the cap falls out of the maths rather than being
clamped. There is no "behind", no "exceeded", and no pace anywhere in these
shapes — by design.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HabitRef(BaseModel):
    """A habit as the UI needs it: identity, grouping, and ordering hints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    bucket_id: int
    bucket_name: str
    bucket_color_hex: str
    sort_order: int
    anytime: bool
    time_cap_minutes: int | None = None
    season_dependent: bool = False


class CompletedEntry(BaseModel):
    """A habit that was ticked, with when it happened (the pile's sort key)."""

    habit: HabitRef
    completed_at: datetime
    is_bonus: bool = False


class TodayView(BaseModel):
    """The home screen: what is left, what is done, and how the day is going."""

    date: date_type
    editable: bool

    active: list[HabitRef] = Field(default_factory=list)
    """Scheduled habits not yet ticked, ordered by (anytime asc, sort_order asc)."""

    completed: list[CompletedEntry] = Field(default_factory=list)
    """Everything ticked today, bonuses included, in tick order."""

    daily_pct: float | None = None
    """Completed scheduled / total scheduled. `None` on a rest day."""

    done_count: int = 0
    """Scheduled habits completed. Bonuses are not counted."""

    remaining_count: int = 0
    available_extras: list[HabitRef] = Field(default_factory=list)
    """Other active habits with nothing logged today — the "add extra" picker."""

    bonuses: list[CompletedEntry] = Field(default_factory=list)
    """The bonus subset of `completed`, surfaced separately for convenience."""


class DayDetailView(BaseModel):
    """A single day, looked back on from the calendar."""

    model_config = ConfigDict(from_attributes=True)

    date: date_type
    editable: bool
    completed: list[CompletedEntry] = Field(default_factory=list)
    not_completed: list[HabitRef] = Field(default_factory=list)
    bonuses: list[CompletedEntry] = Field(default_factory=list)
    final_pct: float | None = None

    no_data: bool = False
    """True only when the day is locked *and* nothing at all was completed."""


class WeekDayView(BaseModel):
    """One cell of the weekly overview."""

    date: date_type
    weekday: int
    pct: float | None = None
    scheduled_count: int = 0
    done_count: int = 0
    editable: bool = False

    locked_empty: bool = False
    """The weekly rendering of "no data" — same rule as `DayDetailView.no_data`."""


class WeekView(BaseModel):
    """Monday to Sunday of the week containing a given date."""

    week_start: date_type
    week_end: date_type
    days: list[WeekDayView] = Field(default_factory=list)


class MonthHabitRate(BaseModel):
    """How often one habit was completed on the days it was scheduled.

    Stated factually. The UI is expected to show these without ranking, red, or
    any other judgement.
    """

    habit_id: int
    name: str
    bucket_name: str
    bucket_color_hex: str
    scheduled_days: int
    completed_days: int
    rate: float | None = None
    """`completed_days / scheduled_days`, or `None` if it was never scheduled."""


class MonthDayView(BaseModel):
    """One cell of the month calendar."""

    date: date_type
    pct: float | None = None
    no_data: bool = False


class MonthView(BaseModel):
    """A month of per-habit rates plus the calendar fill values."""

    year: int
    month: int
    habits: list[MonthHabitRate] = Field(default_factory=list)
    days: list[MonthDayView] = Field(default_factory=list)
