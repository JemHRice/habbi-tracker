"""FastAPI application: routers, CORS and the error envelope.

Every business rule lives in `app/domain`. This module only wires transport.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.routers import auth, board, buckets, completions, habits
from app.api.routers import settings as settings_router
from app.config import get_settings

DESCRIPTION = """
A calm, non-punitive habit tracker for two people, each with a fully separate board.

**Auth.** `GET /users` once to bind a device, then `POST /auth/login` with a PIN to
get a Bearer token. The token expires at the next local midnight in the user's
timezone — the same day boundary the edit window uses — so it is roughly one PIN
entry each morning.

**Errors.** Always `{"error": {"code": ..., "message": ...}}`. Codes:
`UNAUTHENTICATED`, `PIN_INVALID`, `PIN_THROTTLED`, `EDIT_WINDOW_LOCKED`,
`NOT_FOUND`, `VALIDATION`.

**Dates** are `YYYY-MM-DD`; timestamps are ISO 8601 UTC. Percentages are fractions
from 0.0 to 1.0, or `null` on a rest day — they cap at 100% by construction.
"""


def create_app() -> FastAPI:
    """Build the application. A factory so tests can construct it in isolation."""
    settings = get_settings()

    app = FastAPI(
        title="Habbi-Tracker API",
        version=__version__,
        description=DESCRIPTION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        # Pull-request preview hostnames are generated per PR, so they are
        # matched by pattern rather than listed.
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        """Liveness probe. Returns OK when the process is serving."""
        return {"status": "ok", "version": __version__}

    for router in (
        auth.router,
        board.router,
        completions.router,
        settings_router.router,
        habits.router,
        buckets.router,
    ):
        app.include_router(router)

    return app


app = create_app()
