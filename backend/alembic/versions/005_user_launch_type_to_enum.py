"""Convert profile.user_launch.type column to PostgreSQL ENUM including CALENDAR

Revision ID: 005_user_launch_type_to_enum
Revises: 004_add_calendar_service_type_check
Create Date: 2025-12-26 00:00:00.000000

This migration attempts to migrate the free-form string column `profile.user_launch.type`
into a proper PostgreSQL ENUM type `service_type` to make handoffs between application
and DB safer and to allow native-checking of values like 'CALENDAR'.

Operational notes:
- The migration first checks for any rows with unknown or NULL type values. If any are
  found it will abort and print instructions for remediation. This is deliberate to avoid
  silently converting data.
- If you prefer an automated fallback (e.g., setting unknown values to 'DEFAULT'),
  perform that data fix before running this migration.

Rollout steps for production:
1. Run the check query below to ensure no unexpected types exist:
   SELECT DISTINCT type FROM profile.user_launch WHERE type NOT IN ('TRAIN','DEFAULT','CALENDAR') OR type IS NULL;
2. If the query returns rows, inspect and either delete or update them to one of the
   allowed values.
3. Run the migration (alembic upgrade head).

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "005_user_launch_type_to_enum"
down_revision = "004_add_calendar_service_type_check"
branch_labels = None
depends_on = None

ALLOWED = ("TRAIN", "DEFAULT", "CALENDAR")
ENUM_NAME = "service_type"


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Ensure there are no non-conforming rows
    q = "SELECT COUNT(*) FROM profile.user_launch WHERE type NOT IN ({}) OR type IS NULL".format(
        ",".join([f"'{v}'" for v in ALLOWED])
    )
    count = conn.execute(sa.text(q)).scalar()
    if count and int(count) > 0:
        raise RuntimeError(
            f"Found {count} user_launch rows with types outside {ALLOWED}. Please clean data before applying this migration."
        )

    # 2) Drop old check constraint if present (added by previous migration)
    try:
        op.drop_constraint(
            "ck_profile_user_launch_type_allowed", "user_launch", schema="profile", type_="check"
        )
    except Exception:
        # Ignore if it doesn't exist
        pass

    # 3) Create new ENUM type
    enum = postgresql.ENUM(*ALLOWED, name=ENUM_NAME)
    enum.create(op.get_bind(), checkfirst=True)

    # 4) Alter column type to the new enum
    op.execute(
        f"ALTER TABLE profile.user_launch ALTER COLUMN type TYPE {ENUM_NAME} USING type::text::{ENUM_NAME}"
    )


def downgrade() -> None:
    # Revert column back to plain varchar
    op.execute("ALTER TABLE profile.user_launch ALTER COLUMN type TYPE varchar(50)")
    # Drop enum type
    op.execute(f"DROP TYPE IF EXISTS {ENUM_NAME}")
