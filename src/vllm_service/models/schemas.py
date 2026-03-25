"""Pydantic schemas for OpenAI-compatible API."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


class ModelInfo(BaseModel):
    """Model information response."""

    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "vllm-service"


class ModelList(BaseModel):
    """List of available models."""

    object: str = "list"
    data: List[ModelInfo]


class ChatMessage(BaseModel):
    """Chat message."""

    role: str
    content: Union[str, List[Dict[str, Any]], None] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatCompletionRequest(BaseModel):
    """Chat completion request compatible with OpenAI API."""

    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    n: Optional[int] = Field(default=1, ge=1)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    max_completion_tokens: Optional[int] = Field(default=None, ge=1)
    stop: Optional[Union[str, List[str]]] = None
    stream: Optional[bool] = False
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    # vLLM specific parameters
    top_k: Optional[int] = Field(default=-1, ge=-1)
    min_p: Optional[float] = Field(default=0.0, ge=0, le=1)
    repetition_penalty: Optional[float] = Field(default=1.0, ge=0)
    length_penalty: Optional[float] = Field(default=1.0)
    early_stopping: Optional[bool] = None
    ignore_eos: Optional[bool] = False
    min_tokens: Optional[int] = Field(default=0, ge=0)
    stop_token_ids: Optional[List[int]] = None
    skip_special_tokens: Optional[bool] = True
    spaces_between_special_tokens: Optional[bool] = True
    truncate_prompt_tokens: Optional[int] = None
    prompt_logprobs: Optional[int] = None
    logprobs: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class Usage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionChoice(BaseModel):
    """Single chat completion choice."""

    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None
    logprobs: Optional[Dict[str, Any]] = None


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage
    system_fingerprint: Optional[str] = None


class CompletionRequest(BaseModel):
    """Completion request compatible with OpenAI API."""

    model: str
    prompt: Union[str, List[str], List[int], List[List[int]]]
    suffix: Optional[str] = None
    max_tokens: Optional[int] = Field(default=16, ge=1)
    temperature: Optional[float] = Field(default=1.0, ge=0, le=2)
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    n: Optional[int] = Field(default=1, ge=1)
    stream: Optional[bool] = False
    logprobs: Optional[int] = None
    echo: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    best_of: Optional[int] = None
    user: Optional[str] = None
    # vLLM specific parameters
    top_k: Optional[int] = Field(default=-1, ge=-1)
    min_p: Optional[float] = Field(default=0.0, ge=0, le=1)
    repetition_penalty: Optional[float] = Field(default=1.0, ge=0)

    model_config = ConfigDict(extra="allow")


class CompletionChoice(BaseModel):
    """Single completion choice."""

    index: int
    text: str
    finish_reason: Optional[str] = None
    logprobs: Optional[Dict[str, Any]] = None


class CompletionResponse(BaseModel):
    """Completion response."""

    id: str
    object: str = "text_completion"
    created: int
    model: str
    choices: List[CompletionChoice]
    usage: Usage


class EmbeddingRequest(BaseModel):
    """Embedding request compatible with OpenAI API."""

    model: str
    input: Union[str, List[str], List[int], List[List[int]]]
    encoding_format: Optional[str] = "float"
    dimensions: Optional[int] = None
    user: Optional[str] = None


class EmbeddingData(BaseModel):
    """Single embedding data."""

    index: int
    object: str = "embedding"
    embedding: List[float]


class EmbeddingResponse(BaseModel):
    """Embedding response."""

    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: Usage


class ErrorDetail(BaseModel):
    """Error detail."""

    message: str
    type: str = "invalid_request_error"
    param: Optional[str] = None
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response."""

    error: ErrorDetail
