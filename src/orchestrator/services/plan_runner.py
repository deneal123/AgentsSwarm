from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List, Protocol

from orchestrator.services.agent_executor_factory import AgentExecutorFactory
from orchestrator.services.planner import PlanStep
from orchestrator.services.streaming import StreamCollector, StreamEvent
from orchestrator.services.tasks import TaskStatus, TaskStore


@dataclass
class HandoffResult:
    success: bool
    message: str
    user_message: str | None = None
    retryable: bool = True


class AgentHandoffExecutor(Protocol):
    async def execute(self, task_id: str, step: PlanStep, attempt: int) -> HandoffResult:  # pragma: no cover - interface
        ...


class SimulatedAgentExecutor:
    """Stub executor that imitates agent/tool work with small latency."""

    def __init__(self, latency: float = 0.1) -> None:
        self._latency = latency

    async def execute(self, task_id: str, step: PlanStep, attempt: int) -> HandoffResult:
        await asyncio.sleep(self._latency)
        return HandoffResult(success=True, message=f"{step.agent} finished step {step.id}")


class PlanRunner:
    """Closed-loop executor that handoffs each step to specialized agents.

    Executes steps sequentially, streams lifecycle events, retries failed
    handoffs, and stops on cancellation or error. This remains a lightweight
    stub until Agents SDK integration.
    """

    def __init__(
        self,
        task_store: TaskStore,
        stream_collector: StreamCollector,
        step_delay: float = 0.05,
        retry_delay: float = 0.05,
        max_attempts: int = 2,
        agent_executor: AgentHandoffExecutor | None = None,
    ) -> None:
        self._ts = task_store
        self._sc = stream_collector
        self._step_delay = step_delay
        self._retry_delay = retry_delay
        self._max_attempts = max(1, max_attempts)

        if agent_executor is not None:
            self._agent_executor = agent_executor
        else:
            self._agent_executor = AgentExecutorFactory.create(stream_collector=self._sc, step_delay=step_delay)

    def _stop_status(self, task_id: str) -> TaskStatus | None:
        task = self._ts.get_task(task_id)
        if not task:
            return None
        if task.status in {TaskStatus.CANCELED, TaskStatus.FAILED}:
            return task.status
        return None

    async def _stream_stop(self, task_id: str, stop_status: TaskStatus) -> None:
        # Never overwrite already-completed steps — preserve execution history.
        self._ts.cancel_incomplete_steps(task_id, include_completed=False)
        self._sc.record(
            StreamEvent(
                task_id=task_id,
                source="orchestrator",
                message=(
                    "Task canceled during execution"
                    if stop_status == TaskStatus.CANCELED
                    else "Task failed during execution"
                ),
                level="warning",
                meta={"status": stop_status.value},
            )
        )

    async def _execute_step(self, task_id: str, step: PlanStep) -> tuple[TaskStatus | None, str | None]:
        attempts = 0
        while attempts < self._max_attempts:
            attempts += 1

            stop_status = self._stop_status(task_id)
            if stop_status:
                await self._stream_stop(task_id, stop_status)
                return stop_status, None

            self._ts.update_plan_step(task_id, step.id, "running")
            self._sc.record(
                StreamEvent(
                    task_id=task_id,
                    source="planner",
                    message=f"Plan step {step.id} started: {step.description}",
                    level="info",
                    meta={"agent": step.agent, "attempt": attempts, "depends_on": step.meta.get("depends_on")},
                )
            )
            self._sc.record(
                StreamEvent(
                    task_id=task_id,
                    source="agent",
                    message=f"Handoff to {step.agent} (attempt {attempts})",
                    level="info",
                    meta={"tools": step.meta.get("tools", []), "target_robots": step.meta.get("target_robots", [])},
                )
            )

            result = await self._agent_executor.execute(task_id, step, attempts)

            stop_status = self._stop_status(task_id)
            if stop_status:
                self._ts.update_plan_step(task_id, step.id, TaskStatus.CANCELED.value)
                await self._stream_stop(task_id, stop_status)
                return stop_status, None

            if result.success:
                self._ts.update_plan_step(task_id, step.id, TaskStatus.COMPLETED.value)
                self._sc.record(
                    StreamEvent(
                        task_id=task_id,
                        source="agent",
                        message=f"Plan step {step.id} completed",
                        level="info",
                        meta={"agent": step.agent, "attempt": attempts},
                    )
                )
                return None, result.message

            # failure path
            self._ts.update_plan_step(task_id, step.id, TaskStatus.FAILED.value)
            self._sc.record(
                StreamEvent(
                    task_id=task_id,
                    source="agent",
                    message=f"Plan step {step.id} failed: {result.message}",
                    level="error",
                    meta={"agent": step.agent, "attempt": attempts, "retryable": result.retryable},
                )
            )

            if not result.retryable or attempts >= self._max_attempts:
                self._ts.update_status(task_id, TaskStatus.FAILED)
                self._ts.cancel_incomplete_steps(task_id, include_completed=False)
                self._sc.record(
                    StreamEvent(
                        task_id=task_id,
                        source="orchestrator",
                        message=result.user_message or "Задача остановлена из-за ошибки шага",
                        level="error",
                        meta={"user_facing": True, "code": "step_failed", "step_id": step.id},
                    )
                )
                return TaskStatus.FAILED, None

            self._sc.record(
                StreamEvent(
                    task_id=task_id,
                    source="orchestrator",
                    message=f"Повтор шага {step.id} (попытка {attempts + 1})",
                    level="warning",
                    meta={"step_id": step.id, "next_attempt": attempts + 1},
                )
            )
            await asyncio.sleep(self._retry_delay)

        return TaskStatus.FAILED, None

    async def run(self, task_id: str, plan: List[PlanStep]) -> TaskStatus:
        map_context: str | None = None
        agent_results: list[str] = []

        for step in plan:
            stop_status = self._stop_status(task_id)
            if stop_status:
                await self._stream_stop(task_id, stop_status)
                return stop_status

            if map_context and step.agent in {"Navigation", "SwarmCoordinator"}:
                step.meta["map_context"] = map_context
                step.description = f"{step.description}\n\nКонтекст карты:\n{map_context}"

            outcome, result_msg = await self._execute_step(task_id, step)
            if outcome in {TaskStatus.CANCELED, TaskStatus.FAILED}:
                return outcome

            if step.agent == "MapAnalyst" and result_msg:
                map_context = result_msg
            elif result_msg:
                agent_results.append(result_msg)

        if agent_results:
            self._sc.record(
                StreamEvent(
                    task_id=task_id,
                    source="orchestrator",
                    message="\n\n".join(agent_results),
                    level="info",
                    meta={"user_facing": True, "code": "task_result"},
                )
            )

        return TaskStatus.COMPLETED


__all__ = ["PlanRunner", "AgentHandoffExecutor", "SimulatedAgentExecutor", "HandoffResult"]
