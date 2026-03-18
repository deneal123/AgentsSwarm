"""Rules Marketplace — remove risk catalogue, add UserRulePreference

Revision ID: 007_rules_marketplace
Revises: 006_add_user_role
Create Date: 2026-03-07

Changes:
  1. Drop profile.risks table (and the risk_id FK column in profile.rules).
  2. Add risk_id VARCHAR(100) to profile.rules (informational, no FK).
  3. Add active_version_number removal — was never in DB, nothing to do.
  4. Add UNIQUE constraint (rule_id, version_number) to profile.rule_versions.
  5. Create profile.user_rule_preferences table (per-user active version choice).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "007_rules_marketplace"
down_revision: Union[str, None] = "006_add_user_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Drop the risk_id FK column from profile.rules
    #    (it currently references profile.risks.id)
    # ------------------------------------------------------------------
    # Drop FK constraint first (name may vary — use IF EXISTS via raw SQL)
    op.execute(
        """
        DO $$
        DECLARE
            r record;
        BEGIN
            FOR r IN
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'profile.rules'::regclass
                  AND contype = 'f'
                  AND conname ILIKE '%risk_id%'
            LOOP
                EXECUTE format('ALTER TABLE profile.rules DROP CONSTRAINT %I', r.conname);
            END LOOP;
        END $$;
        """
    )
    # Drop the old UUID risk_id column
    op.execute("ALTER TABLE profile.rules DROP COLUMN IF EXISTS risk_id")

    # ------------------------------------------------------------------
    # 2. Add new informational risk_id VARCHAR column to profile.rules
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE profile.rules ADD COLUMN IF NOT EXISTS risk_id VARCHAR(100)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_rules_risk_id ON profile.rules (risk_id)"
    )

    # ------------------------------------------------------------------
    # 3. Drop profile.risks table (CASCADE removes any remaining FKs)
    # ------------------------------------------------------------------
    op.execute("DROP TABLE IF EXISTS profile.risks CASCADE")

    # ------------------------------------------------------------------
    # 4. Add UNIQUE constraint (rule_id, version_number) to rule_versions
    # ------------------------------------------------------------------
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_rule_version'
                  AND conrelid = 'profile.rule_versions'::regclass
            ) THEN
                ALTER TABLE profile.rule_versions
                    ADD CONSTRAINT uq_rule_version UNIQUE (rule_id, version_number);
            END IF;
        END $$;
        """
    )

    # ------------------------------------------------------------------
    # 5. Add created_by_user_id index to rule_versions if missing
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rule_versions_created_by
            ON profile.rule_versions (created_by_user_id)
        """
    )

    # ------------------------------------------------------------------
    # 6. Create profile.user_rule_preferences
    # ------------------------------------------------------------------
    op.create_table(
        "user_rule_preferences",
        sa.Column(
            "id",
            postgresql.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column("rule_id", postgresql.UUID(), nullable=False),
        sa.Column("pinned_version_number", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "rule_id", name="uq_user_rule_preference"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["profile.user.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["profile.rules.id"],
            ondelete="CASCADE",
        ),
        schema="profile",
        comment="Per-user active version preference for each rule",
    )
    op.create_index(
        "idx_user_rule_prefs_user_id",
        "user_rule_preferences",
        ["user_id"],
        schema="profile",
    )
    op.create_index(
        "idx_user_rule_prefs_rule_id",
        "user_rule_preferences",
        ["rule_id"],
        schema="profile",
    )


def downgrade() -> None:
    # Drop user_rule_preferences
    op.drop_table("user_rule_preferences", schema="profile")

    # Drop uq_rule_version constraint
    op.execute(
        "ALTER TABLE profile.rule_versions DROP CONSTRAINT IF EXISTS uq_rule_version"
    )

    # Drop new risk_id VARCHAR column from rules
    op.execute("ALTER TABLE profile.rules DROP COLUMN IF EXISTS risk_id")

    # Recreate profile.risks table
    op.create_table(
        "risks",
        sa.Column(
            "id",
            postgresql.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        schema="profile",
    )

    # Restore old UUID risk_id FK column in rules (nullable to avoid constraint issues)
    op.execute(
        "ALTER TABLE profile.rules ADD COLUMN risk_id UUID REFERENCES profile.risks(id) ON DELETE CASCADE"
    )
