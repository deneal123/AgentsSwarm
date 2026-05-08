import asyncio
import pytest

from service.services.agents.chat_agent import ChatAgent
from service.services.agents.infrastructure.sessions import PseudoSession


@pytest.mark.asyncio
async def test_chat_agent_with_pseudo_session():
    session = PseudoSession("test_sess_1")
    agent = ChatAgent()

    res = await agent.handle_message(thread_id=1, text="Hello", user_id="u1", session=session)
    # Strict mode uses the orchestrator/runner; accept any non-empty assistant reply
    assert isinstance(res.reply, str)
    assert len(res.reply) > 0

    items = await session.get_items()
    assert len(items) == 2
    assert items[0]["role"] == "user"
    assert items[0]["content"] == "Hello"
    assert items[1]["role"] == "assistant"
    # persisted assistant content should contain the produced reply
    assert res.reply in items[1]["content"]


@pytest.mark.asyncio
async def test_pseudo_session_operations():
    session = PseudoSession("s2")
    await session.add_items([{"role": "user", "content": "Hi"}])
    last = await session.pop_item()
    assert last["role"] == "user"
    await session.add_items([{"role": "user", "content": "x", "ts": "1"}, {"role": "assistant", "content": "y", "ts": "2"}])
    items = await session.get_items(limit=1)
    assert len(items) == 1
    await session.clear_session()
    assert await session.get_items() == []


@pytest.mark.asyncio
async def test_pseudo_session_ttl_and_max_items():
    # max_items should trim older entries
    s = PseudoSession("s3", max_items=2)
    await s.add_items([{"role": "user", "content": "a"}, {"role": "user", "content": "b"}, {"role": "user", "content": "c"}])
    items = await s.get_items()
    assert len(items) == 2
    assert items[0]["content"] == "b"

    # ttl filtering - use old timestamps to ensure they are filtered out
    s2 = PseudoSession("s4", ttl_seconds=1)
    await s2.add_items([{"role": "user", "content": "old", "ts": str(0)}])
    await s2.add_items([{"role": "user", "content": "new", "ts": str(__import__('time').time())}])
    items = await s2.get_items()
    assert any(i["content"] == "new" for i in items)
