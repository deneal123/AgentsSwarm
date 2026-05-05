from __future__ import annotations

from typing import Optional, Any, Literal
from pydantic import BaseModel


# Incoming (client -> server) chat message
class ChatMessageIn(BaseModel):
    type: Literal["message"] = "message"
    id: str
    text: str
    user_id: Optional[int] = None


# Outgoing (server -> client) chat messages
class ChatChunkOut(BaseModel):
    type: Literal["chunk"] = "chunk"
    id: str
    seq: int
    data: str


class ChatProgressOut(BaseModel):
    type: Literal["progress"] = "progress"
    id: str
    progress: int


class ChatDoneOut(BaseModel):
    type: Literal["done"] = "done"
    id: str
    data: str
    metadata: Optional[dict] = None


class ChatErrorOut(BaseModel):
    type: Literal["error"] = "error"
    id: str
    error: str


# Job / Calendar messages (server -> client)
class JobProgressOut(BaseModel):
    event: Literal["progress"] = "progress"
    progress: int
    timestamp: Optional[str] = None


class JobChunkOut(BaseModel):
    event: Literal["chunk"] = "chunk"
    seq: int
    data: Any


class JobCompletedOut(BaseModel):
    event: Literal["completed"] = "completed"
    calendar_id: Optional[str] = None
    result: Optional[dict] = None


class JobErrorOut(BaseModel):
    event: Literal["error"] = "error"
    error: str


# File scan event (published to stream)
class FileScanEvent(BaseModel):
    event: Literal["scanned"] = "scanned"
    file_key: str
    result: dict
