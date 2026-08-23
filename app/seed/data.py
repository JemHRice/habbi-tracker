"""Seed content as plain Python data, kept separate from the loading logic.

**This file is public.** It holds a *demo* board: 29 habits with generic names,
carrying exactly the scheduling, time caps, season flags and `anytime` flags the
real board uses. That is what the test suite runs against, and what anyone
cloning the repository gets.

Real habit names live in `app/seed/data_local.py`, which is gitignored. If that
file exists, :func:`load_boards` uses it; otherwise the demo board is used. See
`data_local.example.py` for the contract.

Two boards are seeded either way:

* **Board A** — a full board of 8 buckets and 29 habits.
* **Board B** — the same app with no habits. Nothing is invented for it here.

Display names are deliberately generic placeholders. Rename in-app.

A note on the schedules: a weekly one-off that could in principle happen on any
of several days (e.g. seeing a friend once a week) is pinned to a single
representative weekday. That keeps the grain honest — "scheduled" means
"expected that day". Flexible "any N days per week" habits are a future
enhancement, deliberately out of scope.
"""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass, field
from types import ModuleType

ALL_WEEK = (0, 1, 2, 3, 4, 5, 6)
WEEKDAYS = (0, 1, 2, 3, 4)


@dataclass(frozen=True)
class BucketSeed:
    """A habit category and the colour the UI paints it with."""

    name: str
    color_hex: str
    sort_order: int
    provisional_color: bool = False
    """True where the colour is a harmonious stand-in, not a palette colour.
    These three are expected to be adjusted once the palette is finalised."""


@dataclass(frozen=True)
class HabitSeed:
    """One habit and the weekdays it is expected on."""

    sort_order: int
    name: str
    bucket: str
    target_per_week: int
    weekdays: tuple[int, ...]
    time_cap_minutes: int | None = None
    season_dependent: bool = False
    anytime: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Board:
    """One person's starting board: who they are and what is on it."""

    display_name: str
    buckets: tuple[BucketSeed, ...]
    habits: tuple[HabitSeed, ...]


# Core palette from the moodboard: olive, rose, sky, blush, gold.
DEMO_BUCKETS: tuple[BucketSeed, ...] = (
    BucketSeed("Self-care", "#CA758A", 1),
    BucketSeed("Health", "#99B4D2", 2),
    BucketSeed("Study", "#6C6C2C", 3),
    BucketSeed("Career", "#DFC980", 4),
    BucketSeed("Relationship", "#E5C2CA", 5),
    BucketSeed("Life admin", "#C9B7A0", 6, provisional_color=True),
    BucketSeed("Social", "#E8A9B8", 7, provisional_color=True),
    BucketSeed("Team sport", "#8A9A5B", 8, provisional_color=True),
)

# `sort_order` is the hand-set chronological display order, morning to night.
# `anytime` habits sort after all timed habits regardless of this number.
DEMO_HABITS: tuple[HabitSeed, ...] = (
    HabitSeed(1, "Morning water", "Self-care", 7, ALL_WEEK),
    HabitSeed(2, "Morning skincare", "Self-care", 7, ALL_WEEK),
    HabitSeed(3, "Brush teeth (AM)", "Self-care", 7, ALL_WEEK),
    HabitSeed(4, "Shower", "Self-care", 7, ALL_WEEK),
    HabitSeed(5, "Meal prep", "Life admin", 5, WEEKDAYS),
    HabitSeed(6, "Focused project work", "Career", 5, WEEKDAYS, time_cap_minutes=30),
    HabitSeed(7, "Career admin", "Career", 5, WEEKDAYS, time_cap_minutes=40),
    HabitSeed(8, "Coursework", "Study", 5, WEEKDAYS, time_cap_minutes=60),
    HabitSeed(9, "Deep study block", "Study", 4, (1, 2, 3, 4), time_cap_minutes=20),
    HabitSeed(10, "Certification study", "Study", 4, (0, 2, 4, 5), time_cap_minutes=30),
    HabitSeed(11, "Movement / gym", "Health", 5, WEEKDAYS, time_cap_minutes=20),
    HabitSeed(12, "Training prep", "Team sport", 1, (0,), time_cap_minutes=20),
    HabitSeed(13, "Team training", "Team sport", 1, (1,), season_dependent=True),
    HabitSeed(14, "Midweek match", "Health", 1, (3,)),
    HabitSeed(15, "Weekend fixture", "Team sport", 1, (5,), season_dependent=True),
    HabitSeed(16, "Reading", "Health", 7, ALL_WEEK, time_cap_minutes=20),
    HabitSeed(17, "Evening skincare", "Self-care", 7, ALL_WEEK),
    HabitSeed(18, "Brush teeth (PM)", "Self-care", 7, ALL_WEEK),
    HabitSeed(19, "Put clothes away", "Life admin", 7, ALL_WEEK),
    HabitSeed(20, "Tidy desk", "Life admin", 7, ALL_WEEK),
    HabitSeed(21, "Laundry", "Life admin", 2, (2, 5)),
    HabitSeed(22, "Finance review", "Life admin", 1, (5,)),
    HabitSeed(23, "See a friend", "Social", 1, (5,)),
    HabitSeed(24, "Quality time", "Relationship", 2, (5, 6)),
    HabitSeed(25, "Wind down early", "Self-care", 5, (0, 1, 2, 4, 5)),
    HabitSeed(26, "Full night's sleep", "Self-care", 7, ALL_WEEK),
    HabitSeed(27, "Water through the day", "Self-care", 7, ALL_WEEK, anytime=True),
    HabitSeed(28, "Daily check-in", "Relationship", 7, ALL_WEEK, anytime=True),
    HabitSeed(29, "Small kind gesture", "Relationship", 1, (2,), anytime=True),
)

DEMO_BOARD_A = Board("User A", DEMO_BUCKETS, DEMO_HABITS)
DEMO_BOARD_B = Board("User B", (), ())


LOCAL_MODULE = "app.seed.data_local"


def _local_module() -> ModuleType | None:
    """Import the private seed module, or return None if it does not exist.

    Deliberately checks for the file with `find_spec` rather than catching
    `ImportError` around the import: if `data_local.py` exists but is broken,
    that error must surface, not be mistaken for "no local board" and silently
    replaced by the demo one.
    """
    if importlib.util.find_spec(LOCAL_MODULE) is None:
        return None
    return importlib.import_module(LOCAL_MODULE)


def load_boards() -> tuple[Board, Board]:
    """Return the two boards to seed.

    Uses `app/seed/data_local.py` when that file exists — that is where real
    habit names live, kept out of version control — and falls back to the demo
    board otherwise. The fallback is what CI and a fresh clone get.
    """
    module = _local_module()
    if module is None:
        return DEMO_BOARD_A, DEMO_BOARD_B
    return module.BOARD_A, module.BOARD_B


def using_local_board() -> bool:
    """Return True if a private `data_local.py` is providing the seed content."""
    return _local_module() is not None
