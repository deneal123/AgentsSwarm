"""
WebSocket обработчики:
  - chat_handler      : чат с AI через RabbitMQ + Redis Pub/Sub
  - telemetry_handler : стриминг телеметрии роботов через Redis Pub/Sub
  - notifications_handler : системные события через Redis Pub/Sub

Общий паттерн:
  1. Аутентификация по ?token= query param
  2. Подключение к ConnectionManager
  3. asyncio.TaskGroup: слушаем Redis Pub/Sub + слушаем клиентский WS
  4. Heartbeat: ping каждые N сек, evict при отсутствии pong
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime

import structlog
from fastapi import WebSocket, WebSocketDisconnect

from gateway_service.auth.middleware import get_current_user
from gateway_service.auth.schemas import UserContext
from gateway_service.config import Settings
from gateway_service.ws.manager import ConnectionManager

logger = structlog.get_logger(__name__)

# ─── Redis channel templates ─────────────────────────────────────────────────

_CHAT_RESPONSE_CHANNEL = "chat.responses.{user_id}"
_TELEMETRY_CHANNEL = "telemetry.{robot_id}"
_NOTIFICATIONS_CHANNEL = "notifications.*"  # pattern subscribe

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


async def _send_error(websocket: WebSocket, code: str, message: str) -> None:
    """Отправить сообщение об ошибке клиенту (безопасно)."""
    try:
        await websocket.send_json({"type": "error", "error_code": code, "message": message, "timestamp": _now_iso()})
    except Exception:
        pass


async def _authenticate_ws(websocket: WebSocket, settings: Settings) -> UserContext | None:
    """
    Аутентификация для WebSocket: токен из query param ?token=...
    Возвращает UserContext или None (соединение уже принято — ошибку отправляем в WS).
    """
    from gateway_service.auth.jwt import verify_token
    from gateway_service.auth.exceptions import AuthError

    token = websocket.query_params.get("token")
    if not token:
        await _send_error(websocket, "MISSING_TOKEN", "Query param ?token= is required")
        return None

    try:
        payload = verify_token(token, settings)
        if payload.token_type != "access":
            await _send_error(websocket, "WRONG_TOKEN_TYPE", "Access token required")
            return None
        return UserContext(
            user_id=payload.sub,
            username="",
            email="",
            role=payload.user_role,
        )
    except AuthError as exc:
        await _send_error(websocket, "AUTH_ERROR", str(exc))
        return None


# ─── Heartbeat task ───────────────────────────────────────────────────────────


async def _heartbeat_loop(
    manager: ConnectionManager,
    connection_id: str,
    heartbeat_sec: int,
    timeout_sec: int,
) -> None:
    """
    Фоновая задача: каждые heartbeat_sec секунд отправляет ping,
    каждые timeout_sec секунд проверяет и отключает молчащие соединения.
    """
    while True:
        await asyncio.sleep(heartbeat_sec)
        evicted = await manager.evict_stale(timeout_sec)
        if evicted:
            logger.info("ws.heartbeat_evicted", count=evicted)
            break  # если наше соединение было evicted — выходим
        await manager.ping_all()


# ─── Chat handler ─────────────────────────────────────────────────────────────


async def chat_handler(
    websocket: WebSocket,
    app_state: object,
    settings: Settings,
    manager: ConnectionManager,
) -> None:
    """
    /ws/chat

    Протокол (JSON):
      Client → Server:
        {"type": "message", "text": "...", "priority": 50, "robot_id": null}
        {"type": "pong"}

      Server → Client:
        {"type": "ack",     "task_id": "...", "timestamp": "..."}
        {"type": "chunk",   "task_id": "...", "text": "...", "is_final": false}
        {"type": "reply",   "task_id": "...", "text": "...", "is_final": true}
        {"type": "ping"}
        {"type": "error",   "error_code": "...", "message": "..."}
    """
    await websocket.accept()

    user = await _authenticate_ws(websocket, settings)
    if user is None:
        await websocket.close(code=4001)
        return

    conn_id = await manager.connect(websocket, user.user_id, channel="chat")
    rabbitmq = getattr(app_state, "rabbitmq", None)
    redis_client = getattr(app_state, "redis", None)

    async def _listen_redis() -> None:
        """Подписаться на Redis Pub/Sub `chat.responses.{user_id}` и пересылать клиенту."""
        if redis_client is None:
            return
        channel = _CHAT_RESPONSE_CHANNEL.format(user_id=user.user_id)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for raw in pubsub.listen():
                if raw["type"] != "message":
                    continue
                try:
                    data = json.loads(raw["data"])
                except (json.JSONDecodeError, TypeError):
                    data = {"text": str(raw["data"]), "is_final": True}

                msg_type = "reply" if data.get("is_final", True) else "chunk"
                await manager.send_to_user(
                    user.user_id,
                    {
                        "type": msg_type,
                        "task_id": data.get("task_id", ""),
                        "text": data.get("text", data.get("reply", "")),
                        "is_final": data.get("is_final", True),
                        "timestamp": _now_iso(),
                    },
                )
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def _listen_client() -> None:
        """Читать сообщения клиента и публиковать команды в RabbitMQ."""
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await _send_error(websocket, "INVALID_JSON", "Message must be valid JSON")
                    continue

                msg_type = data.get("type", "message")

                if msg_type == "pong":
                    manager.update_pong(conn_id)
                    continue

                if msg_type == "message":
                    text = data.get("text", "").strip()
                    if not text:
                        await _send_error(websocket, "EMPTY_MESSAGE", "Field 'text' is required")
                        continue

                    task_id = str(uuid.uuid4())
                    if rabbitmq:
                        try:
                            await rabbitmq.publish_command(
                                routing_key="commands.user",
                                payload={
                                    "task_id": task_id,
                                    "user_id": user.user_id,
                                    "text": text,
                                    "priority": data.get("priority", 50),
                                    "robot_id": data.get("robot_id"),
                                    "source": "websocket",
                                    "created_at": _now_iso(),
                                },
                                message_id=task_id,
                            )
                        except Exception as exc:
                            logger.error("ws.chat.publish_failed", error=str(exc), task_id=task_id)
                            await _send_error(websocket, "QUEUE_ERROR", "Failed to submit command")
                            continue
                    else:
                        logger.warning("ws.chat.rabbitmq_unavailable", task_id=task_id)

                    await manager.send_to_connection(
                        conn_id,
                        {"type": "ack", "task_id": task_id, "timestamp": _now_iso()},
                    )

        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            pass

    redis_task = asyncio.create_task(_listen_redis())
    client_task = asyncio.create_task(_listen_client())
    heartbeat_task = asyncio.create_task(
        _heartbeat_loop(manager, conn_id, settings.ws_heartbeat_seconds, settings.ws_disconnect_timeout_seconds)
    )

    try:
        done, pending = await asyncio.wait(
            [redis_task, client_task, heartbeat_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    finally:
        await manager.disconnect(conn_id)


# ─── Telemetry handler ───────────────────────────────────────────────────────


async def telemetry_handler(
    websocket: WebSocket,
    app_state: object,
    settings: Settings,
    manager: ConnectionManager,
    last_message_id: str | None = None,
) -> None:
    """
    /ws/telemetry

    Протокол:
      Client → Server:
        {"type": "subscribe",   "robot_ids": ["r1", "r2"]}  — добавить роботов
        {"type": "unsubscribe", "robot_ids": ["r1"]}        — убрать роботов
        {"type": "pong"}

      Server → Client:
        {"type": "telemetry", "robot_id": "...", "data": {...}, "timestamp": "..."}
        {"type": "subscribed", "robot_ids": [...]}
        {"type": "ping"}
        {"type": "error", ...}
    """
    await websocket.accept()

    user = await _authenticate_ws(websocket, settings)
    if user is None:
        await websocket.close(code=4001)
        return

    conn_id = await manager.connect(
        websocket,
        user.user_id,
        channel="telemetry",
        last_message_id=last_message_id,
    )
    redis_client = getattr(app_state, "redis", None)

    subscribed_robots: set[str] = set()
    pubsub_tasks: dict[str, asyncio.Task] = {}  # robot_id → task

    async def _subscribe_robot(robot_id: str) -> None:
        """Запустить фоновую задачу подписки на телеметрию одного робота."""
        if robot_id in pubsub_tasks or redis_client is None:
            return
        channel = _TELEMETRY_CHANNEL.format(robot_id=robot_id)

        async def _listen() -> None:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(channel)
            try:
                async for raw in pubsub.listen():
                    if raw["type"] != "message":
                        continue
                    try:
                        data = json.loads(raw["data"])
                    except (json.JSONDecodeError, TypeError):
                        data = {"raw": str(raw["data"])}
                    await manager.send_to_connection(
                        conn_id,
                        {"type": "telemetry", "robot_id": robot_id, "data": data, "timestamp": _now_iso()},
                    )
            except asyncio.CancelledError:
                pass
            finally:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()

        pubsub_tasks[robot_id] = asyncio.create_task(_listen())

    async def _unsubscribe_robot(robot_id: str) -> None:
        task = pubsub_tasks.pop(robot_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _listen_client() -> None:
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await _send_error(websocket, "INVALID_JSON", "Message must be valid JSON")
                    continue

                msg_type = data.get("type")

                if msg_type == "pong":
                    manager.update_pong(conn_id)
                    continue

                if msg_type == "subscribe":
                    ids = data.get("robot_ids", [])
                    for rid in ids:
                        subscribed_robots.add(rid)
                        await _subscribe_robot(rid)
                    await manager.send_to_connection(
                        conn_id,
                        {"type": "subscribed", "robot_ids": list(subscribed_robots)},
                    )

                elif msg_type == "unsubscribe":
                    ids = data.get("robot_ids", [])
                    for rid in ids:
                        subscribed_robots.discard(rid)
                        await _unsubscribe_robot(rid)
                    await manager.send_to_connection(
                        conn_id,
                        {"type": "unsubscribed", "robot_ids": ids},
                    )

        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            pass

    client_task = asyncio.create_task(_listen_client())
    heartbeat_task = asyncio.create_task(
        _heartbeat_loop(manager, conn_id, settings.ws_heartbeat_seconds, settings.ws_disconnect_timeout_seconds)
    )

    try:
        done, pending = await asyncio.wait(
            [client_task, heartbeat_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    finally:
        # Отписываемся от всех роботов
        for robot_id in list(pubsub_tasks.keys()):
            await _unsubscribe_robot(robot_id)
        await manager.disconnect(conn_id)


# ─── Notifications handler ───────────────────────────────────────────────────


async def notifications_handler(
    websocket: WebSocket,
    app_state: object,
    settings: Settings,
    manager: ConnectionManager,
    last_message_id: str | None = None,
) -> None:
    """
    /ws/notifications

    Протокол:
      Client → Server:
        {"type": "pong"}

      Server → Client:
        {"type": "notification", "notification_type": "...", "title": "...",
         "message": "...", "payload": {...}, "timestamp": "..."}
        {"type": "ping"}
        {"type": "error", ...}

    Redis Pub/Sub: подписка на pattern `notifications.*`
      Сообщения публикуются другими сервисами (Orchestrator, robots).
    """
    await websocket.accept()

    user = await _authenticate_ws(websocket, settings)
    if user is None:
        await websocket.close(code=4001)
        return

    conn_id = await manager.connect(
        websocket,
        user.user_id,
        channel="notifications",
        last_message_id=last_message_id,
    )
    redis_client = getattr(app_state, "redis", None)

    async def _listen_redis() -> None:
        if redis_client is None:
            return
        pubsub = redis_client.pubsub()
        # Pattern subscribe: notifications.* → task_update, robot_event, incident, etc.
        await pubsub.psubscribe("notifications.*")
        try:
            async for raw in pubsub.listen():
                if raw["type"] not in ("pmessage", "message"):
                    continue
                try:
                    data = json.loads(raw["data"])
                except (json.JSONDecodeError, TypeError):
                    data = {"message": str(raw["data"])}

                # Личные уведомления доставляем только адресату
                target_user = data.get("user_id")
                if target_user and target_user != user.user_id:
                    continue

                await manager.send_to_connection(
                    conn_id,
                    {
                        "type": "notification",
                        "notification_type": data.get("notification_type", "info"),
                        "title": data.get("title", ""),
                        "message": data.get("message", ""),
                        "payload": data.get("payload", {}),
                        "robot_id": data.get("robot_id"),
                        "task_id": data.get("task_id"),
                        "timestamp": _now_iso(),
                    },
                )
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.punsubscribe("notifications.*")
            await pubsub.aclose()

    async def _listen_client() -> None:
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "pong":
                    manager.update_pong(conn_id)
        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            pass

    redis_task = asyncio.create_task(_listen_redis())
    client_task = asyncio.create_task(_listen_client())
    heartbeat_task = asyncio.create_task(
        _heartbeat_loop(manager, conn_id, settings.ws_heartbeat_seconds, settings.ws_disconnect_timeout_seconds)
    )

    try:
        done, pending = await asyncio.wait(
            [redis_task, client_task, heartbeat_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    finally:
        await manager.disconnect(conn_id)
