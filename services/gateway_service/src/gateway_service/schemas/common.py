"""
Общие Pydantic-схемы: пагинация, универсальный ответ, ErrorResponse.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")


# ─── Пагинация ───────────────────────────────────────────────────────────────


class PaginationParams(BaseModel):
    """Параметры пагинации для GET-запросов со списками."""

    page: int = Field(default=1, ge=1, description="Номер страницы (с 1)")
    page_size: int = Field(default=20, ge=1, le=100, description="Элементов на странице")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def pagination_params(
    page: int = Query(default=1, ge=1, description="Номер страницы"),
    page_size: int = Query(default=20, ge=1, le=100, description="Элементов на странице"),
) -> PaginationParams:
    """FastAPI Depends-фабрика для параметров пагинации."""
    return PaginationParams(page=page, page_size=page_size)


class PaginatedResponse(BaseModel, Generic[T]):
    """Унифицированный ответ со списком и мета-данными пагинации."""

    items: list[T]
    total: int = Field(description="Общее количество элементов")
    page: int = Field(description="Текущая страница")
    page_size: int = Field(description="Элементов на странице")
    pages: int = Field(description="Всего страниц")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        pages = max(1, (total + page_size - 1) // page_size)
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)


# ─── Ошибки ──────────────────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Унифицированный формат ответа об ошибке."""

    error_code: str = Field(description="Код ошибки в UPPER_SNAKE_CASE")
    message: str = Field(description="Читаемое сообщение об ошибке")
    details: list[dict] | None = Field(default=None, description="Детали (напр., ошибки валидации)")
    trace_id: str | None = Field(default=None, description="Идентификатор трассировки")


class MessageResponse(BaseModel):
    """Простой ответ с текстовым сообщением."""

    message: str
