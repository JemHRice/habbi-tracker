# Habit Tracker

A two-person habit-tracking PWA. Two people each keep a private daily board on their
phone: open the app, see today's scheduled habits, tick them off. Boards are fully
separate — no shared habits, no seeing each other's data.

**Product philosophy — hold this in every decision:** the app is a calm, non-punitive
*recording* tool. It celebrates what gets done and **never** flags, reddens, or
guilt-trips what doesn't. Percentages only ever cap at 100%; there is no "behind",
no "exceeded", no streak-shaming. Celebrate progress; stay silent on gaps.

## How to work in this repo
- Read `docs/SPEC.md` and the relevant `docs/PHASE_N_*.md` before building anything.
- Every design decision is logged in `docs/DECISIONS.md`. Check it before making a
  choice. If we make a new decision, **add it there as part of the same change.**
- Build phases **in order** (1 → 2 → 3 → 4). Each phase assumes the previous is built
  and its tests pass.
- **Never rewrite history:** forward-only migrations, archive-not-delete, today+yesterday
  edit window only. The past is immutable.
- Keep business logic in the Python backend; the frontend renders what the API returns.
- When something is ambiguous, choose the simplest option consistent with the calm,
  non-punitive philosophy, and record the assumption in the relevant doc.

## Stack
Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 · Postgres (Neon in prod,
SQLite in local dev) · React + TypeScript + Vite (PWA) · TanStack Query · Azure Container
Apps (backend) + Azure Static Web Apps (frontend) · GitHub Actions CI/CD.

## Phase map
- `docs/PHASE_1_data_model.md` — schema, domain logic, read models, seed, tests
- `docs/PHASE_2_api.md` — FastAPI HTTP surface over the domain layer
- `docs/PHASE_3_pwa.md` — React + Vite installable PWA frontend
- `docs/PHASE_4_deployment.md` — Azure + Neon + GitHub Actions deployment
