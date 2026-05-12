"""Create billing webhooks table

Revision ID: 017_billing_webhooks_table
Revises: 016_billing_idx_trgs
Create Date: 2025-12-26 20:40:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "017_billing_webhooks"
down_revision = "016_billing_idx_trgs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS profile;")
    op.create_table(
        "billing_webhooks",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("webhook_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="profile",
    )
    op.create_index(
        "ix_profile_billing_webhooks_webhook_id",
        "billing_webhooks",
        ["webhook_id"],
        unique=True,
        schema="profile",
    )
    op.create_index(
        "ix_profile_billing_webhooks_created_at",
        "billing_webhooks",
        ["created_at"],
        schema="profile",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_profile_billing_webhooks_created_at", table_name="billing_webhooks", schema="profile"
    )
    op.drop_index(
        "ix_profile_billing_webhooks_webhook_id", table_name="billing_webhooks", schema="profile"
    )
    op.drop_table("billing_webhooks", schema="profile")
