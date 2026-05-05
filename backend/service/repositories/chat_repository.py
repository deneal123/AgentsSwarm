import logging
from typing import List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import text

import service.infrastructure.database.postgresql as pgmod
from service.settings import config

logger = logging.getLogger(__name__)


class ChatRepository:
    """Repository encapsulating DB access for chat threads and messages.

    Uses PgConnector internally by default but accepts a connector replacement in tests.
    """

    def __init__(self, connector=None):
        self._connector = connector

    def _get_connector(self):
        if self._connector is not None:
            return self._connector
        return pgmod.PgConnector(config.pg)

    async def create_thread(self, user_id: Optional[int], title: Optional[str], thread_id: Optional[str] = None) -> str:
        thread_uuid = thread_id or str(uuid4())
        connector = self._get_connector()
        async with connector.get_session_context() as session:
            # Use RETURNING created_at so callers can return a proper timestamp
            res = await session.execute(
                text(
                    "INSERT INTO profile.chat_threads (thread_id, user_id, title, created_at, updated_at) "
                    "VALUES (:thread_id, :user_id, :title, NOW(), NOW()) RETURNING created_at"
                ),
                {"thread_id": thread_uuid, "user_id": user_id, "title": title},
            )
            # Attempt to fetch returned created_at; fall back to selecting it explicitly later
            row = res.first()
            created_at = row[0] if row else None
            await session.commit()
        # Return a tuple (thread_uuid, created_at) so callers can decide how to format
        return thread_uuid, created_at

    async def get_thread_pk(self, thread_id: str) -> Optional[int]:
        connector = self._get_connector()
        async with connector.get_session_context() as session:
            # SQLAlchemy 2.0 requires textual SQL to be wrapped with text(...)
            res = await session.execute(
                text("SELECT id FROM profile.chat_threads WHERE thread_id = :thread_id"),
                {"thread_id": thread_id},
            )
            row = res.first()
            return row[0] if row else None

    async def insert_message(
        self,
        thread_pk: int,
        sender: str,
        content: str,
        message_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> None:
        connector = self._get_connector()
        async with connector.get_session_context() as session:
            await session.execute(
                text(
                    "INSERT INTO profile.chat_messages (message_id, thread_id, user_id, sender, content, created_at) "
                    "VALUES (:mid, :tpk, :uid, :sender, :content, NOW())"
                ),
                {
                    "mid": message_id or str(uuid4()),
                    "tpk": thread_pk,
                    "uid": user_id,
                    "sender": sender,
                    "content": content,
                },
            )
            await session.commit()

    async def fetch_messages(self, thread_pk: int, limit: int, offset: int) -> List[Tuple[str, str, Optional[str]]]:
        connector = self._get_connector()
        async with connector.get_session_context() as session:
            res = await session.execute(
                text(
                    "SELECT sender, content, created_at FROM profile.chat_messages "
                    "WHERE thread_id = :tpk ORDER BY created_at LIMIT :lim OFFSET :off"
                ),
                {"tpk": thread_pk, "lim": limit, "off": offset},
            )
            return res.fetchall()

    async def list_threads(self, user_id: Optional[int], limit: int, offset: int):
        connector = self._get_connector()
        async with connector.get_session_context() as session:
            if user_id is None:
                res = await session.execute(
                    text(
                        "SELECT thread_id, title, created_at, updated_at FROM profile.chat_threads ORDER BY updated_at DESC NULLS LAST LIMIT :lim OFFSET :off"
                    ),
                    {"lim": limit, "off": offset},
                )
            else:
                res = await session.execute(
                    text(
                        "SELECT thread_id, title, created_at, updated_at FROM profile.chat_threads WHERE user_id = :uid ORDER BY updated_at DESC NULLS LAST LIMIT :lim OFFSET :off"
                    ),
                    {"lim": limit, "off": offset, "uid": user_id},
                )
            return res.fetchall()

    async def delete_thread(self, thread_id: str) -> int:
        """Delete thread by external thread_id. Returns number of rows deleted from chat_threads."""
        connector = self._get_connector()
        async with connector.get_session_context() as session:
            # Delete thread (messages cascade via FK)
            res = await session.execute(
                text("DELETE FROM profile.chat_threads WHERE thread_id = :tid RETURNING id"),
                {"tid": thread_id},
            )
            await session.commit()
            # rowcount is not always available; inspect `res.first()`
            first = res.first()
            return 1 if first else 0
