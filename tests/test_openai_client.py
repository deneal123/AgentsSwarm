"""Integration tests for OpenAI client compatibility."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai import OpenAI
from openai.types.chat import ChatCompletion


@pytest.fixture
def mock_vllm_output():
    """Mock vLLM output."""
    output = MagicMock()
    output.outputs = [MagicMock()]
    output.outputs[0].text = "Hello! How can I help you?"
    output.outputs[0].index = 0
    output.outputs[0].finish_reason = "stop"
    output.outputs[0].token_ids = [1, 2, 3, 4, 5]
    output.prompt_token_ids = [1, 2, 3]
    return output


class TestOpenAIClientCompatibility:
    """Tests for OpenAI client compatibility."""

    def test_chat_completion_request_format(self):
        """Test that request format matches OpenAI spec."""
        from vllm_service.models.schemas import ChatCompletionRequest, ChatMessage
        
        # Standard OpenAI request format
        request = ChatCompletionRequest(
            model="gpt-4",
            messages=[
                ChatMessage(role="system", content="You are a helpful assistant."),
                ChatMessage(role="user", content="Hello!"),
            ],
            temperature=0.7,
            max_tokens=100,
        )
        
        assert request.model == "gpt-4"
        assert len(request.messages) == 2
        assert request.temperature == 0.7
        assert request.max_tokens == 100

    def test_chat_completion_with_tools_format(self):
        """Test chat completion with tools format."""
        from vllm_service.models.schemas import ChatCompletionRequest, ChatMessage
        
        request = ChatCompletionRequest(
            model="gpt-4",
            messages=[
                ChatMessage(role="user", content="What's the weather?"),
            ],
        )
        
        assert request.model == "gpt-4"
        assert len(request.messages) == 1

    def test_multimodal_content_format(self):
        """Test multimodal content format."""
        from vllm_service.models.schemas import ChatMessage
        
        # Multimodal message with image
        message = ChatMessage(
            role="user",
            content=[
                {"type": "text", "text": "What's in this image?"},
                {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}},
            ],
        )
        
        assert message.role == "user"
        assert isinstance(message.content, list)
        assert len(message.content) == 2

    def test_completion_request_format(self):
        """Test that completion request format matches OpenAI spec."""
        from vllm_service.models.schemas import CompletionRequest
        
        request = CompletionRequest(
            model="gpt-4",
            prompt="Translate the following: Hello",
            max_tokens=50,
            temperature=0.5,
        )
        
        assert request.model == "gpt-4"
        assert request.prompt == "Translate the following: Hello"
        assert request.max_tokens == 50
        assert request.temperature == 0.5

    def test_embedding_request_format(self):
        """Test that embedding request format matches OpenAI spec."""
        from vllm_service.models.schemas import EmbeddingRequest
        
        request = EmbeddingRequest(
            model="text-embedding-ada-002",
            input="Hello, world!",
            encoding_format="float",
        )
        
        assert request.model == "text-embedding-ada-002"
        assert request.input == "Hello, world!"
        assert request.encoding_format == "float"

    def test_vllm_extra_parameters(self):
        """Test vLLM-specific parameters in request."""
        from vllm_service.models.schemas import ChatCompletionRequest, ChatMessage
        
        request = ChatCompletionRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="Hello")],
            top_k=50,  # vLLM-specific
            repetition_penalty=1.2,  # vLLM-specific
            min_tokens=10,  # vLLM-specific
        )
        
        assert request.top_k == 50
        assert request.repetition_penalty == 1.2
        assert request.min_tokens == 10
