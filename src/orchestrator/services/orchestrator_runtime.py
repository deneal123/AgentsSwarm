from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict

from fastapi import HTTPException, status

from orchestrator.services.plan_runner import PlanRunner
from orchestrator.services.planner import PlanStep, build_plan
from orchestrator.services.streaming import StreamCollector, StreamEvent
from orchestrator.services.tasks import TaskInfo, TaskStatus, TaskStore
from orchestrator.utils.env import env_int


class OrchestratorRuntime:
    def __init__(
        self,
        task_store: TaskStore,
        stream_collector: StreamCollector,
        plan_builder: Callable[[str], Awaitable[list[PlanStep]]] = build_plan,
    ) -> None:
        self._task_store = task_store
        self._stream_collector = stream_collector
        self._plan_builder = plan_builder

    def get_task_or_404(self, task_id: str) -> TaskInfo:
        task = self._task_store.get_task(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    def record_user_error(self, task_id: str, message: str, code: str = "internal_error", detail: str | None = None) -> None:
        self._stream_collector.record(
            StreamEvent(
                task_id=task_id,
                source="orchestrator",
                message=message,
                level="error",
                meta={"user_facing": True, "code": code, "detail": detail},
            )
        )

    async def build_and_store_plan(self, task_id: str, prompt: str, message: str, attempt: int | None = None) -> list[PlanStep]:
        plan = await self._plan_builder(prompt)
        payload = [step.as_dict() for step in plan]
        self._task_store.set_plan(task_id, payload)
        meta: Dict[str, Any] = {"steps": payload}
        if attempt is not None:
            meta["attempt"] = attempt
        self._stream_collector.record(
            StreamEvent(
                task_id=task_id,
                source="planner",
                message=message,
                level="info",
                meta=meta,
            )
        )
        return plan

    async def run_task(self, task_id: str, prompt: str) -> None:
        existing = self._task_store.get_task(task_id)
        if existing and existing.status in {TaskStatus.CANCELED, TaskStatus.FAILED}:
            self._task_store.cancel_incomplete_steps(task_id, include_completed=True)
            self._stream_collector.record(
                StreamEvent(
                    task_id=task_id,
                    source="orchestrator",
                    message="Task stopped before start",
                    level="warning",
                    meta={"status": existing.status.value},
                )
            )
            return

        max_replans = env_int("PLAN_REPLAN_MAX", 1)
        attempt = 0
        self._task_store.update_status(task_id, TaskStatus.RUNNING)
        # Single runner instance shared across retries — preserves configuration.
        runner = PlanRunner(task_store=self._task_store, stream_collector=self._stream_collector)

        while True:
            plan = await self.build_and_store_plan(task_id, prompt, message="Plan created", attempt=attempt + 1)
            self._stream_collector.record(
                StreamEvent(
                    task_id=task_id,
                    source="orchestrator",
                    message="Processing started",
                    level="info",
                    meta={"prompt": prompt, "plan_attempt": attempt + 1},
                )
            )
            try:
                await asyncio.sleep(0.05)
                outcome = await runner.run(task_id, plan)

                current = self._task_store.get_task(task_id)
                if outcome == TaskStatus.COMPLETED and current and current.status != TaskStatus.CANCELED:
                    self._stream_collector.record(
                        StreamEvent(
                            task_id=task_id,
                            source="agent",
                            message="Task completed",
                            level="info",
                            meta={"steps": len(plan), "plan_attempt": attempt + 1},
                        )
                    )
                    self._task_store.update_status(task_id, TaskStatus.COMPLETED)
                    break
                if outcome == TaskStatus.CANCELED:
                    self._task_store.update_status(task_id, TaskStatus.CANCELED)
                    break

                attempt += 1
                if attempt > max_replans:
                    self._task_store.update_status(task_id, TaskStatus.FAILED)
                    break
                self._stream_collector.record(
                    StreamEvent(
                        task_id=task_id,
                        source="planner",
                        message="Replanning after failure",
                        level="warning",
                        meta={"attempt": attempt, "max": max_replans},
                    )
                )
            except Exception as exc:
                self._task_store.update_status(task_id, TaskStatus.FAILED)
                self._stream_collector.record(
                    StreamEvent(
                        task_id=task_id,
                        source="orchestrator",
                        message=f"Task failed: {exc}",
                        level="error",
                        meta={"plan_attempt": attempt + 1},
                    )
                )
                break


__all__ = ["OrchestratorRuntime"]
