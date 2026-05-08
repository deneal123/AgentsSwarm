"""Session backends — infrastructure implementations.

PseudoSession: in-memory (no external dependency).
RedisSession:  Redis-backed, requires configured Redis client.
SQLiteSession: SQLite-backed, for lightweight long-term storage.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import asyncio
import json
import logging

from cryptography.fernet import Fernet, InvalidToken
from service.services.agents.schemas.sessions import SessionItem

from service.settings import config as service_config
from service.infrastructure.secrets import secret_loader

logger = logging.getLogger(__name__)


def record_session_items_added(_session_id: str, _count: int) -> None:
    """Best-effort session metrics hook (no-op by default)."""
    return None


def record_session_length(_session_id: str, _length: int) -> None:
    """Best-effort session size gauge hook (no-op by default)."""
    return None


class PseudoSession:
    """In-memory session with optional TTL and max_items trimming."""

    def __init__(self, session_id: str, ttl_seconds: Optional[int] = None, max_items: Optional[int] = None):
        self.session_id = session_id
        self._items: List[Dict] = []
        self._lock = asyncio.Lock()
        self._ttl = ttl_seconds
        self._max_items = max_items

    async def get_items(self, limit: Optional[int] = None) -> List[Dict]:
        async with self._lock:
            items = list(self._items)

        if self._ttl is not None:
            cutoff = (datetime.now(timezone.utc).timestamp() - self._ttl)
            items = [it for it in items if float(it.get("ts", datetime.now(timezone.utc).timestamp())) >= cutoff]

        if limit is not None:
            items = items[-limit:]
        return items

    async def add_items(self, items: List[Dict]) -> None:
        async with self._lock:
            self._items.extend(items)
            if self._max_items is not None and len(self._items) > self._max_items:
                self._items = self._items[-self._max_items:]

    async def pop_item(self) -> Optional[Dict]:
        async with self._lock:
            if not self._items:
                return None
            item = self._items.pop()

        try:
            current_len = len(await self.get_items())
            record_session_length(self.session_id, current_len)
        except Exception:
            logger.debug("Failed to update session length metric after pop", exc_info=True)
        return item

    async def clear_session(self) -> None:
        async with self._lock:
            self._items.clear()
        record_session_length(self.session_id, 0)


class RedisSession:
    """Redis-backed conversation session.

    Stores messages in a Redis List at key: "{session_prefix}:agents:{session_id}".
    """

    def __init__(
        self,
        session_id: str,
        client: Optional[Any] = None,
        *,
        ttl_seconds: Optional[int] = None,
        max_items: Optional[int] = None,
        prefix: Optional[str] = None,
    ):
        try:
            from service.container import get_current_container
            if client is None:
                client = get_current_container().infra.redis_client
        except Exception:
            pass

        self.session_id = session_id
        self._client = client
        self._config = service_config.redis
        self._ttl = ttl_seconds or self._config.session_ttl_seconds
        self._max_items = max_items
        self._prefix = prefix or f"{self._config.session_prefix}:agents"

    def _key(self) -> str:
        return f"{self._prefix}:{self.session_id}"

    async def get_items(self, limit: Optional[int] = None) -> list[dict]:
        if self._client is None:
            raise RuntimeError("Redis client not configured for RedisSession")

        raw = await self._client.lrange(self._key(), 0, -1)
        items = []
        for item in raw:
            try:
                if getattr(self, "_encryption_key", None):
                    txt = _maybe_decrypt(item, getattr(self, "_encryption_key"))
                else:
                    txt = item.decode("utf-8") if isinstance(item, (bytes, bytearray)) else str(item)
                items.append(json.loads(txt))
            except Exception:
                logger.warning("Invalid JSON found in session list; skipping", exc_info=True)

        if limit is None:
            return items
        return items[-limit:]

    async def add_items(self, items: list[dict]) -> None:
        if self._client is None:
            raise RuntimeError("Redis client not configured for RedisSession")

        if not items:
            return

        payloads = [json.dumps(it, default=str) for it in items]
        await self._client.rpush(self._key(), *payloads)
        if self._max_items:
            await self._client.ltrim(self._key(), -self._max_items, -1)
        await self._client.expire(self._key(), max(int(self._ttl), 1))

    async def pop_item(self) -> Optional[dict]:
        if self._client is None:
            raise RuntimeError("Redis client not configured for RedisSession")

        raw = await self._client.rpop(self._key())
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON popped from session")
            return None
        finally:
            try:
                current_len = len(await self.get_items())
                record_session_length(self.session_id, current_len)
            except Exception:
                logger.debug("Failed to update session length metric after pop", exc_info=True)

    async def clear_session(self) -> None:
        if self._client is None:
            raise RuntimeError("Redis client not configured for RedisSession")
        await self._client.delete(self._key())
        record_session_length(self.session_id, 0)

    @classmethod
    def from_container(cls, session_id: str, max_items: Optional[int] = None, ttl_seconds: Optional[int] = None):
        from service.container import get_current_container

        client = get_current_container().infra.redis_client
        cfg = service_config.redis
        inst = cls(session_id, client=client, ttl_seconds=ttl_seconds or cfg.session_ttl_seconds, max_items=max_items)
        keycfg = getattr(service_config, "sessions", None)
        if keycfg and getattr(keycfg, "encryption_key", None):
            inst._encryption_key = keycfg.encryption_key.encode("utf-8")
        else:
            try:
                secret = secret_loader.get_encryption_key()
            except Exception:
                secret = None
            if secret:
                inst._encryption_key = secret.encode("utf-8")
        return inst


class SQLiteSession:
    """Simple SQLite-backed session for long-term storage."""

    def __init__(
        self,
        session_id: str,
        db_path: str = "sessions.db",
        *,
        max_items: Optional[int] = None,
        encryption_key: Optional[bytes] = None,
    ):
        import sqlite3

        self.session_id = session_id
        self._db_path = db_path
        self._max_items = max_items
        self._encryption_key = encryption_key
        if self._encryption_key is None:
            global_key = getattr(service_config, "sessions", None)
            if global_key and getattr(global_key, "encryption_key", None):
                self._encryption_key = getattr(global_key, "encryption_key").encode("utf-8")
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                ts REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    async def get_items(self, limit: Optional[int] = None) -> list[dict]:
        cur = self._conn.execute(
            "SELECT payload FROM sessions WHERE session_id = ? ORDER BY id ASC", (self.session_id,)
        )
        rows = cur.fetchall()
        items = []
        for (raw,) in rows:
            try:
                raw_json = _maybe_decrypt(raw, self._encryption_key)
                items.append(json.loads(raw_json))
            except Exception:
                logger.exception("Failed to decode row payload in SQLiteSession")
        if limit:
            return items[-limit:]
        return items

    async def add_items(self, items: list[dict]) -> None:
        validated = [SessionItem(**it).model_dump() for it in items]
        for it in validated:
            payload = json.dumps(it, default=str)
            enc = _maybe_encrypt(payload, self._encryption_key)
            self._conn.execute(
                "INSERT INTO sessions (session_id, payload, ts) VALUES (?, ?, ?)",
                (self.session_id, enc, it.get("ts", 0)),
            )
        self._conn.commit()
        if self._max_items:
            cur = self._conn.execute(
                "SELECT id FROM sessions WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (self.session_id, self._max_items),
            )
            keep = [r[0] for r in cur.fetchall()][::-1]
            if keep:
                self._conn.execute(
                    "DELETE FROM sessions WHERE session_id = ? AND id < ?",
                    (self.session_id, keep[0]),
                )
                self._conn.commit()
        record_session_items_added(self.session_id, len(validated))
        items_len = self._conn.execute(
            "SELECT COUNT(1) FROM sessions WHERE session_id = ?", (self.session_id,)
        ).fetchone()[0]
        record_session_length(self.session_id, items_len)

    async def pop_item(self) -> Optional[dict]:
        cur = self._conn.execute(
            "SELECT id, payload FROM sessions WHERE session_id = ? ORDER BY id DESC LIMIT 1",
            (self.session_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        row_id, raw = row
        try:
            raw_json = _maybe_decrypt(raw, self._encryption_key)
            payload = json.loads(raw_json)
        except Exception:
            logger.exception("Failed to decode row payload during pop")
            payload = None
        self._conn.execute("DELETE FROM sessions WHERE id = ?", (row_id,))
        self._conn.commit()
        record_session_length(
            self.session_id,
            self._conn.execute(
                "SELECT COUNT(1) FROM sessions WHERE session_id = ?", (self.session_id,)
            ).fetchone()[0],
        )
        return payload

    async def clear_session(self) -> None:
        self._conn.execute("DELETE FROM sessions WHERE session_id = ?", (self.session_id,))
        self._conn.commit()
        record_session_length(self.session_id, 0)

    def close(self):
        self._conn.close()

    @classmethod
    def from_file(cls, session_id: str, file_path: str, **kwargs):
        return cls(session_id, db_path=file_path, **kwargs)


# Validation helpers -------------------------------------------------------

def _validate_items(items: list[dict]) -> list[dict]:
    return [SessionItem(**it).model_dump() for it in items]


# Monkey-patch add_items on Redis/Pseudo to add validation + encryption -----

_ORIG_REDIS_ADD = RedisSession.add_items


async def _redis_add_items_with_validation(self, items: list[dict]) -> None:
    valid = _validate_items(items)
    payloads = [json.dumps(it, default=str) for it in valid]
    if getattr(self, "_encryption_key", None):
        payloads = [_maybe_encrypt(p, getattr(self, "_encryption_key")) for p in payloads]
    await self._client.rpush(self._key(), *payloads)
    if self._max_items:
        await self._client.ltrim(self._key(), -self._max_items, -1)
    await self._client.expire(self._key(), max(int(self._ttl), 1))
    record_session_items_added(self.session_id, len(valid))
    current_len = len(await self.get_items())
    record_session_length(self.session_id, current_len)


RedisSession.add_items = _redis_add_items_with_validation

_ORIG_PSEUDO_ADD = PseudoSession.add_items


async def _pseudo_add_items_with_validation(self, items: list[dict]) -> None:
    valid = _validate_items(items)
    async with self._lock:
        self._items.extend(valid)
        if self._max_items is not None and len(self._items) > self._max_items:
            self._items = self._items[-self._max_items:]
    record_session_items_added(self.session_id, len(valid))
    record_session_length(self.session_id, len(await self.get_items()))


PseudoSession.add_items = _pseudo_add_items_with_validation


# Convenience constructors -------------------------------------------------

def redis_session_with_key(session_id: str, key: Optional[bytes], **kwargs) -> RedisSession:
    s = RedisSession(session_id, **kwargs)
    s._encryption_key = key
    return s


def sqlite_session_with_key(session_id: str, file_path: str, key: Optional[bytes], **kwargs) -> SQLiteSession:
    return SQLiteSession(session_id, db_path=file_path, encryption_key=key, **kwargs)


def create_session(session_id: str, backend: Optional[str] = None, **kwargs):
    """Factory to create a session instance based on configuration.

    backend: 'redis' | 'sqlite' | 'pseudo' | 'auto'
    If 'auto' or None, prefer Redis if configured, else SQLite if db_path given, else PseudoSession.
    """
    b = backend or (
        getattr(service_config, "sessions", None)
        and getattr(service_config.sessions, "backend", None)
    )
    if not b or b == "auto":
        if getattr(service_config, "redis", None) and service_config.redis.enabled:
            b = "redis"
        elif getattr(service_config, "sessions", None) and getattr(service_config.sessions, "sqlite_db_path", None):
            b = "sqlite"
        else:
            b = "pseudo"

    b = b.lower()
    if b == "redis":
        return RedisSession.from_container(session_id, max_items=kwargs.get("max_items"))
    if b == "sqlite":
        path = kwargs.get("db_path") or (
            getattr(service_config, "sessions", None)
            and getattr(service_config.sessions, "sqlite_db_path", None)
        )
        return SQLiteSession.from_file(session_id, path or "sessions.db", max_items=kwargs.get("max_items"))

    return PseudoSession(session_id, ttl_seconds=kwargs.get("ttl_seconds"), max_items=kwargs.get("max_items"))


# Encryption helpers -------------------------------------------------------

def _maybe_encrypt(payload: str, key: Optional[bytes]) -> bytes:
    if not key:
        return payload.encode("utf-8")
    f = Fernet(key)
    return f.encrypt(payload.encode("utf-8"))


def _maybe_decrypt(raw: bytes | str, key: Optional[bytes]) -> str:
    if not key:
        return raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
    f = Fernet(key)
    try:
        return f.decrypt(raw if isinstance(raw, (bytes, bytearray)) else raw.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise ValueError("Decryption failed: invalid key or corrupt payload")
