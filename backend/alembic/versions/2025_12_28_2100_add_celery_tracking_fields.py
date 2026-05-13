"""Add Celery task tracking fields to user_launch table

Revision ID: 2b7c8d9e1f2a
Revises: 1a65587dc2e1
Create Date: 2025-12-28 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b7c8d9e1f2a"
down_revision: str | Sequence[str] | None = "1a65587dc2e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - add Celery tracking fields to user_launch table."""
    # Add celery_task_id column
    op.add_column(
        "user_launch",
        sa.Column(
            "celery_task_id",
            sa.String(length=255),
            nullable=True,
            comment="Celery task ID for job tracking",
        ),
        schema="profile",
    )

    # Add celery_status column
    op.add_column(
        "user_launch",
        sa.Column(
            "celery_status", sa.String(length=50), nullable=True, comment="Celery task status"
        ),
        schema="profile",
    )


def downgrade() -> None:
    """Downgrade schema - remove Celery tracking fields."""
    # Remove celery_status column
    op.drop_column("user_launch", "celery_status", schema="profile")

    # Remove celery_task_id column
    op.drop_column("user_launch", "celery_task_id", schema="profile")
