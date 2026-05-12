import pytest

from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

from service.main import app
from service.composition.state import get_chat_application_service


@pytest.mark.asyncio
async def test_create_thread_persists():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    created = {"called": False}

    class _FakeSvc:
        async def create_thread(self, user_id, title):
            created["called"] = True
            return {"thread_id": "t-123", "title": title, "created_at": now.isoformat()}

    app.dependency_overrides[get_chat_application_service] = lambda: _FakeSvc()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/chats/", json={"user_id": 123, "title": "My thread"})

        assert resp.status_code == 201
        assert created["called"] is True
        body = resp.json()
        assert "created_at" in body and isinstance(body["created_at"], str) and body["created_at"] != ""
    finally:
        app.dependency_overrides.pop(get_chat_application_service, None)


@pytest.mark.asyncio
async def test_get_thread_messages_returns_rows():
    class _FakeSvc:
        async def get_thread_messages(self, thread_id, page, per_page):
            return {
                "thread_id": thread_id,
                "messages": [{"sender": "user", "content": "hello", "created_at": None}],
                "page": page,
                "per_page": per_page,
            }

    app.dependency_overrides[get_chat_application_service] = lambda: _FakeSvc()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/chats/test-thread-id")

        assert resp.status_code == 200
        body = resp.json()
        assert body["thread_id"] == "test-thread-id"
        assert isinstance(body["messages"], list)
    finally:
        app.dependency_overrides.pop(get_chat_application_service, None)
