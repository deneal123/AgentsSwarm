import asyncio
import logging
from datetime import datetime
from uuid import UUID

from service.services.agents.application.agent_file_bridge import resolve_user_uuid
from service.services.chat.application.use_cases.ws_message_use_case import HandleWsChatMessageUseCase
from service.services.chat.presentation.error_mapper import map_to_ws_error_payload, normalize_response_metadata
from service.services.chat.presentation.ws.chat_ws.metrics import ChatWsMetrics

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
            file_ids = msg.get("file_ids") if isinstance(msg.get("file_ids"), list) else []
            if file_ids:
                self._register_temp_file_ids(session, file_ids)

            result = await HandleWsChatMessageUseCase(self._job_service, self._chat_service).execute(
                thread_id=thread_id,
                msg=msg,
                session=session,
            )
            if result["type"] == "job_created":
                await websocket.send_json(result)
                return

            fallback_result = result["fallback_result"]
            await websocket.send_json(
                {
                    "type": "agent_reply",
                    "reply": str(fallback_result.get("reply") or ""),
                    "thread_id": result["thread_id"],
                    "file_url": fallback_result.get("file_url"),
                    "metadata": normalize_response_metadata(fallback_result.get("metadata"), selected_model=result["selected_model"]),
                    "message_id": result["message_id"],
                    "timestamp": result["timestamp"],
                }
            )
            await websocket.send_json(
                {
                    "type": "agent_complete",
                    "agent_name": (fallback_result.get("metadata") or {}).get("agent_type", "general"),
                    "message_id": result["message_id"],
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
