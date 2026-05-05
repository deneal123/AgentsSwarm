import pytest

from orchestrator.services.guardrails import (
    ALLOWED_ROUTER_CATEGORIES,
    prompt_input_guardrail,
    router_output_guardrail,
)


@pytest.mark.asyncio
async def test_prompt_input_guardrail_blocks_empty_and_passes_valid():
    res = await prompt_input_guardrail.guardrail_function(None, None, " ")
    assert res.tripwire_triggered is True

    ok = await prompt_input_guardrail.guardrail_function(None, None, "navigate to point")
    assert ok.tripwire_triggered is False
    assert ok.output_info == "navigate to point"


@pytest.mark.asyncio
async def test_router_output_guardrail_corrects_invalid_category():
    invalid = await router_output_guardrail.guardrail_function(None, None, {"category": "unknown"})
    assert invalid.tripwire_triggered is False  # silent fallback — run continues with corrected category
    assert invalid.output_info["category"] == "general"

    for cat in ALLOWED_ROUTER_CATEGORIES:
        valid = await router_output_guardrail.guardrail_function(None, None, {"category": cat})
        assert valid.tripwire_triggered is False
        assert valid.output_info["category"] == cat
