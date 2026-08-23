# BUILD PROMPT — Phase 3: React + Vite PWA

You are a Claude Code agent. Build the **frontend**: an installable Progressive Web App
that consumes the Phase 2 HTTP API. Phases 1 (data model + domain) and 2 (HTTP API) are
built and passing — **consume the API, do not reimplement any logic**. The backend
computes everything meaningful (what's scheduled today, percentages, the edit window,
month/week aggregates); this app renders what the API returns and handles interaction,
animation, and feel.

The product philosophy is **calm and non-punitive**. It celebrates what gets done and
**never** flags, reddens, or guilt-trips what doesn't. Hold that in every design
decision below.

---

## 1. Locked technical decisions

| Area | Decision |
|---|---|
| Build tool | Vite |
| Framework | React + TypeScript |
| PWA | `vite-plugin-pwa` (Workbox) — installable, offline **read-cache** only |
| Server state | TanStack Query (React Query) — fetching, caching, optimistic ticking |
| Routing | React Router |
| Styling | Your choice of a lightweight, readable approach (CSS Modules or Tailwind); use design tokens (§4) |
| Auth storage | Device remembers its bound `user_id`; session token + expiry in `localStorage` |
| Offline | Cache app shell + last-known board for viewing offline; **mutations require a connection** (no offline queue this phase) |
| Notifications | **None.** Do not request notification permission or build any nudge. |

TypeScript is required — a tap-heavy, stateful UI benefits materially from it, and it
makes the code self-documenting for review.

---

## 2. Auth & session flow (matches the backend exactly)

1. **First run on a device:** show a one-time "who are you?" screen. Fetch `GET /users`,
   let the person pick themselves, store that `user_id` on the device. This screen is
   never shown again unless storage is cleared.
2. **Every day:** the device knows who it is, so it goes **straight to a PIN screen**
   (no "pick who you are"). Enter PIN → `POST /auth/login` → store token + `expires_at`.
3. **Session lasts until the day boundary.** The token expires at next local midnight
   (the backend sets this). On app open, if the stored token is expired or missing,
   show the PIN screen; otherwise go straight to Today. So in practice: one PIN entry in
   the morning, then free ticking all day.
4. On any `401` from the API, drop to the PIN screen.

Do not build a persistent "stay logged in for weeks" mode — the one-day, PIN-per-day
behaviour is intentional.

---

## 3. Screens & behaviour

### Today (the home screen)
The heart of the app. It shows **only today's scheduled habits** for the logged-in user.

- **Ordering:** active (not-yet-done) habits in fixed order — the API returns them
  ordered (`anytime` habits last, otherwise by `sort_order`). Render in that order; do
  not re-sort.
- **Ticking:** tap a habit to complete it. Use an **optimistic update** (flip it
  instantly, reconcile with the API response, roll back on failure). On completion the
  item **strikes through and drops to a completed pile at the bottom**, stacked in the
  order ticked. The next active habit rises to the top.
- **Un-tick:** tapping a struck-through item restores it to its place in the active list.
- **Daily percentage:** at the top, shown **both numerically and visually** (e.g. a
  filling ring or bar). Scheduled habits only. It can only ever reach 100% — there is no
  over-100, no "behind". If the API returns `null` (nothing scheduled), present it
  gently as a rest day, not 0%.
- **Add something extra:** a control that opens a picker of the user's **other** habits
  (`available_extras` from the API). Choosing one logs a **bonus** via
  `POST /completions/bonus`. A bonus joins the completed pile but **does not count
  toward the percentage** — it's a bonus *outside* the count. Make that feel like a
  little win, not a metric.
- **Celebration ladder** (all encouraging, never punishing):
  - **Halfway:** a small, quick "yippee" moment.
  - **Last one left:** a gentle "let's keep going" nudge of encouragement.
  - **Day done (100%):** the **big** moment — the mascot (§5) doing something cute, with
    extra flourish (confetti/floral motifs in-palette).
  - Never show a negative state for an unfinished day. No red, no frown, no counter of
    what's missing beyond the neutral "X to go".

### Tracking (a tab, for looking back — not for ticking)
Two views:

- **Weekly — simple and calming.** A quick, manageable overview of each day this week
  (`GET /weeks`). Show each day's completion in a light, glanceable way. A
  **locked-empty day** (the API's `locked_empty` flag) reads as crossed out (a line
  through the day / its habits), quietly — not as a failure.
- **Monthly — the richer view** (`GET /months/{year}/{month}`). Two stacked sections:
  1. **Completion trends** at the top: per-habit "how it went this month"
     (completed vs scheduled), shown **factually** — same calm treatment for a habit
     that stuck and one that slipped. No red, no ranking, no shaming. Just the numbers.
  2. **A calendar** below: each day coloured by its completion (a fill indicator).
     Tapping a day opens its **detail** (see below). A **no-data day** shows the mascot
     with arms bent, captioned "no data here".

### Day detail (opened from the calendar)
`GET /days/{date}`. Show what was and wasn't done that day and its **final percentage**.
Read-only for locked days; today/yesterday remain editable (the API enforces this — mirror
it in the UI by disabling controls on locked days rather than letting a tap fail).

### Settings
- Season toggle (`season_active`) and timezone via `PATCH /me`.
- A **basic** habit-management area (list / add / edit / archive / reorder, and set
  scheduled weekdays) backed by the Phase 2 habit/bucket endpoints. Keep it functional
  and clear; heavy visual polish here is optional. This is how User B (seeded with an
  empty board) builds their habits and how either user adjusts theirs.

No welcome/onboarding tour beyond the one-time "who are you?" — after that, straight to
the checklist.

---

## 4. Design tokens & visual direction

The look is **playful, warm, a touch girly**, botanical-calm — never corporate, never
childish. Draw from this palette (extracted from the reference moodboard):

| Token | Hex | Suggested use |
|---|---|---|
| `rose` | `#CA758A` | hero / primary accent |
| `olive` | `#6C6C2C` | grounding / text-on-light headings |
| `sky` | `#99B4D2` | secondary accent |
| `blush` | `#E5C2CA` | soft fills / backgrounds |
| `gold` | `#DFC980` | warm highlight |
| `cream` | `#FAF6EE` (suggested) | page background — lots of breathing room |

- Use generous whitespace on cream, rounded soft shapes, a friendly rounded/serif-ish
  display face for headings paired with a clean readable body font.
- **Original decorative elements only:** simple florals, swirls, botanical line motifs —
  drawn as original SVGs, used sparingly as accents (corners, dividers, celebration
  bursts). Do not use any third-party or trademarked imagery, icon sets with licensing
  strings attached, or stock illustrations.
- Bucket colours come from the API (`color_hex`); render them as-is.
- Mobile-first, one-handed use, standard comfortable tap-target sizing. It must feel
  good to tick a habit with a thumb on a bus.

---

## 5. Mascot — "Habbi" (original asset, IMPORTANT)

The app has a bunny mascot named **Habbi**. Habbi must be an **original character you
create** — a simple, cute, line-drawn bunny in the palette above. **Do not reproduce,
trace, approximate, or take inspiration from any existing copyrighted or trademarked
character** (no Miffy, no other brand mascots). Original work only.

Produce Habbi as reusable SVG(s) in a few poses:
- **Cheer** — used for the halfway "yippee" and the big day-done celebration.
- **Encourage** — used for "last one left, let's keep going".
- **Shrug** (arms bent) — used for a no-data day, captioned "no data here".

Keep the style consistent, minimal, and sweet. Habbi is the emotional signature of the
whole app — warm, never nagging.

---

## 6. PWA & offline

- Installable to the home screen: web manifest (name, icons generated from Habbi/an
  original mark, theme colours from the palette, standalone display).
- Service worker (Workbox via `vite-plugin-pwa`): cache the app shell so it opens
  offline, and persist the React Query cache so the **last-known board is viewable
  offline**.
- **Ticking requires a connection this phase.** If a mutation is attempted offline,
  fail gently ("we'll need signal for that") — do **not** build an offline queue or
  sync/reconciliation. Full offline-sync is explicitly deferred.
- Do not request notification permission.

---

## 7. Quality bar & tests

- Optimistic ticking feels instant and rolls back cleanly on API failure.
- Locked days are visibly read-only; the UI never lets a user tap into a `403`.
- The celebration ladder fires at the right thresholds and is purely additive (test that
  no negative/failure state is ever rendered for an unfinished day).
- Component tests for Today (ordering, tick → move to pile, un-tick → restore, bonus →
  pile-but-not-counted, percentage display) and for the month calendar (fill by
  completion, no-data → mascot, tap → detail).
- Basic accessibility: sensible contrast on cream, focus states, hit areas.
- Runs against the local Phase 2 API; API base URL configurable via env.

---

## 8. Definition of done

- `npm run dev` runs the app against the local API; `npm run build` produces an
  installable PWA (passes a Lighthouse PWA-installability check).
- All screens in §3 implemented with the behaviours described; the auth flow in §2 works
  end to end (first-run pick → daily PIN → day-boundary expiry).
- Habbi exists as original SVG poses; palette tokens applied throughout; no third-party
  or trademarked imagery anywhere.
- Both users can use their own board on their own device with separate data.
- README: how to run, the env config, the offline behaviour (read-cache, no mutation
  offline), and a note that Habbi and all decorative art are original assets.

---

## 9. Out of scope (do NOT build this phase)

- Offline mutation queue / sync / conflict resolution.
- Push notifications or any reminder UI (the backend fields stay dormant).
- Warehouse / analytics dashboards.
- Public sign-up.
- Flexible "any N days per week" habit type.
- Any reproduction of copyrighted characters or licensed art — original assets only.

Build only §1–§8. When something is ambiguous, choose the calmest, simplest option
consistent with "celebrate what's done, never flag what isn't", and note the assumption
in the README.
