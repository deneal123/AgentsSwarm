from __future__ import annotations

import json
from pathlib import Path

from tests.test_critical_endpoint_snapshots import _extract_openapi_operation_snapshot


def main() -> None:
    openapi_path = Path("artifacts/openapi.json")
    snapshot_path = Path("tests/snapshots/critical_endpoint_openapi.json")
    if not openapi_path.exists():
        raise SystemExit(f"missing generated schema: {openapi_path}")
    openapi_schema = json.loads(openapi_path.read_text(encoding="utf-8"))
    current_critical = _extract_openapi_operation_snapshot(openapi_schema)
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if current_critical != expected:
        raise SystemExit(
            "critical OpenAPI snapshot changed. run tests to inspect and update snapshots intentionally"
        )


if __name__ == "__main__":
    main()
