"""Drop phone column from profile.user

Revision ID: 017_drop_phone
Revises: 016_billing_idx_trgs
Create Date: 2025-12-26 13:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "017_drop_phone"
down_revision = "016_billing_idx_trgs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Safely remove the legacy `phone` column from the user table.

    The migration uses IF EXISTS to make it safe to run multiple times and in
    environments where the column might already be absent.
    """
    # Drop column if it exists (Postgres supports IF EXISTS)
    op.execute('ALTER TABLE profile."user" DROP COLUMN IF EXISTS phone;')


def downgrade() -> None:
    """Bring back the `phone` column as nullable text. This is a best-effort
    downgrade to restore schema compatibility; historical data cannot be
    recovered by this operation.
    """
    op.add_column(
        "user",
        sa.Column("phone", sa.String(length=20), nullable=True),
        schema="profile",
    )
