"""Add partial indexes and triggers for billing tables

Revision ID: 016_billing_partial_indexes_triggers
Revises: 001_initial
Create Date: 2025-12-26 12:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "016_billing_idx_trgs"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Partial indexes for fast lookup of active reservations (status = 'reserved')
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_profile_token_reservations_user_id_reserved
        ON profile.token_reservations (user_id)
        WHERE status = 'reserved'
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_profile_token_reservations_expires_at_reserved
        ON profile.token_reservations (expires_at)
        WHERE status = 'reserved'
        """
    )

    # Index to help queries that look up the relevant quota row for a user/period
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_profile_token_quotas_user_period
        ON profile.token_quotas (user_id, period_start, period_end)
        """
    )

    # Index to speed up recent billing event queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_profile_billing_events_created_at
        ON profile.billing_events (created_at)
        """
    )

    # Trigger function to mark reservations expired immediately on insert/update when expires_at is in the past
    op.execute(
        """
        CREATE OR REPLACE FUNCTION profile.expire_reservation_if_past()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (NEW.expires_at IS NOT NULL AND NEW.expires_at < now()) THEN
                NEW.status := 'expired';
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )

    # Trigger to invoke function before insert or update
    # Ensure any existing trigger is removed first
    op.execute(
        "DROP TRIGGER IF EXISTS trg_expire_reservation_before_insert_update ON profile.token_reservations;"
    )

    # Then create the trigger invoking the plpgsql function
    op.execute(
        """
        CREATE TRIGGER trg_expire_reservation_before_insert_update
        BEFORE INSERT OR UPDATE ON profile.token_reservations
        FOR EACH ROW
        EXECUTE PROCEDURE profile.expire_reservation_if_past();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_expire_reservation_before_insert_update ON profile.token_reservations;"
    )
    op.execute("DROP FUNCTION IF EXISTS profile.expire_reservation_if_past();")
    op.execute("DROP INDEX IF EXISTS profile.ix_profile_token_reservations_user_id_reserved;")
    op.execute("DROP INDEX IF EXISTS profile.ix_profile_token_reservations_expires_at_reserved;")
    op.execute("DROP INDEX IF EXISTS profile.ix_profile_token_quotas_user_period;")
    op.execute("DROP INDEX IF EXISTS profile.ix_profile_billing_events_created_at;")
