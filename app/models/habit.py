"""The `habits` and `habit_schedules` tables.

A habit is scheduled on a fixed set of weekdays (0 = Monday ... 6 = Sunday).
Habits are never hard-deleted: removal sets `active = False` and `archived_at`,
so every completion fact the habit ever produced stays readable.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UtcDateTime

if TYPE_CHECKING:
    from app.models.bucket import Bucket
    from app.models.user import User


class Habit(Base, TimestampMixin):
    """One trackable habit on one user's board."""

    __tablename__ = "habits"
    __table_args__ = (Index("ix_habits_user_active", "user_id", "active"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    bucket_id: Mapped[int] = mapped_column(ForeignKey("buckets.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    target_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    """Reference/config only. Currently equals the number of scheduled weekdays.
    Never used to cap, penalise or compute a percentage."""

    time_cap_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_dependent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    """Fixed chronological display order, morning to night."""

    anytime: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    """Habits with no natural time of day. They always sort after timed habits."""

    reminder_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    """Dormant: designed-for, not built. Nothing reads this in v1."""

    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    archived_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="habits")
    bucket: Mapped["Bucket"] = relationship(back_populates="habits")
    schedules: Mapped[list["HabitSchedule"]] = relationship(
        back_populates="habit", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def scheduled_weekdays(self) -> set[int]:
        """The weekdays this habit is scheduled on, as a set of 0-6 integers."""
        return {schedule.weekday for schedule in self.schedules}

    def __repr__(self) -> str:
        return f"<Habit id={self.id} name={self.name!r} active={self.active}>"


class HabitSchedule(Base):
    """One weekday on which a habit is expected. Grain: (habit, weekday)."""

    __tablename__ = "habit_schedules"
    __table_args__ = (
        UniqueConstraint("habit_id", "weekday", name="uq_habit_schedules_habit_weekday"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    habit_id: Mapped[int] = mapped_column(
        ForeignKey("habits.id", ondelete="CASCADE"), nullable=False
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    """0 = Monday ... 6 = Sunday, matching `datetime.date.weekday()`."""

    habit: Mapped["Habit"] = relationship(back_populates="schedules")

    def __repr__(self) -> str:
        return f"<HabitSchedule habit_id={self.habit_id} weekday={self.weekday}>"
