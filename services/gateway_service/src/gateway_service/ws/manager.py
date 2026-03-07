"""
ConnectionManager — реестр активных WebSocket-соединений.

Хранит соединения в dict[user_id, list[WebSocket]].
Поддерживает множественные вкладки/устройства одного пользователя.

Потокобезопасность: asyncio.Lock защищает операции connect/disconnect.

Reconnect buffer:
  MessageBuffer хранит последние N сообщений (per channel).
  При переподключении клиент передаёт ?last_message_id=<uuid>,
  и ему автоматически отдаются пропущенные сообщения.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import NamedTuple

import structlog
from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = structlog.get_logger(__name__)

# ─── Message Buffer ──────────────────────────────────────────────────────────

_DEFAULT_BUFFER_SIZE = 100  # максимум сообщений в буфере на канал


class _BufferedMessage(NamedTuple):
    message_id: str
    channel: str
    payload: dict


class MessageBuffer:
    """
    Кольцевой буфер сообщений для поддержки переподключения клиентов.

    Каждое сообщение получает уникальный message_id (UUID4).
    При переподключении клиент передаёт last_message_id,
    и ему возвращаются все сообщения, опубликованные после него.

    Потокобезопасность: guarded by asyncio.Lock (не нужна для asyncio,
    но оставлена для консистентности с ConnectionManager).
    """

    def __init__(self, maxsize: int = _DEFAULT_BUFFER_SIZE) -> None:
        self._maxsize = maxsize
        # channel → deque[_BufferedMessage]
        self._buffers: dict[str, deque[_BufferedMessage]] = {}

    def store(self, channel: str, payload: dict, message_id: str | None = None) -> str:
        """
        Сохранить сообщение в буфер.
        Возвращает присвоенный message_id.
        """
        mid = message_id or str(uuid.uuid4())
        buf = self._buffers.setdefault(channel, deque(maxlen=self._maxsize))
        buf.append(_BufferedMessage(message_id=mid, channel=channel, payload=payload))
        return mid

    def get_missed(self, channel: str, last_message_id: str) -> list[dict]:
        """
        Вернуть все сообщения из канала, опубликованные *после* last_message_id.
        Если last_message_id не найден в буфере — возвращает все буферизованные.
        """
        buf = self._buffers.get(channel)
        if buf is None:
            return []

        messages = list(buf)

        # Найти индекс last_message_id
        found_idx: int | None = None
        for i, msg in enumerate(messages):
            if msg.message_id == last_message_id:
                found_idx = i
                break

        if found_idx is None:
            # Клиент пропустил слишком много — отдаём весь буфер
            return [m.payload | {"_message_id": m.message_id} for m in messages]

        # Отдаём всё после найденного
        return [
            m.payload | {"_message_id": m.message_id}
            for m in messages[found_idx + 1:]
        ]

    def clear_channel(self, channel: str) -> None:
        self._buffers.pop(channel, None)


@dataclass
class _Connection:
    """Метаданные одного WebSocket-соединения."""

    connection_id: str
    user_id: str
    websocket: WebSocket
    channel: str  # "chat" | "telemetry" | "notifications"
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_pong: datetime = field(default_factory=datetime.utcnow)
    last_message_id: str | None = None  # ID последнего полученного сообщения (для replay)

    def is_connected(self) -> bool:
        return self.websocket.client_state == WebSocketState.CONNECTED


class ConnectionManager:
    """
    Менеджер WebSocket-соединений.

    Использование:
        manager = ConnectionManager()

        # При подключении (с поддержкой replay пропущенных сообщений)
        conn_id = await manager.connect(websocket, user_id, channel="telemetry",
                                        last_message_id="<uuid>")

        # Отправка конкретному пользователю (все его вкладки/устройства)
        await manager.send_to_user(user_id, {"type": "message", "data": "..."})

        # Широковещательная рассылка (буферизуется для reconnect)
        await manager.broadcast({"type": "system", "data": "..."})

        # При отключении
        await manager.disconnect(conn_id)
    """

    def __init__(self, buffer_size: int = _DEFAULT_BUFFER_SIZE) -> None:
        # connection_id → _Connection
        self._connections: dict[str, _Connection] = {}
        # user_id → set[connection_id]
        self._user_index: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()
        # Буфер для reconnect (per channel)
        self._buffer = MessageBuffer(maxsize=buffer_size)

    # ─── Connect / Disconnect ────────────────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        channel: str = "notifications",
        last_message_id: str | None = None,
    ) -> str:
        """
        Зарегистрировать принятое WebSocket-соединение.
        Возвращает connection_id.
        Ожидает, что websocket.accept() уже был вызван вызывающей стороной.

        Если передан last_message_id — клиенту немедленно отправляются
        все пропущенные сообщения из буфера (replay).
        """
        conn_id = str(uuid.uuid4())

        conn = _Connection(
            connection_id=conn_id,
            user_id=user_id,
            websocket=websocket,
            channel=channel,
            last_message_id=last_message_id,
        )

        async with self._lock:
            self._connections[conn_id] = conn
            self._user_index.setdefault(user_id, set()).add(conn_id)

        logger.info(
            "ws.connected",
            connection_id=conn_id,
            user_id=user_id,
            channel=channel,
            reconnect=last_message_id is not None,
            total_connections=len(self._connections),
        )

        # Replay пропущенных сообщений
        if last_message_id is not None:
            missed = self._buffer.get_missed(channel, last_message_id)
            if missed:
                logger.info(
                    "ws.replay_missed",
                    connection_id=conn_id,
                    count=len(missed),
                    channel=channel,
                )
                for msg in missed:
                    try:
                        await websocket.send_json(msg)
                    except Exception as exc:
                        logger.warning("ws.replay_send_failed", connection_id=conn_id, error=str(exc))
                        break

        return conn_id

    async def disconnect(self, connection_id: str) -> None:
        """Удалить соединение из реестра и закрыть его."""
        async with self._lock:
            conn = self._connections.pop(connection_id, None)
            if conn is None:
                return
            user_ids = self._user_index.get(conn.user_id, set())
            user_ids.discard(connection_id)
            if not user_ids:
                self._user_index.pop(conn.user_id, None)

        # Закрываем вне локи чтобы не блокировать
        if conn.is_connected():
            try:
                await conn.websocket.close()
            except Exception:
                pass

        logger.info(
            "ws.disconnected",
            connection_id=connection_id,
            user_id=conn.user_id,
            channel=conn.channel,
            total_connections=len(self._connections),
        )

    async def disconnect_user(self, user_id: str) -> int:
        """Отключить все соединения пользователя. Возвращает кол-во закрытых."""
        async with self._lock:
            conn_ids = list(self._user_index.get(user_id, set()))

        count = 0
        for conn_id in conn_ids:
            await self.disconnect(conn_id)
            count += 1
        return count

    # ─── Send ────────────────────────────────────────────────────────────────

    async def send_to_user(self, user_id: str, message: dict) -> int:
        """
        Отправить JSON-сообщение всем соединениям пользователя.
        Возвращает кол-во успешно доставленных.
        """
        async with self._lock:
            conn_ids = list(self._user_index.get(user_id, set()))

        delivered = 0
        dead: list[str] = []
        for conn_id in conn_ids:
            conn = self._connections.get(conn_id)
            if conn is None:
                continue
            try:
                await conn.websocket.send_json(message)
                delivered += 1
            except Exception as exc:
                logger.warning("ws.send_failed", connection_id=conn_id, error=str(exc))
                dead.append(conn_id)

        # Чистим мёртвые соединения
        for conn_id in dead:
            await self.disconnect(conn_id)

        return delivered

    async def send_to_connection(self, connection_id: str, message: dict) -> bool:
        """Отправить сообщение конкретному соединению."""
        conn = self._connections.get(connection_id)
        if conn is None or not conn.is_connected():
            return False
        try:
            await conn.websocket.send_json(message)
            return True
        except Exception as exc:
            logger.warning("ws.send_failed", connection_id=connection_id, error=str(exc))
            await self.disconnect(connection_id)
            return False

    async def broadcast(
        self,
        message: dict,
        channel: str | None = None,
        buffer: bool = True,
    ) -> int:
        """
        Широковещательная рассылка всем (или только нужному каналу).
        Возвращает кол-во доставленных.

        buffer=True (по умолчанию): сообщение сохраняется в reconnect-буфер.
        message_id добавляется в payload как '_message_id'.
        """
        # Буферизуем сообщение (если нужен канал)
        if buffer and channel is not None:
            mid = self._buffer.store(channel, message)
            message = message | {"_message_id": mid}
        elif buffer:
            # Broadcast на все каналы — буферизуем в общий буфер
            mid = self._buffer.store("*", message)
            message = message | {"_message_id": mid}

        async with self._lock:
            targets = [
                c for c in self._connections.values()
                if channel is None or c.channel == channel
            ]

        delivered = 0
        dead: list[str] = []
        for conn in targets:
            try:
                await conn.websocket.send_json(message)
                delivered += 1
            except Exception:
                dead.append(conn.connection_id)

        for conn_id in dead:
            await self.disconnect(conn_id)

        return delivered

    # ─── Heartbeat ───────────────────────────────────────────────────────────

    def update_pong(self, connection_id: str) -> None:
        """Обновить время последнего pong (вызывается при получении pong от клиента)."""
        conn = self._connections.get(connection_id)
        if conn:
            conn.last_pong = datetime.utcnow()

    async def ping_all(self) -> None:
        """Отправить ping всем соединениям (вызывается периодически)."""
        async with self._lock:
            all_conn = list(self._connections.values())

        for conn in all_conn:
            if conn.is_connected():
                try:
                    await conn.websocket.send_json({"type": "ping"})
                except Exception:
                    await self.disconnect(conn.connection_id)

    async def evict_stale(self, timeout_seconds: int) -> int:
        """
        Отключить соединения, не ответившие на ping дольше timeout_seconds.
        Возвращает кол-во отключённых.
        """
        now = datetime.utcnow()
        async with self._lock:
            stale = [
                c.connection_id
                for c in self._connections.values()
                if (now - c.last_pong).total_seconds() > timeout_seconds
            ]

        for conn_id in stale:
            logger.info("ws.evict_stale", connection_id=conn_id)
            await self.disconnect(conn_id)

        return len(stale)

    # ─── Stats ───────────────────────────────────────────────────────────────

    def total_connections(self) -> int:
        return len(self._connections)

    def connections_for_user(self, user_id: str) -> int:
        return len(self._user_index.get(user_id, set()))

    def connection_info(self) -> list[dict]:
        """Список активных соединений (для gRPC GetActiveConnections)."""
        return [
            {
                "connection_id": c.connection_id,
                "user_id": c.user_id,
                "channel": c.channel,
                "connected_at": c.connected_at.isoformat(),
            }
            for c in self._connections.values()
        ]

    # ─── Reconnect Buffer ─────────────────────────────────────────────────────

    def get_missed_messages(self, channel: str, last_message_id: str) -> list[dict]:
        """
        Получить сообщения, пропущенные клиентом (для ручного вызова из хэндлеров).
        Удобно использовать в telemetry_handler при ре-подписке.
        """
        return self._buffer.get_missed(channel, last_message_id)

    def store_message(self, channel: str, payload: dict) -> str:
        """
        Вручную сохранить сообщение в буфер (без отправки).
        Возвращает message_id.
        """
        return self._buffer.store(channel, payload)


# ─── Singleton ───────────────────────────────────────────────────────────────

_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """FastAPI Depends-совместимый синглтон ConnectionManager."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
