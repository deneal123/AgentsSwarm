"""
Роутер чата — REST-интерфейс для NL-команд.

Эндпоинты:
  POST /chat/message — отправить команду на естественном языке

Команда публикуется в RabbitMQ exchange `commands`, routing key `commands.user`.
Orchestrator подхватывает сообщение, обрабатывает через LLM + LangGraph
и публикует ответ обратно через Redis Pub/Sub `chat.responses.{user_id}`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

from gateway_service.auth.permissions import require_authenticated
from gateway_service.auth.schemas import UserContext
from gateway_service.schemas.chat import ChatMessage, CommandAck

logger = structlog.get_logger(__name__)

router = APIRouter()

_COMMANDS_ROUTING_KEY = "commands.user"


@router.post(
    "/message",
    response_model=CommandAck,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Отправить команду на естественном языке",
    description=(
        "Принимает текстовую команду, присваивает task_id и публикует в очередь RabbitMQ. "
        "Для получения ответа подключитесь к WebSocket `/ws/chat` или опрашивайте "
        "GET `/api/v1/tasks/{task_id}`."
    ),
    responses={
        202: {"description": "Команда принята в обработку"},
        503: {"description": "Очередь сообщений недоступна"},
    },
)
async def send_message(
    body: ChatMessage,
    request: Request,
    current_user: UserContext = Depends(require_authenticated),
) -> CommandAck:
    task_id = str(uuid.uuid4())
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))

    logger.info(
        "chat.message_received",
        user_id=current_user.user_id,
        task_id=task_id,
        priority=body.priority,
        text_len=len(body.text),
    )

    # Публикуем команду в RabbitMQ
    rabbitmq = getattr(request.app.state, "rabbitmq", None)
    if rabbitmq:
        try:
            await rabbitmq.publish_command(
                routing_key=_COMMANDS_ROUTING_KEY,
                payload={
                    "task_id": task_id,
                    "user_id": current_user.user_id,
                    "username": current_user.username,
                    "text": body.text,
                    "priority": body.priority,
                    "robot_id": body.robot_id,
                    "context": body.context,
                    "trace_id": trace_id,
                    "created_at": datetime.utcnow().isoformat(),
                },
                message_id=task_id,
            )
            logger.debug("chat.published_to_rabbitmq", task_id=task_id, routing_key=_COMMANDS_ROUTING_KEY)
        except Exception as exc:
            logger.error("chat.publish_failed", task_id=task_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error_code": "QUEUE_UNAVAILABLE",
                    "message": "Command queue is temporarily unavailable. Please try again.",
                },
            ) from exc
    else:
        # Dev-режим без RabbitMQ: логируем и продолжаем
        logger.warning("chat.rabbitmq_not_available", task_id=task_id, text=body.text[:100])

    return CommandAck(
        task_id=task_id,
        message="Your command has been received and is being processed.",
        status="pending",
        trace_id=trace_id,
        created_at=datetime.utcnow(),
    )
