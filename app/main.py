"""FastAPI bootstrap.

Phase 1 deliberately exposes nothing but `/health`. Login, today, tick, week and
month endpoints are Phase 2; the domain layer they will sit on is already built
and tested under `app/domain/`.
"""

from __future__ import annotations

from fastapi import FastAPI

from app import __version__

app = FastAPI(
    title="Habit Tracker API",
    version=__version__,
    description="A calm, non-punitive habit tracker. Phase 1: health check only.",
)


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    """Liveness probe. Returns OK when the process is serving."""
    return {"status": "ok", "version": __version__}
