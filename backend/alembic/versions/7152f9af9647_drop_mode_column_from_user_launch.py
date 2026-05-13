"""Drop mode column from user_launch table

Revision ID: 7152f9af9647
Revises: 2b7c8d9e1f2a
Create Date: 2026-04-13 11:09:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7152f9af9647"
down_revision: str | Sequence[str] | None = "2b7c8d9e1f2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop mode column from user_launch table."""
    op.drop_column("user_launch", "mode", schema="profile")


def downgrade() -> None:
    """Add mode column back to user_launch table."""
    op.add_column("user_launch", sa.Column("mode", sa.String(50), nullable=True), schema="profile")
