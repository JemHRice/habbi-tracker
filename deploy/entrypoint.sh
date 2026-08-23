#!/bin/sh
# Container entrypoint: migrate, then serve.
#
# Migrations run on every start and are idempotent — Alembic applies only what
# is missing, so the production schema always matches the deployed code. They
# are forward-only; nothing here ever drops or rewrites data.
#
# The seed is deliberately NOT run here. It is a one-time step, documented in
# docs/RUNBOOK.md, so a redeploy can never duplicate a board.
set -eu

echo "==> Applying database migrations"
alembic upgrade head

echo "==> Starting API on port ${PORT:-8000}"
# One worker on purpose: the PIN throttle keeps its state in process, so a
# second worker would give an attacker a second allowance. At two users there
# is nothing to gain from more.
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers 1 \
  --proxy-headers \
  --forwarded-allow-ips '*'
