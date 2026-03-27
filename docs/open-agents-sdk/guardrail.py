from agents import (
    Agent, 
    input_guardrail,
    output_guardrail,
    GuardrailFunctionOutput,
    RunContextWrapper
)
from service.agents.pydantic.agents import MealCalendarOutput


@input_guardrail
async def check_appropriate_language(
    context: RunContextWrapper,
    agent: Agent,
    input,
) -> GuardrailFunctionOutput:
    """Проверка на недопустимые выражения.

    Normalize the input to text: sometimes the agents framework may pass a
    list/tuple or other structure as the input; coerce to a string to avoid
    AttributeError when calling .lower().
    """
    # normalize various input shapes to a single text string
    try:
        if isinstance(input, (list, tuple)):
            input_text = " ".join(map(str, input))
        else:
            input_text = str(input)
    except Exception:
        input_text = ""

    forbidden_words = ["хамство", "оскорбление", "мат"]
    found_words = [word for word in forbidden_words if word in input_text.lower()]
    
    return GuardrailFunctionOutput(
        tripwire_triggered=len(found_words) > 0,
        output_info={"found_words": found_words}
    )


@output_guardrail
async def validate_response_relevance(
    context: RunContextWrapper,
    agent: Agent,
    output: str
) -> GuardrailFunctionOutput:
    """Проверка релевантности ответа"""
    min_length = 20
    max_length = 1000
    valid = min_length <= len(output) <= max_length
    
    return GuardrailFunctionOutput(
        tripwire_triggered=not valid,
        output_info={"length": len(output)}
    )


async def validate_calendar_schema_raw(
    context: RunContextWrapper,
    agent: Agent,
    output: str,
) -> GuardrailFunctionOutput:
    """Validate that calendar agent output is valid JSON and matches expected keys."""
    import json
    try:
        parsed = json.loads(output) if isinstance(output, str) else output
        # validate with Pydantic model
        MealCalendarOutput.model_validate(parsed)
    except Exception as exc:  # noqa: BLE001
        return GuardrailFunctionOutput(tripwire_triggered=True, output_info={"error": "schema_validation_failed", "reason": str(exc)})

    # size limit: avoid massive calendars
    try:
        parsed = parsed if isinstance(parsed, dict) else json.loads(output)
        if len(parsed.get("calendar", [])) > 365:
            return GuardrailFunctionOutput(tripwire_triggered=True, output_info={"error": "calendar_too_large"})
    except Exception:
        pass

    return GuardrailFunctionOutput(tripwire_triggered=False, output_info={"valid": True})


@output_guardrail
async def validate_calendar_schema(context: RunContextWrapper, agent: Agent, output: str) -> GuardrailFunctionOutput:
    return await validate_calendar_schema_raw(context, agent, output)


@input_guardrail
async def check_forbidden_topics(
    context: RunContextWrapper,
    agent: Agent,
    input: str,
) -> GuardrailFunctionOutput:
    forbidden = ["самолечение", "лекарство", "наркотик", "опасная диета"]
    found = [w for w in forbidden if w in input.lower()]
    return GuardrailFunctionOutput(tripwire_triggered=len(found) > 0, output_info={"found": found})


@output_guardrail
async def fact_check_output(
    context: RunContextWrapper,
    agent: Agent,
    output: str,
) -> GuardrailFunctionOutput:
    # Very lightweight heuristic: detect absolute cure claims
    bad_phrases = ["вылечит", "гарантированно", "без противопоказаний"]
    found = [p for p in bad_phrases if p in output.lower()]
    return GuardrailFunctionOutput(tripwire_triggered=bool(found), output_info={"found": found})


@output_guardrail
async def format_calendar_output(
    context: RunContextWrapper,
    agent: Agent,
    output: str,
) -> GuardrailFunctionOutput:
    # Try to parse and reserialize to canonical JSON using Pydantic model
    import json
    try:
        parsed = json.loads(output) if isinstance(output, str) else output
        model = MealCalendarOutput.model_validate(parsed)
        # return formatted JSON in output_info for potential replacement
        return GuardrailFunctionOutput(tripwire_triggered=False, output_info={"formatted_output": model.model_dump_json()})
    except Exception as exc:
        return GuardrailFunctionOutput(tripwire_triggered=True, output_info={"error": "format_failed", "reason": str(exc)})