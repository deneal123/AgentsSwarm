"""Configuration module for vLLM Service."""

import os
from pathlib import Path

from dynaconf import Dynaconf

BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent.parent

settings = Dynaconf(
    root_path=BASE_DIR,
    environments=True,
    load_dotenv=True,
    envvar_prefix="VLLM_",
    settings_files=["settings.toml"],
)
