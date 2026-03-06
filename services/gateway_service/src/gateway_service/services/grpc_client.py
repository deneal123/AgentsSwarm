"""
gRPC-клиент к Orchestrator Service.

Использует сгенерированные protobuf-стабы:
  gateway/proto/orchestrator/v1/orchestrator_pb2.py
  gateway/proto/orchestrator/v1/orchestrator_pb2_grpc.py

Если стабы не сгенерированы — клиент работает в режиме заглушки
(все методы возвращают None, логируют предупреждение).

Паттерны надёжности:
  - Таймаут: settings.grpc_deadline_seconds на каждый вызов
  - Retry: до 3 попыток с экспоненциальной выдержкой (только на UNAVAILABLE)
  - Circuit Breaker: CLOSED → OPEN (5 ошибок) → HALF_OPEN (30 сек) → CLOSED
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ─── Lazy import protobuf stubs ───────────────────────────────────────────────

try:
    import grpc
    import grpc.aio as grpc_aio
    _GRPC_AVAILABLE = True
except ImportError:
    _GRPC_AVAILABLE = False
    logger.warning("grpc.import_failed", hint="pip install grpcio")

try:
    from gateway.proto.orchestrator.v1 import orchestrator_pb2, orchestrator_pb2_grpc  # type: ignore[import]
    _STUBS_AVAILABLE = True
except ImportError:
    _STUBS_AVAILABLE = False
    logger.warning(
        "grpc.stubs_not_found",
        hint="Run 'bash proto/scripts/gen-proto.sh' to generate protobuf stubs",
    )


# ─── Circuit Breaker ─────────────────────────────────────────────────────────


class _CBState(Enum):
    CLOSED = "closed"        # нормальная работа
    OPEN = "open"            # не пропускаем запросы
    HALF_OPEN = "half_open"  # один пробный запрос


@dataclass
class _CircuitBreaker:
    """
    Простой circuit breaker.

    Переходы:
      CLOSED  → OPEN     : failure_threshold последовательных ошибок
      OPEN    → HALF_OPEN: через recovery_timeout секунд
      HALF_OPEN → CLOSED  : успешный вызов
      HALF_OPEN → OPEN    : неуспешный вызов
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0

    _state: _CBState = field(default=_CBState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _opened_at: float | None = field(default=None, init=False)

    @property
    def state(self) -> _CBState:
        if self._state == _CBState.OPEN:
            if self._opened_at and (time.monotonic() - self._opened_at) >= self.recovery_timeout:
                self._state = _CBState.HALF_OPEN
                logger.info("circuit_breaker.half_open")
        return self._state

    def is_open(self) -> bool:
        return self.state == _CBState.OPEN

    def record_success(self) -> None:
        self._failure_count = 0
        if self._state != _CBState.CLOSED:
            logger.info("circuit_breaker.closed")
        self._state = _CBState.CLOSED
        self._opened_at = None

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._state == _CBState.HALF_OPEN or self._failure_count >= self.failure_threshold:
            self._state = _CBState.OPEN
            self._opened_at = time.monotonic()
            logger.warning(
                "circuit_breaker.opened",
                failures=self._failure_count,
            )


# ─── Result dataclasses (независимы от proto) ────────────────────────────────


@dataclass
class RobotStateResult:
    robot_id: str
    status: str = "unspecified"
    battery_level: float = 0.0
    zone_id: str = ""
    current_task_id: str = ""
    last_seen: datetime | None = None
    position_x: float = 0.0
    position_y: float = 0.0


@dataclass
class TaskStatusResult:
    task_id: str
    status: str = "unspecified"
    assigned_robot_id: str = ""
    progress_message: str = ""
    result: dict[str, str] = field(default_factory=dict)
    created_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass
class SubmitCommandResult:
    task_id: str
    message: str = ""
    status: str = "pending"


# ─── Status enum mapping ──────────────────────────────────────────────────────

_ROBOT_STATUS_MAP = {
    0: "unspecified", 1: "idle", 2: "moving", 3: "executing",
    4: "charging", 5: "error", 6: "offline", 7: "maintenance",
}
_TASK_STATUS_MAP = {
    0: "unspecified", 1: "pending", 2: "assigned", 3: "in_progress",
    4: "completed", 5: "failed", 6: "cancelled",
}


# ─── gRPC Client ─────────────────────────────────────────────────────────────


class OrchestratorGrpcClient:
    """
    Асинхронный gRPC-клиент к OrchestratorService.

    Использование:
        client = OrchestratorGrpcClient(target="localhost:50051", deadline=10.0)
        await client.connect()

        state = await client.get_robot_state("robot-1")
        task  = await client.get_task_status("task-uuid")
        result = await client.submit_command(user_id="u1", text="Go to zone A")

        await client.close()
    """

    _MAX_RETRIES = 3
    _RETRY_BASE_DELAY = 0.1  # секунды

    def __init__(self, target: str, deadline: float = 10.0) -> None:
        self._target = target
        self._deadline = deadline
        self._channel: Any = None
        self._stub: Any = None
        self._cb = _CircuitBreaker()

    async def connect(self) -> None:
        """Создать gRPC-канал (не устанавливает TCP — lazy connect)."""
        if not _GRPC_AVAILABLE:
            logger.warning("grpc.skipped_no_grpcio")
            return
        if not _STUBS_AVAILABLE:
            logger.warning("grpc.skipped_no_stubs")
            return

        self._channel = grpc_aio.insecure_channel(
            self._target,
            options=[
                ("grpc.keepalive_time_ms", 30_000),
                ("grpc.keepalive_timeout_ms", 5_000),
                ("grpc.keepalive_permit_without_calls", 1),
                ("grpc.max_reconnect_backoff_ms", 10_000),
            ],
        )
        self._stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self._channel)
        logger.info("grpc.channel_created", target=self._target)

    async def close(self) -> None:
        if self._channel:
            await self._channel.close()
            logger.info("grpc.channel_closed")

    async def is_healthy(self) -> bool:
        """Проверка доступности Orchestrator (ping через GetTaskStatus с несуществующим ID)."""
        if not self._stub or self._cb.is_open():
            return False
        try:
            await self._stub.GetTaskStatus(
                orchestrator_pb2.GetTaskStatusRequest(task_id="health-check"),
                timeout=2.0,
            )
            return True
        except Exception:
            return False

    # ─── Core call wrapper ────────────────────────────────────────────────────

    async def _call(self, method_name: str, request: Any) -> Any:
        """
        Выполнить gRPC-вызов с таймаутом, retry и circuit breaker.
        Возвращает ответ или пробрасывает исключение.
        """
        if not _GRPC_AVAILABLE or not _STUBS_AVAILABLE or self._stub is None:
            return None

        if self._cb.is_open():
            raise RuntimeError(f"Circuit breaker OPEN for Orchestrator ({self._target})")

        last_exc: Exception | None = None
        for attempt in range(self._MAX_RETRIES):
            try:
                stub_method = getattr(self._stub, method_name)
                response = await stub_method(request, timeout=self._deadline)
                self._cb.record_success()
                return response

            except Exception as exc:
                last_exc = exc
                err_name = type(exc).__name__
                is_retryable = _GRPC_AVAILABLE and isinstance(
                    exc, grpc.aio.AioRpcError
                ) and exc.code() in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED)

                logger.warning(
                    "grpc.call_failed",
                    method=method_name,
                    attempt=attempt + 1,
                    error=str(exc),
                    retryable=is_retryable,
                )

                if not is_retryable:
                    self._cb.record_failure()
                    raise

                if attempt < self._MAX_RETRIES - 1:
                    delay = self._RETRY_BASE_DELAY * (2 ** attempt)
                    await asyncio.sleep(delay)

        self._cb.record_failure()
        raise last_exc  # type: ignore[misc]

    # ─── Public API ───────────────────────────────────────────────────────────

    async def get_robot_state(self, robot_id: str) -> RobotStateResult | None:
        """
        Получить текущее состояние робота от Orchestrator.
        Возвращает None если сервис недоступен.
        """
        try:
            if not _STUBS_AVAILABLE:
                return None
            request = orchestrator_pb2.GetRobotStateRequest(robot_id=robot_id)
            resp = await self._call("GetRobotState", request)
            if resp is None:
                return None

            last_seen: datetime | None = None
            if resp.HasField("last_seen"):
                last_seen = resp.last_seen.ToDatetime()

            return RobotStateResult(
                robot_id=resp.robot_id,
                status=_ROBOT_STATUS_MAP.get(resp.status, "unspecified"),
                battery_level=resp.battery_level,
                zone_id=resp.zone_id,
                current_task_id=resp.current_task_id,
                last_seen=last_seen,
                position_x=resp.position.x if resp.HasField("position") else 0.0,
                position_y=resp.position.y if resp.HasField("position") else 0.0,
            )
        except Exception as exc:
            logger.error("grpc.get_robot_state.failed", robot_id=robot_id, error=str(exc))
            return None

    async def get_task_status(self, task_id: str) -> TaskStatusResult | None:
        """
        Получить статус задачи от Orchestrator.
        Возвращает None если сервис недоступен.
        """
        try:
            if not _STUBS_AVAILABLE:
                return None
            request = orchestrator_pb2.GetTaskStatusRequest(task_id=task_id)
            resp = await self._call("GetTaskStatus", request)
            if resp is None:
                return None

            created_at: datetime | None = None
            finished_at: datetime | None = None
            if resp.HasField("created_at"):
                created_at = resp.created_at.ToDatetime()
            if resp.HasField("finished_at"):
                finished_at = resp.finished_at.ToDatetime()

            return TaskStatusResult(
                task_id=resp.task_id,
                status=_TASK_STATUS_MAP.get(resp.status, "unspecified"),
                assigned_robot_id=resp.assigned_robot_id,
                progress_message=resp.progress_message,
                result=dict(resp.result),
                created_at=created_at,
                finished_at=finished_at,
            )
        except Exception as exc:
            logger.error("grpc.get_task_status.failed", task_id=task_id, error=str(exc))
            return None

    async def submit_command(
        self,
        user_id: str,
        text: str,
        priority: int = 50,
        trace_id: str = "",
    ) -> SubmitCommandResult | None:
        """
        Отправить NL-команду напрямую в Orchestrator (bypass RabbitMQ).
        Используется для высокоприоритетных команд (priority >= 80).
        Возвращает None если сервис недоступен.
        """
        try:
            if not _STUBS_AVAILABLE:
                return None
            from google.protobuf.timestamp_pb2 import Timestamp  # type: ignore[import]
            ts = Timestamp()
            ts.GetCurrentTime()

            request = orchestrator_pb2.SubmitCommandRequest(
                user_id=user_id,
                text=text,
                priority=priority,
                trace_id=trace_id,
                timestamp=ts,
            )
            resp = await self._call("SubmitCommand", request)
            if resp is None:
                return None

            return SubmitCommandResult(
                task_id=resp.task_id,
                message=resp.message,
                status=_TASK_STATUS_MAP.get(resp.status, "pending"),
            )
        except Exception as exc:
            logger.error("grpc.submit_command.failed", user_id=user_id, error=str(exc))
            return None


# ─── Singleton & Depends ──────────────────────────────────────────────────────

_grpc_client: OrchestratorGrpcClient | None = None


def get_grpc_client() -> OrchestratorGrpcClient:
    """FastAPI Depends-совместимый синглтон."""
    global _grpc_client
    if _grpc_client is None:
        from gateway_service.config import get_settings
        s = get_settings()
        _grpc_client = OrchestratorGrpcClient(
            target=s.grpc_target,
            deadline=s.grpc_deadline_seconds,
        )
    return _grpc_client


def set_grpc_client(client: OrchestratorGrpcClient) -> None:
    """Переопределить клиент (для тестов)."""
    global _grpc_client
    _grpc_client = client
