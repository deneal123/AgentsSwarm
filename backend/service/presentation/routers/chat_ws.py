import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, WebSocket, status
from starlette.websockets import WebSocketDisconnect

from service import container
from service.services.chat_ws import (
    ChatMessageHandler,
    ChatStreamConsumer,
    ChatWsAuthService,
    ChatWsConnectionService,
    ChatWsMetrics,
)
from service.security import AuthValidator
from service.settings import config

logger = logging.getLogger(__name__)
router = APIRouter()
_metrics = ChatWsMetrics()


def get_optional_job_service(app_container: Annotated[container.AppContainer, Depends(container.get_app_container)]) -> Any:
    return app_container.services.job_service


def get_optional_file_service(app_container: Annotated[container.AppContainer, Depends(container.get_app_container)]) -> Any:
    return app_container.services.file_saver_service


def get_chat_ws_connection_service(
    redis_client: Annotated[Any, Depends(container.get_optional_redis_client)],
    session_store: Annotated[Any, Depends(container.get_optional_redis_session_store)],
    job_service: Annotated[Any, Depends(get_optional_job_service)],
    file_service: Annotated[Any, Depends(get_optional_file_service)],
) -> ChatWsConnectionService:
    ws_settings = config.chat_ws.settings
    auth_service = ChatWsAuthService(AuthValidator(config.auth), session_store)
    stream_consumer = ChatStreamConsumer(redis_client, ws_settings, _metrics)
    message_handler = ChatMessageHandler(job_service, file_service, _metrics)
    return ChatWsConnectionService(auth_service, stream_consumer, message_handler, ws_settings, _metrics)


@router.websocket("/api/chats/{thread_id}/ws")
async def chat_ws(
    websocket: WebSocket,
    thread_id: str,
    orchestrator: Annotated[ChatWsConnectionService, Depends(get_chat_ws_connection_service)],
) -> None:
    last_id = websocket.query_params.get("last_id")
    try:
        await orchestrator.run(websocket, thread_id, last_id=last_id)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for thread %s", thread_id)
    except Exception:
        logger.exception("Error in chat websocket for thread %s", thread_id)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass


async def process_claimed_entries(websocket, redis_client, stream_key: str, group: str, claimed: list):
    consumer = ChatStreamConsumer(redis_client, config.chat_ws.settings, _metrics)
    await consumer.process_claimed_entries(websocket, stream_key, group, claimed)
