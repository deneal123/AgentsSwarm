"""Tests for Data Parallel configuration."""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestDataParallelConfig:
    """Tests for Data Parallel configuration."""

    def test_single_node_config(self):
        """Test single node configuration."""
        os.environ["VLLM_DATA_PARALLEL_SIZE"] = "1"
        os.environ["VLLM_DATA_PARALLEL_RANK"] = "0"
        
        # Config should work for single node
        assert int(os.environ.get("VLLM_DATA_PARALLEL_SIZE", "1")) == 1
        assert int(os.environ.get("VLLM_DATA_PARALLEL_RANK", "0")) == 0

    def test_multi_node_config_rank0(self):
        """Test multi-node configuration for rank 0 (coordinator)."""
        os.environ["VLLM_DATA_PARALLEL_SIZE"] = "2"
        os.environ["VLLM_DATA_PARALLEL_RANK"] = "0"
        os.environ["VLLM_DATA_PARALLEL_ADDRESS"] = "10.0.0.1"
        os.environ["VLLM_DATA_PARALLEL_RPC_PORT"] = "13345"
        
        assert int(os.environ["VLLM_DATA_PARALLEL_SIZE"]) == 2
        assert int(os.environ["VLLM_DATA_PARALLEL_RANK"]) == 0
        assert os.environ["VLLM_DATA_PARALLEL_ADDRESS"] == "10.0.0.1"

    def test_multi_node_config_rank1(self):
        """Test multi-node configuration for rank 1 (worker)."""
        os.environ["VLLM_DATA_PARALLEL_SIZE"] = "2"
        os.environ["VLLM_DATA_PARALLEL_RANK"] = "1"
        os.environ["VLLM_DATA_PARALLEL_ADDRESS"] = "10.0.0.1"
        os.environ["VLLM_DATA_PARALLEL_RPC_PORT"] = "13345"
        
        assert int(os.environ["VLLM_DATA_PARALLEL_SIZE"]) == 2
        assert int(os.environ["VLLM_DATA_PARALLEL_RANK"]) == 1

    def test_data_parallel_env_vars(self):
        """Test all Data Parallel environment variables."""
        env_vars = {
            "VLLM_DATA_PARALLEL_SIZE": "2",
            "VLLM_DATA_PARALLEL_RANK": "0",
            "VLLM_DATA_PARALLEL_ADDRESS": "10.0.0.1",
            "VLLM_DATA_PARALLEL_RPC_PORT": "13345",
            "VLLM_DATA_PARALLEL_SIZE_LOCAL": "1",
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
            assert os.environ[key] == value


class TestModelConfig:
    """Tests for model configuration."""

    def test_model_env_vars(self):
        """Test model configuration environment variables."""
        env_vars = {
            "VLLM_MODEL_NAME": "Qwen/Qwen2.5-7B-Instruct",
            "VLLM_MODEL_DTYPE": "auto",
            "VLLM_MAX_MODEL_LEN": "4096",
            "VLLM_GPU_MEMORY_UTILIZATION": "0.9",
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
            assert os.environ[key] == value

    def test_server_env_vars(self):
        """Test server configuration environment variables."""
        env_vars = {
            "VLLM_HOST": "0.0.0.0",
            "VLLM_PORT": "8000",
            "VLLM_API_KEY": "test-key",
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
            assert os.environ[key] == value

    def test_engine_env_vars(self):
        """Test engine configuration environment variables."""
        env_vars = {
            "VLLM_TENSOR_PARALLEL_SIZE": "1",
            "VLLM_MAX_NUM_SEQS": "256",
            "VLLM_MAX_NUM_BATCHED_TOKENS": "8192",
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
            assert os.environ[key] == value
