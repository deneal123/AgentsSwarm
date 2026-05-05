import pytest

from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

from service.main import app
from tests.test_helpers import FakeDBSession, FakeConnector


@pytest.mark.asyncio
async def test_create_thread_persists(monkeypatch):
    # prepare fake session that records executed SQL
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    fake_session = FakeDBSession(first_map={"INSERT INTO profile.chat_threads": (now,)})
    fake_connector = FakeConnector(fake_session)

    # monkeypatch PgConnector to return our fake connector
    import service.infrastructure.database.postgresql as pgmod

    monkeypatch.setattr(pgmod, "PgConnector", lambda config, force_new=False: fake_connector)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/chats/", json={"user_id": 123, "title": "My thread"})

    assert resp.status_code == 201
    # ensure DB insert was executed and commit was called
    executed = "\n".join(s for s, _ in fake_session.executed)
    assert "INSERT INTO profile.chat_threads" in executed
    assert fake_session._committed is True
    body = resp.json()
    assert "created_at" in body and isinstance(body["created_at"], str) and body["created_at"] != ""


@pytest.mark.asyncio
async def test_get_thread_messages_returns_rows(monkeypatch):
    # prepare fake session that returns rows for SELECT
    # first SELECT to resolve thread id
    fake_session = FakeDBSession(
        first_map={"SELECT id FROM profile.chat_threads": (1,)},
        all_map={
            "SELECT sender, content, created_at FROM profile.chat_messages": [
                ("user", "hello", None),
            ],
        },
    )
    fake_connector = FakeConnector(fake_session)

    import service.infrastructure.database.postgresql as pgmod

    monkeypatch.setattr(pgmod, "PgConnector", lambda config, force_new=False: fake_connector)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/chats/test-thread-id")

    assert resp.status_code == 200
    body = resp.json()
    assert body["thread_id"] == "test-thread-id"
    assert isinstance(body["messages"], list)

# EOF
