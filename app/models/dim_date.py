"""The `dim_date` table: a classic pre-populated date dimension.

Keeping calendar attributes in a table (rather than deriving them in every
query) is what makes week/month rollups trivial joins instead of engine-specific
date arithmetic — and it keeps the same SQL working on SQLite and Postgres.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


class DimDate(Base):
    """One row per calendar date, keyed by the date itself."""

    __tablename__ = "dim_date"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    month_name: Mapped[str] = mapped_column(Text, nullable=False)
    day_of_month: Mapped[int] = mapped_column(Integer, nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    """0 = Monday ... 6 = Sunday."""

    weekday_name: Mapped[str] = mapped_column(Text, nullable=False)
    iso_week: Mapped[int] = mapped_column(Integer, nullable=False)
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    """The Monday of the ISO week containing this date."""

    is_weekend: Mapped[bool] = mapped_column(Boolean, nullable=False)

    def __repr__(self) -> str:
        return f"<DimDate {self.date.isoformat()}>"


def build_row(day: date) -> dict[str, object]:
    """Derive every `dim_date` attribute for a single calendar date."""
    weekday = day.weekday()
    return {
        "date": day,
        "year": day.year,
        "quarter": (day.month - 1) // 3 + 1,
        "month": day.month,
        "month_name": MONTH_NAMES[day.month - 1],
        "day_of_month": day.day,
        "weekday": weekday,
        "weekday_name": WEEKDAY_NAMES[weekday],
        "iso_week": day.isocalendar().week,
        "week_start_date": day.fromordinal(day.toordinal() - weekday),
        "is_weekend": weekday >= 5,
    }
