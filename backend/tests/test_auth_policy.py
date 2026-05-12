import pytest

from service.shared.security.auth_validation import AuthValidator
from service.settings import AuthConfig


class FakeWebSocket:
    def __init__(self, *, query_token=None, auth_header=None, cookies=None):
        self.query_params = {"token": query_token} if query_token is not None else {}
        self.headers = {"authorization": auth_header} if auth_header else {}
        self.cookies = cookies or {}


class FakeSessionStore:
    async def get_session_by_token(self, token):
        if token == "good-token":
            return {"id": "s-1", "user_id": "u-1"}
        return None


@pytest.mark.asyncio
async def test_prod_policy_blocks_legacy_query_token():
    validator = AuthValidator(
        AuthConfig(
            auth_mode="prod",
            secret="super-secret-key",
            algorithm="HS256",
            jwt_exp_hours=24,
            ws_auth_allowlist_prod=["jwt_cookie"],
            enable_legacy_ws_token_auth=True,
        )
    )
    ws = FakeWebSocket(query_token="good-token")
    session = await validator.authenticate_websocket(ws, FakeSessionStore())
    assert session is None


@pytest.mark.asyncio
async def test_prod_policy_blocks_dev_test_token_even_when_feature_enabled():
    validator = AuthValidator(
        AuthConfig(
            auth_mode="prod",
            secret="super-secret-key",
            algorithm="HS256",
            jwt_exp_hours=24,
            ws_auth_allowlist_prod=["jwt_cookie", "query_token"],
            enable_legacy_ws_token_auth=True,
            enable_dev_test_token=True,
            enforce_prod_runtime_auth_guard=True,
        )
    )
    ws = FakeWebSocket(query_token="test-token")
    session = await validator.authenticate_websocket(ws, FakeSessionStore())
    assert session is None


@pytest.mark.asyncio
async def test_dev_policy_allows_legacy_token_when_flag_enabled():
    validator = AuthValidator(
        AuthConfig(
            auth_mode="dev",
            secret="super-secret-key",
            algorithm="HS256",
            jwt_exp_hours=24,
            ws_auth_allowlist_dev=["query_token"],
            enable_legacy_ws_token_auth=True,
        )
    )
    ws = FakeWebSocket(query_token="good-token")
    session = await validator.authenticate_websocket(ws, FakeSessionStore())
    assert session == {"id": "s-1", "user_id": "u-1"}


@pytest.mark.asyncio
async def test_dev_policy_blocks_legacy_token_when_feature_disabled():
    validator = AuthValidator(
        AuthConfig(
            auth_mode="dev",
            secret="super-secret-key",
            algorithm="HS256",
            jwt_exp_hours=24,
            ws_auth_allowlist_dev=["query_token"],
            enable_legacy_ws_token_auth=False,
        )
    )
    ws = FakeWebSocket(query_token="good-token")
    session = await validator.authenticate_websocket(ws, FakeSessionStore())
    assert session is None
