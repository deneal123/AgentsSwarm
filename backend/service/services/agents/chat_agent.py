"""Chat agent wrapper - integrates AgentProcessor with WebSocket/HTTP."""

import logging
from datetime import UTC, datetime
from typing import Any

from service.services.agents.application.ports.interfaces import StreamPort
from service.services.agents.application.processor import AgentProcessor
from service.services.agents.domain.events import EventType
from service.services.chat.domain.chat_contracts import ChatProcessingMetadata, ChatReplyResult

logger = logging.getLogger(__name__)


class ChatAgent:
    """Wrapper for agent system that integrates with chat infrastructure.

    Delegates to AgentProcessor for actual agent logic.
    Handles Redis stream publishing and response formatting.
    """

    def __init__(self, config: dict | None = None, stream_port: StreamPort | None = None):
        """Initialize chat agent.

        Args:
            config: Optional configuration dict (for model_settings, etc)
        """
        self.config = config or {}
        self.stream_port = stream_port
        model_settings = self.config.get("model_settings", {})
        self.processor = AgentProcessor(model_settings)

    @staticmethod
    def _provider_unavailable_reply() -> str:
        return (
            "Сейчас не удалось получить ответ от модели. "
            "Проверьте API-ключ/доступ к провайдеру и повторите запрос."
        )

    async def handle_message(
        self,
        thread_id: int | str,
        text: str,
        user_id: int | None = None,
        session: Any | None = None,
    ) -> ChatReplyResult:
        """Handle incoming chat message.

        Processes message through agent system and publishes events to Redis.

        Args:
            thread_id: Thread/conversation identifier
            text: User's message
            user_id: User identifier
            session: Optional session object

        Returns:
            ChatReplyResult
        """
        reply_text = None
        metadata = {}
        final_output = None

        try:
            stream_port = self.stream_port

            # Helper to make data JSON-serializable
            def _make_serializable(obj):
                try:
                    if obj is None:
                        return None
                    if isinstance(obj, (str, int, float, bool)):
                        return obj
                    if isinstance(obj, dict):
                        return {k: _make_serializable(v) for k, v in obj.items()}
                    if isinstance(obj, (list, tuple)):
                        return [_make_serializable(v) for v in obj]
                    if hasattr(obj, "model_dump"):
                        return _make_serializable(obj.model_dump())
                    if hasattr(obj, "dict"):
                        return _make_serializable(obj.dict())
                    return str(obj)
                except Exception:
                    return str(obj)

            # Process message through agent system
            collected_chunks = []
            has_streaming = False
            events_processed = 0

            logger.info(f"Starting to process message stream for thread {thread_id}")

            try:
                async for event in self.processor.process_message_stream(
                    user_input=text, thread_id=str(thread_id), user_id=user_id, session=session
                ):
                    events_processed += 1
                    # Логируем все события агента
                    logger.debug(f"[{events_processed}] Agent event: {event.type}")

                    try:
                        event_dict = event.model_dump()
                        # Ensure type is properly serialized as string
                        if "type" in event_dict and hasattr(event.type, "value"):
                            event_dict["type"] = event.type.value
                        elif "type" in event_dict:
                            event_dict["type"] = str(event.type)
                        safe_event = _make_serializable(event_dict)

                        if stream_port:
                            await stream_port.publish(f"chat:{thread_id}:stream", safe_event)
                    except Exception as e:
                        logger.error(
                            f"CRITICAL ERROR: Failed to publish {event.type} event to Redis: {e}",
                            exc_info=True,
                        )

                    # Collect streaming chunks for final reply
                    if event.type == EventType.STREAM_CHUNK:
                        if event.data:
                            collected_chunks.append(str(event.data))
                            has_streaming = True

                    # Capture structured output (for calendar, etc)
                    if event.type == EventType.STRUCTURED_OUTPUT:
                        final_output = event.data
                        metadata["structured_output"] = _make_serializable(final_output)

            except Exception as loop_error:
                logger.error(
                    f"FATAL ERROR: Event processing loop failed: {loop_error}", exc_info=True
                )
                logger.error(f"Last processed event count: {events_processed}")
            logger.info(
                f"LOOP ENDED: Finished processing {events_processed} events, has_streaming: {has_streaming}, collected_chunks: {len(collected_chunks)}"
            )

            # Build final reply text
            if collected_chunks:
                reply_text = "".join(collected_chunks)
            elif final_output:
                # If we have structured output but no streaming chunks, use that
                reply_text = str(final_output) if final_output else ""
            else:
                reply_text = ""

            if not (reply_text or "").strip():
                reply_text = self._provider_unavailable_reply()
                metadata = {
                    **(metadata if isinstance(metadata, dict) else {}),
                    "provider_unavailable": True,
                }

            # If no streaming chunks were generated, simulate streaming by chunking the reply
            if not has_streaming and reply_text:
                logger.info(
                    f"No streaming chunks generated, simulating streaming for reply of length {len(reply_text)}"
                )
                chunk_size = 20  # characters per chunk
                for i in range(0, len(reply_text), chunk_size):
                    chunk = reply_text[i : i + chunk_size]
                    stream_event = {
                        "type": "stream_chunk",
                        "data": chunk,
                        "job_id": f"job_{thread_id}_{int(datetime.now(UTC).timestamp())}",
                        "seq": i // chunk_size + 1,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    logger.info(f"Publishing simulated chunk {stream_event['seq']}: '{chunk}'")
                    if stream_port:
                        try:
                            await stream_port.publish(f"chat:{thread_id}:stream", stream_event)
                        except Exception:
                            logger.debug("Failed to publish stream chunk", exc_info=True)
                logger.info("Finished simulating streaming")

            if stream_port:
                try:
                    reply_event = {
                        "type": "agent_reply",
                        "job_id": f"job_{thread_id}_{int(datetime.now(UTC).timestamp())}",
                        "reply": reply_text,
                        "metadata": metadata,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    await stream_port.publish(f"chat:{thread_id}:stream", reply_event)
                except Exception:
                    logger.debug("Failed to publish agent_reply event", exc_info=True)

            # Persist to session if provided
            if session:
                try:
                    await session.add_items(
                        [
                            {"role": "user", "content": text, "ts": datetime.now(UTC).timestamp()},
                            {
                                "role": "assistant",
                                "content": reply_text,
                                "ts": datetime.now(UTC).timestamp(),
                            },
                        ]
                    )
                except Exception:
                    logger.debug("Failed to persist to session", exc_info=True)

        except Exception:
            logger.exception("Error in ChatAgent.handle_message")
            raise

        return ChatReplyResult(
            thread_id=str(thread_id),
            reply=reply_text,
            metadata=ChatProcessingMetadata(data=metadata),
        )
