from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text


_ANONYMOUS_USER_IDS = {
    "",
    "none",
    "null",
    "anon",
    "anonymous",
    "00000000-0000-0000-0000-000000000000",
}


class ChatWorkerRepository:
    @staticmethod
    def _is_memory_eligible_user(user_id: str | None) -> bool:
        if user_id is None:
            return False
        normalized = str(user_id).strip().lower()
        return normalized not in _ANONYMOUS_USER_IDS

    @staticmethod
    def _normalize_user_uuid(user_id: str | None) -> str | None:
        if user_id is None:
            return None
        value = str(user_id).strip()
        if not value or value.lower() in _ANONYMOUS_USER_IDS:
            return None
        try:
            return str(UUID(value))
        except Exception:
            return None

    async def resolve_memory_user(self, *, db_session: Any, user_id: Any, thread_id: str) -> str | None:
        raw_user_id = str(user_id).strip() if user_id is not None else None
        if self._is_memory_eligible_user(raw_user_id):
            return raw_user_id
        if not thread_id:
            return None
        owner_res = await db_session.execute(
            text("SELECT user_id FROM profile.chat_threads WHERE thread_id = :thread_id LIMIT 1"),
            {"thread_id": thread_id},
        )
        owner_user_id = owner_res.scalar_one_or_none()
        owner_str = str(owner_user_id).strip() if owner_user_id is not None else None
        if self._is_memory_eligible_user(owner_str):
            return owner_str
        return None

    async def restore_thread_history(
        self,
        *,
        db_session: Any,
        thread_id: str,
        session_data: dict[str, Any] | None,
        history_limit: int,
    ) -> list[dict[str, Any]]:
        def normalize_role(raw_role: Any) -> str:
            role = str(raw_role or "").strip().lower()
            return "assistant" if role == "agent" else role

        restored_items: list[dict[str, Any]] = []
        raw_history = (session_data or {}).get("history") if isinstance(session_data, dict) else None

        if isinstance(raw_history, list):
            for item in raw_history[-history_limit:]:
                if not isinstance(item, dict):
                    continue
                role = normalize_role(item.get("role"))
                if role not in {"user", "assistant", "system"}:
                    continue
                content = str(item.get("content") or "").strip()
                if not content:
                    continue
                restored_items.append(
                    {
                        "role": role,
                        "content": content,
                        "ts": float(item.get("ts") or datetime.now(timezone.utc).timestamp()),
                    }
                )

        if restored_items:
            return restored_items

        res = await db_session.execute(
            text(
                """
                SELECT m.sender, m.content, m.created_at
                FROM profile.chat_messages m
                JOIN profile.chat_threads t ON t.id = m.thread_id
                WHERE t.thread_id = :thread_id
                ORDER BY m.created_at DESC
                LIMIT :lim
                """
            ),
            {"thread_id": thread_id, "lim": max(int(history_limit), 1)},
        )
        rows = list(res.fetchall())
        rows.reverse()

        for sender, content, created_at in rows:
            role = normalize_role(sender)
            if role not in {"user", "assistant", "system"}:
                continue
            txt = str(content or "").strip()
            if not txt:
                continue
            try:
                ts = float(created_at.timestamp()) if created_at is not None else datetime.now(timezone.utc).timestamp()
            except Exception:
                ts = datetime.now(timezone.utc).timestamp()
            restored_items.append({"role": role, "content": txt, "ts": ts})

        return restored_items

    async def persist_turn(
        self,
        *,
        db_session: Any,
        thread_id: str,
        user_text: str,
        assistant_text: str,
        user_id: str | None,
    ) -> bool:
        normalized_uid = self._normalize_user_uuid(user_id)

        thread_res = await db_session.execute(
            text("SELECT id FROM profile.chat_threads WHERE thread_id = :thread_id LIMIT 1"),
            {"thread_id": thread_id},
        )
        row = thread_res.first()
        if not row:
            create_res = await db_session.execute(
                text(
                    """
                    INSERT INTO profile.chat_threads (thread_id, user_id, title, created_at, updated_at)
                    VALUES (:thread_id, :user_id, :title, NOW(), NOW())
                    ON CONFLICT (thread_id)
                    DO UPDATE SET updated_at = NOW()
                    RETURNING id
                    """
                ),
                {
                    "thread_id": thread_id,
                    "user_id": normalized_uid,
                    "title": "Chat",
                },
            )
            row = create_res.first()

        if not row:
            return False

        thread_pk = row[0]

        if str(user_text or "").strip():
            await db_session.execute(
                text(
                    """
                    INSERT INTO profile.chat_messages (message_id, thread_id, user_id, sender, content, created_at)
                    VALUES (:mid, :tpk, :uid, :sender, :content, NOW())
                    """
                ),
                {
                    "mid": str(uuid4()),
                    "tpk": thread_pk,
                    "uid": normalized_uid,
                    "sender": "user",
                    "content": str(user_text),
                },
            )

        if str(assistant_text or "").strip():
            await db_session.execute(
                text(
                    """
                    INSERT INTO profile.chat_messages (message_id, thread_id, user_id, sender, content, created_at)
                    VALUES (:mid, :tpk, :uid, :sender, :content, NOW())
                    """
                ),
                {
                    "mid": str(uuid4()),
                    "tpk": thread_pk,
                    "uid": None,
                    "sender": "assistant",
                    "content": str(assistant_text),
                },
            )

        return True
