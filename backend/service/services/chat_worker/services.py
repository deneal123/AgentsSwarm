from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from service.infrastructure.messaging.agent_streaming import AgentStreamPublisher, EventSerializer
from service.infrastructure.messaging import stream_helpers
from service.repositories.chat_worker_repository import ChatWorkerRepository


@dataclass(slots=True)
class ChatWorkerConversationService:
    repository: ChatWorkerRepository

    async def resolve_memory_user(self, *, db_session: Any, user_id: Any, thread_id: str) -> str | None:
        return await self.repository.resolve_memory_user(db_session=db_session, user_id=user_id, thread_id=thread_id)

    async def restore_thread_history(
        self,
        *,
        pseudo_session: Any,
        db_session: Any,
        thread_id: str,
        session_data: dict[str, Any] | None,
        history_limit: int = 12,
    ) -> int:
        if pseudo_session is None:
            return 0
        history = await self.repository.restore_thread_history(
            db_session=db_session,
            thread_id=thread_id,
            session_data=session_data,
            history_limit=history_limit,
        )
        if history:
            await pseudo_session.add_items(history)
        return len(history)

    async def persist_turn(
        self,
        *,
        db_session: Any,
        thread_id: str,
        user_text: str,
        assistant_text: str,
        user_id: str | None,
    ) -> bool:
        return await self.repository.persist_turn(
            db_session=db_session,
            thread_id=thread_id,
            user_text=user_text,
            assistant_text=assistant_text,
            user_id=user_id,
        )


@dataclass(slots=True)
class WorkerStreamPublisherService:
    stream_key: str
    redis_client: Any

    def __post_init__(self) -> None:
        self.publisher = AgentStreamPublisher(redis_client=self.redis_client, stream_key=self.stream_key)
        self.serializer = EventSerializer()

    def publish_payload(self, payload: dict[str, Any]) -> bool:
        return self.publisher.publish(payload)

    def publish_agent_event(self, *, event: Any, job_id: str) -> bool:
        payload = self.serializer.serialize(event=event, job_id=job_id)
        return self.publisher.publish(payload)

    def publish_sync_json(self, payload: dict[str, Any]) -> None:
        if not self.redis_client:
            return
        stream_helpers.xadd_sync(self.redis_client, self.stream_key, {"data": json.dumps(payload)})

    def close(self) -> None:
        self.publisher.close()
