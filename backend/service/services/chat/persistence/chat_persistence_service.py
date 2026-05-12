from datetime import datetime
from typing import Any

from service.shared.repositories.exceptions import RepositoryNotFoundError


class ChatPersistenceService:
    def __init__(self, repository=None):
        if repository is None:
            from service.services.chat.persistence.chat_repository import ChatRepository

            self.repo = ChatRepository()
        else:
            self.repo = repository

    async def create_thread(self, user_id: str | int | None, title: str | None, thread_id: str | None = None) -> dict[str, Any]:
        tid, created_at = await self.repo.create_thread(user_id=user_id, title=title, thread_id=thread_id)
        created_iso = None
        if created_at is not None:
            created_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
        return {"thread_id": tid, "title": title, "created_at": created_iso}

    async def persist_messages(self, thread_id: str, user_text: str, agent_reply: str, user_id: str | int | None) -> None:
        thread_pk = await self.repo.get_thread_pk(thread_id)
        if thread_pk is None:
            return
        await self.repo.insert_message(thread_pk=thread_pk, sender="user", content=user_text, user_id=user_id)
        await self.repo.insert_message(thread_pk=thread_pk, sender="agent", content=agent_reply, user_id=None)

    async def get_messages(self, thread_id: str, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        if page < 1 or per_page < 1 or per_page > 500:
            raise ValueError("Invalid pagination parameters")

        offset = (page - 1) * per_page
        thread_pk = await self.repo.get_thread_pk(thread_id)
        if thread_pk is None:
            raise RepositoryNotFoundError("Thread not found")

        rows = await self.repo.fetch_messages(thread_pk=thread_pk, limit=per_page, offset=offset)
        messages = []
        for row in rows:
            created = row[2]
            created_iso = created.isoformat() if isinstance(created, datetime) else str(created) if created is not None else None
            messages.append({"sender": row[0], "content": row[1], "created_at": created_iso})
        return {"thread_id": thread_id, "page": page, "per_page": per_page, "messages": messages}

    async def list_threads(self, user_id: str | int | None = None, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        if page < 1 or per_page < 1 or per_page > 500:
            raise ValueError("Invalid pagination parameters")
        offset = (page - 1) * per_page
        rows = await self.repo.list_threads(user_id=user_id, limit=per_page, offset=offset)
        threads = []
        for row in rows:
            created = row[2]
            updated = row[3]
            threads.append(
                {
                    "thread_id": row[0],
                    "title": row[1],
                    "created_at": created.isoformat() if hasattr(created, "isoformat") else None,
                    "updated_at": updated.isoformat() if hasattr(updated, "isoformat") else None,
                }
            )
        return {"page": page, "per_page": per_page, "threads": threads}

    async def delete_thread(self, thread_id: str) -> bool:
        return bool(await self.repo.delete_thread(thread_id))
