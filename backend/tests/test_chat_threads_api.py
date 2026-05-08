import pytest
from httpx import AsyncClient, ASGITransport

from service.main import app
from service.services.chat.domain import chat_service


@pytest.mark.asyncio
async def test_list_threads_returns_threads(monkeypatch):
    async def fake_list_threads(self, user_id, page, per_page):
        return {"page": page, "per_page": per_page, "threads": [{"thread_id": "T1", "title": "Hello", "created_at": "2025-01-01T00:00:00Z", "updated_at": None}]}

    monkeypatch.setattr(chat_service.ChatService, "list_threads", fake_list_threads)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/chats/?page=1&per_page=10")

    assert r.status_code == 200
    data = r.json()
    assert data["threads"][0]["thread_id"] == "T1"


@pytest.mark.asyncio
async def test_delete_thread_returns_404_when_not_found(monkeypatch):
    async def fake_delete(self, thread_id):
        return False

    monkeypatch.setattr(chat_service.ChatService, "delete_thread", fake_delete)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.delete("/api/chats/UNKNOWN")

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_thread_returns_204_when_deleted(monkeypatch):
    async def fake_delete(self, thread_id):
        return True

    monkeypatch.setattr(chat_service.ChatService, "delete_thread", fake_delete)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.delete("/api/chats/T1")

    assert r.status_code == 204
