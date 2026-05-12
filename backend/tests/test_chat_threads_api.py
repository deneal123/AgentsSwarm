import pytest
from httpx import AsyncClient, ASGITransport

from service.main import app
from service.composition.state import get_chat_application_service


@pytest.mark.asyncio
async def test_list_threads_returns_threads():
    class _FakeSvc:
        async def list_threads(self, user_id, page, per_page):
            return {"page": page, "per_page": per_page, "threads": [{"thread_id": "T1", "title": "Hello", "created_at": "2025-01-01T00:00:00Z", "updated_at": None}]}

    app.dependency_overrides[get_chat_application_service] = lambda: _FakeSvc()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/chats/?page=1&per_page=10")

        assert r.status_code == 200
        data = r.json()
        assert data["threads"][0]["thread_id"] == "T1"
    finally:
        app.dependency_overrides.pop(get_chat_application_service, None)


@pytest.mark.asyncio
async def test_delete_thread_returns_404_when_not_found():
    class _FakeSvc:
        async def delete_thread(self, thread_id):
            return False

    app.dependency_overrides[get_chat_application_service] = lambda: _FakeSvc()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.delete("/api/chats/UNKNOWN")

        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(get_chat_application_service, None)


@pytest.mark.asyncio
async def test_delete_thread_returns_204_when_deleted():
    class _FakeSvc:
        async def delete_thread(self, thread_id):
            return True

    app.dependency_overrides[get_chat_application_service] = lambda: _FakeSvc()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.delete("/api/chats/T1")

        assert r.status_code == 204
    finally:
        app.dependency_overrides.pop(get_chat_application_service, None)
