"""Add CHAT to ServiceType and ServiceMode enums

Revision ID: 1a65587dc2e1
Revises: 017_billing_webhooks
Create Date: 2025-12-28 19:21:51.433030

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1a65587dc2e1"
down_revision: Union[str, Sequence[str], None] = "017_billing_webhooks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add CHAT to enums."""
    # Create ServiceType enum if it doesn't exist, otherwise add CHAT value
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'service_type') THEN
                CREATE TYPE service_type AS ENUM ('CALENDAR', 'CHAT');
            ELSE
                ALTER TYPE service_type ADD VALUE IF NOT EXISTS 'CHAT';
            END IF;
        END
        $$;
    """)

    # Create ServiceMode enum if it doesn't exist, otherwise add CHAT value
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'service_mode') THEN
                CREATE TYPE service_mode AS ENUM ('CALENDAR', 'CHAT');
            ELSE
                ALTER TYPE service_mode ADD VALUE IF NOT EXISTS 'CHAT';
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    """Downgrade schema.
    
    Note: PostgreSQL does not support removing enum values directly.
    This would require recreating the enum type, which is complex and risky.
    For safety, we leave the enum values in place.
    """
    # Cannot safely remove enum values in PostgreSQL
    pass

