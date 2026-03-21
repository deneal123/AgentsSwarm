"""Test configuration."""

import pytest
import os


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ["VLLM_MODEL_NAME"] = "test-model"
    os.environ["VLLM_HOST"] = "127.0.0.1"
    os.environ["VLLM_PORT"] = "8000"
    os.environ["VLLM_DATA_PARALLEL_SIZE"] = "1"
    os.environ["VLLM_DATA_PARALLEL_RANK"] = "0"
    yield
    # Cleanup
    for key in list(os.environ.keys()):
        if key.startswith("VLLM_"):
            del os.environ[key]
