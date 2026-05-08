"""
Legacy runner module - kept for backward compatibility with tests.
After refactoring, runner functionality was moved to base_agent.py and processor.py
"""

from agents import Runner as ExternalRunner


class Runner:
    """Legacy Runner class - delegates to ExternalRunner"""

    @staticmethod
    async def run(starting_agent, input, context, max_turns=None):
        """Delegate to ExternalRunner.run"""
        return await ExternalRunner.run(starting_agent, input, context, max_turns=max_turns)

    @staticmethod
    def run_streamed(starting_agent, input, context, max_turns=None):
        """Delegate to ExternalRunner.run_streamed"""
        return ExternalRunner.run_streamed(starting_agent, input, context, max_turns=max_turns)
