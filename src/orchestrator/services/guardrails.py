"""Lightweight guardrails for Agents SDK agents.

Includes:
- prompt_input_guardrail: blocks пустые/слишком длинные промпты
- router_output_guardrail: нормализует категорию роутера в допустимый список
"""

from __future__ import annotations

from typing import Any

from agents.guardrail import GuardrailFunctionOutput, input_guardrail, output_guardrail

ALLOWED_ROUTER_CATEGORIES = {"robot_info", "navigation", "swarm_coord", "general"}


def _extract_text(user_input: Any) -> str:
    if isinstance(user_input, str):
        return user_input
    if isinstance(user_input, list):
        return "\n".join(str(item) for item in user_input)
    return str(user_input)


@input_guardrail(name="prompt_input_guardrail")
async def prompt_input_guardrail(ctx, agent, user_input):  # pragma: no cover - thin wrapper
    text = _extract_text(user_input).strip()
    if not text:
        return GuardrailFunctionOutput("Empty prompt", tripwire_triggered=True)
    if len(text) > 4000:
        return GuardrailFunctionOutput("Input too long", tripwire_triggered=True)
    return GuardrailFunctionOutput(user_input, tripwire_triggered=False)


@output_guardrail(name="router_output_guardrail")
async def router_output_guardrail(ctx, agent, output):  # pragma: no cover - thin wrapper
    category = None
    if hasattr(output, "category"):
        category = getattr(output, "category")
    elif isinstance(output, dict):
        category = output.get("category")

    normalized = (category or "").lower()
    if normalized not in ALLOWED_ROUTER_CATEGORIES:
        # Silently correct to safe fallback — tripwire_triggered=False so the
        # agent run continues with the corrected category rather than raising
        # GuardrailTripwireTriggered.
        corrected = {"category": "general", "reason": "fallback guardrail"}
        return GuardrailFunctionOutput(corrected, tripwire_triggered=False)

    return GuardrailFunctionOutput(output, tripwire_triggered=False)


__all__ = [
    "prompt_input_guardrail",
    "router_output_guardrail",
    "ALLOWED_ROUTER_CATEGORIES",
]
