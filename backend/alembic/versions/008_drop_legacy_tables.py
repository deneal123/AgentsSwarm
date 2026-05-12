"""Drop legacy nutrition calendar and batch tables

Revision ID: 008_drop_legacy_tables
Revises: 7152f9af9647
Create Date: 2026-05-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "008_drop_legacy_tables"
down_revision: Union[str, Sequence[str], None] = "7152f9af9647"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("nutrition_calendar_versions", schema="profile")
    op.drop_table("nutrition_calendars", schema="profile")
    op.drop_table("batch_items", schema="profile")
    op.drop_table("batches", schema="profile")

    # Remove CALENDAR value from service_type enum if it exists
    op.execute("ALTER TYPE service_type RENAME TO service_type_old")
    op.execute("CREATE TYPE service_type AS ENUM ('CHAT')")
    op.execute(
        "ALTER TABLE profile.user_launch "
        "ALTER COLUMN type TYPE service_type USING type::text::service_type"
    )
    op.execute("DROP TYPE service_type_old")


def downgrade() -> None:
    op.create_table(
        "batches",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("batch_id", UUID(), unique=True, nullable=False),
        sa.Column("user_id", UUID(), sa.ForeignKey("profile.user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("size", sa.BigInteger(), nullable=True),
        sa.Column("progress", JSONB(), nullable=True),
        schema="profile",
    )
    op.create_table(
        "batch_items",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("batch_id", sa.BigInteger(), sa.ForeignKey("profile.batches.id", ondelete="CASCADE")),
        sa.Column("item_index", sa.BigInteger(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("result", JSONB(), nullable=True),
        schema="profile",
    )
    op.create_table(
        "nutrition_calendars",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("calendar_id", UUID(), unique=True, nullable=False),
        sa.Column("user_id", UUID(), sa.ForeignKey("profile.user.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("manifest", JSONB(), nullable=True),
        sa.Column("storage_uri", sa.String(1000), nullable=True),
        schema="profile",
    )
    op.create_table(
        "nutrition_calendar_versions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("calendar_id", sa.BigInteger(), sa.ForeignKey("profile.nutrition_calendars.id", ondelete="CASCADE")),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("manifest", JSONB(), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        schema="profile",
    )
