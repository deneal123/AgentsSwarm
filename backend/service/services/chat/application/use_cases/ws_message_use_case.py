from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from service.services.chat.application.use_cases.chat_use_cases import StreamChatResponseUseCase


@dataclass(slots=True)
class HandleWsChatMessageUseCase:
    job_service: Any
    chat_service: Any

    async def execute(self, *, thread_id: str, msg: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
        text = msg.get("text")
        user_id_str = msg.get("user_id") or session.get("user_id")
        user_id = UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
        message_id = msg.get("id")
        selected_model = msg.get("model")
        route_override = msg.get("route_override")
        input_type = msg.get("input_type")
        web_search = bool(msg.get("web_search", False))
        deep_research = bool(msg.get("deep_research", False))
        file_context = msg.get("file_context", "")
        try:
            job_response = await self.job_service.create_chat_job(user_id=user_id, thread_id=thread_id, text=text)
            job_queue = getattr(self.job_service, "job_queue", None)
            if job_queue is None:
                raise RuntimeError("Job queue is disabled")
            task_id = job_queue.enqueue_agent_message(
                job_id=str(job_response.job_id),
                thread_id=thread_id,
                text=text,
                user_id=str(user_id) if user_id else None,
                session_data={"session_id": thread_id},
                selected_model=selected_model,
                route_override=route_override,
                input_type=input_type,
                web_search=web_search,
                deep_research=deep_research,
                file_context=file_context,
                queue="agents",
            )
            if task_id:
                await self.job_service.update_job_celery_task_id(job_response.job_id, str(task_id))
            return {
                "type": "job_created",
                "job_id": str(job_response.job_id),
                "celery_task_id": str(task_id) if task_id else None,
                "message_id": message_id,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception:
            fallback_result = await StreamChatResponseUseCase(self.chat_service).execute(
                thread_id=thread_id,
                text=text,
                user_id=str(user_id) if user_id else None,
                selected_model=selected_model,
                input_type=input_type,
                web_search=web_search,
                deep_research=deep_research,
                file_context=file_context,
                route_override=route_override,
                routing_metadata=None,
            )
            return {
                "type": "fallback",
                "message_id": message_id,
                "thread_id": thread_id,
                "selected_model": selected_model,
                "fallback_result": fallback_result,
                "timestamp": datetime.now().isoformat(),
            }
