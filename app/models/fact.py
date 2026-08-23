"""The `fact_completion` table: the heart of the model.

Grain: exactly one row per (user, habit, date).

Every habit scheduled on a date gets a row when the day is materialised, with
`scheduled = True` and `completed = False`. That makes "scheduled but not done"
a first-class, queryable fact rather than an absence to be inferred — which is
what lets week/month rollups be plain aggregations.

A row with `scheduled = False, is_bonus = True` records something done on a day
it was not expected. Bonuses are deliberately excluded from the daily
percentage: they are a bonus *outside* the count, never a way to exceed 100%.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UtcDateTime
from app.models.habit import Habit


class FactCompletion(Base, TimestampMixin):
    """One user's standing with one habit on one date."""

    __tablename__ = "fact_completion"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "habit_id", "date", name="uq_fact_completion_user_habit_date"
        ),
        Index("ix_fact_completion_user_date", "user_id", "date"),
        Index("ix_fact_completion_habit_date", "habit_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, ForeignKey("dim_date.date"), nullable=False)

    scheduled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    """True when the habit was expected on this date. Only these rows count
    toward the daily percentage."""

    completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    """When it was ticked. Also the sort key for the completed pile."""

    is_bonus: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    habit: Mapped["Habit"] = relationship(lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<FactCompletion user_id={self.user_id} habit_id={self.habit_id} "
            f"date={self.date.isoformat()} scheduled={self.scheduled} "
            f"completed={self.completed}>"
        )
