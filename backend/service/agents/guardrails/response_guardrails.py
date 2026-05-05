from __future__ import annotations

from agents import Agent, GuardrailFunctionOutput, RunContextWrapper, input_guardrail, output_guardrail


@input_guardrail
async def check_appropriate_language(
    context: RunContextWrapper,
    agent: Agent,
    input,
) -> GuardrailFunctionOutput:
    """Block abusive language in user input."""
    try:
        input_text = " ".join(map(str, input)) if isinstance(input, (list, tuple)) else str(input)
    except Exception:
        input_text = ""

    forbidden_words = ["оскорбление", "мат", "ненависть", "угроза"]
    found_words = [word for word in forbidden_words if word in input_text.lower()]

    return GuardrailFunctionOutput(
        tripwire_triggered=bool(found_words),
        output_info={"found_words": found_words},
    )


@input_guardrail
async def check_forbidden_topics(
    context: RunContextWrapper,
    agent: Agent,
    input,
) -> GuardrailFunctionOutput:
    """Detect potentially unsafe request topics for escalation."""
    text = str(input or "").lower()
    forbidden = ["самоубий", "взрывчат", "вред себе", "как взломать"]
    found = [w for w in forbidden if w in text]
    return GuardrailFunctionOutput(
        tripwire_triggered=bool(found),
        output_info={"found": found},
    )


@output_guardrail
async def validate_response_relevance(
    context: RunContextWrapper,
    agent: Agent,
    output: str,
) -> GuardrailFunctionOutput:
    """Ensure response length is sensible for user-facing chat."""
    min_length = 8
    max_length = 8000
    valid = min_length <= len(output or "") <= max_length
    return GuardrailFunctionOutput(
        tripwire_triggered=not valid,
        output_info={"length": len(output or "")},
    )


@output_guardrail
async def ensure_non_empty_response(
    context: RunContextWrapper,
    agent: Agent,
    output: str,
) -> GuardrailFunctionOutput:
    """Trip if model returned an empty response."""
    empty = not str(output or "").strip()
    return GuardrailFunctionOutput(
        tripwire_triggered=empty,
        output_info={"empty": empty},
    )


@output_guardrail
async def fact_check_output(
    context: RunContextWrapper,
    agent: Agent,
    output: str,
) -> GuardrailFunctionOutput:
    """Lightweight heuristic for risky absolute claims."""
    text = (output or "").lower()
    bad_phrases = ["гарантированно", "100% безопасно", "без рисков"]
    found = [p for p in bad_phrases if p in text]
    return GuardrailFunctionOutput(
        tripwire_triggered=bool(found),
        output_info={"found": found},
    )
