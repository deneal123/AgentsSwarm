"""Pydantic models for session items."""
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import datetime, timezone


class SessionItem(BaseModel):
    """Single item in a conversation session."""
    
    role: Literal["user", "assistant"] = Field(..., description="role in conversation")
    content: str = Field(..., description="message content")
    ts: Optional[float] = Field(None, description="timestamp (unix float)")

    @field_validator("ts", mode="before")
    def normalize_ts(cls, v):
        """Normalize timestamp to float."""
        if v is None:
            return datetime.now(timezone.utc).timestamp()
        # Accept numeric strings, floats, ints, or ISO datetime strings
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v)
            except Exception:
                # Try ISO format
                try:
                    return datetime.fromisoformat(v).timestamp()
                except Exception:
                    raise ValueError("Invalid timestamp")
        raise ValueError("Invalid timestamp")

