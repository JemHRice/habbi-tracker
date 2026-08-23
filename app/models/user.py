"""The `users` table: one row per person, each with a fully separate board."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.bucket import Bucket
    from app.models.habit import Habit


class User(TimestampMixin, Base):
    """A person with their own private habit board.

    There is no sharing between users: every bucket, habit and completion fact
    belongs to exactly one user.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, unique=True)
    pin_hash: Mapped[str] = mapped_column(Text, nullable=False)
    pin_is_provisional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    """True while the PIN is one the seed issued rather than one the person
    chose. Records where the PIN came from, not what it is — so someone who
    deliberately picks the same digits is never nagged. Cleared by `set_pin`."""

    timezone: Mapped[str] = mapped_column(
        Text, nullable=False, default="Australia/Sydney", server_default="Australia/Sydney"
    )
    season_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    reminders_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    """Dormant: designed-for, not built. Nothing reads this in v1."""

    buckets: Mapped[list["Bucket"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    habits: Mapped[list["Habit"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} display_name={self.display_name!r}>"
