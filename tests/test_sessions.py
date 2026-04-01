import asyncio

import pytest

from orchestrator.services.sessions import SessionManager


@pytest.mark.asyncio
async def test_session_manager_history_and_cache_in_memory():
    sm = SessionManager()
    await sm.connect()

    await sm.update_session("t1", {"foo": "bar"})
    await sm.append_history("t1", "hello")
    await sm.set_last_robot("t1", "robot-1")
    await sm.cache_mcp_result("t1", "key", {"val": 1})

    sess = await sm.get_session("t1")
    assert sess["foo"] == "bar"
    assert sess["history"] == ["hello"]
    assert sess["last_robot_id"] == "robot-1"
    assert sess["mcp_cache"]["key"] == {"val": 1}

    await sm.clear_session("t1")
    assert await sm.get_session("t1") == {}


@pytest.mark.asyncio
async def test_session_manager_status_disabled_without_redis():
    sm = SessionManager()
    await sm.connect()
    assert sm.status in {"disabled", "ok", "error"}
