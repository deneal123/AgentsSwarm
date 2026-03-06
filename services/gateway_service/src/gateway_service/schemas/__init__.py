"""Схемы данных Gateway Service."""

from gateway_service.schemas.chat import ChatMessage, ChatResponse, CommandAck
from gateway_service.schemas.common import (
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
    pagination_params,
)
from gateway_service.schemas.robot import (
    Position,
    RobotDetail,
    RobotListFilters,
    RobotStatus,
    RobotSummary,
    RobotTelemetry,
)
from gateway_service.schemas.task import (
    TaskCancel,
    TaskCreate,
    TaskDetail,
    TaskListFilters,
    TaskStatus,
    TaskSummary,
)
from gateway_service.schemas.telemetry import TelemetryHistory, TelemetryResolution
from gateway_service.schemas.zone import (
    ZoneCreate,
    ZoneDetail,
    ZoneSummary,
    ZoneUpdate,
)

__all__ = [
    # common
    "ErrorResponse",
    "MessageResponse",
    "PaginatedResponse",
    "PaginationParams",
    "pagination_params",
    # robot
    "Position",
    "RobotDetail",
    "RobotListFilters",
    "RobotStatus",
    "RobotSummary",
    "RobotTelemetry",
    # task
    "TaskCancel",
    "TaskCreate",
    "TaskDetail",
    "TaskListFilters",
    "TaskStatus",
    "TaskSummary",
    # zone
    "ZoneCreate",
    "ZoneDetail",
    "ZoneSummary",
    "ZoneUpdate",
    # chat
    "ChatMessage",
    "ChatResponse",
    "CommandAck",
    # telemetry
    "TelemetryHistory",
    "TelemetryResolution",
]
