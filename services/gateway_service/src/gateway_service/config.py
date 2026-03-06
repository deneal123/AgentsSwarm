"""
Конфигурация Gateway Service через Pydantic Settings.
Все параметры читаются из переменных окружения (или .env файла).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки Gateway Service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Приложение ──────────────────────────────────────────────────────────
    app_name: str = "AgentsSwarm Gateway"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Сервер
    host: str = "0.0.0.0"
    port: int = Field(default=8005, ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=16)

    # ─── JWT / Auth ───────────────────────────────────────────────────────────
    jwt_secret: str = Field(..., min_length=32, description="Секрет для подписи JWT")
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = Field(default=15, ge=1)
    jwt_refresh_expire_days: int = Field(default=7, ge=1)

    # ─── Redis ────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_min_size: int = 5
    redis_pool_max_size: int = 20
    redis_decode_responses: bool = True

    # ─── RabbitMQ ────────────────────────────────────────────────────────────
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange_commands: str = "commands"
    rabbitmq_exchange_events: str = "events"
    rabbitmq_queue_user_commands: str = "commands.user"

    # ─── gRPC (Orchestrator) ─────────────────────────────────────────────────
    orchestrator_grpc_host: str = "localhost"
    orchestrator_grpc_port: int = Field(default=50051, ge=1, le=65535)
    grpc_deadline_seconds: float = 10.0

    # ─── CORS ────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # ─── Rate Limiting ───────────────────────────────────────────────────────
    rate_limit_rest_per_minute: int = 100
    rate_limit_chat_per_minute: int = 30
    rate_limit_ws_connections_per_user: int = 5

    # ─── WebSocket ───────────────────────────────────────────────────────────
    ws_heartbeat_seconds: int = 30
    ws_disconnect_timeout_seconds: int = 60

    # ─── Observability ───────────────────────────────────────────────────────
    jaeger_endpoint: str | None = None
    otlp_endpoint: str | None = None
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    tracing_sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)

    # ─── Безопасность ────────────────────────────────────────────────────────
    trusted_hosts: list[str] = ["localhost", "127.0.0.1"]
    max_request_size_bytes: int = 10 * 1024 * 1024  # 10 MB

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Поддержка строки с запятой: 'http://a.com,http://b.com'."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def grpc_target(self) -> str:
        return f"{self.orchestrator_grpc_host}:{self.orchestrator_grpc_port}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Синглтон настроек (кэшируется через lru_cache)."""
    return Settings()  # type: ignore[call-arg]
