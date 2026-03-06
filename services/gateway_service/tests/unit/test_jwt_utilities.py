"""Unit tests for JWT utilities."""

import pytest
from gateway_service.auth.jwt import create_access_token, create_token_pair
from gateway_service.auth.schemas import UserRole
from gateway_service.config import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(  # type: ignore[call-arg]
        environment="development",
        jwt_secret="test-secret-key-minimum-32-chars-ok!",
        jwt_access_expire_minutes=5,
        jwt_refresh_expire_days=1,
    )


class TestJWT:
    """Tests for JWT utilities."""

    def test_create_access_token(self, test_settings: Settings) -> None:
        """Create access token returns a string."""
        token = create_access_token("user-123", UserRole.OPERATOR, test_settings)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_different_roles(self, test_settings: Settings) -> None:
        """Create access token for different roles."""
        token_admin = create_access_token("user-123", UserRole.ADMIN, test_settings)
        token_operator = create_access_token("user-123", UserRole.OPERATOR, test_settings)
        token_viewer = create_access_token("user-123", UserRole.VIEWER, test_settings)
        
        assert token_admin != token_operator
        assert token_operator != token_viewer

    def test_create_token_pair(self, test_settings: Settings) -> None:
        """Create token pair returns two strings."""
        access_token, refresh_token = create_token_pair("user-123", UserRole.OPERATOR, test_settings)
        
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        assert len(access_token) > 0
        assert len(refresh_token) > 0
        assert access_token != refresh_token

    def test_create_token_pair_different_for_users(self, test_settings: Settings) -> None:
        """Create token pair for different users returns different tokens."""
        access1, refresh1 = create_token_pair("user-1", UserRole.OPERATOR, test_settings)
        access2, refresh2 = create_token_pair("user-2", UserRole.OPERATOR, test_settings)
        
        assert access1 != access2
        assert refresh1 != refresh2
