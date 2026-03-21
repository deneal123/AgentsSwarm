"""Tests for API schemas."""

import pytest
from vllm_service.models.schemas import (
    ChatCompletionRequest,
    ChatMessage,
    CompletionRequest,
    EmbeddingRequest,
    ModelInfo,
    Usage,
)


def test_chat_message():
    """Test ChatMessage schema."""
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


def test_chat_message_with_list_content():
    """Test ChatMessage with list content (multimodal)."""
    msg = ChatMessage(
        role="user",
        content=[{"type": "text", "text": "Hello"}]
    )
    assert msg.role == "user"
    assert isinstance(msg.content, list)


def test_chat_completion_request():
    """Test ChatCompletionRequest schema."""
    req = ChatCompletionRequest(
        model="test-model",
        messages=[
            ChatMessage(role="user", content="Hello"),
        ],
    )
    assert req.model == "test-model"
    assert len(req.messages) == 1
    assert req.temperature == 0.7
    assert req.max_tokens is None


def test_chat_completion_request_with_vllm_params():
    """Test ChatCompletionRequest with vLLM-specific parameters."""
    req = ChatCompletionRequest(
        model="test-model",
        messages=[ChatMessage(role="user", content="Hello")],
        top_k=50,
        repetition_penalty=1.1,
        min_tokens=10,
    )
    assert req.top_k == 50
    assert req.repetition_penalty == 1.1
    assert req.min_tokens == 10


def test_completion_request():
    """Test CompletionRequest schema."""
    req = CompletionRequest(
        model="test-model",
        prompt="Hello, world!",
        max_tokens=100,
    )
    assert req.model == "test-model"
    assert req.prompt == "Hello, world!"
    assert req.max_tokens == 100


def test_completion_request_with_list_prompt():
    """Test CompletionRequest with list prompt."""
    req = CompletionRequest(
        model="test-model",
        prompt=["Hello", "World"],
    )
    assert isinstance(req.prompt, list)
    assert len(req.prompt) == 2


def test_embedding_request():
    """Test EmbeddingRequest schema."""
    req = EmbeddingRequest(
        model="test-model",
        input="Hello, world!",
    )
    assert req.model == "test-model"
    assert req.input == "Hello, world!"
    assert req.encoding_format == "float"


def test_model_info():
    """Test ModelInfo schema."""
    info = ModelInfo(id="test-model", owned_by="vllm-service")
    assert info.id == "test-model"
    assert info.object == "model"
    assert info.owned_by == "vllm-service"


def test_usage():
    """Test Usage schema."""
    usage = Usage(
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
    )
    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 20
    assert usage.total_tokens == 30


def test_chat_completion_request_validation():
    """Test ChatCompletionRequest validation."""
    # Invalid temperature
    with pytest.raises(ValueError):
        ChatCompletionRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="Hello")],
            temperature=3.0,  # > 2
        )
    
    # Invalid top_p
    with pytest.raises(ValueError):
        ChatCompletionRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="Hello")],
            top_p=1.5,  # > 1
        )
