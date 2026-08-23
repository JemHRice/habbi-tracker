# BUILD PROMPT — Phase 1: Data Model & Domain Layer

You are a Claude Code agent. Build the **data model, persistence layer, and domain
logic** for a two-person habit-tracker application, exactly as specified below.
This is Phase 1 of a larger project. **Do not build** the HTTP API surface, the
frontend/PWA, mascot assets, or notifications — those are later phases and are listed
under "Out of scope" below. Stay in this lane.

Work methodically. After each major step, run the test suite and confirm it passes
before moving on. Write code that a competent engineer can read and fully understand
— clear names, docstrings on every public function, and a README that explains the
model. No cleverness for its own sake.

---

## 1. Project context (why this exists)

Two people (referred to as **User A** and **User B**) each keep a private daily habit
board. Boards are fully separate — no shared habits, no visibility into each other's
data. Each person opens a phone app, sees the habits scheduled for *today*, and ticks
them off. The product philosophy is **calm and non-punitive**: it records and
celebrates what gets done and never flags or penalises what doesn't. Keep that ethos
in mind — it justifies several modelling choices (e.g. percentages that can only ever
cap at 100%, no "behind/exceeded" concepts).

This phase builds the foundation the rest of the app stands on: an **analytics-shaped
schema** (a completion fact table with date/habit/user dimensions), the domain logic
for scheduling, ticking, the edit window, the season toggle, and the read models the
future API will expose.

---

## 2. Locked technical decisions (do not deviate)

| Area | Decision |
|---|---|
| Language | Python 3.12 |
| ORM | SQLAlchemy 2.0 (declarative, typed) |
| Migrations | Alembic |
| Validation/DTOs | Pydantic v2 |
| Settings | pydantic-settings, config via env (`DATABASE_URL`) |
| Local DB | SQLite |
| Production DB | PostgreSQL (schema must run on both) |
| PIN hashing | argon2 (via `passlib` or `argon2-cffi`) |
| Timezones | `zoneinfo`; per-user timezone, default `Australia/Sydney` |
| Tests | pytest |
| Web framework (scaffold only) | FastAPI — bootstrap the app + a `/health` route, **no feature endpoints this phase** |

Use integer surrogate primary keys throughout (except `dim_date`, keyed by its date).
Everything must run identically on SQLite (dev) and Postgres (prod); avoid engine-
specific SQL. Include a `docker-compose.yml` that stands up a local Postgres so the
Postgres path is testable.

---

## 3. Core domain rules (the logic that must be correct)

Implement these precisely; they are the heart of the phase and must be unit-tested.

1. **Scheduling by weekday.** Each habit is scheduled on a fixed set of weekdays
   (0 = Monday … 6 = Sunday). A habit is "scheduled" on a date if that date's weekday
   is in its schedule **and** (if the habit is season-dependent) the user's season is
   active.

2. **The completion fact grain is one row per `(user, habit, date)`.** For every
   scheduled habit on every date, a fact row exists with `scheduled = true`,
   `completed` starting false. This is what makes "scheduled but not done" a
   first-class, queryable fact rather than an inferred absence.

3. **Day materialisation (idempotent).** Provide a function that, for a given user and
   date, ensures scheduled fact rows exist for all habits scheduled that date. It must
   be safe to call repeatedly (no duplicates — rely on the unique constraint). Also
   provide an idempotent **backfill** that materialises every date from the user's last
   materialised date through a target date, so a user who skips days still ends up with
   correct "scheduled but incomplete" rows. Cap backfill to a sane window (e.g. 60 days)
   to avoid runaway generation.

4. **Edit window.** A date is editable only if it is **today or yesterday** in the
   user's timezone. `can_edit(user, date)` enforces this. All mutating operations
   (complete, uncomplete, add bonus) must reject dates outside the window.

5. **Ticking.** `complete_habit(user, habit, date)` sets `completed = true` and
   `completed_at = now`. `uncomplete_habit(...)` reverses it (`completed = false`,
   `completed_at = null`). Both respect the edit window.

6. **Bonus / "add something extra".** A user may complete a habit on a date it was
   **not** scheduled. This inserts a fact row with `scheduled = false`,
   `is_bonus = true`, `completed = true`. Bonuses are **excluded** from the daily
   percentage — they are a bonus *outside* the count. Respect the edit window.

7. **Daily percentage.** `daily_pct(user, date) = completed_scheduled / total_scheduled`
   over that `(user, date)`, counting only rows where `scheduled = true`. Because
   completed-scheduled is always a subset of scheduled, this **naturally caps at 100%**
   — do not add over-100 logic. If `total_scheduled = 0`, return `null` (a rest day),
   not a divide-by-zero. There is **no** "exceeded", no "behind", no pace/ahead-behind
   anywhere. Those concepts are retired.

8. **No-data day.** A past date reads as "no data" (the state the UI will represent with
   the mascot) only when it is **locked** (older than yesterday) **and** has zero
   completed rows. A locked 0% day is "no data"; an editable unfinished day is not.

9. **Season toggle.** `user.season_active` (bool). When false, season-dependent habits
   are neither scheduled nor materialised, and are absent from all counts — with no
   penalty. Flipping it affects only *future* materialisation and *current* reads;
   already-materialised past rows are not rewritten.

10. **Sessions (PIN auth support).** After PIN verification, issue an opaque session
    token whose **expiry is the next local midnight in the user's timezone** (day-
    boundary expiry, the same boundary used by the edit window). Store a hash of the
    token. Provide verify/expire. (No HTTP login endpoint this phase — just the domain
    functions and their tests.)

11. **Habit changes are forward-only and non-destructive.** Editing a habit's schedule
    (or any attribute) affects only **future** materialisation and current reads; days
    already materialised keep exactly the rows they had — no retroactive reshaping of a
    week in progress. Removing a habit is an **archive** (`active = false`,
    `archived_at` set), never a hard delete: the habit stops being scheduled/materialised
    from that point, but every past `fact_completion` row it produced stays intact, so
    history remains honest. This mirrors the season-toggle rule (9) and the edit-window
    rule (4): the past is never rewritten.

Celebration thresholds (halfway, last-one-left, done) are **frontend** concerns. The
backend only returns the daily percentage and the done/remaining counts; do not
implement celebration logic here.

---

## 4. Schema

Convention: weekdays are integers 0–6, Monday = 0. Timestamps are timezone-aware UTC
in storage; convert to the user's zone only for day-boundary calculations.

### `users`
- `id` PK
- `display_name` text, not null
- `email` text, nullable, unique
- `pin_hash` text, not null (argon2)
- `timezone` text, not null, default `'Australia/Sydney'`
- `season_active` bool, not null, default false
- `reminders_enabled` bool, not null, default false  *(dormant — see §6)*
- `created_at`, `updated_at`

### `buckets`
- `id` PK
- `user_id` FK → users.id, not null
- `name` text, not null
- `color_hex` text, not null
- `sort_order` int, not null
- `created_at`
- unique(`user_id`, `name`)

### `habits`
- `id` PK
- `user_id` FK → users.id, not null
- `bucket_id` FK → buckets.id, not null
- `name` text, not null
- `target_per_week` int, not null  *(reference/config; currently equals the number of
  scheduled weekdays. Not used to cap or penalise. Retained for clarity and future
  flexible-target habits.)*
- `time_cap_minutes` int, nullable
- `season_dependent` bool, not null, default false
- `sort_order` int, not null  *(fixed chronological display order, morning → night)*
- `anytime` bool, not null, default false  *(habits with no natural time; always sort
  after timed habits regardless of sort_order)*
- `reminder_time` time, nullable  *(dormant — see §6)*
- `active` bool, not null, default true  *(soft delete)*
- `created_at`, `updated_at`, `archived_at` (nullable)
- index(`user_id`, `active`)

### `habit_schedules`
- `id` PK
- `habit_id` FK → habits.id, not null
- `weekday` int, not null (0–6)
- unique(`habit_id`, `weekday`)

### `dim_date`  *(classic date dimension)*
- `date` DATE PK
- `year` int, `quarter` int, `month` int, `month_name` text
- `day_of_month` int
- `weekday` int (0–6), `weekday_name` text
- `iso_week` int, `week_start_date` DATE (the Monday of that week)
- `is_weekend` bool
- Populate a parameterised range; default **2025-01-01 → 2030-12-31**.

### `fact_completion`  *(grain: one row per user + habit + date)*
- `id` PK
- `user_id` FK → users.id, not null
- `habit_id` FK → habits.id, not null
- `date` DATE FK → dim_date.date, not null
- `scheduled` bool, not null
- `completed` bool, not null, default false
- `completed_at` timestamptz, nullable
- `is_bonus` bool, not null, default false
- `created_at`, `updated_at`
- unique(`user_id`, `habit_id`, `date`)
- index(`user_id`, `date`), index(`habit_id`, `date`)

### `sessions`
- `id` PK
- `user_id` FK → users.id, not null
- `token_hash` text, not null, unique
- `expires_at` timestamptz, not null
- `created_at`
- index(`token_hash`)

---

## 5. Domain / service layer (public functions to implement and test)

Group these into clean modules (e.g. `domain/scheduling.py`, `domain/tracking.py`,
`domain/reads.py`, `domain/auth.py`). Each takes a DB session explicitly. Enforce all
rules from §3.

**Scheduling & materialisation**
- `is_scheduled(habit, date, *, season_active) -> bool`
- `ensure_day_materialised(session, user, date) -> None`
- `backfill(session, user, through_date) -> None`  *(idempotent, capped)*

**Auth**
- `create_user(session, display_name, pin, timezone=...) -> User`
- `verify_pin(user, pin) -> bool`
- `create_session(session, user) -> (token, expires_at)`  *(expiry = next local midnight)*
- `validate_session(session, token) -> User | None`
- `expire_session(session, token) -> None`

**Edit window & mutations**
- `can_edit(user, date) -> bool`  *(today or yesterday in user's tz)*
- `complete_habit(session, user, habit, date) -> FactCompletion`
- `uncomplete_habit(session, user, habit, date) -> FactCompletion`
- `add_bonus(session, user, habit, date) -> FactCompletion`

**Reads (return Pydantic models; these are what the future API will serve)**
- `get_today(session, user) -> TodayView`
  - Active (not-yet-completed) scheduled habits, ordered by `(anytime asc, sort_order asc)`
  - Completed pile, ordered by `completed_at asc` (tick order)
  - `daily_pct` (scheduled only, or null on a rest day)
  - `done_count`, `remaining_count`
  - `available_extras`: the user's other active habits **not** scheduled today (for the
    "add extra" picker)
  - `bonuses`: bonus completions logged today
- `get_day_detail(session, user, date) -> DayDetailView`
  - What was / wasn't done, plus `final_pct`; `no_data` flag per §3.8
- `get_week(session, user, containing_date) -> WeekView`
  - Seven days (Mon–Sun of that week), each with its `pct` and a `locked_empty` flag
- `get_month(session, user, year, month) -> MonthView`
  - Per-habit completion rate for the month: `completed_days / scheduled_days`
    (this powers "what stuck / what slipped", shown **factually** — no red, no ranking)
  - Per-day calendar fill value (the day's pct) plus `no_data` flags for the calendar

Return shapes should be UI-ready but presentation-free (no colours, no copy).

---

## 6. Dormant (build the shape, not the feature)

Notifications are **out of scope** for v1 but must not require a schema rewrite later.
Include the fields only — `users.reminders_enabled` and `habits.reminder_time` — and
do nothing with them. No delivery, no scheduling, no UI. Note them in the README as
"designed-for, not built."

---

## 7. Seed data

Seed **two users**.

> **Redacted for publication (2026-08-23).** This repository is public, so the table
> below is the **demo board** that ships in `app/seed/data.py`: generic habit names
> carrying exactly the real scheduling, caps and flags. The real habit names live in
> `app/seed/data_local.py`, which is gitignored; the seed prefers that file when it
> exists and falls back to this demo board otherwise. Nothing else about the seed —
> counts, weekdays, caps, season and `anytime` flags — has changed.

**User A — full board (this is the tested dataset).** 8 buckets, 29 habits with
the attributes below. Bucket colours draw from a five-colour palette (olive `#6C6C2C`,
rose `#CA758A`, sky `#99B4D2`, blush `#E5C2CA`, gold `#DFC980`); three buckets use
provisional harmonious extras — mark them adjustable.

Bucket → colour:
- Self-care → `#CA758A` (rose)
- Health → `#99B4D2` (sky)
- Study → `#6C6C2C` (olive)
- Career → `#DFC980` (gold)
- Relationship → `#E5C2CA` (blush)
- Life admin → `#C9B7A0` (provisional)
- Social → `#E8A9B8` (provisional)
- Team sport → `#8A9A5B` (provisional)

Habits (`sort_order` = the number in the first column; weekdays 0=Mon…6=Sun;
`target` = target_per_week; `cap` = time_cap_minutes; `season` = season_dependent;
`anytime` where noted):

| # | Habit | Bucket | target | cap | weekdays | season | anytime |
|---|---|---|---|---|---|---|---|
| 1 | Morning water | Self-care | 7 | – | 0,1,2,3,4,5,6 | N | N |
| 2 | Morning skincare | Self-care | 7 | – | 0,1,2,3,4,5,6 | N | N |
| 3 | Brush teeth (AM) | Self-care | 7 | – | 0,1,2,3,4,5,6 | N | N |
| 4 | Shower | Self-care | 7 | – | 0,1,2,3,4,5,6 | N | N |
| 5 | Meal prep | Life admin | 5 | – | 0,1,2,3,4 | N | N |
| 6 | Focused project work | Career | 5 | 30 | 0,1,2,3,4 | N | N |
| 7 | Career admin | Career | 5 | 40 | 0,1,2,3,4 | N | N |
| 8 | Coursework | Study | 5 | 60 | 0,1,2,3,4 | N | N |
| 9 | Deep study block | Study | 4 | 20 | 1,2,3,4 | N | N |
| 10 | Certification study | Study | 4 | 30 | 0,2,4,5 | N | N |
| 11 | Movement / gym | Health | 5 | 20 | 0,1,2,3,4 | N | N |
| 12 | Training prep | Team sport | 1 | 20 | 0 | N | N |
| 13 | Team training | Team sport | 1 | – | 1 | **Y** | N |
| 14 | Midweek match | Health | 1 | – | 3 | N | N |
| 15 | Weekend fixture | Team sport | 1 | – | 5 | **Y** | N |
| 16 | Reading | Health | 7 | 20 | 0,1,2,3,4,5,6 | N | N |
| 17 | Evening skincare | Self-care | 7 | – | 0,1,2,3,4,5,6 | N | N |
| 18 | Brush teeth (PM) | Self-care | 7 | – | 0,1,2,3,4,5,6 | N | N |
| 19 | Put clothes away | Life admin | 7 | – | 0,1,2,3,4,5,6 | N | N |
| 20 | Tidy desk | Life admin | 7 | – | 0,1,2,3,4,5,6 | N | N |
| 21 | Laundry | Life admin | 2 | – | 2,5 | N | N |
| 22 | Finance review | Life admin | 1 | – | 5 | N | N |
| 23 | See a friend | Social | 1 | – | 5 | N | N |
| 24 | Quality time | Relationship | 2 | – | 5,6 | N | N |
| 25 | Wind down early | Self-care | 5 | – | 0,1,2,4,5 | N | N |
| 26 | Full night's sleep | Self-care | 7 | – | 0,1,2,3,4,5,6 | N | N |
| 27 | Water through the day | Self-care | 7 | – | 0,1,2,3,4,5,6 | N | **Y** |
| 28 | Daily check-in | Relationship | 7 | – | 0,1,2,3,4,5,6 | N | **Y** |
| 29 | Small kind gesture | Relationship | 1 | – | 2 | N | **Y** |

**User B — empty board.** Create the user (default timezone, a PIN) with **no habits**.
Their habit content has not been defined yet and will be added later via the app or a
future seed. Do not invent habits for User B.

> **Modelling note for the agent (do not "fix" this):** weekly one-off habits that in
> principle could happen on any of several days (e.g. "see a friend, once a week, Fri
> *or* Sat *or* Sun") are pinned to a **single representative scheduled day** in this
> model (here, Saturday). This keeps the "scheduled = expected that day" grain clean.
> Flexible "any N days per week" habits are a deliberate **future enhancement**, out of
> scope for this phase.

---

## 8. Repository layout

```
habit-tracker/
  app/
    main.py                 # FastAPI bootstrap + /health only
    config.py               # pydantic-settings, DATABASE_URL
    db.py                   # engine/session, SQLite+Postgres aware
    models/                 # SQLAlchemy models (one concern per file is fine)
    schemas/                # Pydantic read models (TodayView, WeekView, ...)
    domain/
      scheduling.py
      tracking.py
      reads.py
      auth.py
    seed/
      seed.py               # loads User A (full) + User B (empty)
      data.py               # the seed tables above as Python data
  alembic/                  # migrations
  tests/                    # pytest
  docker-compose.yml        # local Postgres
  .env.example
  Makefile                  # common commands (migrate, seed, test, run)
  README.md
  pyproject.toml            # or requirements.txt
```

---

## 9. Tests (must pass on both SQLite and Postgres)

Cover at minimum:
- Migrations apply cleanly; all tables/constraints/indexes exist.
- `dim_date` populated for the configured range with correct derived fields.
- Seed loads: User A has 8 buckets and 29 habits with correct schedules; User B empty.
- `is_scheduled` respects weekday and season flag.
- `ensure_day_materialised` is idempotent (calling twice creates no duplicates).
- `backfill` fills the gap and is capped.
- Edit window: today/yesterday editable; two-days-ago rejected (use a fixed/frozen
  clock in a known timezone).
- `complete_habit` / `uncomplete_habit` round-trip; `completed_at` set/cleared.
- `add_bonus` on an unscheduled day creates a `scheduled=false, is_bonus=true` row and
  is **excluded** from `daily_pct`.
- `daily_pct`: correct value; caps at 100%; returns null when nothing scheduled;
  ignores bonuses.
- `no_data`: locked-empty day flagged; editable-unfinished day not flagged.
- Season toggle changes the scheduled set and the counts.
- Sessions: token issued, validates, expires exactly at next local midnight in the
  user's timezone.
- Read models (`get_today`, `get_week`, `get_month`, `get_day_detail`) return the
  documented shapes with correct ordering (active by `(anytime, sort_order)`; completed
  by `completed_at`).

Use a frozen clock / injectable "now" so timezone and edit-window tests are
deterministic. Do not rely on the real system date.

---

## 10. Definition of done

- `make migrate && make seed && make test` succeeds on SQLite.
- The same succeeds against the docker-compose Postgres (document the one-command path).
- `uvicorn app.main:app` serves `/health` returning OK.
- README explains: the domain rules (§3), the schema and why it's shaped this way (the
  fact table + dimensions), how to run everything, and which fields are dormant (§6).
- Every public domain function has a docstring. No feature endpoints, no frontend, no
  notification logic exists.

---

## 11. Out of scope (do NOT build this phase)

- HTTP API feature endpoints (login, today, tick, week, month) — **next phase**.
- Frontend / React / Vite / PWA / offline caching.
- Mascot ("Habbi") assets, illustrations, animations, celebration logic.
- Notification delivery or scheduling (fields only, dormant).
- Warehouse / dbt / Snowflake analytics pipeline — **phase 2**.
- Flexible "any N days per week" habit type — future enhancement.

Build only what §1–§10 describe. If a requirement seems ambiguous, prefer the simplest
interpretation consistent with the calm, non-punitive philosophy, and note the
assumption in the README rather than expanding scope.
