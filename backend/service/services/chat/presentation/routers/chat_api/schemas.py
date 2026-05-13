from typing import Literal

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    # require non-empty text
    text: str = Field(..., min_length=1)
    user_id: int | str | None = None
    model: str | None = None
    input_type: Literal["text", "image", "audio", "video"] | None = None
    web_search: bool = False
    deep_research: bool = False
    route_override: (
        Literal[
            "general", "web_search", "deep_research", "audio_transcribe", "image_gen", "pptx_gen"
        ]
        | None
    ) = None
    file_context: str = ""
    file_ids: list[str] = Field(default_factory=list)


class MessageResponse(BaseModel):
    reply: str
    thread_id: str | None = None
    metadata: dict | None = None


class ThreadCreate(BaseModel):
    user_id: int | None = None
    title: str | None = None


class ThreadResponse(BaseModel):
    thread_id: str
    title: str | None = None
    created_at: str | None = None


class ModelsResponse(BaseModel):
    models: list[str]


class UploadFileResponse(BaseModel):
    filename: str
    file_type: str
    size: int
    extracted_text: str
    thread_id: str
    file_id: str | None = None
    file_url: str | None = None
    file_key: str | None = None
    temp_file: bool
