"""Add metadata_json JSONB column to profile.files

Revision ID: 008_add_metadata_json_to_files
Revises: 007_rules_marketplace
Create Date: 2026-03-10

Adds a nullable JSONB column `metadata_json` to the profile.files table so
the application can persist file metadata produced by the scanner/thumbnail
generator. The column is added with IF NOT EXISTS to be resilient on
databases that were already manually migrated.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "008_add_metadata_json_to_files"
down_revision: Union[str, None] = "007_rules_marketplace"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the metadata_json JSONB column if it's missing.
    # Use raw SQL to leverage IF NOT EXISTS which is concise here.
    op.execute(
        "ALTER TABLE profile.files ADD COLUMN IF NOT EXISTS metadata_json JSONB"
    )


def downgrade() -> None:
    # Remove the column if present.
    op.execute("ALTER TABLE profile.files DROP COLUMN IF EXISTS metadata_json")
