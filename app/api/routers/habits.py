"""Habit management: create, edit, reschedule, reorder, archive.

Two guarantees the API must not work around, both enforced in the domain layer:

* **Archive, never delete.** There is no hard-delete endpoint anywhere.
* **Edits are forward-only.** Changing a habit affects future materialisation
  and current reads; an already-materialised day keeps exactly the rows it had.
"""

from __future__ import annotations

from fastapi import APIRouter, Path

from app.api.deps import CurrentUser, DbSession
from app.api.schemas import HabitCreate, HabitOut, HabitUpdate, ReorderItem, ScheduleUpdate
from app.domain.habits import (
    archive_habit,
    create_habit,
    list_habits,
    reorder_habits,
    set_schedule,
    update_habit,
)

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("", response_model=list[HabitOut])
def read_habits(
    session: DbSession, user: CurrentUser, include_archived: bool = False
) -> list[HabitOut]:
    """The user's habits with their schedules, in display order.

    Archived habits are excluded by default: they no longer belong on a board,
    even though their history still appears in week and month reads.
    """
    return [
        HabitOut.from_habit(habit)
        for habit in list_habits(session, user, include_archived=include_archived)
    ]


@router.post("", response_model=HabitOut, status_code=201)
def add_habit(
    payload: HabitCreate, session: DbSession, user: CurrentUser
) -> HabitOut:
    """Create a habit. It starts appearing from the next materialisation on."""
    habit = create_habit(
        session,
        user,
        bucket_id=payload.bucket_id,
        name=payload.name,
        target_per_week=payload.target_per_week,
        weekdays=payload.weekdays,
        sort_order=payload.sort_order,
        time_cap_minutes=payload.time_cap_minutes,
        season_dependent=payload.season_dependent,
        anytime=payload.anytime,
    )
    return HabitOut.from_habit(habit)


@router.patch("/reorder", response_model=list[HabitOut])
def reorder(
    payload: list[ReorderItem], session: DbSession, user: CurrentUser
) -> list[HabitOut]:
    """Apply new display positions in one batch.

    Declared before `/{habit_id}` so the literal path wins the match.
    """
    ordering = [(item.habit_id, item.sort_order) for item in payload]
    return [HabitOut.from_habit(habit) for habit in reorder_habits(session, user, ordering)]


@router.patch("/{habit_id}", response_model=HabitOut)
def edit_habit(
    payload: HabitUpdate,
    session: DbSession,
    user: CurrentUser,
    habit_id: int = Path(ge=1),
) -> HabitOut:
    """Edit a habit's attributes. Partial update, forward-only."""
    habit = update_habit(
        session,
        user,
        habit_id,
        bucket_id=payload.bucket_id,
        name=payload.name,
        target_per_week=payload.target_per_week,
        time_cap_minutes=payload.time_cap_minutes,
        season_dependent=payload.season_dependent,
        sort_order=payload.sort_order,
        anytime=payload.anytime,
        clear_time_cap=payload.clear_time_cap,
    )
    return HabitOut.from_habit(habit)


@router.put("/{habit_id}/schedule", response_model=HabitOut)
def replace_schedule(
    payload: ScheduleUpdate,
    session: DbSession,
    user: CurrentUser,
    habit_id: int = Path(ge=1),
) -> HabitOut:
    """Replace the weekdays a habit is scheduled on. Forward-only."""
    return HabitOut.from_habit(set_schedule(session, user, habit_id, payload.weekdays))


@router.post("/{habit_id}/archive", response_model=HabitOut)
def archive(
    session: DbSession, user: CurrentUser, habit_id: int = Path(ge=1)
) -> HabitOut:
    """Archive a habit: a soft delete that preserves all of its history."""
    return HabitOut.from_habit(archive_habit(session, user, habit_id))
