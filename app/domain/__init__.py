"""The domain layer: every rule that makes this app what it is.

Modules
-------
`dates`       Local day boundaries and the `dim_date` dimension.
`scheduling`  What is expected when, and writing days into the fact table.
`tracking`    Ticking, un-ticking, bonuses, and the edit window.
`reads`       The today/day/week/month read models the API will serve.
`auth`        PIN hashing and day-bounded sessions.
`errors`      The refusals, mapped to HTTP status codes in Phase 2.

Every function takes a SQLAlchemy `Session` explicitly; nothing here reaches for
a global connection, and nothing here knows about HTTP.
"""

from app.domain import auth, dates, errors, reads, scheduling, tracking

__all__ = ["auth", "dates", "errors", "reads", "scheduling", "tracking"]
