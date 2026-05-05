from fastapi import Cookie

from service.models.auth_models import AuthProfile
from service.security import AuthValidator
from service.settings import config

_validator = AuthValidator(config.auth)


def check_auth(auth_token: str = Cookie(None)) -> AuthProfile:
    return _validator.validate_http_jwt(auth_token)
