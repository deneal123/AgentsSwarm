"""
WebSocket роутер.

Маршруты (монтируются под /ws в main.py):
  WS /ws/chat          — чат с AI (NL команды + streaming ответы)
  WS /ws/telemetry     — стриминг телеметрии роботов
  WS /ws/notifications — системные события и уведомления

Аутентификация: ?token=<access_jwt> в query string.
Heartbeat: ping каждые settings.ws_heartbeat_seconds секунд.
Reconnect: ?last_message_id=<uuid> для получения пропущенных сообщений.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, WebSocket

from gateway_service.config import get_settings
from gateway_service.ws.handlers import (
    chat_handler,
    notifications_handler,
    telemetry_handler,
)
from gateway_service.ws.manager import get_connection_manager

logger = structlog.get_logger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/chat")
async def ws_chat(websocket: WebSocket) -> None:
    """
    WebSocket чат с AI.

    Подключение: `ws://host/ws/chat?token=<access_token>`

    Клиент отправляет:
      `{"type": "message", "text": "Робот 1, возьми коробку", "priority": 50}`

    Сервер отвечает:
      `{"type": "ack",   "task_id": "..."}`
      `{"type": "chunk", "task_id": "...", "text": "...", "is_final": false}`
      `{"type": "reply", "task_id": "...", "text": "...", "is_final": true}`
    """
    settings = get_settings()
    manager = get_connection_manager()
    await chat_handler(
        websocket=websocket,
        app_state=websocket.app.state,
        settings=settings,
        manager=manager,
    )


@ws_router.websocket("/telemetry")
async def ws_telemetry(websocket: WebSocket) -> None:
    """
    WebSocket телеметрия роботов.

    Подключение: `ws://host/ws/telemetry?token=<access_token>[&last_message_id=<uuid>]`

    Клиент отправляет:
      `{"type": "subscribe",   "robot_ids": ["robot-1", "robot-2"]}`
      `{"type": "unsubscribe", "robot_ids": ["robot-1"]}`

    Сервер отвечает:
      `{"type": "subscribed", "robot_ids": [...]}`
      `{"type": "telemetry",  "robot_id": "...", "data": {...}}`

    При переподключении передайте last_message_id для получения пропущенных сообщений.
    """
    settings = get_settings()
    manager = get_connection_manager()
    last_message_id = websocket.query_params.get("last_message_id")
    await telemetry_handler(
        websocket=websocket,
        app_state=websocket.app.state,
        settings=settings,
        manager=manager,
        last_message_id=last_message_id,
    )


@ws_router.websocket("/notifications")
async def ws_notifications(websocket: WebSocket) -> None:
    """
    WebSocket системные уведомления.

    Подключение: `ws://host/ws/notifications?token=<access_token>[&last_message_id=<uuid>]`

    Сервер отправляет:
      `{"type": "notification", "notification_type": "task_update",
        "title": "...", "message": "...", "payload": {...}}`

    При переподключении передайте last_message_id для получения пропущенных уведомлений.
    """
    settings = get_settings()
    manager = get_connection_manager()
    last_message_id = websocket.query_params.get("last_message_id")
    await notifications_handler(
        websocket=websocket,
        app_state=websocket.app.state,
        settings=settings,
        manager=manager,
        last_message_id=last_message_id,
    )
