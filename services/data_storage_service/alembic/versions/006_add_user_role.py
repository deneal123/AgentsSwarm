"""Add role column to profile.user table.

Revision ID: 006_add_user_role
Revises: 005_refactoring_cleanup
Create Date: 2026-03-06 16:00:00.000000

Changes:
- Added 'role' column (VARCHAR 50, default 'lawyer') to profile.user
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_add_user_role"
down_revision: Union[str, None] = "005_refactoring_cleanup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add role column to profile.user."""
    op.add_column(
        "user",
        sa.Column(
            "role",
            sa.String(length=50),
            nullable=False,
            server_default="lawyer",
            comment="User role: lawyer | admin",
        ),
        schema="profile",
    )
    op.create_index("idx_users_role", "user", ["role"], schema="profile")


def downgrade() -> None:
    """Remove role column from profile.user."""
    op.drop_index("idx_users_role", table_name="user", schema="profile")
    op.drop_column("user", "role", schema="profile")
