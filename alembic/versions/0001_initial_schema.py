"""Initial schema: users, buckets, habits, dim_date, fact_completion, sessions.

Also populates `dim_date` for the configured range, because a fact row cannot
reference a date that does not exist in the dimension — the table is part of the
schema being ready, not user data.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-23
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import get_settings
from app.domain.dates import date_range
from app.models.dim_date import build_row

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("pin_hash", sa.Text(), nullable=False),
        sa.Column(
            "pin_is_provisional", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column(
            "timezone", sa.Text(), nullable=False, server_default="Australia/Sydney"
        ),
        sa.Column("season_active", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("reminders_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "buckets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color_hex", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_buckets_user_id", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("user_id", "name", name="uq_buckets_user_name"),
    )

    op.create_table(
        "habits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bucket_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("target_per_week", sa.Integer(), nullable=False),
        sa.Column("time_cap_minutes", sa.Integer(), nullable=True),
        sa.Column("season_dependent", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("anytime", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("reminder_time", sa.Time(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_habits_user_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["bucket_id"], ["buckets.id"], name="fk_habits_bucket_id"
        ),
    )
    op.create_index("ix_habits_user_active", "habits", ["user_id", "active"])

    op.create_table(
        "habit_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("habit_id", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["habit_id"],
            ["habits.id"],
            name="fk_habit_schedules_habit_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "habit_id", "weekday", name="uq_habit_schedules_habit_weekday"
        ),
    )

    op.create_table(
        "dim_date",
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("month_name", sa.Text(), nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("weekday_name", sa.Text(), nullable=False),
        sa.Column("iso_week", sa.Integer(), nullable=False),
        sa.Column("week_start_date", sa.Date(), nullable=False),
        sa.Column("is_weekend", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "fact_completion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("habit_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("scheduled", sa.Boolean(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_bonus", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_fact_completion_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["habit_id"], ["habits.id"], name="fk_fact_completion_habit_id"
        ),
        sa.ForeignKeyConstraint(
            ["date"], ["dim_date.date"], name="fk_fact_completion_date"
        ),
        sa.UniqueConstraint(
            "user_id", "habit_id", "date", name="uq_fact_completion_user_habit_date"
        ),
    )
    op.create_index(
        "ix_fact_completion_user_date", "fact_completion", ["user_id", "date"]
    )
    op.create_index(
        "ix_fact_completion_habit_date", "fact_completion", ["habit_id", "date"]
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_sessions_user_id", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"])

    _populate_dim_date()


def _populate_dim_date() -> None:
    """Insert the configured date range into `dim_date`.

    Uses a plain table insert rather than the ORM so the migration does not
    depend on model state that later revisions may change.
    """
    settings = get_settings()
    days = date_range(settings.dim_date_start, settings.dim_date_end)
    if not days:
        return

    dim_date = sa.table(
        "dim_date",
        sa.column("date", sa.Date),
        sa.column("year", sa.Integer),
        sa.column("quarter", sa.Integer),
        sa.column("month", sa.Integer),
        sa.column("month_name", sa.Text),
        sa.column("day_of_month", sa.Integer),
        sa.column("weekday", sa.Integer),
        sa.column("weekday_name", sa.Text),
        sa.column("iso_week", sa.Integer),
        sa.column("week_start_date", sa.Date),
        sa.column("is_weekend", sa.Boolean),
    )
    op.bulk_insert(dim_date, [build_row(day) for day in days])


def downgrade() -> None:
    op.drop_index("ix_sessions_token_hash", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_fact_completion_habit_date", table_name="fact_completion")
    op.drop_index("ix_fact_completion_user_date", table_name="fact_completion")
    op.drop_table("fact_completion")
    op.drop_table("dim_date")
    op.drop_table("habit_schedules")
    op.drop_index("ix_habits_user_active", table_name="habits")
    op.drop_table("habits")
    op.drop_table("buckets")
    op.drop_table("users")
