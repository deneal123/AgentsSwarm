import asyncio
import json
import logging

from celery import shared_task

from service.services.chat.domain.chat_contracts import (
    ChatProcessingMetadata,
    ChatReplyResult,
)
from service.services.chat.infrastructure.chat_worker_tasks import (
    _persist_chat_turn,
    _resolve_memory_user_id,
    _restore_pseudo_session_history,
    delete_old_chat_history,
    process_agent_message,
    process_agent_message_async,
)

logger = logging.getLogger(__name__)


def process_chat_message_core(
    thread_id: str, message_id: str, text: str, user_id: int | None = None
) -> dict:
    from service.composition import state as svc_container
    from service.infrastructure.messaging import stream_helpers as stream_helpers_module

    try:
        chat_svc = svc_container.get_current_container().services.chat_application_service
        res = asyncio.run(
            chat_svc.post_message(
                thread_id=thread_id,
                payload=type(
                    "P",
                    (),
                    {
                        "text": text,
                        "user_id": user_id,
                        "model": None,
                        "input_type": None,
                        "web_search": False,
                        "deep_research": False,
                        "file_context": "",
                        "route_override": None,
                        "file_ids": [],
                    },
                )(),
            )
        )
        res = ChatReplyResult(
            reply=res.get("reply", ""),
            thread_id=res.get("thread_id", thread_id),
            metadata=ChatProcessingMetadata(data=res.get("metadata") or {}),
        )
    except Exception:
        logger.exception("process_chat_message_core failed")
        res = ChatReplyResult(
            reply="", thread_id=thread_id, metadata=ChatProcessingMetadata(data={})
        )

    redis_client = None
    try:
        redis_client = svc_container.get_current_container().infra.redis_client
    except Exception:
        redis_client = None

    if redis_client:
        payload = {
            "type": "agent_reply",
            "id": message_id,
            "reply": res.reply,
            "metadata": res.metadata.data,
        }
        try:
            stream_helpers_module.xadd_sync(
                redis_client, f"chat:{thread_id}:stream", {"data": json.dumps(payload)}
            )
        except Exception:
            logger.exception("Failed to publish agent reply")

    return res.to_dict()


@shared_task(bind=True, name="service.infrastructure.messaging.tasks.process_chat_message")
def process_chat_message(
    self, thread_id: str, message_id: str, text: str, user_id: int | None = None
) -> dict:
    try:
        result = process_chat_message_core(thread_id, message_id, text, user_id)
        return {"status": "ok", "result": result}
    except Exception:
        logger.exception("process_chat_message failed")
        return {"status": "error"}


@shared_task(name="service.infrastructure.messaging.tasks.cleanup_old_streams")
def cleanup_old_streams():
    from service.infrastructure.cache.redis_manager import RedisManager
    from service.infrastructure.messaging import stream_helpers
    from service.settings import Config

    try:
        config = Config()
        if not config.redis or not config.redis.enabled:
            return {"status": "skipped", "reason": "redis_disabled"}
        redis_client = RedisManager(config.redis).get_client()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            trimmed = loop.run_until_complete(
                stream_helpers.cleanup_old_streams(
                    redis_client, pattern="chat:*:stream", maxlen=1000
                )
            )
            return {"status": "success", "trimmed": trimmed}
        finally:
            loop.close()
    except Exception as exc:
        logger.exception("Failed to cleanup old streams: %s", exc)
        return {"status": "error", "error": str(exc)}


__all__ = [
    "process_chat_message_core",
    "process_chat_message",
    "process_agent_message_async",
    "process_agent_message",
    "delete_old_chat_history",
    "cleanup_old_streams",
    "_resolve_memory_user_id",
    "_restore_pseudo_session_history",
    "_persist_chat_turn",
]
