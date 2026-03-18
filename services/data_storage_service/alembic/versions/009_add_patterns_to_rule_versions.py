"""Add patterns JSONB column to rule_versions

Revision ID: 009_add_patterns_to_rule_versions
Revises: 008_add_metadata_json_to_files
Create Date: 2026-03-11

Changes:
  1. Add `patterns` JSONB column to profile.rule_versions
     (dict of {key: regex_string} for simple/combine rules).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "009_add_patterns_to_rule_versions"
down_revision: Union[str, None] = "008_add_metadata_json_to_files"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE profile.rule_versions
            ADD COLUMN IF NOT EXISTS patterns JSONB NOT NULL DEFAULT '{}'
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rule_versions_patterns
            ON profile.rule_versions USING gin (patterns)
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS profile.idx_rule_versions_patterns"
    )
    op.execute(
        "ALTER TABLE profile.rule_versions DROP COLUMN IF EXISTS patterns"
    )
