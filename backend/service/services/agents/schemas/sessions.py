from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SessionItem(BaseModel):
    """Single item in a conversation session."""

    role: Literal["user", "assistant"] = Field(..., description="role in conversation")
    content: str = Field(..., description="message content")
    ts: float | None = Field(None, description="timestamp (unix float)")

    @field_validator("ts", mode="before")
    @classmethod
    def normalize_ts(cls, v):
        if v is None:
            return datetime.now(UTC).timestamp()
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v)
            except Exception:
                try:
                    return datetime.fromisoformat(v).timestamp()
                except Exception:
                    raise ValueError("Invalid timestamp")
        raise ValueError("Invalid timestamp")
