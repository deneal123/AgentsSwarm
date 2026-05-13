from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ENUM_SOURCE_FILES = {
    Path("backend/service/models/key_value.py"),
}
MIGRATION_PREFIX = Path("backend/alembic/versions")


def _git_diff_files(base_ref: str, head_ref: str) -> list[Path]:
    cmd = ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def _enum_related_file(path: Path) -> bool:
    if path in ENUM_SOURCE_FILES:
        return True
    if not path.parts[:3] == ("backend", "service", "models"):
        return False
    if path.suffix != ".py":
        return False
    full_path = Path.cwd() / path
    if not full_path.exists():
        return False
    return "StrEnum" in full_path.read_text(encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python backend/scripts/check_enum_revision_guard.py <base_ref> <head_ref>"
        )

    base_ref = sys.argv[1]
    head_ref = sys.argv[2]
    changed_files = _git_diff_files(base_ref, head_ref)

    enum_files_changed = any(_enum_related_file(path) for path in changed_files)
    if not enum_files_changed:
        print("Enum files were not changed")
        return 0

    has_new_migration = any(
        path.parts[:3] == MIGRATION_PREFIX.parts and path.suffix == ".py" for path in changed_files
    )
    if has_new_migration:
        print("Enum files changed and migration revision detected")
        return 0

    print("Enum files changed but no Alembic revision added under backend/alembic/versions")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
