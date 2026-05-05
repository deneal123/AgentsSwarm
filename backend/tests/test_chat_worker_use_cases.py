from datetime import datetime, timezone

import pytest

from service.repositories.chat_worker_repository import ChatWorkerRepository
from service.services.chat_worker.services import ChatWorkerConversationService


class _FakePseudoSession:
    def __init__(self):
        self.items = []

    async def add_items(self, items):
        self.items.extend(items)


class _FakeResult:
    def __init__(self, rows=None, scalar_value=None):
        self._rows = rows or []
        self._scalar_value = scalar_value

    def fetchall(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self):
        return self._scalar_value


class _FakeDbSession:
    def __init__(self):
        self.calls = []
        self.thread_exists = True

    async def execute(self, query, params=None):
        sql = str(query)
        self.calls.append((sql, params))
        if "SELECT user_id FROM profile.chat_threads" in sql:
            return _FakeResult(scalar_value="thread-owner")
        if "SELECT m.sender" in sql:
            now = datetime.now(timezone.utc)
            return _FakeResult(rows=[("agent", "hello", now), ("user", "hi", now)])
        if "SELECT id FROM profile.chat_threads" in sql:
            return _FakeResult(rows=[(11,)]) if self.thread_exists else _FakeResult(rows=[])
        if "INSERT INTO profile.chat_threads" in sql:
            self.thread_exists = True
            return _FakeResult(rows=[(11,)])
        return _FakeResult(rows=[])


@pytest.mark.asyncio
async def test_use_case_resolve_memory_user_fallback_to_thread_owner():
    service = ChatWorkerConversationService(ChatWorkerRepository())
    db = _FakeDbSession()

    result = await service.resolve_memory_user(
        db_session=db,
        user_id="00000000-0000-0000-0000-000000000000",
        thread_id="thread-1",
    )

    assert result == "thread-owner"


@pytest.mark.asyncio
async def test_use_case_restore_thread_history_restores_items():
    service = ChatWorkerConversationService(ChatWorkerRepository())
    db = _FakeDbSession()
    pseudo = _FakePseudoSession()

    restored = await service.restore_thread_history(
        pseudo_session=pseudo,
        db_session=db,
        thread_id="thread-2",
        session_data=None,
        history_limit=10,
    )

    assert restored == 2
    assert pseudo.items[0]["role"] == "user"
    assert pseudo.items[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_use_case_persist_turn_writes_two_messages():
    service = ChatWorkerConversationService(ChatWorkerRepository())
    db = _FakeDbSession()

    ok = await service.persist_turn(
        db_session=db,
        thread_id="thread-3",
        user_text="hello",
        assistant_text="world",
        user_id="00000000-0000-0000-0000-000000000111",
    )

    assert ok is True
    inserts = [sql for sql, _ in db.calls if "INSERT INTO profile.chat_messages" in sql]
    assert len(inserts) == 2
