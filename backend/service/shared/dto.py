from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class BaseDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ErrorDetail(BaseDTO):
    code: str
    message: str
    type: str
    details: dict | list | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


class AppErrorResponse(BaseDTO):
    error: ErrorDetail


class AppResult(BaseDTO, Generic[T]):
    ok: bool = Field(default=True)
    data: T | None = None
    error: ErrorDetail | None = None
