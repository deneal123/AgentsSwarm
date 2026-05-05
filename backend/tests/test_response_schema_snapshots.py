import json
from pathlib import Path

from service.presentation.routers.chat_api.schemas import MessageResponse, ThreadResponse
from service.presentation.routers.jobs_api.schemas import JobResponse


def _schema_signature(model) -> dict[str, object]:
    return {
        "title": model.__name__,
        "fields": sorted(model.model_fields.keys()),
        "required": sorted(name for name, field in model.model_fields.items() if field.is_required()),
    }


def test_critical_response_schema_snapshot() -> None:
    actual = {
        "MessageResponse": _schema_signature(MessageResponse),
        "JobResponse": _schema_signature(JobResponse),
        "ThreadResponse": _schema_signature(ThreadResponse),
    }
    snapshot_path = Path(__file__).parent / "snapshots" / "critical_response_schemas.json"
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert actual == expected
