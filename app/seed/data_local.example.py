"""Template for `app/seed/data_local.py` — copy it, drop the `.example`.

`data_local.py` is gitignored. Anything personal (real habit names, real display
names) belongs there rather than in `data.py`, which is public. When the file
exists, `app.seed.data.load_boards()` uses it; when it does not, the public demo
board is used instead, so CI and a fresh clone still work.

Both boards must be defined, even if one is empty.
"""

from __future__ import annotations

from app.seed.data import ALL_WEEK, WEEKDAYS, Board, BucketSeed, HabitSeed

BUCKETS: tuple[BucketSeed, ...] = (
    BucketSeed("Self-care", "#CA758A", 1),
    BucketSeed("Health", "#99B4D2", 2),
)

HABITS: tuple[HabitSeed, ...] = (
    # sort_order, name, bucket, target_per_week, weekdays, then keyword extras.
    HabitSeed(1, "Drink water", "Self-care", 7, ALL_WEEK),
    HabitSeed(2, "Movement", "Health", 5, WEEKDAYS, time_cap_minutes=20),
    HabitSeed(3, "Evening walk", "Health", 2, (2, 5), anytime=True),
)

BOARD_A = Board("User A", BUCKETS, HABITS)
BOARD_B = Board("User B", (), ())
