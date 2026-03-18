import os
from typing import Optional

import dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = dotenv.find_dotenv()
if ENV_FILE:
    try:
        dotenv.load_dotenv(ENV_FILE, override=False)
    except Exception:
        pass


LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL", "debug").upper()

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


# --------------------------------------------------------------------------------------------------

class CorsConfig(BaseSettings):
    """CORS configuration"""

    allow_origins: list[str] = Field(default_factory=list)
    
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="CORS__"
    )


class FastAPIConfig(BaseSettings):
    """FASTAPI app configuration"""

    service_name: str = "pushi-backend"
    description: str | None = None
    version: str = "v0.0.1"
    docs_url: str = "/docs"
    openapi_url: str = "/openapi.json"
    redoc_url: str = "/redoc"

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="FASTAPI__"
    )


class RateLimitConfig(BaseSettings):
    """RateLimitMiddleware configuration"""
    
    requests_per_minute: int = 60
    burst_limit: int = 10

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="RATELIMIT__"
    )


class PostgresqlConfig(BaseSettings):
    """Postgres configuration"""

    protocol: str = "postgresql+asyncpg"
    host: str = "postgres"
    port: int = 5432
    user: str | None = "postgres"
    password: str | None = "postgres"
    db: str = "main"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: float = 5.0
    db_pool_recycle: int = 3600
    db_pool_pre_ping: bool = True

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="POSTGRESQL__"
    )

    @property
    def dsn(self) -> str:
        return f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def dsn_safe(self) -> str:
        return f"{self.protocol}://{self.user}:***@{self.host}:{self.port}/{self.db}"


class AuthConfig(BaseSettings):
    """Auth configuration"""

    dev_mode: bool = False
    secret: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    jwt_exp_hours: int = 24
    refresh_token_exp_days: int = 30
    max_login_attempts: int = 5
    lockout_minutes: int = 15

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="AUTH__"
    )


class MinioConfig(BaseSettings):
    """MinIO/S3 storage configuration"""

    endpoint: str = "minio:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket: str = "pushi-files"
    region: str = "us-east-1"
    secure: bool = False
    public_endpoint: str = "http://localhost:9000"
    retry_attempts: int = 3
    retry_backoff: float = 0.5
    presign_expiry: int = 3600

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="MINIO__"
    )


class RedisConfig(BaseSettings):
    """Redis cache/session configuration"""

    enabled: bool = True
    host: str = "redis"
    port: int = 6379
    db: int = 0
    password: str | None = None
    use_ssl: bool = False
    decode_responses: bool = True
    health_check_interval: int = 30

    session_prefix: str = "session"
    session_ttl_seconds: int = 3600

    cache_prefix: str = "cache"
    cache_default_ttl_seconds: int = 300
    profile_cache_ttl_seconds: int = 900

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="REDIS__"
    )

    @property
    def dsn(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        scheme = "rediss" if self.use_ssl else "redis"
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


class TaskConfig(BaseSettings):
    """Task configuration with concurrency management"""

    # Timing and intervals
    wait_time_sec: int = 10
    processing_interval_sec: int = 5
    processing_batch_size: int = 5
    processing_timeout_sec: int = 300
    cleanup_retention_days: int = 30
    cleanup_interval_seconds: int = 3600
    dependency_check_interval_sec: int = 60
    retry_interval_seconds: int = 300
    retry_backoff_base: float = 2.0
    default_priority: int = 5
    max_retry_attempts: int = 6
    retry_backoff_cap_seconds: int = 3600

    # Concurrency management (Phase 1)
    # Maximum total threads available for all task types combined
    max_project_threads: int = 10
    
    # Default settings for tasks
    default_batch_size: int = 10
    default_max_parallel_batches: int = 3
    
    # Timeouts
    playground_timeout_seconds: int = 300  # 5 minutes
    pipeline_timeout_seconds: int = 3600   # 1 hour
    
    # Queue position check interval (seconds)
    queue_position_update_interval: int = 5

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="TASK__"
    )


class FileConfig(BaseSettings):
    """File upload and storage configuration"""

    max_size_mb: int = 10
    allowed_extensions: list[str] = Field(
        default_factory=lambda: [
            ".png",
            ".pdf",
            ".yaml",
            ".toml",
            ".xlsx"
        ]
    )
    scan_on_upload: bool = True
    optimize_images: bool = True
    image_max_width: int = 2048
    image_max_height: int = 2048
    image_quality: int = 85
    thumbnail_size: int = 150
    thumbnail_quality: int = 75
    thumbnail_folder: str = "thumbnails"
    storage_quota_mb: int = 512
    temporary_retention_days: int = 30
    temporary_cleanup_batch_size: int = 100

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="FILE__"
    )

    # environment variables are provided as comma-separated strings
    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def _split_allowed_extensions(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class SessionsConfig(BaseSettings):
    """Configuration for session handling (encryption, persistence)."""

    encryption_key: Optional[str] = None
    backend: str = "auto"
    sqlite_db_path: Optional[str] = None

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="SESSIONS__"
    )


class ServersConfig(BaseSettings):
    """Servers configuration"""

    service_nginx_port: int = 80
    service_backend_port: int = 8000
    service_frontend_port: int = 3000
    service_app_domain: str = '109.196.99.102'
    react_app_api_base_url: str = f'http://{service_app_domain}'
    react_app_ws_base_url: str = f'wss://{service_app_domain}'
    react_app_enable_admin_ui: bool = True
    admin_user_ids: list[str] = Field(
        default_factory=lambda: ["00000000-0000-0000-0000-000000000000"]
    )

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="SERVERS__"
    )

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


class StorageConfig(BaseSettings):
    """Storage configuration"""

    root: str = '/var/lib/app/storage'
    backend: str = 'local'

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="STORAGE__"
    )


# --------------------------------------------------------------------------------------------------


class Config(BaseSettings):
    fastapi_app: FastAPIConfig = Field(default_factory=FastAPIConfig)
    cors: CorsConfig = Field(default_factory=CorsConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    pg: PostgresqlConfig = Field(default_factory=PostgresqlConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    minio: MinioConfig = Field(default_factory=MinioConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    task: TaskConfig = Field(default_factory=TaskConfig)
    file: FileConfig = Field(default_factory=FileConfig)
    sessions: SessionsConfig = Field(default_factory=SessionsConfig)
    servers: ServersConfig = Field(default_factory=ServersConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)


def _get_config() -> Config:
    config = Config()
    return config


config = _get_config()
