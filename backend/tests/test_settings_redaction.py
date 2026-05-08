from service.settings import Config, redact_config_for_logging


def test_redact_config_for_logging_returns_whitelisted_fields_only():
    config = Config()
    config.service.name = "svc"
    config.service.server_port = 8080
    config.auth.auth_mode = "prod"
    config.storage.backend = "minio"
    config.auth.secret = "super-secret"
    config.pg.password = "db-secret"
    config.minio.access_key = "access-key"
    config.minio.secret_key = "secret-key"
    config.redis.password = "redis-secret"
    config.agents.openai_api_key = "openai-secret"

    redacted = redact_config_for_logging(config)

    assert redacted == {
        "service": {"name": "svc", "server_port": 8080},
        "auth": {"auth_mode": "prod"},
        "storage": {"backend": "minio"},
    }

    dump = str(redacted)
    for value in [
        "super-secret",
        "db-secret",
        "access-key",
        "secret-key",
        "redis-secret",
        "openai-secret",
    ]:
        assert value not in dump
