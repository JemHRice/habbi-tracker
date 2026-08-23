"""SQLAlchemy models.

Importing this package registers every model on :class:`~app.models.base.Base`,
which is what Alembic autogenerate and `Base.metadata.create_all` rely on.
"""

from app.models.auth_session import AuthSession
from app.models.base import Base, TimestampMixin, UtcDateTime
from app.models.bucket import Bucket
from app.models.dim_date import DimDate
from app.models.fact import FactCompletion
from app.models.habit import Habit, HabitSchedule
from app.models.user import User

__all__ = [
    "AuthSession",
    "Base",
    "Bucket",
    "DimDate",
    "FactCompletion",
    "Habit",
    "HabitSchedule",
    "TimestampMixin",
    "User",
    "UtcDateTime",
]
