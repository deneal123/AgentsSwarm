from __future__ import annotations

import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect

from orchestrator.services.streaming import StreamCollector
from orchestrator.services.tasks import TaskStatus, TaskStore
from orchestrator.utils.logger import get_logger


logger = get_logger(__name__)

_TERMINAL_STATUSES = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED}


class WebSocketTaskStreamService:
    def __init__(self, task_store: TaskStore, stream_collector: StreamCollector, poll_interval: float = 0.2) -> None:
        self._task_store = task_store
        self._stream_collector = stream_collector
        self._poll_interval = poll_interval

    async def stream_task_events(self, websocket: WebSocket, task_id: str) -> None:
        await websocket.accept()
        try:
            task = self._task_store.get_task(task_id)
            if not task:
                await websocket.send_json({"error": "Task not found", "task_id": task_id})
                await websocket.close(code=4004)
                return

            initial = self._stream_collector.as_payload(task_id, after_seq=0)
            await websocket.send_json(initial)
            last_seq = initial.get("last_seq", 0)

            while True:
                payload = self._stream_collector.as_payload(task_id, after_seq=last_seq)
                last_seq = payload.get("last_seq", last_seq)
                if payload.get("events"):
                    await websocket.send_text(json.dumps(payload))

                # Stop polling once the task reaches a terminal state and all
                # buffered events have been drained.
                current = self._task_store.get_task(task_id)
                if current and current.status in _TERMINAL_STATUSES and not payload.get("events"):
                    await websocket.close(code=1000)
                    return

                await asyncio.sleep(self._poll_interval)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected for task %s", task_id)
        except Exception as exc:
            logger.exception("WebSocket error for task %s", task_id, exc_info=exc)
            try:
                await websocket.send_json({"error": "internal", "detail": str(exc)})
            finally:
                await websocket.close(code=1011)


__all__ = ["WebSocketTaskStreamService"]
