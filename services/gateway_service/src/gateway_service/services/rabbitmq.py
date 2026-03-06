"""RabbitMQ Publisher через aio-pika с автопереподключением."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aio_pika
import structlog
from aio_pika import ExchangeType, Message, RobustConnection
from aio_pika.abc import AbstractRobustChannel, AbstractRobustConnection

logger = structlog.get_logger(__name__)


class RabbitMQPublisher:
    """
    Асинхронный publisher с:
    - Автопереподключением (RobustConnection)
    - Подтверждением доставки (publisher confirms)
    - Поддержкой topic и direct exchanges
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractRobustChannel | None = None
        self._exchanges: dict[str, aio_pika.abc.AbstractRobustExchange] = {}

    async def connect(self) -> None:
        """Установить соединение и объявить exchanges."""
        self._connection = await aio_pika.connect_robust(
            self._url,
            reconnect_interval=5,
            fail_fast=False,
        )
        # Канал с publisher confirms
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)

        # Объявляем exchanges
        for exchange_name, exchange_type in [
            ("commands", ExchangeType.TOPIC),
            ("events", ExchangeType.TOPIC),
            ("telemetry", ExchangeType.TOPIC),
        ]:
            exchange = await self._channel.declare_exchange(
                exchange_name,
                exchange_type,
                durable=True,
            )
            self._exchanges[exchange_name] = exchange  # type: ignore[assignment]

        logger.info("rabbitmq.connected", url=self._url)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
        logger.info("rabbitmq.closed")

    @property
    def channel(self) -> AbstractRobustChannel:
        if self._channel is None:
            raise RuntimeError("RabbitMQ not connected. Call connect() first.")
        return self._channel

    # ─── Публикация ──────────────────────────────────────────────────────────

    async def publish(
        self,
        exchange: str,
        routing_key: str,
        payload: dict[str, Any],
        *,
        persistent: bool = True,
        expiration: int | None = None,
        message_id: str | None = None,
    ) -> None:
        """
        Опубликовать сообщение в exchange.

        Args:
            exchange:    Имя exchange (commands, events, telemetry)
            routing_key: Ключ маршрутизации (напр. "user.commands")
            payload:     Тело сообщения (будет сериализовано в JSON)
            persistent:  Сохранять на диск (delivery_mode=2)
            expiration:  TTL сообщения в миллисекундах
            message_id:  Идентификатор сообщения для идемпотентности
        """
        if exchange not in self._exchanges:
            raise ValueError(f"Unknown exchange: {exchange!r}")

        body = json.dumps(payload, ensure_ascii=False).encode()

        message = Message(
            body=body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT if persistent else aio_pika.DeliveryMode.NOT_PERSISTENT,
            message_id=message_id,
            expiration=str(expiration) if expiration else None,
        )

        await self._exchanges[exchange].publish(message, routing_key=routing_key)

        logger.debug(
            "rabbitmq.published",
            exchange=exchange,
            routing_key=routing_key,
            size=len(body),
        )

    async def publish_command(
        self,
        routing_key: str,
        payload: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Shortcut: публикация в exchange 'commands'."""
        await self.publish("commands", routing_key, payload, **kwargs)

    async def publish_event(
        self,
        routing_key: str,
        payload: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Shortcut: публикация в exchange 'events'."""
        await self.publish("events", routing_key, payload, **kwargs)

    # ─── Health check ────────────────────────────────────────────────────────

    async def is_healthy(self) -> bool:
        try:
            return (
                self._connection is not None
                and not self._connection.is_closed
            )
        except Exception:
            return False
