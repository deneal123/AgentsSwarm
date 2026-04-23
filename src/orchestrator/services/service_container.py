from __future__ import annotations

from dataclasses import dataclass

from orchestrator.services.orchestrator_runtime import OrchestratorRuntime
from orchestrator.services.sessions import SessionManager
from orchestrator.services.streaming import StreamCollector
from orchestrator.services.task_application_service import TaskApplicationService
from orchestrator.services.task_event_ingestion_service import TaskEventIngestionService
from orchestrator.services.tasks import TaskStore


@dataclass(frozen=True)
class ServiceContainer:
    task_store: TaskStore
    session_manager: SessionManager
    stream_collector: StreamCollector
    runtime: OrchestratorRuntime
    event_ingestion_service: TaskEventIngestionService
    task_app_service: TaskApplicationService


class ServiceContainerFactory:
    @staticmethod
    def create(
        task_store: TaskStore | None = None,
        session_manager: SessionManager | None = None,
        stream_collector: StreamCollector | None = None,
    ) -> ServiceContainer:
        resolved_task_store = task_store or TaskStore()
        resolved_session_manager = session_manager or SessionManager()
        resolved_stream_collector = stream_collector or StreamCollector(task_store=resolved_task_store)
        runtime = OrchestratorRuntime(task_store=resolved_task_store, stream_collector=resolved_stream_collector)
        event_ingestion_service = TaskEventIngestionService(
            task_store=resolved_task_store,
            stream_collector=resolved_stream_collector,
            runtime=runtime,
        )
        task_app_service = TaskApplicationService(
            task_store=resolved_task_store,
            session_manager=resolved_session_manager,
            stream_collector=resolved_stream_collector,
            runtime=runtime,
            event_ingestion_service=event_ingestion_service,
        )
        return ServiceContainer(
            task_store=resolved_task_store,
            session_manager=resolved_session_manager,
            stream_collector=resolved_stream_collector,
            runtime=runtime,
            event_ingestion_service=event_ingestion_service,
            task_app_service=task_app_service,
        )


__all__ = ["ServiceContainer", "ServiceContainerFactory"]
