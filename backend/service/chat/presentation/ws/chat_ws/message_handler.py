import asyncio
import logging
from datetime import datetime
from uuid import UUID

from service.infrastructure.messaging import tasks as messaging_tasks
from service.agents.application.agent_file_bridge import resolve_user_uuid
from service.chat.application.use_cases.chat_use_cases import StreamChatResponseUseCase
from service.chat.presentation.error_mapper import map_to_ws_error_payload, normalize_response_metadata
from service.chat.presentation.ws.chat_ws.metrics import ChatWsMetrics

logger = logging.getLogger(__name__)


class ChatMessageHandler:
    def __init__(self, job_service, file_service, metrics: ChatWsMetrics, chat_service) -> None:
        self._job_service = job_service
        self._file_service = file_service
        self._metrics = metrics
        self._chat_service = chat_service

    async def handle_incoming_messages(self, websocket, thread_id: str, session: dict, consumer_task: asyncio.Task, heartbeat_task: asyncio.Task) -> None:
        try:
            while True:
                try:
                    msg = await websocket.receive_json()
                except Exception:
                    break

                self._metrics.inc("messages_received_total")
                if msg.get("type") == "message":
                    await self._handle_chat_message(websocket, thread_id, msg, session)
        finally:
            consumer_task.cancel()
            heartbeat_task.cancel()
            for task in (consumer_task, heartbeat_task):
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            await self._cleanup_temp_files(session)

    async def _handle_chat_message(self, websocket, thread_id: str, msg: dict, session: dict) -> None:
        try:
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
            file_ids = msg.get("file_ids") if isinstance(msg.get("file_ids"), list) else []

            if file_ids:
                self._register_temp_file_ids(session, file_ids)

            try:
                job_response = await self._job_service.create_chat_job(user_id=user_id, thread_id=thread_id, text=text)
                task = messaging_tasks.process_agent_message.apply_async(
                    kwargs={
                        "job_id": str(job_response.job_id),
                        "thread_id": thread_id,
                        "text": text,
                        "user_id": str(user_id) if user_id else None,
                        "session_data": {"session_id": thread_id},
                        "selected_model": selected_model,
                        "route_override": route_override,
                        "input_type": input_type,
                        "web_search": web_search,
                        "deep_research": deep_research,
                        "file_context": file_context,
                    },
                    queue="agents",
                )
                await self._job_service.update_job_celery_task_id(job_response.job_id, str(task.id))
                await websocket.send_json(
                    {
                        "type": "job_created",
                        "job_id": str(job_response.job_id),
                        "celery_task_id": str(task.id),
                        "message_id": message_id,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return
            except Exception:
                fallback_result = await StreamChatResponseUseCase(self._chat_service).execute(
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
                await websocket.send_json(
                    {
                        "type": "agent_reply",
                        "reply": str(fallback_result.get("reply") or ""),
                        "thread_id": thread_id,
                        "file_url": fallback_result.get("file_url"),
                        "metadata": normalize_response_metadata(fallback_result.get("metadata"), selected_model=selected_model),
                        "message_id": message_id,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                await websocket.send_json(
                    {
                        "type": "agent_complete",
                        "agent_name": (fallback_result.get("metadata") or {}).get("agent_type", "general"),
                        "message_id": message_id,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
        except Exception as exc:
            await websocket.send_json(map_to_ws_error_payload(exc, message_id=msg.get("id")))

    @staticmethod
    def _register_temp_file_ids(session: dict, file_ids: list[str]) -> None:
        bucket = session.setdefault("_temp_file_ids", set())
        if not isinstance(bucket, set):
            bucket = set(bucket) if isinstance(bucket, (list, tuple)) else set()
            session["_temp_file_ids"] = bucket
        for item in file_ids:
            file_id = str(item).strip()
            if file_id:
                bucket.add(file_id)

    async def _cleanup_temp_files(self, session: dict) -> None:
        temp_file_ids = session.get("_temp_file_ids")
        if not temp_file_ids or self._file_service is None:
            return
        user_uuid = resolve_user_uuid(session.get("user_id"), anonymous_fallback=True)
        if user_uuid is None:
            return
        for raw_id in list(temp_file_ids):
            try:
                await self._file_service.delete(user_id=user_uuid, file_id=UUID(str(raw_id)))
            except Exception:
                logger.debug("Failed to cleanup temp file %s", raw_id, exc_info=True)
