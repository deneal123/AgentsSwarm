from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "<revision_id>"
down_revision: str | Sequence[str] | None = "<down_revision_id>"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_NAME = "<enum_name>"
OLD_VALUES: tuple[str, ...] = ("<old_value_1>",)
NEW_VALUES: tuple[str, ...] = ("<new_value_1>", "<new_value_2>")
AFFECTED_TABLES: tuple[tuple[str, str], ...] = (("<schema>", "<table>"),)
AFFECTED_COLUMNS: tuple[str, ...] = ("<column>",)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _create_temp_enum(enum_name: str, values: tuple[str, ...]) -> None:
    op.execute(sa.text(f"CREATE TYPE {enum_name} AS ENUM ({_quoted(values)})"))


def _alter_column_to_enum(schema: str, table: str, column: str, enum_name: str) -> None:
    op.execute(
        sa.text(
            "ALTER TABLE "
            f"{schema}.{table} "
            f"ALTER COLUMN {column} TYPE {enum_name} "
            f"USING {column}::text::{enum_name}"
        )
    )


def _alter_column_to_text(schema: str, table: str, column: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {schema}.{table} ALTER COLUMN {column} TYPE text USING {column}::text"))


def _add_backfill() -> None:
    op.execute(sa.text("<backfill_sql>"))


def _check_data_for_downgrade() -> None:
    op.execute(sa.text("<downgrade_data_check_sql>"))


def upgrade() -> None:
    _add_backfill()
    for value in NEW_VALUES:
        op.execute(sa.text(f"ALTER TYPE {ENUM_NAME} ADD VALUE IF NOT EXISTS '{value}'"))


def downgrade() -> None:
    _check_data_for_downgrade()
    temp_enum_name = f"{ENUM_NAME}_tmp"
    _create_temp_enum(temp_enum_name, OLD_VALUES)
    for schema, table in AFFECTED_TABLES:
        for column in AFFECTED_COLUMNS:
            _alter_column_to_text(schema, table, column)
    op.execute(sa.text(f"DROP TYPE {ENUM_NAME}"))
    op.execute(sa.text(f"ALTER TYPE {temp_enum_name} RENAME TO {ENUM_NAME}"))
    for schema, table in AFFECTED_TABLES:
        for column in AFFECTED_COLUMNS:
            _alter_column_to_enum(schema, table, column, ENUM_NAME)
