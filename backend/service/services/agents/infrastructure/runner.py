"""Thin wrapper around the OpenAI Agents SDK runner — infrastructure adapter."""
from agents import Runner as ExternalRunner


class Runner:
    """Delegates to the external OpenAI Agents SDK Runner."""

    @staticmethod
    async def run(starting_agent, input, context, max_turns=None):
        return await ExternalRunner.run(starting_agent, input, context, max_turns=max_turns)

    @staticmethod
    def run_streamed(starting_agent, input, context, max_turns=None):
        return ExternalRunner.run_streamed(starting_agent, input, context, max_turns=max_turns)
