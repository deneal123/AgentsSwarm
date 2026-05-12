from datetime import datetime

import pytest

from service.shared.repositories.exceptions import RepositoryNotFoundError
from service.services.chat.persistence.chat_persistence_service import ChatPersistenceService


class _Repo:
    async def create_thread(self, user_id, title, thread_id=None):
        return "t1", datetime(2025, 1, 1)

    async def get_thread_pk(self, thread_id):
        return 10 if thread_id == "t1" else None

    async def insert_message(self, thread_pk, sender, content, user_id):
        return None

    async def fetch_messages(self, thread_pk, limit, offset):
        return [("user", "hello", datetime(2025, 1, 1))]

    async def list_threads(self, user_id, limit, offset):
        return [("t1", "title", datetime(2025, 1, 1), datetime(2025, 1, 2))]

    async def delete_thread(self, thread_id):
        return thread_id == "t1"


@pytest.mark.asyncio
async def test_create_thread() -> None:
    service = ChatPersistenceService(repository=_Repo())
    result = await service.create_thread(user_id=1, title="A")
    assert result["thread_id"] == "t1"
    assert result["created_at"] == "2025-01-01T00:00:00"


@pytest.mark.asyncio
async def test_get_messages_not_found() -> None:
    service = ChatPersistenceService(repository=_Repo())
    with pytest.raises(RepositoryNotFoundError):
        await service.get_messages("missing")
