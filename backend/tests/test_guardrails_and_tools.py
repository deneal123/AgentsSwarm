import pytest

from service.agents.guardrails import (
    check_appropriate_language,
    check_forbidden_topics,
    ensure_non_empty_response,
    fact_check_output,
)
from service.agents.tools.function_tools import fetch_runtime_context_tool, summarize_brief_tool


@pytest.mark.asyncio
async def test_check_appropriate_language_failure():
    res = await check_appropriate_language.guardrail_function(None, None, "Это мат и оскорбление")
    assert res.tripwire_triggered is True


@pytest.mark.asyncio
async def test_check_appropriate_language_success():
    res = await check_appropriate_language.guardrail_function(None, None, "Привет, помоги с задачей")
    assert res.tripwire_triggered is False


@pytest.mark.asyncio
async def test_check_forbidden_topics():
    res = await check_forbidden_topics.guardrail_function(None, None, "Я хочу узнать про самоубийство")
    assert res.tripwire_triggered is True


@pytest.mark.asyncio
async def test_fact_check_output():
    res = await fact_check_output.guardrail_function(None, None, "Это гарантированно вылечит вас")
    assert res.tripwire_triggered is True


@pytest.mark.asyncio
async def test_ensure_non_empty_response():
    res = await ensure_non_empty_response.guardrail_function(None, None, "")
    assert res.tripwire_triggered is True


@pytest.mark.asyncio
async def test_runtime_context_and_summary_tools():
    class DummyCtx:
        context = {
            "user_id": "u1",
            "thread_id": "t1",
            "input_type": "text",
        }

    ctx = DummyCtx()
    runtime = await fetch_runtime_context_tool(ctx, "{}")
    assert "u1" in runtime
    assert "t1" in runtime

    short = await summarize_brief_tool(ctx, '{"text":"one two three"}')
    assert "one two three" in short
