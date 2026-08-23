"""Engine and session plumbing, aware of both SQLite (dev) and Postgres (prod)."""

from __future__ import annotations

from typing import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def is_sqlite_url(url: str) -> bool:
    """Return True if `url` addresses a SQLite database."""
    return url.startswith("sqlite")


def create_db_engine(url: str | None = None) -> Engine:
    """Build an :class:`~sqlalchemy.Engine` for `url` (default: settings).

    SQLite needs two accommodations that Postgres does not: relaxed thread
    checking, and foreign keys switched on per connection (SQLite disables
    them by default, which would silently skip our referential integrity).
    """
    url = url or get_settings().database_url
    kwargs: dict[str, object] = {"pool_pre_ping": True, "future": True}
    if is_sqlite_url(url):
        kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(url, **kwargs)

    if is_sqlite_url(url):

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = create_db_engine()

SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Yield a database session, closing it afterwards.

    Shaped as a generator so Phase 2 can use it directly as a FastAPI dependency.
    """
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()
