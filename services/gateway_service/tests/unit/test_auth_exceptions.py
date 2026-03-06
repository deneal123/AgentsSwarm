"""
Unit tests for auth exceptions and other edge cases.
"""

import pytest
from gateway_service.auth.exceptions import (
    AuthError,
    TokenExpiredError,
    TokenBlacklistedError,
    PermissionDeniedError,
)


class TestAuthExceptions:
    """Tests for authentication exceptions"""

    def test_auth_error_creation(self):
        """AuthError can be created"""
        exc = AuthError("Invalid credentials")
        assert "Invalid credentials" in str(exc)
        assert isinstance(exc, Exception)

    def test_auth_error_default_message(self):
        """AuthError with default message"""
        exc = AuthError()
        assert exc.message == "Could not validate credentials"

    def test_token_expired_error(self):
        """TokenExpiredError creation"""
        exc = TokenExpiredError()
        assert "expired" in str(exc).lower()
        assert isinstance(exc, AuthError)

    def test_token_blacklisted_error(self):
        """TokenBlacklistedError creation"""
        exc = TokenBlacklistedError()
        assert "revoked" in str(exc).lower() or "blacklist" in str(exc).lower()
        assert isinstance(exc, AuthError)

    def test_permission_denied_error_no_roles(self):
        """PermissionDeniedError without required roles"""
        exc = PermissionDeniedError()
        assert exc is not None

    def test_permission_denied_error_with_roles(self):
        """PermissionDeniedError with required roles"""
        exc = PermissionDeniedError(required_roles=["admin", "operator"])
        assert exc is not None

    def test_exception_inheritance(self):
        """Auth exceptions inherit correctly"""
        assert issubclass(TokenExpiredError, AuthError)
        assert issubclass(TokenBlacklistedError, AuthError)
        assert issubclass(PermissionDeniedError, Exception)
