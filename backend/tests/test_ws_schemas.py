import pytest
from pydantic import ValidationError

from service.shared.presentation.routers import ws_schemas


def test_chat_models_valid_and_invalid():
    # valid ChatChunkOut
    m = ws_schemas.ChatChunkOut(id="c1", seq=1, data="hello")
    assert m.type == "chunk"

    # invalid: missing required fields
    with pytest.raises(ValidationError):
        ws_schemas.ChatChunkOut(id="c1", data="x")  # missing seq

    # valid ChatMessageIn
    mi = ws_schemas.ChatMessageIn(id="m1", text="hi")
    assert mi.type == "message"

    # invalid type value
    with pytest.raises(ValidationError):
        ws_schemas.ChatMessageIn(type="not-message", id="m1", text="hi")


def test_job_models_validation():
    jp = ws_schemas.JobProgressOut(progress=50)
    assert jp.event == "progress"

    with pytest.raises(ValidationError):
        ws_schemas.JobProgressOut(event="not-progress", progress=10)

    jc = ws_schemas.JobChunkOut(seq=2, data={"partial": True})
    assert jc.event == "chunk"


def test_file_scan_event_model():
    f = ws_schemas.FileScanEvent(file_key="uploads/abc.jpg", result={"status": "ok"})
    assert f.event == "scanned"

    with pytest.raises(ValidationError):
        ws_schemas.FileScanEvent(file_key=123, result={})  # file_key must be str
