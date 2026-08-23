"""The `sessions` table: opaque tokens issued after a PIN check.

Only a hash of the token is stored, so a database leak does not hand anyone a
usable session. Sessions expire at the next local midnight in the user's
timezone — the same day boundary the edit window uses — which works out as
roughly one PIN entry each morning.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import clock
from app.models.base import Base, UtcDateTime
from app.models.user import User


class AuthSession(Base):
    """A logged-in session. Named `AuthSession` to keep it distinct from a
    SQLAlchemy `Session`; the table itself is `sessions`."""

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_token_hash", "token_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=clock.utcnow
    )

    user: Mapped["User"] = relationship(lazy="joined")

    def __repr__(self) -> str:
        return f"<AuthSession id={self.id} user_id={self.user_id}>"
