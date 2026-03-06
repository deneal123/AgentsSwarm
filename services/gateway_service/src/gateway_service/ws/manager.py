"""
ConnectionManager — реестр активных WebSocket-соединений.

Хранит соединения в dict[user_id, list[WebSocket]].
Поддерживает множественные вкладки/устройства одного пользователя.

Потокобезопасность: asyncio.Lock защищает операции connect/disconnect.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import structlog
from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = structlog.get_logger(__name__)


@dataclass
class _Connection:
    """Метаданные одного WebSocket-соединения."""

    connection_id: str
    user_id: str
    websocket: WebSocket
    channel: str  # "chat" | "telemetry" | "notifications"
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_pong: datetime = field(default_factory=datetime.utcnow)

    def is_connected(self) -> bool:
        return self.websocket.client_state == WebSocketState.CONNECTED


class ConnectionManager:
    """
    Менеджер WebSocket-соединений.

    Использование:
        manager = ConnectionManager()

        # При подключении
        conn_id = await manager.connect(websocket, user_id, channel="chat")

        # Отправка конкретному пользователю (все его вкладки/устройства)
        await manager.send_to_user(user_id, {"type": "message", "data": "..."})

        # Широковещательная рассылка
        await manager.broadcast({"type": "system", "data": "..."})

        # При отключении
        await manager.disconnect(conn_id)
    """

    def __init__(self) -> None:
        # connection_id → _Connection
        self._connections: dict[str, _Connection] = {}
        # user_id → set[connection_id]
        self._user_index: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    # ─── Connect / Disconnect ────────────────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        channel: str = "notifications",
    ) -> str:
        """
        Зарегистрировать принятое WebSocket-соединение.
        Возвращает connection_id.
        Ожидает, что websocket.accept() уже был вызван вызывающей стороной.
        """
        conn_id = str(uuid.uuid4())

        conn = _Connection(
            connection_id=conn_id,
            user_id=user_id,
            websocket=websocket,
            channel=channel,
        )

        async with self._lock:
            self._connections[conn_id] = conn
            self._user_index.setdefault(user_id, set()).add(conn_id)

        logger.info(
            "ws.connected",
            connection_id=conn_id,
            user_id=user_id,
            channel=channel,
            total_connections=len(self._connections),
        )
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

    async def broadcast(self, message: dict, channel: str | None = None) -> int:
        """
        Широковещательная рассылка всем (или только нужному каналу).
        Возвращает кол-во доставленных.
        """
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


# ─── Singleton ───────────────────────────────────────────────────────────────

_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """FastAPI Depends-совместимый синглтон ConnectionManager."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
