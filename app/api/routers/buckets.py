"""Bucket management."""

from __future__ import annotations

from fastapi import APIRouter, Path

from app.api.deps import CurrentUser, DbSession
from app.api.schemas import BucketCreate, BucketOut, BucketUpdate
from app.domain.buckets import create_bucket, list_buckets, update_bucket
from app.models.bucket import Bucket

router = APIRouter(prefix="/buckets", tags=["buckets"])


@router.get("", response_model=list[BucketOut])
def read_buckets(session: DbSession, user: CurrentUser) -> list[Bucket]:
    """The user's buckets, in display order."""
    return list_buckets(session, user)


@router.post("", response_model=BucketOut, status_code=201)
def add_bucket(
    payload: BucketCreate, session: DbSession, user: CurrentUser
) -> Bucket:
    """Create a bucket."""
    return create_bucket(
        session,
        user,
        name=payload.name,
        color_hex=payload.color_hex,
        sort_order=payload.sort_order,
    )


@router.patch("/{bucket_id}", response_model=BucketOut)
def edit_bucket(
    payload: BucketUpdate,
    session: DbSession,
    user: CurrentUser,
    bucket_id: int = Path(ge=1),
) -> Bucket:
    """Rename, recolour or reorder a bucket. Partial update."""
    return update_bucket(
        session,
        user,
        bucket_id,
        name=payload.name,
        color_hex=payload.color_hex,
        sort_order=payload.sort_order,
    )
