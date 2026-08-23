# DECISIONS — Habit Tracker

A running log of what we chose and why. Check this before making a choice. When a new
decision is made, add it here as part of the same change. Newest decisions can go at the
bottom of each section.

Format: **Decision** — rationale. (Alternatives considered / rejected, where useful.)

---

## Product & philosophy
- **Calm, non-punitive recording tool** — celebrate what's done, never flag what isn't.
  Drives many downstream choices (100% cap, no pace, no shaming). This is the north star.
- **Two fully separate boards, no shared habits** — simplifies the model to two
  independent single-user trackers sharing a codebase and login. (Dropped shared/hybrid
  boards entirely.)
- **Portfolio-grade + personal data project** — choices weigh "does this make a better
  data/portfolio piece", not just "does it work".

## Interface
- **Today screen: self-sorting checklist** — only today's scheduled habits, in a fixed
  chronological (hand-set) display order. Ticked items strike through and drop to a
  completed pile at the bottom, stacked in tick order; the next active habit rises to top.
- **Display order is fixed; tick order is free** — you can tick in any sequence. Nothing is
  gated behind completing another habit. "Fixed order" means display only, not sequential
  unlocking.
- **No-natural-time habits sort to the end** (an `anytime` flag), since they can't be done
  until later in the day anyway.
- **Un-tick restores** a completed item to its place in the active list.
- **Daily % = scheduled habits only**, shown numerically *and* visually, at the top.
- **"Add something extra"** — completes an unscheduled habit from the user's own list; joins
  the completed pile but is a **bonus that does NOT count toward the %**. ("Done my day
  *and* a bonus.")
- **Celebration ladder** (all encouraging, never punishing): halfway = small "yippee";
  last-one-left = gentle "let's keep going"; **100% = big mascot moment** with extra
  flourish. No negative/failure state ever rendered for an unfinished day.
- **Tracking tab is for looking back, not ticking.** Weekly = simple/calming overview of
  each day. Monthly = richer: per-habit completion trends (factual, no red, no ranking) +
  colour-coded calendar; tap a day for detail.
- **Calendar day states:** a day shows its real completion %; a **locked-empty** day (past
  the edit window with zero completions) shows the mascot "no data here"; weekly view shows
  a locked-empty day crossed out. There is **no separate "partial" state** — a half-done
  day simply shows its real %.
- **Past-day detail** (from calendar): what was/wasn't done + final %. Read-only when locked.
- **No welcome/onboarding** beyond the one-time "who are you?" device binding — straight to
  the checklist.
- **Both users' apps look the same**, only the data differs.
- **No reminders / no nudges** — deliberate, to keep it pressure-free.

## Editing & history
- **Edit window: today + yesterday editable; older locked.** Reinforces the habit (catch up
  one day) without letting history be rewritten. Cutoff at the **day boundary (local
  midnight)** in the user's timezone.
- **Older gaps are permanent** — miss two+ days and the older day keeps its real number
  (often 0% → reads as "no data"). Consistent with the no-pressure ethos (mascot shrugs).
- **Remove a habit = archive, not delete** — habit gets `active=false` + `archived_at`; its
  past completion history is preserved and still appears in week/month views. No hard delete.
- **Schedule/attribute edits apply forward-only** — changing a habit never retroactively
  reshapes an already-materialised week. The past is immutable.

## Completion maths
- **Percentages cap at 100% for both boards** — completed-scheduled is always a subset of
  scheduled, so this falls out naturally; add no over-100 logic.
- **"Exceeded" is fully retired** (was in the original Excel) — extras are a daily bonus
  only, never pushing any habit past 100% in weekly/monthly trends. Simpler and calmer.
- **No pace / no "ahead-behind"** anywhere. Retired along with exceeded.

## Data model
- **History is persistent from day one** — forced by the monthly trends + calendar; it's
  also what makes this a *data* project.
- **Fact table grain: one row per (user, habit, date)** — a completion log. Scheduled
  habits get a row each day (`scheduled=true`, `completed` starts false), so "scheduled but
  not done" is a first-class queryable fact, not an inference. (Chosen over row-per-tick.)
- **Analytics-shaped / star schema** — a `fact_completion` with `dim_date` + habit/user
  dimensions. Mild overkill for two users, deliberately, because the shape is the portfolio
  point and makes trend queries trivial.
- **`dim_date`** — classic date dimension, pre-populated (default 2025–2030).
- **Scheduling by explicit weekday** (`habit_schedules`, weekday 0=Mon…6=Sun).
- **Weekly one-off habits are pinned to a single representative day** (e.g. "see a friend"
  1×/wk → Saturday). Flexible "any N days per week" habits are a **future enhancement**, out
  of scope for v1. (This keeps the "scheduled = expected that day" grain clean.)
- **`target_per_week`** retained as reference/config (currently equals the count of
  scheduled weekdays); not used to cap or penalise.
- **Season toggle** is a per-user setting (`season_active`). When off, season-dependent
  habits (the team-sport training + weekend fixture) are neither scheduled nor counted
  — no penalty. Flipping affects only future materialisation + current reads.
- **Day materialisation** is idempotent; an idempotent backfill fills gaps so missed days
  still get correct "scheduled but incomplete" rows.

## Architecture
- **Frontend: React + TypeScript + Vite, as an installable PWA.** TS for a stateful tap-heavy
  UI; Vite over Next.js because the app needs no SSR and a clean SPA is the honest engineering
  call ("make it work, not tick keyword boxes").
- **Backend: FastAPI, decoupled from the frontend over a JSON API.** Modern, portfolio-legible,
  maps onto Azure Static Web Apps + Container Apps.
- **Logic lives in the Python backend**; the frontend renders what the API returns. Keeps the
  interesting, testable logic in one place.
- **Persistence: SQLite in local dev, Postgres in production.** Env-parity story; the split is
  a feature, not a compromise.
- **Server state via TanStack Query** with optimistic ticking (instant feel, rollback on
  failure).
- **Offline: read-cache only for v1** — installs, opens offline, shows last-known board;
  ticking requires a connection. Full offline-sync (conflict resolution) explicitly deferred.
- **Time model: continuous roll by date** (no 4-week "blocks" — that was a spreadsheet
  workaround). Per-user timezone, default `Australia/Sydney`.
- **Notifications: designed-for, not built** — dormant fields (`users.reminders_enabled`,
  `habits.reminder_time`) exist so it's not a rewrite later, but no delivery/UI in v1. (User
  explicitly does not want nudges; kept as a future toggle only.)

## Auth
- **Per-user PIN** (argon2-hashed). Chosen over magic-link (email round-trip too slow for a
  daily-open app) and over a full auth provider (overkill for two users; "make it work, not
  tick boxes").
- **Device remembers whose it is** — no "pick who you are" screen after first setup; straight
  to PIN. A one-time `GET /users` picker binds the device.
- **Session expires at the day boundary** (next local midnight in the user's timezone — the
  same cutoff as the edit window). So ~one PIN entry each morning, then free use all day.
  (Chosen over lock-every-open and over stay-signed-in-for-weeks.)
- **Light PIN throttling** against brute force (small attempt cap + cooldown). Pragmatic, not
  bank-grade.

## Deployment
- **Frontend hosting: Azure Static Web Apps** (free tier — hosting, SSL, CDN, per-PR previews).
- **Backend hosting: Azure Container Apps**, scale-to-zero (near-$0 at idle; cold start of a
  second or two is a non-issue for this app). The Container Apps *environment* is reusable for
  future containerised projects at near-zero marginal cost — a deliberate "personal hosting
  platform" choice.
- **You are using Docker regardless** — the app is containerised (Dockerfile); Container Apps
  is just the managed *runner* for that container, chosen over self-managing a VM (avoids
  sysadmin toil, cheaper, keeps the Docker skill + portfolio story).
- **Database: Neon free tier (serverless Postgres).** $0/month; real Postgres (identical
  schema/migrations/queries). Chosen over Azure managed Postgres (~$20 AUD/mo, no free tier,
  no scale-to-zero) because nothing else in the pipeline forces that cost and the certs don't
  require it. **Flagged as a potential future move** to Azure Database for PostgreSQL Flexible
  Server (B1ms) — trivial `pg_dump`/`pg_restore` + connection-string swap; runbook to be
  documented in Phase 4 (Appendix B).
- **CI/CD: GitHub Actions** — push to `main` → tests run → deploy on pass. Tests gate the
  deploy. Portfolio-standard "it ships itself".
- **Runtime secrets: Container Apps secrets** (env-injected). CI secrets in GitHub repository
  secrets. **Azure Key Vault documented as a future hardening upgrade** (Phase 4, Appendix A),
  not built — its managed-identity + permissions setup buys nothing at two users.
- **Domain:** ship on the free `*.azurestaticapps.net` HTTPS URL (enough to install the PWA);
  custom domain deferred.
- **Environments: single production** + Static Web Apps' free automatic per-PR preview
  environments. A standing staging environment is over-engineering at this scale.
- **Migrations run on every deploy; seed runs once on first provision only** (guarded so
  deploys never duplicate data). Deploys are forward-only, never destructive.

## Phase 1 implementation decisions (added when the data model was built)
- **Python 3.13 everywhere, superseding the Phase 1 "locked" 3.12.** Nothing in the
  stack (FastAPI, SQLAlchemy 2.0, Pydantic v2, psycopg 3) needs 3.12, and running one
  version across dev, CI and prod is worth more than honouring the original lock.
  `requires-python` is `>=3.13`. **Phase 4 must containerise on a 3.13 base image**
  (e.g. `python:3.13-slim`), not 3.12.
- **`make` is not available on Windows, so the repo ships a `Makefile` *and* a
  `make.ps1` wrapper** with identical target names. CI and any POSIX shell use the
  Makefile; PowerShell uses the wrapper. Rejected installing GNU make (a machine
  dependency the repo can't guarantee) and shipping only a Makefile (unusable in the
  dev's default shell). `make.ps1` deliberately does *not* set
  `$ErrorActionPreference = 'Stop'` — alembic and pytest log progress to stderr,
  which PowerShell would otherwise treat as fatal; success is decided by exit code.
- **Seed users are the generic placeholders "User A" / "User B"** and seed PINs come
  from `SEED_USER_A_PIN` / `SEED_USER_B_PIN`. The repo is going public, so no real
  name, email or PIN may be committed. `.env` is gitignored; only `.env.example`
  (placeholder values) is tracked.
- **The seed board is split into a public demo and a private local file.**
  `app/seed/data.py` (tracked) holds 29 habits with *generic* names carrying exactly
  the real scheduling, caps and flags; `app/seed/data_local.py` (gitignored) holds the
  real names. `load_boards()` prefers the local file and falls back to the demo, so a
  fresh clone and CI both work. Driven by the repo going public: the real list is not
  *identifying*, but it describes a daily routine in detail (sleep, relationship,
  job-hunting) and does not need to be public to make the portfolio point. The tests
  seed the **demo** boards explicitly rather than calling `seed_all`, so the suite
  asserts the same things on every machine. `data_local.example.py` documents the
  contract, and a test guards against the private names drifting back into `data.py`.
- **Existence of `data_local.py` is checked with `find_spec`, not by catching
  `ImportError`** — a broken private file must fail loudly rather than be mistaken for
  "no local board" and silently replaced by the demo one.
- **PINs are exactly 6 digits** (`settings.pin_length`), validated when a PIN is *set*
  and never when one is *verified* — a wrong guess at login is an expected outcome,
  not an error. Six digits is a million combinations instead of ten thousand, for two
  extra taps each morning. Previously there was no PIN validation at all; that was an
  oversight, not a decision.
- **Reordering habits in-app needs no schema work.** `habits.sort_order` is a plain
  editable integer and is display-only — it never touches `fact_completion`, so
  reordering cannot distort history. Only the Phase 2 endpoint and Phase 3 UI are
  outstanding.
- **Percentages are fractions (`0.0–1.0`), or `None` for a rest day.** Formatting to
  "72%" is the frontend's job; the backend states the number.
- **Reads are pure — they never materialise.** `get_today` and friends only read;
  the caller runs `backfill` first. Phase 2's API layer does that on the way in.
  Keeps a GET from having write side effects.
- **`complete_habit` requires an existing fact row**; completing an unscheduled habit
  raises `HabitNotScheduled` and points at `add_bonus`. Keeps "did my day" and
  "did something extra" from silently blurring into one another.
- **Un-completing a bonus keeps the row** as an inert `scheduled=false,
  completed=false` record (no read surfaces it); re-logging re-completes that same
  row. Chosen over deleting, to stay consistent with archive-not-delete.
- **`available_extras` = active habits with *nothing logged today***, so a habit
  already logged as a bonus leaves the picker. Season-dependent habits still appear
  when the season is off, so an out-of-season one-off can be logged as a bonus.
- **A locked day where only a bonus was done is NOT "no data"** — something happened
  that day, so the mascot shrug would be wrong.
- **Session expiry is exclusive at the boundary** (`expires_at <= now` is expired).
  Signing in at 23:59 buys a minute, not another day — the price of an unambiguous
  day boundary, and consistent with the edit window.
- **Archived habits are neither schedulable nor tickable**, but every past fact row
  survives and still appears in week/month views. `is_scheduled` returns False for an
  archived habit.
- **Backfill is capped at 60 days and floored at the user's creation date**, so a
  long-dormant account cannot trigger unbounded row generation.
- **`dim_date` is populated by the initial migration** (and again, idempotently, by
  the seed). A fact row cannot reference a date the dimension lacks, so the dimension
  is part of "the schema is ready", not user data. Materialising a date outside the
  range raises `DateOutOfRange` rather than a raw integrity error.
- **Timestamps go through a `UtcDateTime` type decorator.** Postgres round-trips
  `timestamptz`; SQLite has no timezone type and returns naive values. The decorator
  normalises both to aware UTC so the two engines cannot disagree.
- **Tests run against an Alembic-migrated database, not `create_all`** — model and
  migration drift then fails the suite instead of hiding. The clock is injectable
  (`app/clock.py`) and every timezone-sensitive function takes an optional `now`, so
  no test reads the system date.
- **PIN brute-force throttling is deferred to Phase 2**, where the request context
  that makes rate limiting meaningful actually exists. The domain layer only hashes
  and verifies.
- **A seeded PIN is marked provisional, rather than the default value being
  blocklisted.** `users.pin_is_provisional` is set by the seed and cleared by
  `set_pin`; Phase 2's login will surface it so the person is asked to choose their
  own. It records *where a PIN came from, not what it is*, which is what makes the
  chance-collision case a non-event: someone who deliberately picks the same digits
  the seed used has still made a choice and is never nagged. Rejected blocklisting
  the seed value because it bans one string without verifying anything actually
  changed, misses a weak *custom* `SEED_USER_*_PIN`, and — since argon2 hashes are
  salted — would force production to retain the seed PIN in its environment forever
  just to compare against. With the flag, prod can drop `SEED_USER_*_PIN` as soon as
  provisioning finishes. Folded into migration `0001` because nothing was deployed
  yet; this is the last change that may do so.

## Phase 2 implementation decisions (added when the HTTP API was built)
- **Habit and bucket management got their own domain modules** (`app/domain/habits.py`,
  `app/domain/buckets.py`) rather than being written inline in the routers. Phase 2's
  brief is "controllers are thin, no business rules in router files", and archive-not-
  delete plus forward-only edits are business rules. Routers now contain no SQL.
- **Mutations return the live view of the date they changed** — a `TodayView` when that
  date is the user's today, a `DayDetailView` when it is yesterday being caught up — so
  an optimistic client can settle without a second round trip and always gets data about
  the screen it is on. To keep that union properly typed, `TodayView` and `DayDetailView`
  each gained a `kind` discriminator (`"today"` / `"day"`). Rejected always returning
  `TodayView` (wrong data when catching up yesterday) and always returning
  `DayDetailView` (lacks `available_extras`, so the extras picker would go stale).
- **Reads backfill up to the user's local today, and no further.** This is what stops the
  frontend seeing a gap, but it deliberately never materialises a historical month that
  was never generated: doing so would write past rows from *today's* schedule, which is
  precisely the retroactive reshaping the model forbids. A GET therefore has a write side
  effect, accepted knowingly — the alternative is a frontend that must know when to ask
  the backend to generate days.
- **PIN throttling: 10 failures, then a 5-minute cooldown**, in-process and per user.
  Chosen over a stricter 5/15 because a wrong-finger lockout costs the two actual users,
  not an attacker — 10 tries is still nothing against a million combinations, and it fits
  the calm, non-punitive ethos. The cooldown is checked *before* the PIN is verified, so
  it cannot be used to confirm a guess. State is in memory and resets on restart: at two
  users a restart is not a practical attack vector, and it avoids a table, a migration
  and a cleanup job.
- **`PUT /me/pin` was added, beyond the Phase 2 spec's endpoint table.** The spec predates
  `pin_is_provisional`; without a change endpoint the flag would be unactionable. Login and
  `GET /me` surface it as `must_change_pin`. Changing a PIN does **not** invalidate the
  current session — logging someone out of the device in their hand is hostile.
- **`PATCH /me` accepts `display_name`, beyond the spec's table.** The seed uses the
  placeholders "User A"/"User B", so without this they could only be renamed by re-seeding
  or editing the database by hand, contradicting the "rename in-app" plan.
- **Cross-board access is `404 NOT_FOUND`, never `403`.** Telling one board that a habit
  exists but belongs to the other board is itself a leak, so "not yours" and "not there"
  are made indistinguishable. `get_habit`/`get_bucket` scope every lookup by `user_id`.
- **One request is one transaction.** The `get_db` dependency commits on success and rolls
  back on any exception, so endpoints never call `commit()` and a failed request leaves
  nothing behind.
- **Domain errors map to HTTP in exactly one place** (`app/api/errors.py`), walking the
  exception's MRO so a new subclass is reported sensibly before it is listed explicitly.
  Routers never re-check a rule the domain already enforces — the edit window is surfaced
  by letting `EditWindowClosed` propagate.
- **Clearing a habit's time cap needs an explicit `clear_time_cap` flag**, because in a
  partial update a null already means "leave this alone".
- **CORS origins come from `CORS_ORIGINS`** (comma-separated), defaulting to Vite's dev
  server. Production overrides it with the deployed frontend origin.
- **`app/main.py` exposes a `create_app()` factory** so tests build an isolated app with
  the database dependency overridden, rather than mutating a module-level singleton.

## Phase 3 implementation decisions (added when the PWA was built)
- **Node 24 LTS, and the frontend lives in `frontend/` in the same repo.** Node was not
  installed at all; winget's LTS channel has moved past 22. One repo keeps Phase 4's
  CI able to build both halves from a single checkout.
- **Styling is CSS Modules over design tokens**, not Tailwind. The palette is defined
  once as custom properties in `src/styles/tokens.css`; the design is bespoke and
  botanical rather than utility-shaped, and the decorative SVG work needed real CSS
  anyway. **The token set deliberately contains no error/danger/warning colour for
  habit state**, so nothing can render an unfinished day as a failure by accident.
- **Habbi is line-plus-soft-fill**: olive outline, blush inner ears and cheeks. Chosen
  over pure line (too faint at calendar size) and solid fills (reads childish, and
  further from botanical-calm). Drawn from scratch as ellipses and stroked paths in
  `src/components/Habbi.tsx`; three poses, cheer/encourage/oops, and **no sad pose,
  ever**. The no-data pose is Habbi covering her mouth with both paws — an "oops",
  not a shrug (decided 2026-08-23); its arms draw in front of the face rather than
  behind the body, which is the one pose-dependent bit of draw order. Arms are filled
  capsules matching the feet, with **no hands or mitts**.
- **Habbi is a girl (she/her), with a small rose-and-gold flower at the base of her left
  ear** (decided 2026-08-23). "Left" is hers, so it renders on the viewer's right. The
  flower is part of the character, so it appears in every pose and in the app mark, not
  just at large sizes. Fonts are Fraunces + Nunito Sans, self-hosted via Fontsource so the PWA makes
  no third-party requests and renders correctly offline.
- **The habit editor is properly built, not "basic" as the spec allowed.** Since User B
  now builds their whole board in-app, that screen is the only way their habits ever
  exist, so it got a weekday picker, bucket creation with colour, inline editing and
  reordering. **Reordering uses up/down buttons rather than drag** — dragging fights
  scrolling on a phone and is hostile to keyboards and screen readers.
- **Celebrations fire on the transition, never on load.** The ladder watches for
  `done_count` to *increase*; opening the app onto a half-finished day sets the baseline
  silently. Un-ticking never celebrates. Rejected persisting fired tiers per date — the
  increase-only rule solves the reload case with no storage.
- **Mutations are optimistic, and the server's response replaces the prediction.** The
  local predictions in `src/api/optimistic.ts` mirror the backend rules (most importantly
  that a bonus never moves the percentage) and are pure functions, so they are tested
  directly. On failure the change rolls back and a soft notice explains why; **nothing
  retries silently**, because a surprise re-tick is worse than an honest failure.
- **API responses are never precached by the service worker.** The shell is precached so
  the app opens offline, and the *last-known board* comes from a persisted React Query
  cache, which knows how old it is. A stale board served from a service worker that
  didn't know it was stale would be worse than no board.
- **Locked days disable their controls** rather than letting a tap become a 403. The UI
  mirrors the edit window instead of discovering it by being refused.
- **The PIN screen uses its own on-screen keypad**, not a text input: bigger targets, no
  system keyboard sliding over the layout, one-handed.
- **A 401 from anywhere ends the session in exactly one place** (`AuthContext`
  subscribes to the API client), so no screen has to handle expiry itself.
- **Vitest 3, not 2.** Vitest 2 bundles its own Vite 5, which collided with the project's
  Vite 6 and produced duplicate-type errors in `vite.config.ts`.

## Still-soft / open items (cheap to change, decide when convenient)
- The three **provisional bucket colours** (Life admin, Social, Team sport) — palette only has
  five core colours; these are placeholders. **Kept as-is for now** (decided 2026-08-23).
- The **morning→night sort order** for the 29 habits — a best-guess seed. Trivial to
  reorder, and will be reorderable in-app once Phase 2/3 land.
- ~~**User B's actual habit list**~~ — **settled 2026-08-23: User B builds their board
  in-app; nothing will ever be seeded for them.** The list was lost, and re-deriving it
  to seed once is pointless now that the management endpoints exist. `BOARD_B` stays
  empty in both the demo board and `data_local.py`. This is also the honest test of the
  habit-management surface: it exists precisely so a board can be built from nothing.
- **Habbi's final look** — first pass built in `src/components/Habbi.tsx` (line + soft
  fill, three poses). Style approved 2026-08-23; the drawing itself still to be eyeballed
  and redirected if wanted.

## Explicitly deferred (not v1)
- Flexible "any N days per week" habit type.
- Push notifications / reminders (fields dormant).
- Offline mutation queue / sync / conflict resolution.
- Warehouse pipeline (Snowflake/dbt) — phase 2 of the wider roadmap.
- Azure managed Postgres, Key Vault, custom domain, standing staging environment (all
  documented as upgrade paths).
