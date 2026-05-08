import pytest
from pydantic import ValidationError

from service.settings import AuthConfig


def test_auth_config_fails_with_empty_secret_in_prod():
    with pytest.raises(ValidationError):
        AuthConfig(
            auth_mode="prod",
            secret="",
            algorithm="HS256",
            jwt_exp_hours=24,
        )


def test_auth_config_allows_explicit_dev_defaults():
    config = AuthConfig(
        auth_mode="dev",
        secret="dev-insecure-secret-change-me",
        algorithm="HS256",
        jwt_exp_hours=24,
    )

    assert config.secret == "dev-insecure-secret-change-me"
    assert config.algorithm == "HS256"
    assert config.jwt_exp_hours == 24
