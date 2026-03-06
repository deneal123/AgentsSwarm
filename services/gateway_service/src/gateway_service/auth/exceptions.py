"""
Пользовательские исключения для слоя аутентификации и авторизации.
Обрабатываются глобальным exception handler в main.py.
"""

from __future__ import annotations


class AuthError(Exception):
    """Ошибка аутентификации (401)."""

    def __init__(self, message: str = "Could not validate credentials") -> None:
        self.message = message
        super().__init__(message)


class TokenExpiredError(AuthError):
    """Токен истёк (401)."""

    def __init__(self) -> None:
        super().__init__("Token has expired")


class TokenBlacklistedError(AuthError):
    """Токен отозван/в blacklist (401)."""

    def __init__(self) -> None:
        super().__init__("Token has been revoked")


class PermissionDeniedError(Exception):
    """Недостаточно прав (403)."""

    def __init__(self, required_roles: list[str] | None = None) -> None:
        roles_str = ", ".join(required_roles) if required_roles else "higher"
        self.message = f"Access denied. Required role(s): {roles_str}"
        super().__init__(self.message)


class UserNotFoundError(Exception):
    """Пользователь не найден (404)."""

    def __init__(self, identifier: str = "") -> None:
        self.message = f"User not found: {identifier}" if identifier else "User not found"
        super().__init__(self.message)


class UserAlreadyExistsError(Exception):
    """Пользователь с таким именем/email уже существует (409)."""

    def __init__(self, field: str = "username") -> None:
        self.message = f"User with this {field} already exists"
        super().__init__(self.message)


class InvalidCredentialsError(AuthError):
    """Неверный логин или пароль (401)."""

    def __init__(self) -> None:
        super().__init__("Invalid username or password")
