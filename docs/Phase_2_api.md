# BUILD PROMPT — Phase 2: HTTP API Surface

You are a Claude Code agent. Build the **HTTP API** that exposes the Phase 1 domain
layer over the network. Phase 1 (data model, persistence, domain logic, read models,
seed, tests) is already built and passing — **use it, do not rebuild it or duplicate
its logic**. This phase is a thin, well-tested transport layer: controllers validate
input, call domain functions, and shape responses. All business rules already live in
`app/domain/*` and the Pydantic read models in `app/schemas/*`.

Work methodically, run tests after each group of endpoints, and keep controllers thin.
If you find yourself reimplementing a rule (edit window, percentage, scheduling), stop
— call the domain function instead.

---

## 1. Context and dependencies

- Framework: **FastAPI** (already bootstrapped in Phase 1 with a `/health` route).
- The app has two provisioned users (seeded). **There is no public sign-up** — user
  creation stays a seed/admin concern. Auth is a per-user **PIN**; the client device
  remembers which user it belongs to.
- Reuse Phase 1: domain functions for all mutations and reads, Pydantic read models
  (`TodayView`, `DayDetailView`, `WeekView`, `MonthView`) for responses.
- Keep the "logic in the backend" principle: the frontend (Phase 3) will render exactly
  what these endpoints return and compute nothing meaningful itself.

---

## 2. Locked technical decisions

| Area | Decision |
|---|---|
| Framework | FastAPI |
| Auth | PIN → opaque session token (Bearer), expiry at next local midnight in user's tz |
| Session store | The Phase 1 `sessions` table + domain auth functions |
| DB session | Dependency-injected per request |
| Current user | Dependency that resolves the Bearer token to a user; 401 if missing/expired |
| CORS | Configurable allowed origins (the Phase 3 dev + prod origins) via env |
| Docs | FastAPI's automatic OpenAPI/Swagger at `/docs` |
| Tests | pytest + FastAPI `TestClient` (httpx), against SQLite; smoke against Postgres |

---

## 3. Cross-cutting behaviour

- **Auth dependency.** Every endpoint except `GET /users`, `POST /auth/login`, and
  `/health` requires a valid Bearer session token. Resolve it to the current user;
  reject expired/invalid tokens with `401 UNAUTHENTICATED`.
- **Edit window.** Mutation endpoints must surface the domain edit-window rule as
  `403` with error code `EDIT_WINDOW_LOCKED` when the target date is older than
  yesterday (in the user's timezone). Do not re-implement the check — let the domain
  function raise, and map it.
- **Materialisation on read.** `GET /today` (and the week/month/day reads) must ensure
  the relevant days are materialised/backfilled first, by calling the Phase 1
  `ensure_day_materialised` / `backfill` functions. The frontend should never see a
  gap because a day wasn't generated.
- **PIN throttling.** Add lightweight protection against PIN brute force: after a small
  number of failed attempts for a user (e.g. 5 within a window), return
  `429 PIN_THROTTLED` with a short cooldown. Keep it simple and in-process; this is a
  two-user app, not a bank.
- **Consistent error envelope.** All errors return JSON `{"error": {"code": "...",
  "message": "..."}}`. Codes: `UNAUTHENTICATED`, `PIN_INVALID`, `PIN_THROTTLED`,
  `EDIT_WINDOW_LOCKED`, `NOT_FOUND`, `VALIDATION`. Map FastAPI validation errors into
  this envelope too.
- **Timezone.** All date reasoning uses the user's stored timezone via the domain layer.
  Endpoints accept and return dates as `YYYY-MM-DD` strings; timestamps as ISO 8601.

---

## 4. Endpoints

### Auth & identity
| Method | Path | Body / Query | Returns | Notes |
|---|---|---|---|---|
| GET | `/users` | – | `[{id, display_name}]` | First-run device binding only. Names only, no sensitive data. |
| POST | `/auth/login` | `{user_id, pin}` | `{token, expires_at}` | Verify PIN via domain; issue session (day-boundary expiry). Throttled. |
| POST | `/auth/logout` | – | `204` | Expire current session. |

### Board reads
| Method | Path | Query | Returns |
|---|---|---|---|
| GET | `/today` | – | `TodayView` (ensures today + yesterday materialised) |
| GET | `/days/{date}` | – | `DayDetailView` |
| GET | `/weeks` | `containing_date?` (default: today) | `WeekView` (Mon–Sun of that week) |
| GET | `/months/{year}/{month}` | – | `MonthView` |

### Mutations (edit-window enforced)
| Method | Path | Body | Returns | Notes |
|---|---|---|---|---|
| POST | `/completions` | `{habit_id, date}` | updated day/today fragment | Mark scheduled habit complete. |
| DELETE | `/completions` | `{habit_id, date}` | updated fragment | Un-tick. |
| POST | `/completions/bonus` | `{habit_id, date}` | updated fragment | "Add extra": complete an unscheduled habit; excluded from %. |

For the three mutations, return enough for the client to update optimistically —
simplest is to return the fresh `TodayView` (or `DayDetailView` when the date isn't
today). Pick one and be consistent; document it.

### Settings
| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/me` | – | `{display_name, timezone, season_active, reminders_enabled}` |
| PATCH | `/me` | `{timezone?, season_active?}` | updated settings |

`reminders_enabled` is **read-only / dormant** here — expose it, don't let it be set to
anything meaningful, and wire no behaviour to it.

### Habit & bucket management (needed so boards can be built and edited)
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/buckets` | – | user's buckets, ordered |
| POST | `/buckets` | `{name, color_hex, sort_order}` | |
| PATCH | `/buckets/{id}` | partial | rename / recolour / reorder |
| GET | `/habits` | – | user's active habits with schedule + bucket |
| POST | `/habits` | `{bucket_id, name, target_per_week, time_cap_minutes?, season_dependent, sort_order, anytime, weekdays[]}` | |
| PATCH | `/habits/{id}` | partial | edit fields |
| PUT | `/habits/{id}/schedule` | `{weekdays[]}` | replace scheduled weekdays |
| POST | `/habits/{id}/archive` | – | soft delete (`active=false`, `archived_at`) |
| PATCH | `/habits/reorder` | `[{habit_id, sort_order}]` | batch reorder |

Scope note: keep these functional and correct; the frontend for managing habits can be
minimal in Phase 3. This surface exists so User B (seeded empty) can build a board and
either user can adjust theirs.

**Two behaviours to enforce (do not let the agent improvise):**
- **Archive, never delete.** `POST /habits/{id}/archive` is a soft delete
  (`active = false`, `archived_at` set). The habit disappears from future boards, but
  its past `fact_completion` history is preserved and still appears in week/month reads.
  There is no hard-delete endpoint.
- **Schedule/attribute edits are forward-only.** `PATCH /habits/{id}` and
  `PUT /habits/{id}/schedule` change future materialisation and current reads only.
  Already-materialised days keep their existing rows — never retroactively reshape a
  week in progress. (This is the Phase 1 domain guarantee; the API must not work around
  it.)

---

## 5. Structure

Add to the Phase 1 repo:

```
app/
  api/
    deps.py            # get_db, get_current_user, error mapping
    errors.py          # error envelope + exception handlers
    routers/
      auth.py
      board.py         # today, days, weeks, months
      completions.py
      settings.py
      habits.py
      buckets.py
  main.py              # include routers, CORS, exception handlers
tests/
  api/                 # endpoint tests
```

Controllers import from `app/domain` and `app/schemas`. No SQL or business rules in the
router files.

---

## 6. Tests

- Auth: login with correct PIN issues a token; wrong PIN → `PIN_INVALID`; repeated
  failures → `PIN_THROTTLED`; token expires at next local midnight (frozen clock);
  expired/missing token → `401` on protected routes; logout expires the session.
- `GET /today`: returns ordered active list (`anytime` last, then `sort_order`),
  completed pile in tick order, correct `daily_pct` and counts, `available_extras`,
  bonuses; triggers materialisation of today + yesterday.
- Mutations: complete/uncomplete round-trip; bonus creates an excluded-from-% row;
  editing a locked date → `403 EDIT_WINDOW_LOCKED`.
- Reads: `/days/{date}` (incl. `no_data` for a locked-empty day), `/weeks`, `/months`
  return the documented shapes.
- Settings: PATCH timezone and season_active take effect; `reminders_enabled` cannot be
  meaningfully changed.
- Habit/bucket management: create → appears in `/habits`; schedule replace; archive
  hides from active reads; reorder persists.
- Isolation: User A cannot read or mutate User B's data (auth scoping) — assert a
  cross-user access attempt is rejected/empty.
- Use a frozen/injectable clock for all timezone-sensitive tests.

---

## 7. Definition of done

- All endpoints implemented, documented in the auto-generated OpenAPI at `/docs`.
- `make test` passes on SQLite; smoke-tested against the docker-compose Postgres.
- CORS configurable via env; error envelope consistent everywhere.
- No business logic duplicated from Phase 1 — controllers are thin.
- README updated with the endpoint list, the auth flow (PIN → token → day-boundary
  expiry), and the error codes.

---

## 8. Out of scope (do NOT build this phase)

- Any frontend / React / PWA — **Phase 3**.
- Notification delivery/scheduling (the dormant fields stay dormant).
- Offline sync, request queueing.
- Public sign-up / self-service account creation.
- Warehouse / analytics pipeline — **phase 2 of the wider roadmap**, not this API phase.
- Flexible "any N days per week" habit type.

Build only §1–§7. Prefer the simplest interpretation consistent with the calm,
non-punitive product philosophy, and record any assumption in the README rather than
widening scope.
