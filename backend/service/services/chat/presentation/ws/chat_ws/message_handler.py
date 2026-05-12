import asyncio

from service.services.chat.application.use_cases.ws_message_use_case import (
    HandleWsChatMessageUseCase,
)
from service.services.chat.presentation.error_mapper import map_to_ws_error_payload
from service.services.chat.presentation.ws.chat_ws.metrics import ChatWsMetrics
from service.services.chat.presentation.ws.chat_ws.payload_builder import ChatWsPayloadBuilder
from service.services.chat.presentation.ws.chat_ws.temp_files import TempFilesManager


class ChatMessageHandler:
    def __init__(self, job_service, file_service, metrics: ChatWsMetrics, chat_service) -> None:
        self._job_service = job_service
        self._file_service = file_service
        self._metrics = metrics
        self._chat_service = chat_service

    async def handle_incoming_messages(
        self,
        websocket,
        thread_id: str,
        session: dict,
        consumer_task: asyncio.Task,
        heartbeat_task: asyncio.Task,
    ) -> None:
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
            await TempFilesManager.cleanup_temp_files(session, self._file_service)

    async def _handle_chat_message(
        self, websocket, thread_id: str, msg: dict, session: dict
    ) -> None:
        try:
            file_ids = msg.get("file_ids") if isinstance(msg.get("file_ids"), list) else []
            if file_ids:
                TempFilesManager.register_temp_file_ids(session, file_ids)

            result = await HandleWsChatMessageUseCase(
                self._job_service, self._chat_service
            ).execute(
                thread_id=thread_id,
                msg=msg,
                session=session,
            )
            if result["type"] == "job_created":
                await websocket.send_json(result)
                return

            await websocket.send_json(ChatWsPayloadBuilder.agent_reply_payload(result))
            await websocket.send_json(ChatWsPayloadBuilder.agent_complete_payload(result))
        except Exception as exc:
            await websocket.send_json(map_to_ws_error_payload(exc, message_id=msg.get("id")))
