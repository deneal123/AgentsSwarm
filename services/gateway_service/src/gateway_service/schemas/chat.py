"""
Pydantic-схемы для чата и команд на естественном языке.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Тело запроса POST /chat/message."""

    text: str = Field(
        min_length=1,
        max_length=2000,
        description="Команда или вопрос на естественном языке",
    )
    priority: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Приоритет выполнения: 1 (низкий) … 100 (экстренный)",
    )
    robot_id: str | None = Field(
        default=None,
        description="Адресовать конкретному роботу (None = оркестратор выберет сам)",
    )
    context: dict[str, str] = Field(
        default_factory=dict,
        description="Дополнительный контекст (зона, сессия, etc.)",
    )


class CommandAck(BaseModel):
    """Подтверждение приёма команды (ответ POST /chat/message)."""

    task_id: str = Field(description="Идентификатор созданной задачи для отслеживания")
    message: str = Field(description="Текстовое подтверждение от оркестратора")
    status: str = Field(description="Начальный статус: pending | queued")
    trace_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatResponse(BaseModel):
    """
    Ответ AI на сообщение пользователя.
    Используется как в REST-ответе, так и в WebSocket streaming.
    """

    task_id: str
    reply: str = Field(description="Текстовый ответ AI")
    is_final: bool = Field(default=True, description="False — промежуточный чанк стриминга")
    sources: list[str] = Field(default_factory=list, description="Источники/ссылки")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
