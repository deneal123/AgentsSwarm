"""Add check constraint to user_launch.type to include CALENDAR

Revision ID: 004_add_calendar_service_type_check
Revises: 003_drop_phone_column
Create Date: 2025-12-26 12:00:00.000000
"""
from typing import Union, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_add_calendar_service_type_check"
# Fix: previous migration file uses revision '017_drop_phone' (003 file's revision).
# Align down_revision so Alembic can build the correct revision map.
down_revision: Union[str, Sequence[str], None] = "017_drop_phone"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "ck_profile_user_launch_type_allowed"
ALLOWED = ("TRAIN", "CALENDAR")


def upgrade() -> None:
    conn = op.get_bind()
    # If there are user_launch rows with unknown types, skip adding the constraint
    sql = sa.text(
        "SELECT COUNT(*) FROM profile.user_launch WHERE type NOT IN (:a, :b) OR type IS NULL"
    )
    res = conn.execute(sql, {"a": ALLOWED[0], "b": ALLOWED[1]})
    cnt = int(res.scalar() or 0)
    if cnt > 0:
        # Don't enforce constraint when unknown values present; log via SQL comment
        op.execute(
            "/* Skipping adding %s because %d rows with non-conforming types exist */" % (CONSTRAINT_NAME, cnt)
        )
        return

    # Add check constraint enforcing allowed type values
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "user_launch",
        "type IN (%s)" % ", ".join("'%s'" % v for v in ALLOWED),
        schema="profile",
    )


def downgrade() -> None:
    try:
        op.drop_constraint(CONSTRAINT_NAME, "user_launch", schema="profile", type_="check")
    except Exception:
        # best-effort cleanup
        conn = op.get_bind()
        conn.execute(sa.text("/* Unable to drop %s - may not exist */" % CONSTRAINT_NAME))
