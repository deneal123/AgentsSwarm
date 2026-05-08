import os
import json

import dotenv
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = dotenv.find_dotenv()
if ENV_FILE:
    # Load .env into os.environ early so modules that read os.environ at import time
    # (for example the OpenAI client) will see variables such as OPENAI_API_KEY.
    # Do not override existing environment variables.
    try:
        dotenv.load_dotenv(ENV_FILE, override=False)
    except Exception:
        # Best-effort: if loading fails, continue — BaseSettings still uses env_file
        pass

LOGGING_LEVEL = os.environ.get("SERVICE_LOGGING_LEVEL", "debug").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "level": LOGGING_LEVEL,
            "formatter": "default",
        },
    },
    "loggers": {
        "service": {
            "level": LOGGING_LEVEL,
            "handlers": ["default"],
            "propagate": False,
        },
    },
    "root": {"level": LOGGING_LEVEL, "handlers": ["default"]},
}


class Postgresql(BaseModel):
    protocol: str = "postgresql+asyncpg"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: float = 5.0
    db_pool_recycle: int = 3600
    db_pool_pre_ping: bool = True

    @property
    def dsn(self) -> str:
        return f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def dsn_safe(self) -> str:
        return f"{self.protocol}://{self.user}:***@{self.host}:{self.port}/{self.db}"


class PgConfig(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "password"
    db: str = "main"
    settings: Optional[Postgresql] = Postgresql()
    model_config = SettingsConfigDict(env_prefix="PG__")

    @property
    def dsn(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class ServiceConfig(BaseSettings):
    logging_level: str = Field(default_factory=str)
    server_port: int = Field(default_factory=int)
    name: str = Field(default_factory=str)
    app_domain: str = Field(default_factory=str)
    admin_user_ids: list[str] | str = Field(default_factory=list)
    nginx_port: int = Field(default_factory=int)
    react_app_api_base_url: str = Field(default_factory=str)
    react_app_ws_base_url: str = Field(default_factory=str)
    react_app_enable_admin_ui: bool = Field(default_factory=bool)
    model_config = SettingsConfigDict(env_prefix="SERVICE__")

    @field_validator("admin_user_ids", mode="before")
    @classmethod
    def _split_admin_ids(cls, value):  # noqa: D401 - simple converter
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip().lower() for item in value if str(item).strip()]
        return value

    @property
    def admin_user_ids_set(self) -> set[str]:
        return {item.lower() for item in self.admin_user_ids}


class AuthConfig(BaseSettings):
    dev_mode: bool = Field(default_factory=bool)
    auth_mode: str = "prod"
    secret: str = Field(default_factory=str)
    algorithm: str = Field(default_factory=str)
    jwt_exp_hours: int = Field(default_factory=int)
    ws_auth_allowlist_prod: list[str] = Field(default_factory=lambda: ["jwt_cookie"])
    ws_auth_allowlist_dev: list[str] = Field(
        default_factory=lambda: [
            "jwt_cookie",
            "query_token",
            "authorization_bearer",
            "session_cookie",
            "anon_token",
        ]
    )
    enable_legacy_ws_token_auth: bool = False
    enable_dev_test_token: bool = False
    enforce_prod_runtime_auth_guard: bool = True
    model_config = SettingsConfigDict(env_prefix="AUTH__")

    @field_validator("auth_mode", mode="before")
    @classmethod
    def _normalize_auth_mode(cls, value):
        normalized = str(value or "").strip().lower()
        if normalized in {"dev", "prod"}:
            return normalized
        return "prod"


class ProfileConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROFILE__")


class Job(BaseModel):
    wait_time_sec: int = 10
    processing_interval_sec: int = 5
    processing_batch_size: int = 5
    processing_timeout_sec: int = 300


class JobConfig(BaseSettings):
    settings: Job = Job()
    model_config = SettingsConfigDict(env_prefix="JOB__")


class CorsConfig(BaseSettings):
    allow_origins: list[str] = Field(default_factory=list)
    model_config = SettingsConfigDict(env_prefix="CORS_")


class MinioConfig(BaseSettings):
    endpoint: str = Field(default_factory=str)
    access_key: str = Field(default_factory=str)
    secret_key: str = Field(default_factory=str)
    bucket: str = Field(default_factory=str)
    region: str = Field(default_factory=str)
    secure: bool = Field(default_factory=bool)
    public_endpoint: str = Field(default_factory=str)
    retry_attempts: int = Field(default_factory=int)
    retry_backoff: float = Field(default_factory=float)
    presign_expiry: int = Field(default_factory=int)
    model_config = SettingsConfigDict(env_prefix="MINIO__")


class Redis(BaseModel):
    use_ssl: bool = False
    decode_responses: bool = True
    health_check_interval: int = 30


class RedisConfig(BaseSettings):
    enabled: bool = Field(default_factory=bool)
    host: str = Field(default_factory=str)
    port: int = Field(default_factory=int)
    db: int = Field(default_factory=int)
    password: str = Field(default_factory=str)
    session_prefix: str = Field(default_factory=str)
    session_ttl_seconds: int = Field(default_factory=int)
    cache_prefix: str = Field(default_factory=str)
    cache_default_ttl_seconds: int = Field(default_factory=int)
    profile_cache_ttl_seconds: int = Field(default_factory=int)
    settings: Redis = Redis()

    @property
    def dsn(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        scheme = "rediss" if self.settings.use_ssl else "redis"
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


class Sessions(BaseModel):
    encryption_key: Optional[str] = None
    backend: str = "redis"
    sqlite_db_path: Optional[str] = None


class SessionsConfig(BaseSettings):
    settings: Sessions = Sessions()
    model_config = SettingsConfigDict(env_prefix="SESSIONS__")


class StorageConfig(BaseSettings):
    root: str = Field(default_factory=str)
    backend: str = Field(default_factory=str)  # "local" or "minio"
    model_config = SettingsConfigDict(env_prefix="STORAGE__")


class File(BaseModel):
    allowed_extensions: list[str] = Field(default_factory=lambda: [".png", ".jpg", ".jpeg"])
    max_file_size_byte: int = 2_000_000  # 2 MB


class FileConfig(BaseSettings):
    settings: File = File()
    model_config = SettingsConfigDict(env_prefix="FILE__")


class Celery(BaseModel):
    chat_retention_days: int = 365
    

class CeleryConfig(BaseSettings):
    broker_url: str = Field(default_factory=str)
    result_backend: str = Field(default_factory=str)
    queues: str = Field(default_factory=str)
    settings: Celery = Celery()
    model_config = SettingsConfigDict(env_prefix="CELERY__")


class Agents(BaseModel):
    agents_two_phase: list[str] = Field(default_factory=list)


class AgentsConfig(BaseSettings):
    settings: Agents = Agents()
    llm_provider: str = "auto"
    max_turns: int = Field(default_factory=int)
    chat_history_messages_limit: int = 8
    max_context_chars: int = 12000
    mem0_api_key: str = Field(default_factory=str)
    mem0_app_id: str = "gpthub"
    proxy_host: str = Field(default_factory=str)
    proxy_port: int | None = None
    proxy_user: str = Field(default_factory=str)
    proxy_pass: str = Field(default_factory=str)
    mws_api_key: str = Field(default_factory=str)
    mws_base_url: str = Field(default_factory=str)
    mws_timeout_sec: float = 20.0
    mws_models_cache_ttl_sec: int = 180
    openai_api_key: str = Field(default_factory=str)
    openai_base_url: str = Field(default_factory=str)
    openrouter_api_key: str = Field(default_factory=str)
    openrouter_base_url: str = Field(default_factory=str)
    openrouter_timeout_sec: float = 20.0
    openrouter_models_cache_ttl_sec: int = 180
    model_config = SettingsConfigDict(env_prefix="AGENTS__")

    @field_validator("proxy_port", mode="before")
    @classmethod
    def _normalize_proxy_port(cls, value):
        if value in (None, ""):
            return None
        return value

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _normalize_llm_provider(cls, value):
        provider = str(value or "auto").strip().lower()
        if provider not in {"auto", "mws", "openai", "openrouter"}:
            return "auto"
        return provider

    @field_validator("chat_history_messages_limit", "max_context_chars", mode="before")
    @classmethod
    def _normalize_positive_int(cls, value):
        if value in (None, ""):
            return 0
        parsed = int(value)
        return max(parsed, 0)



class ChatWs(BaseModel):
    max_replay: int = 200
    max_claim: int = 100
    pel_min_idle_ms: int = 60_000
    heartbeat_interval: int = 5


class ChatWsConfig(BaseSettings):
    settings: ChatWs = ChatWs()
    model_config = SettingsConfigDict(env_prefix="CHAT_WS__")


class Config(BaseSettings):

    service: ServiceConfig = Field(default_factory=ServiceConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    profile: ProfileConfig = Field(default_factory=ProfileConfig)
    pg: PgConfig = Field(default_factory=PgConfig)
    job: JobConfig = Field(default_factory=JobConfig)
    cors: CorsConfig = Field(default_factory=CorsConfig)
    minio: MinioConfig = Field(default_factory=MinioConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    sessions: SessionsConfig = Field(default_factory=SessionsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    file: FileConfig = Field(default_factory=FileConfig)
    celery: CeleryConfig = Field(default_factory=CeleryConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    chat_ws: ChatWsConfig = Field(default_factory=ChatWsConfig)

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
    )


def _get_config() -> Config:
    config = Config()
    return config


def redact_config_for_logging(config: Config) -> dict:
    return {
        "service": {
            "name": config.service.name,
            "server_port": config.service.server_port,
        },
        "auth": {
            "auth_mode": config.auth.auth_mode,
        },
        "storage": {
            "backend": config.storage.backend,
        },
    }

config = _get_config()
