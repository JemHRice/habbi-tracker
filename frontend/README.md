# Habbi-Tracker

Welcome to Habbi-Tracker! A (currently) two-person habit tracker. Two people 
each keep a private daily board: open the app, see the habits scheduled for 
today, tick them off. The boards are fully separate with no shared habits, no 
visibility into each other's data. Right now, it has simply been one-shotted 
by Opus 5 after exhaustive planning, and is for myself and one other. Once 
deployed, I'll be slowly adding features to hopefully be more flexible for 
more people. Stay tuned!

## The frontend — Phase 3

An installable PWA built with React, TypeScript and Vite. It **consumes** the
Phase 2 API and reimplements none of its logic: what's scheduled today, the
percentages, the edit window, the week and month rollups all come from the
backend. This app renders what it's given and handles interaction, animation
and feel.

Requires **Node 22+** (developed on 24 LTS).

```bash
npm install
npm run dev        # http://localhost:5173, against the API on :8000
npm run build      # production build, including the service worker
npm run preview    # serve the built app
npm test           # component and logic tests
npm run typecheck
npm run icons      # regenerate PWA icons from habbi-mark.svg
```

The backend needs to be running for anything past the "who are you?" screen:

```bash
cd ..  &&  make run          # or: .\make.ps1 run
```

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Where the API lives. |

Copy `.env.example` to `.env.local` to override. The backend's `CORS_ORIGINS`
must include this app's origin — its default already covers the Vite dev server.

---

## Auth, exactly as the backend expects it

1. **First run on a device** — a one-time "who are you?" screen lists the
   provisioned users and binds this device to one. There is no sign-up.
2. **Every morning** — the device knows who it is, so it goes straight to a
   six-digit PIN.
3. **The session lasts until the next local midnight**, which the backend sets.
   So it's one PIN entry a day, then free ticking.
4. **Any 401 drops back to the PIN screen**, handled in one place rather than
   per-screen.

There is deliberately no "stay signed in for weeks" mode.

---

## Offline behaviour

Read-only, on purpose.

- The **app shell is precached** by a Workbox service worker, so the app opens
  without a connection.
- The **last-known board is viewable offline** from a persisted React Query
  cache in `localStorage`. API responses are never served from the service
  worker cache — a stale board that doesn't know it's stale would be worse than
  no board.
- **Ticking requires a connection.** A mutation attempted offline fails gently
  ("We'll need signal for that") and the optimistic change rolls back.

There is **no offline queue and no sync**. Replaying queued ticks against a
day-boundary edit window is a real conflict-resolution problem, and pretending
otherwise would quietly lose data. It is explicitly deferred.

No notification permission is ever requested.

---

## Art

**Habbi and every decorative element in this app are original work**, drawn as
plain SVG in this repository. Habbi is a girl bunny with a small flower tucked
at the base of her left ear. She lives in
[`src/components/Habbi.tsx`](src/components/Habbi.tsx) as a few dozen ellipses
and stroked paths — an olive outline with blush fills — in three poses:

- **cheer** — the halfway "yippee" and the day-done celebration
- **encourage** — "last one left, let's keep going", and the PIN screen
- **oops** — both paws over her mouth, for a day with nothing recorded,
  captioned "no data here"

There is no sad pose and there should never be one. The petals in the
celebration burst and every icon in the app are likewise drawn here. No
third-party, stock or trademarked imagery is used anywhere.

Fonts are **Fraunces** (display) and **Nunito Sans** (body), both open-licensed
and self-hosted via Fontsource so the app renders correctly offline and makes no
third-party requests.

---

## Structure

```
src/
  api/          client, typed endpoints, query hooks, optimistic predictions
  auth/         device binding, session storage, the auth gate
  components/   Habbi, progress ring, habit rows, celebrations, layout
  screens/      Today, Tracking, DayDetail, Settings, Habits, auth screens
  styles/       design tokens and global styles
  test/         setup and render helpers
```

Styling is **CSS Modules over design tokens** (`src/styles/tokens.css`). The
palette is defined once as custom properties; bucket colours come from the API
and are rendered as given.

Note what the palette lacks: there is no error, danger or warning colour for
habit state. An unfinished day is never drawn as a failure, so the tokens give
nobody the means to do it by accident.

---

## Assumptions made while building

- **Celebrations fire on the tick, not on load.** Opening the app onto a
  half-finished day should feel like picking up where you left off, not like
  being congratulated for arriving. Un-ticking never celebrates.
- **Reordering habits uses up/down buttons, not drag.** Dragging is nicer on a
  desktop and worse everywhere else: it fights scrolling on a phone and is
  hostile to keyboards and screen readers.
- **The PIN screen has its own keypad** rather than a text input — bigger
  targets, no keyboard sliding over the layout, and it suits one thumb.
- **Locked days disable their controls** rather than letting a tap become a
  403. The API would refuse it anyway, and being told "no" is worse than never
  being offered.
- **A failed mutation shows a soft notice and rolls back.** Nothing retries
  silently, because the person can see the result and a surprise re-tick would
  be worse than an honest failure.
