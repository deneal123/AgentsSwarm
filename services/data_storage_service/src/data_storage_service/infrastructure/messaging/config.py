import os
from typing import Optional

import dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = dotenv.find_dotenv()
if ENV_FILE:
    try:
        dotenv.load_dotenv(ENV_FILE, override=False)
    except Exception:
        pass


class CeleryConfig(BaseSettings):
    broker_url: str = Field(default="amqp://guest:guest@rabbitmq:5672//")
    result_backend: str = Field(default="redis://redis:6379/1")
    task_serializer: str = Field(default="json")
    accept_content: list[str] = Field(default=["json"])
    result_serializer: str = Field(default="json")
    timezone: str = Field(default="UTC")
    enable_utc: bool = Field(default=True)
    task_acks_late: bool = Field(default=True)
    task_reject_on_worker_lost: bool = Field(default=True)
    task_soft_time_limit: int = Field(default=3600)
    task_time_limit: int = Field(default=3900)
    worker_prefetch_multiplier: int = Field(default=1)
    worker_max_tasks_per_child: int = Field(default=50)
    result_expires: int = Field(default=86400)
    result_extended: bool = Field(default=True)
    task_default_retry_delay: int = Field(default=60)
    task_max_retries: int = Field(default=3)
    task_default_queue: str = Field(default="default")

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="CELERY__"
    )


class MessagingConfig(BaseSettings):
    celery: CeleryConfig = Field(default_factory=CeleryConfig)


def _get_messaging_config() -> MessagingConfig:
    config = MessagingConfig()
    return config


messaging_config = _get_messaging_config()
