"""Add updated_at column to communication_task

Revision ID: 002
Revises: 001_pushi_initial_v2
Create Date: 2026-02-19 14:55:00.000000
"""
from typing import Union, Sequence

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001_pushi_initial_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "communication_task",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="profile",
    )


def downgrade() -> None:
    op.drop_column("communication_task", "updated_at", schema="profile")
