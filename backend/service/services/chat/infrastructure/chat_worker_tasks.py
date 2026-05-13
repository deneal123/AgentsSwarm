from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from celery import shared_task

from service.services.agents.application.ports.interfaces import AgentExecutionPort
from service.services.chat.application.error_handling import (
    map_to_worker_error_payload,
    normalize_response_metadata,
)
from service.services.chat.application.use_cases.chat_use_cases import PersistChatMessagesUseCase
from service.services.chat.infrastructure.chat_worker import (
    ChatWorkerConversationService,
    ChatWorkerDependencyFactory,
    WorkerStreamPublisherService,
)
from service.services.chat.persistence.chat_worker_repository import ChatWorkerRepository

logger = logging.getLogger(__name__)


async def _update_job_status_with_session(
    job_repo, job_id: str, status, session, user_id, result_data: dict | None = None
):
    from uuid import UUID

    try:
        job_uuid = UUID(job_id)
        user_uuid = (
            UUID("00000000-0000-0000-0000-000000000000")
            if user_id is None
            else UUID(user_id)
            if isinstance(user_id, str)
            else user_id
        )
        job = await job_repo.fetch_job_by_id(job_uuid, user_uuid, session=session)
        if not job:
            return
        job.status = status
        if result_data:
            job.payload = job.payload or {}
            job.payload.update(result_data)
        await job_repo.update_job_status(job, session=session)
    except Exception:
        logger.exception("Failed to update job status for %s", job_id)


async def _resolve_memory_user_id(*, db_session, user_id: Any, thread_id: str) -> str | None:
    return await ChatWorkerConversationService(ChatWorkerRepository()).resolve_memory_user(
        db_session=db_session,
        user_id=user_id,
        thread_id=thread_id,
    )


async def _restore_pseudo_session_history(
    *,
    pseudo_session,
    db_session,
    thread_id: str,
    session_data: dict | None,
    history_limit: int = 12,
) -> int:
    return await ChatWorkerConversationService(ChatWorkerRepository()).restore_thread_history(
        pseudo_session=pseudo_session,
        db_session=db_session,
        thread_id=thread_id,
        session_data=session_data,
        history_limit=history_limit,
    )


async def _persist_chat_turn(
    *, db_session, thread_id: str, user_text: str, assistant_text: str, user_id: str | None
) -> bool:
    return await ChatWorkerConversationService(ChatWorkerRepository()).persist_turn(
        db_session=db_session,
        thread_id=thread_id,
        user_text=user_text,
        assistant_text=assistant_text,
        user_id=user_id,
    )


async def process_agent_message_async(
    job_id: str,
    thread_id: str,
    text: str,
    user_id: str | None,
    session_data: dict | None = None,
    selected_model: str | None = None,
    route_override: str | None = None,
    input_type: str | None = None,
    web_search: bool = False,
    deep_research: bool = False,
    file_context: str = "",
    dependency_factory: ChatWorkerDependencyFactory | None = None,
    agent_execution: AgentExecutionPort | None = None,
) -> dict:
    from service.composition import state as container
    from service.models.key_value import ProcessingStatus
    from service.services.agents.application.agent_execution_service import (
        DefaultAgentExecutionService,
    )
    from service.services.agents.application.agent_file_bridge import persist_generated_artifacts
    from service.services.agents.application.agent_session_service import AgentSessionService
    from service.services.files.application.file_saver_service import FileSaverService
    from service.services.files.persistence.file_repository import FileRepository
    from service.services.jobs.persistence.job_repository import JobRepository
    from service.settings import Config

    config = Config()
    deps = dependency_factory or ChatWorkerDependencyFactory()
    pg_connector = deps.create_pg_connector(config)
    redis_client = deps.create_redis_client(config)

    publisher = WorkerStreamPublisherService(
        redis_client=redis_client, stream_key=f"chat:{thread_id}:stream"
    )
    job_repo = JobRepository(pg_connector)

    backend = config.storage.backend.strip().lower()
    if backend == "minio":
        from service.infrastructure.storage.minio_file_storage import MinioFileStorage

        storage = MinioFileStorage(config.minio)
    else:
        from service.infrastructure.storage.local_file_storage import LocalFileStorage

        storage = LocalFileStorage()

    file_service = FileSaverService(
        repository=FileRepository(pg_connector), folder_name="uploads", file_storage=storage
    )

    async with pg_connector.get_session_context() as session:
        try:
            await _update_job_status_with_session(
                job_repo, job_id, ProcessingStatus.PROCESSING, session, user_id
            )
            pseudo_session = AgentSessionService.create(
                session_id=(session_data or {}).get("session_id", thread_id)
            )
            await _restore_pseudo_session_history(
                pseudo_session=pseudo_session,
                db_session=session,
                thread_id=thread_id,
                session_data=session_data,
                history_limit=max(getattr(config.agents, "chat_history_messages_limit", 8), 1),
            )
            publisher.publish_payload(
                {"type": "processing", "job_id": job_id, "timestamp": datetime.now(UTC).isoformat()}
            )

            execution_service = agent_execution or DefaultAgentExecutionService()
            execution_result = await execution_service.execute(
                text=text,
                thread_id=thread_id,
                user_id=user_id,
                session_data=session_data,
                selected_model=selected_model,
                route_override=route_override,
                input_type=input_type,
                web_search=web_search,
                deep_research=deep_research,
                file_context=file_context,
                pseudo_session=pseudo_session,
            )
            for event in execution_result["events"]:
                publisher.publish_agent_event(event=event, job_id=job_id)

            reply = str(execution_result["reply"])
            metadata: dict[str, Any] = execution_result["metadata"]
            resolved_model = execution_result["resolved_model"]
            publisher.publish_payload(
                {
                    "type": "stream_complete",
                    "job_id": job_id,
                    "metadata": {
                        "chunks": execution_result["reply_parts_count"],
                        "reply_chars": execution_result["reply_chars_count"],
                    },
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

            file_url, metadata = await persist_generated_artifacts(
                file_service=file_service, user_id=user_id, metadata=metadata, job_id=job_id
            )
            metadata = normalize_response_metadata(
                metadata, selected_model=resolved_model or selected_model
            )
            await PersistChatMessagesUseCase(
                container.get_current_container().services.chat_application_service.services.chat_service
            ).execute(
                thread_id=thread_id,
                user_text=text,
                assistant_text=reply,
                user_id=user_id,
            )

            await _update_job_status_with_session(
                job_repo,
                job_id,
                ProcessingStatus.SUCCESS,
                session,
                user_id,
                {"reply": reply, "file_url": file_url, "metadata": metadata},
            )
            publisher.publish_payload(
                {
                    "type": "agent_reply",
                    "job_id": job_id,
                    "reply": reply,
                    "file_url": file_url,
                    "metadata": metadata,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

            try:
                memory_user_id = await _resolve_memory_user_id(
                    db_session=session, user_id=user_id, thread_id=thread_id
                )
                if memory_user_id:
                    from service.services.analytics.application.memory_service import MemoryService

                    await MemoryService().extract_and_save_facts(
                        memory_user_id,
                        thread_id,
                        [
                            {"role": "user", "content": text},
                            {"role": "assistant", "content": reply},
                        ],
                    )
            except Exception:
                logger.debug("Memory extraction failed", exc_info=True)

            await session.commit()
            return {
                "status": "success",
                "job_id": job_id,
                "reply": reply,
                "file_url": file_url,
                "metadata": {**metadata, "selected_model": resolved_model or "mws-gpt-alpha"},
            }
        except Exception as exc:
            await session.rollback()
            await _update_job_status_with_session(
                job_repo, job_id, ProcessingStatus.FAILURE, session, user_id
            )
            publisher.publish_payload(map_to_worker_error_payload(exc, job_id=job_id))
            return {"status": "error", "error": str(exc)}
        finally:
            publisher.close()


@shared_task(
    bind=True,
    name="service.services.chat.infrastructure.chat_worker_tasks.process_agent_message",
    soft_time_limit=300,
    time_limit=330,
)
def process_agent_message(
    self,
    job_id: str,
    thread_id: str,
    text: str,
    user_id: int,
    session_data: dict | None = None,
    selected_model: str | None = None,
    route_override: str | None = None,
    input_type: str | None = None,
    web_search: bool = False,
    deep_research: bool = False,
    file_context: str = "",
) -> dict:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            process_agent_message_async(
                job_id=job_id,
                thread_id=thread_id,
                text=text,
                user_id=str(user_id) if user_id is not None else None,
                session_data=session_data,
                selected_model=selected_model,
                route_override=route_override,
                input_type=input_type,
                web_search=web_search,
                deep_research=deep_research,
                file_context=file_context or "",
            )
        )
    finally:
        loop.close()


@shared_task(
    bind=True,
    name="service.services.chat.infrastructure.chat_worker_tasks.delete_old_chat_history",
    time_limit=300,
    soft_time_limit=280,
)
def delete_old_chat_history(self) -> dict:
    from service.settings import config

    retention_days = int(config.chat_retention_days)
    deps = ChatWorkerDependencyFactory()
    pg_connector = deps.create_pg_connector(config)
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    async def run_cleanup() -> None:
        async with pg_connector.get_session_context() as session:
            await session.execute(
                "DELETE FROM profile.chat_messages WHERE created_at < :cutoff", {"cutoff": cutoff}
            )
            await session.execute(
                "DELETE FROM profile.chat_threads WHERE id NOT IN (SELECT DISTINCT thread_id FROM profile.chat_messages)"
            )
            await session.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_cleanup())
    finally:
        loop.close()
    return {"status": "ok", "retention_days": retention_days}
