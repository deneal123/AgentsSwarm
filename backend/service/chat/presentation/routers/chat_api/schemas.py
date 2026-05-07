from typing import Literal, Optional

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    # require non-empty text
    text: str = Field(..., min_length=1)
    user_id: Optional[int | str] = None
    model: Optional[str] = None
    input_type: Optional[Literal["text", "image", "audio", "video"]] = None
    web_search: bool = False
    deep_research: bool = False
    route_override: Optional[Literal["general", "web_search", "deep_research", "audio_transcribe", "image_gen", "pptx_gen"]] = None
    file_context: str = ""
    file_ids: list[str] = Field(default_factory=list)


class MessageResponse(BaseModel):
    reply: str
    thread_id: Optional[str] = None
    metadata: Optional[dict] = None


class ThreadCreate(BaseModel):
    user_id: Optional[int] = None
    title: Optional[str] = None


class ThreadResponse(BaseModel):
    thread_id: str
    title: Optional[str] = None
    created_at: Optional[str] = None


class ModelsResponse(BaseModel):
    models: list[str]
