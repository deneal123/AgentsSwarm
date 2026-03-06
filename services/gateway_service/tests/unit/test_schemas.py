"""
Unit-тесты: Pydantic-схемы (schemas/).

Покрывает:
  - PaginationParams: offset/limit расчёт, граничные значения
  - PaginatedResponse: create(), pages расчёт, Generic[T]
  - RegisterRequest: валидация пароля, username pattern, role
  - TaskCreate, TaskSummary, TaskStatus
  - ZoneCreate, ZoneBounds
  - ChatMessage, CommandAck
  - TelemetryResolution enum
  - ErrorResponse, MessageResponse
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gateway_service.auth.schemas import RegisterRequest, UserRole
from gateway_service.schemas.chat import ChatMessage, CommandAck
from gateway_service.schemas.common import (
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
)
from gateway_service.schemas.task import TaskCreate, TaskStatus, TaskSummary
from gateway_service.schemas.telemetry import TelemetryResolution
from gateway_service.schemas.zone import ZoneBounds, ZoneCreate


# ─── PaginationParams ─────────────────────────────────────────────────────────


def test_pagination_default_values() -> None:
    p = PaginationParams()
    assert p.page == 1
    assert p.page_size == 20


def test_pagination_offset_first_page() -> None:
    p = PaginationParams(page=1, page_size=10)
    assert p.offset == 0
    assert p.limit == 10


def test_pagination_offset_second_page() -> None:
    p = PaginationParams(page=2, page_size=10)
    assert p.offset == 10


def test_pagination_offset_third_page() -> None:
    p = PaginationParams(page=3, page_size=5)
    assert p.offset == 10


def test_pagination_min_page_size() -> None:
    p = PaginationParams(page=1, page_size=1)
    assert p.page_size == 1


def test_pagination_max_page_size() -> None:
    p = PaginationParams(page=1, page_size=100)
    assert p.page_size == 100


def test_pagination_page_too_small() -> None:
    with pytest.raises(ValidationError):
        PaginationParams(page=0, page_size=10)


def test_pagination_page_size_too_large() -> None:
    with pytest.raises(ValidationError):
        PaginationParams(page=1, page_size=101)


# ─── PaginatedResponse ────────────────────────────────────────────────────────


def test_paginated_response_create_basic() -> None:
    items = ["a", "b", "c"]
    resp = PaginatedResponse.create(items=items, total=3, page=1, page_size=10)
    assert resp.items == items
    assert resp.total == 3
    assert resp.pages == 1


def test_paginated_response_pages_calculation() -> None:
    resp = PaginatedResponse.create(items=[], total=25, page=1, page_size=10)
    assert resp.pages == 3


def test_paginated_response_exact_pages() -> None:
    resp = PaginatedResponse.create(items=[], total=20, page=1, page_size=10)
    assert resp.pages == 2


def test_paginated_response_empty_list() -> None:
    resp = PaginatedResponse.create(items=[], total=0, page=1, page_size=20)
    assert resp.pages == 1  # минимум 1 страница
    assert resp.total == 0


def test_paginated_response_generic_typed() -> None:
    """Generic[T] работает с разными типами."""
    resp: PaginatedResponse[int] = PaginatedResponse.create(
        items=[1, 2, 3], total=3, page=1, page_size=10
    )
    assert resp.items[0] == 1


# ─── RegisterRequest ──────────────────────────────────────────────────────────


def test_register_request_valid() -> None:
    r = RegisterRequest(username="user1", email="u@test.com", password="Pass1234")
    assert r.username == "user1"


def test_register_request_password_no_digit() -> None:
    with pytest.raises(ValidationError, match="digit"):
        RegisterRequest(username="user1", email="u@test.com", password="OnlyLetters")


def test_register_request_password_no_letter() -> None:
    with pytest.raises(ValidationError, match="letter"):
        RegisterRequest(username="user1", email="u@test.com", password="12345678")


def test_register_request_password_too_short() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(username="user1", email="u@test.com", password="Ab1")


def test_register_request_username_invalid_chars() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(username="user name!", email="u@test.com", password="Pass1234")


def test_register_request_username_too_short() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(username="ab", email="u@test.com", password="Pass1234")


def test_register_request_robot_role_forbidden() -> None:
    with pytest.raises(ValidationError, match="ROBOT"):
        RegisterRequest(
            username="robotuser",
            email="r@test.com",
            password="Pass1234",
            role=UserRole.ROBOT,
        )


def test_register_request_default_role() -> None:
    r = RegisterRequest(username="user1", email="u@test.com", password="Pass1234")
    assert r.role == UserRole.OPERATOR


# ─── TaskCreate / TaskStatus ─────────────────────────────────────────────────


def test_task_create_minimal() -> None:
    t = TaskCreate(text="Move to zone A")
    assert t.text == "Move to zone A"
    assert t.priority == 50  # default


def test_task_create_with_priority() -> None:
    t = TaskCreate(text="Emergency stop", priority=100)
    assert t.priority == 100


def test_task_create_priority_too_high() -> None:
    with pytest.raises(ValidationError):
        TaskCreate(text="Move", priority=101)


def test_task_create_empty_text() -> None:
    with pytest.raises(ValidationError):
        TaskCreate(text="")


def test_task_status_enum_values() -> None:
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.IN_PROGRESS.value == "in_progress"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"
    assert TaskStatus.CANCELLED.value == "cancelled"


def test_task_summary_requires_fields() -> None:
    with pytest.raises(ValidationError):
        TaskSummary()  # type: ignore[call-arg]


# ─── ZoneCreate / ZoneBounds ─────────────────────────────────────────────────


def test_zone_create_valid() -> None:
    z = ZoneCreate(
        name="Zone A",
        description="Main work area",
        bounds=ZoneBounds(x_min=0.0, y_min=0.0, x_max=10.0, y_max=10.0),
    )
    assert z.name == "Zone A"


def test_zone_bounds_valid() -> None:
    b = ZoneBounds(x_min=-5.0, y_min=-5.0, x_max=5.0, y_max=5.0)
    assert b.x_max == 5.0


# ─── ChatMessage / CommandAck ─────────────────────────────────────────────────


def test_chat_message_valid() -> None:
    m = ChatMessage(text="Move robot to charging station")
    assert m.text == "Move robot to charging station"
    assert m.priority == 50  # default


def test_chat_message_empty_text() -> None:
    with pytest.raises(ValidationError):
        ChatMessage(text="")


def test_command_ack_fields() -> None:
    ack = CommandAck(
        task_id="task-001",
        trace_id="trace-001",
        message="Command accepted",
        status="pending",
    )
    assert ack.task_id == "task-001"
    assert ack.trace_id == "trace-001"


# ─── TelemetryResolution ─────────────────────────────────────────────────────


def test_telemetry_resolution_enum_values() -> None:
    assert TelemetryResolution.RAW.value == "raw"
    assert TelemetryResolution.MIN1.value == "1m"
    assert TelemetryResolution.HOUR1.value == "1h"
    assert TelemetryResolution.DAY1.value == "1d"


# ─── ErrorResponse / MessageResponse ─────────────────────────────────────────


def test_error_response_required_fields() -> None:
    e = ErrorResponse(error_code="NOT_FOUND", message="Resource not found")
    assert e.error_code == "NOT_FOUND"
    assert e.details is None
    assert e.trace_id is None


def test_message_response() -> None:
    m = MessageResponse(message="OK")
    assert m.message == "OK"
