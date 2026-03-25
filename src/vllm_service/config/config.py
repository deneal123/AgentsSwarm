"""Configuration module for vLLM Service."""

import os
from pathlib import Path

from dynaconf import Dynaconf

BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent.parent

# Map docker-compose env vars (without VLLM_ prefix) to settings keys
ENV_KEYS = {
    "MODEL_NAME": "model_name",
    "MODEL_DTYPE": "model_dtype",
    "MAX_MODEL_LEN": "max_model_len",
    "GPU_MEMORY_UTILIZATION": "gpu_memory_utilization",
    "HOST": "host",
    "PORT": "port",
    "API_KEY": "api_key",
    "DATA_PARALLEL_SIZE": "data_parallel_size",
    "DATA_PARALLEL_RANK": "data_parallel_rank",
    "DATA_PARALLEL_ADDRESS": "data_parallel_address",
    "DATA_PARALLEL_RPC_PORT": "data_parallel_rpc_port",
    "DATA_PARALLEL_SIZE_LOCAL": "data_parallel_size_local",
    "TENSOR_PARALLEL_SIZE": "tensor_parallel_size",
    "MAX_NUM_SEQS": "max_num_seqs",
    "MAX_NUM_BATCHED_TOKENS": "max_num_batched_tokens",
    "LOG_LEVEL": "log_level",
}


def _load_env_vars():
    """Load environment variables into os.environ for Dynaconf."""
    for env_key, settings_key in ENV_KEYS.items():
        if env_key in os.environ:
            os.environ[settings_key.upper()] = os.environ[env_key]


# Load env vars before Dynaconf initialization
_load_env_vars()

settings = Dynaconf(
    root_path=BASE_DIR,
    environments=True,
    load_dotenv=True,
    envvar_prefix="",
    settings_files=["settings.toml"],
)

