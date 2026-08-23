# SPEC — Habit Tracker

Top-level overview. For decisions and rationale see `DECISIONS.md`; for build
instructions see the `PHASE_N_*.md` files.

## What it is
A Progressive Web App (installable to a phone home screen, works like a native app)
where two people each track their own daily habits. One shared codebase and login
screen; two completely separate boards. Built as a portfolio-grade project and a
personal data project.

## Who uses it
- **User A** — full board seeded (29 habits across 8 buckets).
- **User B** — seeded with an empty board; their habits are added in-app later.

## The three screens
1. **Today** — the home screen. Shows only today's scheduled habits in a fixed
   chronological order. Tap to tick; completed items strike through and drop to a pile at
   the bottom (in tick order); un-tick to restore. A daily % (numeric + visual, scheduled
   habits only) sits at the top. "Add something extra" lets you complete an unscheduled
   habit as a **bonus that does not count toward the %**. Celebration ladder: a small
   "yippee" at halfway, gentle encouragement at last-one-left, and a big mascot moment at
   100%.
2. **Tracking** — for looking back, not ticking. **Weekly**: a simple, calming overview
   of each day. **Monthly**: per-habit completion trends (factual, no shaming) plus a
   colour-coded calendar; tap a day for its detail.
3. **Settings** — season toggle, timezone, and a basic habit-management area
   (add / edit / archive / reorder / set scheduled days).

## Core rules
- **Scheduling** is by fixed weekday per habit. A habit shows on a day only if scheduled
  (and, if season-dependent, only when the user's season is active).
- **Edit window:** today and yesterday are editable; everything older is locked.
- **No data:** a locked day with zero completions reads as "no data" (mascot shrug).
- **Percentages cap at 100%.** Bonuses are excluded. No "exceeded", no "behind".
- **Non-destructive:** removing a habit archives it (history preserved); schedule edits
  apply forward-only; migrations never rewrite the past.

## The mascot
An **original** bunny mascot named **Habbi** (not Miffy or any existing character —
original art only), in poses for cheer, encourage, and shrug (no-data).

## Look & feel
Playful, warm, a touch girly; botanical-calm. Palette (from the Aesté moodboard):
rose `#CA758A`, olive `#6C6C2C`, sky `#99B4D2`, blush `#E5C2CA`, gold `#DFC980`, on
cream. Original florals/swirls as accents. No reminders, no nudges — calm by design.

## Auth
Per-user **PIN**. The device remembers whose it is and goes straight to the PIN screen.
Sessions last until the day boundary (next local midnight), so it's roughly one PIN entry
each morning, then free use all day.

## Cost posture
Runs at effectively $0/month: free frontend tier, scale-to-zero backend, Neon free-tier
Postgres. The Azure Container Apps environment is reusable for future projects at near-zero
marginal cost.
