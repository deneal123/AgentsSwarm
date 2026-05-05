from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from service.main import create_app

CRITICAL_OPERATIONS = (
    ("post", "/api/auth/v1/register"),
    ("post", "/api/auth/v1/login"),
    ("post", "/api/chats/"),
    ("get", "/api/chats/{thread_id}"),
    ("post", "/api/chats/{thread_id}/message"),
    ("post", "/api/jobs/v1/start"),
    ("get", "/api/jobs/v1/result/{job_id}"),
)


def _sorted_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sorted_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sorted_json(item) for item in value]
    return value


def _collect_schema_refs(value: Any, refs: set[str]) -> None:
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            refs.add(ref.split("/")[-1])
        for nested in value.values():
            _collect_schema_refs(nested, refs)
    elif isinstance(value, list):
        for nested in value:
            _collect_schema_refs(nested, refs)


def _collect_component_schemas(openapi_schema: dict[str, Any], root_refs: set[str]) -> dict[str, Any]:
    components = openapi_schema.get("components", {}).get("schemas", {})
    collected: dict[str, Any] = {}
    queue = list(root_refs)
    seen: set[str] = set()
    while queue:
        schema_name = queue.pop()
        if schema_name in seen:
            continue
        seen.add(schema_name)
        schema = components.get(schema_name)
        if schema is None:
            continue
        collected[schema_name] = schema
        nested_refs: set[str] = set()
        _collect_schema_refs(schema, nested_refs)
        queue.extend(sorted(nested_refs - seen))
    return collected


def _extract_openapi_operation_snapshot(openapi_schema: dict[str, Any]) -> dict[str, Any]:
    paths = openapi_schema.get("paths", {})
    snapshot_paths: dict[str, Any] = {}
    root_refs: set[str] = set()
    for method, path in CRITICAL_OPERATIONS:
        operation = paths[path][method]
        operation_snapshot = {
            "operationId": operation.get("operationId"),
            "parameters": operation.get("parameters", []),
            "requestBody": operation.get("requestBody"),
            "responses": operation.get("responses", {}),
        }
        snapshot_paths[f"{method.upper()} {path}"] = operation_snapshot
        _collect_schema_refs(operation_snapshot, root_refs)
    return {
        "paths": _sorted_json(snapshot_paths),
        "components": _sorted_json(_collect_component_schemas(openapi_schema, root_refs)),
    }


def test_critical_endpoint_openapi_snapshot() -> None:
    app = create_app()
    actual_snapshot = _extract_openapi_operation_snapshot(app.openapi())
    snapshot_path = Path(__file__).parent / "snapshots" / "critical_endpoint_openapi.json"
    expected_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert actual_snapshot == expected_snapshot
