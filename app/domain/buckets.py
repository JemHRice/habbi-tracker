"""Bucket management.

Buckets are a pure dimension: they group habits and carry the colour the UI
paints them with, and nothing here touches completion maths.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import BucketNotFound
from app.models.bucket import Bucket
from app.models.user import User


def list_buckets(session: Session, user: User) -> list[Bucket]:
    """Return the user's buckets in display order."""
    return list(
        session.scalars(
            select(Bucket)
            .where(Bucket.user_id == user.id)
            .order_by(Bucket.sort_order, Bucket.id)
        ).all()
    )


def get_bucket(session: Session, user: User, bucket_id: int) -> Bucket:
    """Return one of the user's buckets.

    Raises:
        BucketNotFound: if it does not exist *or* belongs to someone else.
    """
    bucket = session.scalar(
        select(Bucket).where(Bucket.id == bucket_id, Bucket.user_id == user.id)
    )
    if bucket is None:
        raise BucketNotFound(f"no bucket {bucket_id} on this board")
    return bucket


def create_bucket(
    session: Session, user: User, name: str, color_hex: str, sort_order: int
) -> Bucket:
    """Add a bucket to the user's board."""
    bucket = Bucket(
        user_id=user.id, name=name, color_hex=color_hex, sort_order=sort_order
    )
    session.add(bucket)
    session.flush()
    return bucket


def update_bucket(
    session: Session,
    user: User,
    bucket_id: int,
    *,
    name: str | None = None,
    color_hex: str | None = None,
    sort_order: int | None = None,
) -> Bucket:
    """Rename, recolour or reorder a bucket. Only the given fields change.

    Raises:
        BucketNotFound: if it is not this user's bucket.
    """
    bucket = get_bucket(session, user, bucket_id)
    if name is not None:
        bucket.name = name
    if color_hex is not None:
        bucket.color_hex = color_hex
    if sort_order is not None:
        bucket.sort_order = sort_order
    session.flush()
    return bucket
