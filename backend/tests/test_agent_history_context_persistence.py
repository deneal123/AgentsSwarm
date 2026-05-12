from datetime import UTC, datetime

import pytest


class _FakePseudoSession:
    def __init__(self):
        self.items = []

    async def add_items(self, items):
        self.items.extend(items)


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeDBSessionForRestore:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, *_args, **_kwargs):
        return _FakeResult(self.rows)


class _FakeDBSessionForPersist:
    def __init__(self, *, thread_exists: bool = True):
        self.calls = []
        self.thread_exists = thread_exists
        self.thread_id = 123

    async def execute(self, query, params):
        sql = str(query)
        self.calls.append((sql, params))
        if "SELECT id FROM profile.chat_threads" in sql:
            return _FakeResult([(self.thread_id,)]) if self.thread_exists else _FakeResult([])
        if "INSERT INTO profile.chat_threads" in sql:
            self.thread_exists = True
            return _FakeResult([(self.thread_id,)])
        return _FakeResult([])


@pytest.mark.asyncio
async def test_restore_pseudo_history_maps_agent_role_from_explicit_history() -> None:
    from service.infrastructure.messaging.tasks import _restore_pseudo_session_history

    pseudo = _FakePseudoSession()
    db_session = _FakeDBSessionForRestore([])

    restored = await _restore_pseudo_session_history(
        pseudo_session=pseudo,
        db_session=db_session,
        thread_id="t-1",
        session_data={
            "history": [
                {"role": "user", "content": "Меня зовут Данил"},
                {"role": "agent", "content": "Приятно познакомиться, Данил"},
            ]
        },
        history_limit=10,
    )

    assert restored == 2
    assert pseudo.items[0]["role"] == "user"
    assert pseudo.items[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_restore_pseudo_history_maps_agent_role_from_db_rows() -> None:
    from service.infrastructure.messaging.tasks import _restore_pseudo_session_history

    now = datetime.now(UTC)
    rows = [
        ("agent", "Помню ваше имя", now),
        ("user", "Как меня зовут?", now),
    ]

    pseudo = _FakePseudoSession()
    db_session = _FakeDBSessionForRestore(rows)

    restored = await _restore_pseudo_session_history(
        pseudo_session=pseudo,
        db_session=db_session,
        thread_id="t-2",
        session_data=None,
        history_limit=10,
    )

    assert restored == 2
    assert {item["role"] for item in pseudo.items} == {"assistant", "user"}


@pytest.mark.asyncio
async def test_persist_chat_turn_writes_user_and_assistant_messages() -> None:
    from service.infrastructure.messaging.tasks import _persist_chat_turn

    db_session = _FakeDBSessionForPersist()

    ok = await _persist_chat_turn(
        db_session=db_session,
        thread_id="thread-abc",
        user_text="Меня зовут Данил",
        assistant_text="Принято, Данил",
        user_id="00000000-0000-0000-0000-000000000111",
    )

    assert ok is True
    insert_calls = [c for c in db_session.calls if "INSERT INTO profile.chat_messages" in c[0]]
    assert len(insert_calls) == 2
    assert insert_calls[0][1]["sender"] == "user"
    assert insert_calls[1][1]["sender"] == "assistant"


@pytest.mark.asyncio
async def test_persist_chat_turn_creates_thread_when_missing() -> None:
    from service.infrastructure.messaging.tasks import _persist_chat_turn

    db_session = _FakeDBSessionForPersist(thread_exists=False)

    ok = await _persist_chat_turn(
        db_session=db_session,
        thread_id="thread-missing",
        user_text="Меня зовут Данил",
        assistant_text="Запомнил",
        user_id="00000000-0000-0000-0000-000000000111",
    )

    assert ok is True
    assert any("INSERT INTO profile.chat_threads" in sql for sql, _ in db_session.calls)
    insert_msg_calls = [c for c in db_session.calls if "INSERT INTO profile.chat_messages" in c[0]]
    assert len(insert_msg_calls) == 2


@pytest.mark.asyncio
async def test_persist_chat_turn_uses_null_user_id_for_anonymous_user() -> None:
    from service.infrastructure.messaging.tasks import _persist_chat_turn

    db_session = _FakeDBSessionForPersist()

    ok = await _persist_chat_turn(
        db_session=db_session,
        thread_id="thread-anon",
        user_text="Меня зовут Данил",
        assistant_text="Запомнил",
        user_id="00000000-0000-0000-0000-000000000000",
    )

    assert ok is True
    insert_msg_calls = [c for c in db_session.calls if "INSERT INTO profile.chat_messages" in c[0]]
    assert len(insert_msg_calls) == 2
    assert insert_msg_calls[0][1]["sender"] == "user"
    assert insert_msg_calls[0][1]["uid"] is None
