from __future__ import annotations

import json
from typing import Any

from celery.result import AsyncResult  # type: ignore[import]

from service.infrastructure.messaging import stream_helpers, tasks
from service.infrastructure.messaging.celery_app import celery_app
from service.services.agents.application.ports.interfaces import StreamPort
from service.services.files.application.ports.interfaces import MessageBusPort
from service.services.jobs.application.ports.interfaces import JobHandlePort, JobQueuePort


class CeleryJobHandle(JobHandlePort):
    def __init__(self, task: Any) -> None:
        self._task = task

    def get(self, timeout: float) -> dict[str, Any]:
        result = self._task.get(timeout=timeout)
        return result if isinstance(result, dict) else {"status": "error", "error": str(result)}


class CeleryJobQueuePort(JobQueuePort):
    def enqueue_process_agent_message(self, **kwargs: Any) -> JobHandlePort:
        return CeleryJobHandle(tasks.process_agent_message.delay(**kwargs))

    def enqueue_agent_message(self, **kwargs: Any) -> str | None:
        task = tasks.process_agent_message.apply_async(kwargs=kwargs)
        return str(task.id) if task and task.id else None

    async def process_agent_message(self, **kwargs: Any) -> dict[str, Any]:
        return await tasks.process_agent_message_async(**kwargs)

    def get_task_state(self, task_id: str) -> tuple[bool, bool, Any, Any, str]:
        result = AsyncResult(task_id, app=celery_app)
        return result.ready(), result.successful(), result.result, result.info or {}, result.state

    def cancel_task(self, task_id: str) -> bool:
        result = AsyncResult(task_id, app=celery_app)
        result.revoke(terminate=True)
        return True


class RedisListMessageBusPort(MessageBusPort):
    def __init__(self, redis_client: Any | None) -> None:
        self._redis_client = redis_client

    async def push(self, queue: str, payload: str) -> None:
        if self._redis_client is None:
            return
        await self._redis_client.lpush(queue, payload)


class RedisStreamPort(StreamPort):
    def __init__(self, redis_client: Any | None) -> None:
        self._redis_client = redis_client

    async def publish(self, stream: str, payload: dict[str, Any]) -> None:
        if self._redis_client is None:
            return
        await stream_helpers.xadd(self._redis_client, stream, {"data": json.dumps(payload)})
