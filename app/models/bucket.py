"""The `buckets` table: a user's habit categories, each with a display colour."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import clock
from app.models.base import Base, UtcDateTime

if TYPE_CHECKING:
    from app.models.habit import Habit
    from app.models.user import User


class Bucket(Base):
    """A grouping of habits (e.g. "Self-care") belonging to one user.

    Buckets carry the colour the UI paints their habits with; the domain layer
    treats them as a pure dimension and never uses them in completion maths.
    """

    __tablename__ = "buckets"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_buckets_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    color_hex: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=clock.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="buckets")
    habits: Mapped[list["Habit"]] = relationship(back_populates="bucket")

    def __repr__(self) -> str:
        return f"<Bucket id={self.id} name={self.name!r}>"
