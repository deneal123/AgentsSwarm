import pytest

from service.services.agents.infrastructure.sessions import create_session, PseudoSession, SQLiteSession, RedisSession
from service.settings import config


def test_create_session_backend_sqlite(monkeypatch):
    config.sessions.backend = "sqlite"
    config.sessions.sqlite_db_path = ":memory:"  # sqlite in memory

    s = create_session("s_sqlite")
    assert isinstance(s, SQLiteSession)


def test_create_session_backend_pseudo(monkeypatch):
    config.sessions.backend = "pseudo"
    s = create_session("s_p")
    assert isinstance(s, PseudoSession)


def test_create_session_backend_redis(monkeypatch):
    config.sessions.backend = "redis"
    class FakeRedis:
        pass

    import service.container as di
    monkeypatch.setattr(di, "get", lambda name: FakeRedis())

    s = create_session("s_r")
    assert isinstance(s, RedisSession)
