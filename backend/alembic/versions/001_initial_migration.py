"""Initial migration with password support and consolidated schema

Revision ID: 001_initial
Revises:
Create Date: 2025-09-24 12:00:00.000000

Note: This initial migration was expanded to include tables and indexes from subsequent revisions
(009..015) for a consolidated starting point. Other revisions remain in the versions directory as
no-op historical entries to preserve Alembic history.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to consolidated state.
    This creates schemas, user/session tables, chat/batch tables, nutrition calendars, and
    billing/token tables as the canonical starting schema for new environments.
    """
    # Create profile and session schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS profile")
    op.execute("CREATE SCHEMA IF NOT EXISTS session")

    # Create user table (phone removed as per final schema decision)
    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("email", sa.String(length=500), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=50), nullable=True),
        sa.Column("available_launches", sa.Integer(), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=True),
        sa.Column("avatar_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        schema="profile",
        comment="User profiles with password authentication",
    )

    # user_launch table
    op.create_table(
        "user_launch",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column("mode", sa.String(length=50), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "is_payment_taken", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["profile.user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="profile",
    )
    op.create_index("ix_profile_user_launch_user_id", "user_launch", ["user_id"], schema="profile")

    # user_session table
    op.create_table(
        "user_session",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column("fingerprint", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_code", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="session",
    )
    op.create_index(
        "ix_session_user_session_user_id", "user_session", ["user_id"], schema="session"
    )

    # Chat tables
    op.create_table(
        "chat_threads",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("thread_id", postgresql.UUID(), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="profile",
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("message_id", postgresql.UUID(), nullable=False, unique=True),
        sa.Column(
            "thread_id",
            sa.BigInteger(),
            sa.ForeignKey("profile.chat_threads.id", ondelete="CASCADE"),
        ),
        sa.Column("user_id", postgresql.UUID(), nullable=True),
        sa.Column("sender", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_tokens", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="profile",
    )

    op.create_index(
        "ix_profile_chat_threads_user_id", "chat_threads", ["user_id"], schema="profile"
    )
    op.create_index(
        "ix_profile_chat_messages_thread_id", "chat_messages", ["thread_id"], schema="profile"
    )

    # Nutrition calendars
    op.create_table(
        "nutrition_calendars",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("calendar_id", postgresql.UUID(), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("manifest", postgresql.JSONB(), nullable=True),
        sa.Column("storage_uri", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="profile",
    )

    op.create_table(
        "nutrition_calendar_versions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "calendar_id",
            sa.BigInteger(),
            sa.ForeignKey("profile.nutrition_calendars.id", ondelete="CASCADE"),
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="profile",
    )
    op.create_index(
        "ix_profile_nutrition_calendars_user_id",
        "nutrition_calendars",
        ["user_id"],
        schema="profile",
    )

    # Batches
    op.create_table(
        "batches",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("batch_id", postgresql.UUID(), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default=sa.text("'queued'")
        ),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("progress", postgresql.JSONB(), server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="profile",
    )
    op.create_table(
        "batch_items",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "batch_id", sa.BigInteger(), sa.ForeignKey("profile.batches.id", ondelete="CASCADE")
        ),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default=sa.text("'queued'")
        ),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="profile",
    )
    op.create_index("ix_profile_batches_status", "batches", ["status"], schema="profile")
    op.create_index(
        "ix_profile_batch_items_batch_id", "batch_items", ["batch_id"], schema="profile"
    )

    # Billing / Token quotas
    op.create_table(
        "token_quotas",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(), sa.ForeignKey("profile.user.id", ondelete="CASCADE")
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("limit", sa.BigInteger(), nullable=False),
        sa.Column("used", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="profile",
    )

    op.create_table(
        "token_reservations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("reservation_id", postgresql.UUID(), nullable=False, unique=True),
        sa.Column(
            "user_id", postgresql.UUID(), sa.ForeignKey("profile.user.id", ondelete="CASCADE")
        ),
        sa.Column("tokens_reserved", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default=sa.text("'reserved'")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        schema="profile",
    )
    op.create_index(
        "ix_profile_token_quotas_user_id",
        "token_quotas",
        ["user_id"],
        schema="profile",
    )
    op.create_index(
        "ix_profile_token_reservations_reservation_id",
        "token_reservations",
        ["reservation_id"],
        schema="profile",
    )

    op.create_table(
        "billing_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(), sa.ForeignKey("profile.user.id", ondelete="SET NULL")
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("tokens", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="profile",
    )
    op.create_index(
        "ix_profile_billing_events_user_id",
        "billing_events",
        ["user_id"],
        schema="profile",
    )

    # user_file table (consolidated from 002_add_user_file)
    op.create_table(
        "user_file",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column("mode", sa.String(length=50), nullable=False),
        sa.Column("file_name", sa.String(length=1000), nullable=False),
        sa.Column("file_url", sa.String(length=1000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["profile.user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="profile",
    )
    op.create_index(
        "ix_profile_user_file_user_id",
        "user_file",
        ["user_id"],
        schema="profile",
    )


def downgrade() -> None:
    """Drop consolidated schema objects."""
    op.drop_index(
        "ix_profile_billing_events_user_id", table_name="billing_events", schema="profile"
    )
    op.drop_index(
        "ix_profile_token_reservations_reservation_id",
        table_name="token_reservations",
        schema="profile",
    )
    op.drop_index("ix_profile_token_quotas_user_id", table_name="token_quotas", schema="profile")

    op.drop_index("ix_profile_batch_items_batch_id", table_name="batch_items", schema="profile")
    op.drop_index("ix_profile_batches_status", table_name="batches", schema="profile")
    op.drop_index(
        "ix_profile_nutrition_calendars_user_id", table_name="nutrition_calendars", schema="profile"
    )
    op.drop_index(
        "ix_profile_chat_messages_thread_id", table_name="chat_messages", schema="profile"
    )
    op.drop_index("ix_profile_chat_threads_user_id", table_name="chat_threads", schema="profile")

    op.drop_table("billing_events", schema="profile")
    op.drop_table("token_reservations", schema="profile")
    op.drop_table("token_quotas", schema="profile")

    op.drop_table("batch_items", schema="profile")
    op.drop_table("batches", schema="profile")
    op.drop_table("nutrition_calendar_versions", schema="profile")
    op.drop_table("nutrition_calendars", schema="profile")
    op.drop_table("chat_messages", schema="profile")
    op.drop_table("chat_threads", schema="profile")

    op.drop_index("ix_session_user_session_user_id", table_name="user_session", schema="session")
    op.drop_table("user_session", schema="session")

    op.drop_index("ix_profile_user_launch_user_id", table_name="user_launch", schema="profile")
    op.drop_table("user_launch", schema="profile")
    op.drop_table("user", schema="profile")

    op.drop_index("ix_profile_user_file_user_id", table_name="user_file", schema="profile")
    op.drop_table("user_file", schema="profile")

    op.execute("DROP SCHEMA IF EXISTS session CASCADE")
    op.execute("DROP SCHEMA IF EXISTS profile CASCADE")
