"""Tests for API endpoints using httpx."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_engine():
    """Mock vLLM engine."""
    engine = MagicMock()
    engine.is_healthy = AsyncMock(return_value=True)
    engine.tokenize = AsyncMock(return_value=[1, 2, 3])
    engine.detokenize = AsyncMock(return_value="Hello")
    return engine


@pytest.fixture
def client(mock_engine):
    """Create test client with mocked engine."""
    with patch("vllm_service.server.app.get_engine", return_value=mock_engine):
        with patch("vllm_service.server.app.initialize_engine", new_callable=AsyncMock):
            from vllm_service.server.app import create_app
            app = create_app()
            with TestClient(app) as test_client:
                yield test_client


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client, mock_engine):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_readiness_check(self, client, mock_engine):
        """Test readiness check endpoint."""
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"


class TestModelsEndpoints:
    """Tests for models endpoints."""

    def test_list_models(self, client):
        """Test list models endpoint."""
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) >= 1

    def test_get_model(self, client):
        """Test get model endpoint."""
        import os
        model_name = os.environ.get("VLLM_MODEL_NAME", "test-model")
        response = client.get(f"/v1/models/{model_name}")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "model"

    def test_get_model_not_found(self, client):
        """Test get model endpoint with non-existent model."""
        response = client.get("/v1/models/nonexistent-model")
        assert response.status_code == 404


class TestTokenizeEndpoints:
    """Tests for tokenize/detokenize endpoints."""

    def test_tokenize(self, client):
        """Test tokenize endpoint."""
        response = client.post("/tokenize", json={"text": "Hello"})
        assert response.status_code == 200
        data = response.json()
        assert "token_ids" in data
        assert "count" in data

    def test_detokenize(self, client):
        """Test detokenize endpoint."""
        response = client.post("/detokenize", json={"token_ids": [1, 2, 3]})
        assert response.status_code == 200
        data = response.json()
        assert "text" in data


class TestChatCompletions:
    """Tests for chat completions endpoint."""

    def test_chat_completion_validation(self, client):
        """Test chat completion request validation."""
        # Missing model
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        assert response.status_code == 422

    def test_chat_completion_missing_messages(self, client):
        """Test chat completion without messages."""
        response = client.post(
            "/v1/chat/completions",
            json={"model": "test-model"}
        )
        assert response.status_code == 422


class TestCompletions:
    """Tests for completions endpoint."""

    def test_completion_validation(self, client):
        """Test completion request validation."""
        # Missing model
        response = client.post(
            "/v1/completions",
            json={"prompt": "Hello"}
        )
        assert response.status_code == 422

    def test_completion_missing_prompt(self, client):
        """Test completion without prompt."""
        response = client.post(
            "/v1/completions",
            json={"model": "test-model"}
        )
        assert response.status_code == 422
