# Habbi-Tracker

Welcome to Habbi-Tracker! A (currently) two-person habit tracker. Two people 
each keep a private daily board: open the app, see the habits scheduled for 
today, tick them off. The boards are fully separate — no shared habits, no 
visibility into each other's data. Right now, it has simply been one-shotted 
by Opus 5 after exhaustive planning, and is for myself and one other. Once 
deployed, I'll be slowly adding features to hopefully be more flexible for 
more people. Stay tuned!

## Habit Tracker — Phase 1: data model & domain layer

The product is a **calm, non-punitive recording tool**. It celebrates what gets
done and never flags, reddens or guilt-trips what doesn't. That single idea
justifies most of what follows: percentages that can only cap at 100%, no
"behind" or "exceeded" anywhere, and a past that is never rewritten.

This phase builds the foundation: the schema, the domain logic, the read models
the API will serve, the seed, and the tests. **There are no feature endpoints,
no frontend and no notifications here** — those are Phases 2–4.

---

## Quick start

Requires **Python 3.13**.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"    # Windows: .venv\Scripts\python.exe

make migrate    # create the schema and populate dim_date
make seed       # load User A (full board) and User B (empty board)
make test       # run the suite against SQLite
make run        # serve the API; GET /health returns {"status":"ok",...}
```

On Windows without GNU make, use the wrapper — same target names:

```powershell
.\make.ps1 migrate
.\make.ps1 seed
.\make.ps1 test
```

### Running against Postgres

Production is Postgres, so the suite has to pass there too. One command:

```bash
make test-postgres      # or: .\make.ps1 test-postgres
```

That starts the `docker-compose.yml` Postgres (on host port `5433`, to avoid
clashing with a locally installed one), waits for it to be healthy, and runs the
identical suite with `TEST_DATABASE_URL` pointed at it. To use Postgres as your
working database rather than just for tests:

```bash
docker compose up -d --wait
DATABASE_URL=postgresql+psycopg://habit:habit@localhost:5433/habit_tracker make migrate
DATABASE_URL=postgresql+psycopg://habit:habit@localhost:5433/habit_tracker make seed
```

Configuration lives in the environment; copy `.env.example` to `.env` to set it
locally. `.env` is gitignored — only the example, with placeholder values, is
tracked.

---

## Why the schema is shaped this way

It is a small **star schema**: one fact table with date, habit and user
dimensions around it. That is more structure than two users strictly need, and
it is deliberate — the shape is what makes trend queries trivial, and this is a
data project as much as an app.

```
users ──< buckets ──< habits ──< habit_schedules
  │                     │
  └────────< fact_completion >──── dim_date
                 (the grain)
```

**`fact_completion` has one row per (user, habit, date).** When a day is
materialised, every habit scheduled that day gets a row with `completed = false`.
So "scheduled but not done" is a *recorded fact*, not an absence you have to
infer from missing rows. Week and month rollups are then plain aggregations
rather than a reconstruction of what should have been there.

**`dim_date` is a classic pre-populated date dimension** (default 2025-01-01 to
2030-12-31). Keeping `iso_week`, `week_start_date`, `quarter` and friends in a
table means the same SQL works on SQLite and Postgres, instead of each engine's
own date arithmetic.

**Bonuses live in the same table**, as rows with `scheduled = false` and
`is_bonus = true`. They record something done on a day it wasn't expected, and
they are excluded from every percentage.

**Archiving, not deleting.** Removing a habit sets `active = false` and
`archived_at`. It stops being scheduled from that moment, but every fact row it
ever produced stays, so month views of the past remain accurate.

Integer surrogate keys throughout, except `dim_date`, which is keyed by its date.
Timestamps are timezone-aware UTC in storage; the user's timezone is used only
for day-boundary maths.

---

## The domain rules

All of these are enforced in `app/domain/` and covered by tests.

1. **Scheduling by weekday.** Each habit has a fixed set of weekdays
   (0 = Monday … 6 = Sunday). It is scheduled on a date if that date's weekday is
   in the set, the habit is active, and — for season-dependent habits — the
   user's season is on.

2. **The grain is (user, habit, date).** Enforced by a unique constraint.

3. **Materialisation is idempotent.** `ensure_day_materialised` writes any
   missing scheduled rows for a date and can be called repeatedly.
   `backfill` extends that from the user's last materialised day through a
   target date, so someone who skips a week still ends up with correct
   "scheduled but not completed" rows. It is capped (default 60 days) and never
   starts before the user existed.

4. **Edit window: today and yesterday**, in the user's timezone. Everything
   older is locked, and so is the future. Every mutation checks it.

5. **Ticking.** `complete_habit` sets `completed` and `completed_at`;
   `uncomplete_habit` clears both. Completing something already complete keeps
   the original timestamp, so the completed pile doesn't reshuffle on a repeat tap.

6. **Bonuses.** `add_bonus` logs a habit on a day it wasn't scheduled. Bonuses
   join the completed pile but are **excluded from the percentage** — a bonus
   *outside* the count, never a way past 100%.

7. **Daily percentage** = completed-scheduled ÷ total-scheduled, over
   `scheduled = true` rows only. Completed-scheduled is a subset of scheduled, so
   it caps at 1.0 naturally — there is no clamping code, and there is no
   "exceeded", "behind" or pace anywhere. If nothing was scheduled the answer is
   `None`, a rest day, **not** zero.

8. **No-data day.** A day reads as "no data" only when it is **locked** (older
   than yesterday) **and** nothing at all was completed. A locked 0% day is no
   data; today, unfinished, is not — it's still live.

9. **Season toggle.** `user.season_active` turns season-dependent habits on and
   off. When off they are neither scheduled nor counted, with no penalty.
   Flipping it affects future materialisation and current reads only; days
   already written keep exactly the rows they had.

10. **Sessions.** After a PIN check, an opaque token is issued that expires at
    the **next local midnight** in the user's timezone — the same boundary the
    edit window uses. Only a hash of the token is stored.

11. **Forward-only, non-destructive.** Editing a habit changes future
    materialisation and current reads, never an already-materialised day.
    Removing a habit archives it. Migrations never rewrite the past.

Celebration thresholds (halfway, last-one-left, 100%) are a **frontend** concern.
The backend returns the percentage and the counts; it does not decide when to cheer.

---

## Layout

```
app/
  main.py         FastAPI bootstrap — /health only in this phase
  config.py       pydantic-settings; everything comes from the environment
  db.py           engine/session, SQLite- and Postgres-aware
  clock.py        the single overridable source of "now"
  models/         SQLAlchemy models, one concern per file
  schemas/        Pydantic read models (TodayView, WeekView, …)
  domain/
    dates.py        local day boundaries, dim_date population
    scheduling.py   is_scheduled, ensure_day_materialised, backfill
    tracking.py     can_edit, complete/uncomplete/add_bonus
    reads.py        get_today, get_day_detail, get_week, get_month
    auth.py         PIN hashing, sessions
    errors.py       the domain's refusals
  seed/
    data.py         the seed boards as plain Python data
    seed.py         the guarded loader
alembic/          migrations
tests/            pytest
```

### The read models

`get_today`, `get_day_detail`, `get_week` and `get_month` return Pydantic models
that are UI-ready but presentation-free: no colours chosen, no copy, no
celebration logic. Percentages are fractions in `0.0–1.0`, or `None` for a rest
day. The active list is ordered by `(anytime, sort_order)` — timed habits in
morning-to-night order, then the ones with no natural time — and the completed
pile by `completed_at`, i.e. the order things were actually ticked.

**Reads are pure.** They never write. A caller that needs today's rows to exist
runs `backfill` first; Phase 2's API layer will do that on the way in.

### Testing

Two things make the suite deterministic: it runs against a database built by
**Alembic** (not `create_all`, so model/migration drift fails the tests), and
nothing reads the system clock. `app/clock.py` provides an overridable `utcnow`,
every timezone-sensitive domain function accepts an explicit `now`, and the
tests pin both — so the timezone and edit-window assertions give the same answer
today and in five years.

---

## Seed data

**User A** — a full board: 8 buckets and 29 habits, with weekday schedules, time
caps, season flags and `anytime` flags. This is the dataset the tests exercise.

**User B** — the same app, no habits. Their board gets filled in through the app
later; nothing has been invented for them.

Display names are the generic placeholders `"User A"` and `"User B"` — rename
them in-app.

### Public demo board vs. private board

`app/seed/data.py` is public and holds a **demo board**: 29 habits with generic
names carrying exactly the scheduling, caps and flags a real board uses. That is
what the tests run against and what a fresh clone gets.

Real habit names belong in `app/seed/data_local.py`, which is **gitignored**.
When that file exists the seed uses it; otherwise it falls back to the demo
board. Copy `data_local.example.py` to get started — it documents the contract.
`make seed` prints which source it used.

```
Seed source: public demo board.
Seeded 'User A' with 29 habits.
```

The tests deliberately seed the demo boards *explicitly* rather than calling
`seed_all`, so the suite asserts the same things whether or not a developer has a
private file.

### Guarded and non-destructive

A user whose display name already exists is left completely alone, so the seed is
safe to run on every deploy. It never updates or deletes anything.

Three bucket colours (Life admin, Social, Team sport) are marked
`provisional_color` — the core palette has five colours and these are harmonious
stand-ins, expected to be adjusted.

### PINs

A PIN is **exactly six digits** (`PIN_LENGTH`, default 6). The format is checked
when a PIN is *set* and never when one is *verified* — a wrong guess at login is
an expected outcome, not an error.

Seed PINs come from `SEED_USER_A_PIN` / `SEED_USER_B_PIN`, so no PIN is written
into the repository. The values in `.env.example` are development throwaways.

A seeded PIN is marked **provisional** (`users.pin_is_provisional`), because
provisioning issued it rather than the person choosing it. `set_pin` clears the
flag, and Phase 2's login will surface it so the person is asked to pick their
own. The flag records where a PIN came from, not what it is — so someone who
deliberately chooses the same digits the seed happened to use is never asked to
change them. Once both people have set their own PIN, production no longer needs
`SEED_USER_*_PIN` in its environment at all.

A note on the schedules: a weekly one-off that could in principle happen on any
of several days (e.g. seeing a friend once a week) is pinned to a **single
representative weekday**. That keeps the grain honest — "scheduled" means
"expected that day". Flexible "any N days per week" habits are a deliberate
future enhancement, out of scope here.

---

## Dormant: designed-for, not built

Notifications are out of scope for v1, but the schema should not need a rewrite
when they arrive. Two fields exist and **nothing reads them**:

- `users.reminders_enabled`
- `habits.reminder_time`

There is no delivery, no scheduling and no UI for either. That is intentional.

---

## Assumptions made while building

Recorded here rather than expanded into scope. All are in `docs/DECISIONS.md` too.

- **`daily_pct` returns a fraction** (`0.0–1.0`), not `0–100`. Formatting is the
  frontend's job.
- **`complete_habit` requires an existing row.** Completing a habit that was not
  scheduled raises `HabitNotScheduled` and points at `add_bonus`, keeping the
  two concepts distinct rather than silently inventing a row.
- **Un-completing a bonus keeps the row** as an inert
  `scheduled=false, completed=false` record that no read surfaces. Logging the
  bonus again re-completes that same row.
- **`available_extras` is "active habits with nothing logged today"**, so a habit
  already logged as a bonus leaves the picker. Season-dependent habits still
  appear when the season is off — you can log an out-of-season one-off as a bonus.
- **A day where only a bonus was done is not "no data".** Something happened.
- **Session expiry is exclusive at the boundary**: a token whose `expires_at` is
  exactly now has expired. Signing in at 23:59 therefore buys a minute, not
  another day — the cost of an unambiguous boundary.
- **Archived habits are not schedulable and not tickable**, but their history is
  fully preserved and still appears in week and month views.
- **`habits.sort_order` is display-only**, so reordering habits in-app (Phase 2/3)
  needs no schema change and cannot distort past percentages.
- **PIN brute-force throttling is Phase 2**, where the request context that makes
  rate limiting meaningful actually exists.

## Not built in this phase

HTTP feature endpoints (login, today, tick, week, month), the React/Vite PWA,
mascot assets and celebration logic, notification delivery, the warehouse
pipeline, and flexible "any N days per week" habits.
