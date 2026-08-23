"""Pydantic read models — the shapes the Phase 2 HTTP API will serve.

These are UI-ready but presentation-free: no colours chosen, no copy, no
celebration logic. The frontend decides how to render a percentage; the backend
only says what it is.
"""

from app.schemas.views import (
    CompletedEntry,
    DayDetailView,
    DayView,
    HabitRef,
    MonthDayView,
    MonthHabitRate,
    MonthView,
    TodayView,
    WeekDayView,
    WeekView,
)

__all__ = [
    "CompletedEntry",
    "DayDetailView",
    "DayView",
    "HabitRef",
    "MonthDayView",
    "MonthHabitRate",
    "MonthView",
    "TodayView",
    "WeekDayView",
    "WeekView",
]
