from __future__ import annotations

import ast
import re
from pathlib import Path

import service.models.db.db_models as db_models
from sqlalchemy import Enum as SqlEnum

from service.models.db.base_db_model import Base

_ = db_models

CREATE_TYPE_PATTERN = re.compile(
    r"CREATE\s+TYPE\s+(?P<name>[a-zA-Z_][\w]*)\s+AS\s+ENUM\s*\((?P<values>[^)]*)\)",
    re.IGNORECASE | re.MULTILINE,
)
ALTER_ADD_VALUE_PATTERN = re.compile(
    r"ALTER\s+TYPE\s+(?P<name>[a-zA-Z_][\w]*)\s+ADD\s+VALUE(?:\s+IF\s+NOT\s+EXISTS)?\s+'(?P<value>[^']+)'",
    re.IGNORECASE | re.MULTILINE,
)
DROP_TYPE_PATTERN = re.compile(
    r"DROP\s+TYPE(?:\s+IF\s+EXISTS)?\s+(?P<name>[a-zA-Z_][\w]*)",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_quoted_values(raw_values: str) -> list[str]:
    return [value.strip("' ") for value in re.findall(r"'([^']+)'", raw_values)]


def _literal_value(node: ast.AST) -> str | list[str] | tuple[str, ...] | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Tuple):
        values: list[str] = []
        for element in node.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                values.append(element.value)
        return tuple(values)
    if isinstance(node, ast.List):
        values: list[str] = []
        for element in node.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                values.append(element.value)
        return values
    return None


def _normalize_down_revisions(value: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if value is None:
        return tuple()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(value)
    return value


def _parse_revision_headers(path: Path) -> tuple[str, tuple[str, ...]]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    revision = ""
    down_revision: str | list[str] | tuple[str, ...] | None = None
    for statement in module.body:
        if not isinstance(statement, ast.AnnAssign | ast.Assign):
            continue
        targets: list[ast.expr] = []
        value: ast.AST | None = None
        if isinstance(statement, ast.Assign):
            targets = list(statement.targets)
            value = statement.value
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            targets = [statement.target]
            value = statement.value
        if value is None:
            continue
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id == "revision":
                literal = _literal_value(value)
                if isinstance(literal, str):
                    revision = literal
            if target.id == "down_revision":
                down_revision = _literal_value(value)
    if not revision:
        raise AssertionError(f"Unable to parse revision id in {path}")
    return revision, _normalize_down_revisions(down_revision)


def _load_revision_files_in_upgrade_order() -> list[Path]:
    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    files = sorted(versions_dir.glob("*.py"))

    parents: dict[str, tuple[str, ...]] = {}
    path_by_revision: dict[str, Path] = {}
    for file_path in files:
        revision, down_revisions = _parse_revision_headers(file_path)
        parents[revision] = down_revisions
        path_by_revision[revision] = file_path

    ordered: list[str] = []
    resolved: set[str] = set()
    unresolved = set(parents)
    while unresolved:
        progressed = False
        for revision in list(unresolved):
            down_revisions = parents[revision]
            if all(parent in resolved or parent not in parents for parent in down_revisions):
                ordered.append(revision)
                resolved.add(revision)
                unresolved.remove(revision)
                progressed = True
        if not progressed:
            raise AssertionError("Unable to resolve Alembic revision order")

    return [path_by_revision[revision] for revision in ordered]


def _enum_values_from_revisions() -> dict[str, list[str]]:
    values_by_type: dict[str, list[str]] = {}
    for path in _load_revision_files_in_upgrade_order():
        source = path.read_text(encoding="utf-8")

        for match in CREATE_TYPE_PATTERN.finditer(source):
            enum_name = match.group("name")
            values_by_type[enum_name] = _extract_quoted_values(match.group("values"))

        for match in ALTER_ADD_VALUE_PATTERN.finditer(source):
            enum_name = match.group("name")
            enum_value = match.group("value")
            enum_values = values_by_type.setdefault(enum_name, [])
            if enum_value not in enum_values:
                enum_values.append(enum_value)

        for match in DROP_TYPE_PATTERN.finditer(source):
            enum_name = match.group("name")
            values_by_type.pop(enum_name, None)

    return values_by_type


def _enum_values_from_sqlalchemy_metadata() -> dict[str, list[str]]:
    enum_values: dict[str, list[str]] = {}
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, SqlEnum) and column.type.enum_class is not None:
                enum_name = column.type.name
                if not enum_name:
                    continue
                values = [member.value for member in column.type.enum_class]
                enum_values[enum_name] = values
    return enum_values


def test_sqlalchemy_enums_are_in_sync_with_alembic_revisions() -> None:
    metadata_enums = _enum_values_from_sqlalchemy_metadata()
    revision_enums = _enum_values_from_revisions()

    missing_enum_types = sorted(name for name in metadata_enums if name not in revision_enums)
    assert not missing_enum_types, f"Missing enum types in Alembic revisions: {missing_enum_types}"

    mismatches: list[tuple[str, list[str], list[str]]] = []
    for enum_name, metadata_values in metadata_enums.items():
        revision_values = revision_enums[enum_name]
        if metadata_values != revision_values:
            mismatches.append((enum_name, metadata_values, revision_values))

    assert not mismatches, f"Enum value mismatch between metadata and Alembic revisions: {mismatches}"
