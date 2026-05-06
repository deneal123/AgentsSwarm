"""Tests for the full MapAnalyst reasoning pipeline in AgentsSDKExecutor.

Covers:
- Phase 1: agent generates route candidates
- Phase 2: visualize_route called per candidate
- Phase 3: vision LLM compares and selects best route
- Non-fatal fallbacks when any phase fails
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.services.plan_runner import HandoffResult
from orchestrator.services.planner import PlanStep
from orchestrator.services.streaming import StreamCollector


# ── fixtures / helpers ────────────────────────────────────────────────────────

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
_JPEG_MAGIC = b"\xff\xd8\xff" + b"\x00" * 100

_METADATA = {
    "map_id": "map",
    "resolution": 0.05,
    "x_offset": -10.275,
    "y_offset": -17.375,
    "safety_distance": 0.45,
}

_CANDIDATES_JSON = {
    "target": {"x": 2.4, "y": 1.8},
    "candidates": [
        {
            "name": "direct",
            "waypoints": [{"x": 0.5, "y": 0.3}, {"x": 2.4, "y": 1.8}],
            "rationale": "Shortest path, slight wall risk",
        },
        {
            "name": "safe",
            "waypoints": [{"x": 0.5, "y": 0.3}, {"x": 1.2, "y": 0.8}, {"x": 2.4, "y": 1.8}],
            "rationale": "Wide clearance from all walls",
        },
        {
            "name": "optimal",
            "waypoints": [{"x": 0.5, "y": 0.3}, {"x": 1.8, "y": 1.2}, {"x": 2.4, "y": 1.8}],
            "rationale": "Balanced path, avoids critical obstacle",
        },
    ],
    "warnings": ["narrow passage at y=0.3"],
}


def _make_step(task_description: str = "Move carter01 to center") -> PlanStep:
    return PlanStep(
        id=3,
        description="Анализ карты окружения для навигации",
        agent="MapAnalyst",
        meta={
            "task_description": task_description,
            "depends_on": [1],
            "tools": [],
        },
    )


def _make_executor() -> "AgentsSDKExecutor":
    from orchestrator.services.agents_sdk import AgentsSDKExecutor
    collector = StreamCollector()
    return AgentsSDKExecutor(stream_collector=collector)


def _make_map_context(image_bytes: bytes = _PNG_MAGIC):
    from orchestrator.services.map_analyst import MapContext
    return MapContext(image_bytes=image_bytes, metadata=_METADATA)


def _mock_agent_result(output_text: str):
    result = MagicMock()
    result.final_output = output_text
    return result


def _mock_comparison_response(winner: str, reason: str):
    """Build a mock OpenAI chat completion response for route comparison."""
    msg = MagicMock()
    msg.content = json.dumps({"winner": winner, "reason": reason})
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ── Phase 1: candidate generation ────────────────────────────────────────────

class TestCandidateGeneration:
    @pytest.mark.asyncio
    async def test_agent_called_with_map_image_and_task(self, monkeypatch):
        executor = _make_executor()
        step = _make_step("Move carter01 to center")
        ctx = _make_map_context()

        runner_calls: list[dict] = []

        async def fake_runner_run(agent, agent_input, run_config=None):
            runner_calls.append({"input": agent_input})
            return _mock_agent_result(json.dumps(_CANDIDATES_JSON))

        with patch("orchestrator.services.agents_sdk.get_map_context", AsyncMock(return_value=ctx)), \
             patch("orchestrator.services.agents_sdk.Runner") as mock_runner, \
             patch("orchestrator.services.agents_sdk._build_agent", return_value=MagicMock(mcp_servers=[], handoffs=[])), \
             patch("orchestrator.services.agents_sdk._mcp_configs_for", return_value=[]), \
             patch("orchestrator.services.agents_sdk._run_config", return_value=MagicMock()), \
             patch("orchestrator.services.agents_sdk._client", return_value=AsyncMock()), \
             patch("httpx.AsyncClient") as mock_http:

            mock_runner.run = fake_runner_run

            # Mock visualize_route HTTP responses
            mock_viz_resp = MagicMock()
            mock_viz_resp.raise_for_status = MagicMock()
            mock_viz_resp.content = _PNG_MAGIC
            mock_http_instance = AsyncMock()
            mock_http_instance.post = AsyncMock(return_value=mock_viz_resp)
            mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
            mock_http_instance.__aexit__ = AsyncMock(return_value=False)
            mock_http.return_value = mock_http_instance

            # Mock comparison response
            mock_openai = AsyncMock()
            mock_openai.chat.completions.create = AsyncMock(
                return_value=_mock_comparison_response("optimal", "best balance")
            )

            with patch("orchestrator.services.agents_sdk._client", return_value=mock_openai):
                await executor._run_map_analyst("task1", step)

        assert len(runner_calls) == 1
        content = runner_calls[0]["input"][0]["content"]
        # Should have text block with task description
        text_blocks = [c for c in content if c.get("type") == "text"]
        assert any("Move carter01 to center" in b["text"] for b in text_blocks)
        # Should have image block
        image_blocks = [c for c in content if c.get("type") == "image_url"]
        assert len(image_blocks) == 1

    @pytest.mark.asyncio
    async def test_png_mime_type_detected_correctly(self, monkeypatch):
        executor = _make_executor()
        step = _make_step()
        ctx = _make_map_context(_PNG_MAGIC)

        captured_content: list = []

        async def fake_runner_run(agent, agent_input, run_config=None):
            captured_content.extend(agent_input[0]["content"])
            return _mock_agent_result(json.dumps(_CANDIDATES_JSON))

        with patch("orchestrator.services.agents_sdk.get_map_context", AsyncMock(return_value=ctx)), \
             patch("orchestrator.services.agents_sdk.Runner") as mock_runner, \
             patch("orchestrator.services.agents_sdk._build_agent", return_value=MagicMock(mcp_servers=[], handoffs=[])), \
             patch("orchestrator.services.agents_sdk._mcp_configs_for", return_value=[]), \
             patch("orchestrator.services.agents_sdk._run_config", return_value=MagicMock()), \
             patch("httpx.AsyncClient") as mock_http:

            mock_runner.run = fake_runner_run

            mock_viz_resp = MagicMock()
            mock_viz_resp.raise_for_status = MagicMock()
            mock_viz_resp.content = _PNG_MAGIC
            mock_http_instance = AsyncMock()
            mock_http_instance.post = AsyncMock(return_value=mock_viz_resp)
            mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
            mock_http_instance.__aexit__ = AsyncMock(return_value=False)
            mock_http.return_value = mock_http_instance

            mock_openai = AsyncMock()
            mock_openai.chat.completions.create = AsyncMock(
                return_value=_mock_comparison_response("optimal", "best")
            )
            with patch("orchestrator.services.agents_sdk._client", return_value=mock_openai):
                await executor._run_map_analyst("task1", step)

        image_block = next(c for c in captured_content if c.get("type") == "image_url")
        assert "image/png" in image_block["image_url"]["url"]


# ── Phase 2: route visualization ─────────────────────────────────────────────

class TestRouteVisualization:
    @pytest.mark.asyncio
    async def test_visualize_route_called_for_each_candidate(self, monkeypatch):
        executor = _make_executor()
        step = _make_step()
        ctx = _make_map_context()

        post_calls: list[dict] = []

        async def fake_post(url, **kwargs):
            post_calls.append({"url": url, "json": kwargs.get("json", {})})
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.content = _PNG_MAGIC
            return resp

        async def fake_runner_run(agent, agent_input, run_config=None):
            return _mock_agent_result(json.dumps(_CANDIDATES_JSON))

        mock_http_instance = AsyncMock()
        mock_http_instance.post = fake_post
        mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http_instance.__aexit__ = AsyncMock(return_value=False)

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create = AsyncMock(
            return_value=_mock_comparison_response("optimal", "best balance")
        )

        with patch("orchestrator.services.agents_sdk.get_map_context", AsyncMock(return_value=ctx)), \
             patch("orchestrator.services.agents_sdk.Runner") as mock_runner, \
             patch("orchestrator.services.agents_sdk._build_agent", return_value=MagicMock(mcp_servers=[], handoffs=[])), \
             patch("orchestrator.services.agents_sdk._mcp_configs_for", return_value=[]), \
             patch("orchestrator.services.agents_sdk._run_config", return_value=MagicMock()), \
             patch("orchestrator.services.agents_sdk._client", return_value=mock_openai), \
             patch("httpx.AsyncClient", return_value=mock_http_instance):

            mock_runner.run = fake_runner_run
            await executor._run_map_analyst("task1", step)

        # 3 candidates → 3 visualize_route calls
        viz_calls = [c for c in post_calls if "visualize_route" in c["url"]]
        assert len(viz_calls) == 3

    @pytest.mark.asyncio
    async def test_visualization_failure_uses_fallback(self, monkeypatch):
        """If all visualizations fail, falls back to first candidate without comparison."""
        executor = _make_executor()
        step = _make_step()
        ctx = _make_map_context()

        async def fake_post(url, **kwargs):
            raise Exception("Connection refused")

        mock_http_instance = AsyncMock()
        mock_http_instance.post = fake_post
        mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http_instance.__aexit__ = AsyncMock(return_value=False)

        async def fake_runner_run(agent, agent_input, run_config=None):
            return _mock_agent_result(json.dumps(_CANDIDATES_JSON))

        with patch("orchestrator.services.agents_sdk.get_map_context", AsyncMock(return_value=ctx)), \
             patch("orchestrator.services.agents_sdk.Runner") as mock_runner, \
             patch("orchestrator.services.agents_sdk._build_agent", return_value=MagicMock(mcp_servers=[], handoffs=[])), \
             patch("orchestrator.services.agents_sdk._mcp_configs_for", return_value=[]), \
             patch("orchestrator.services.agents_sdk._run_config", return_value=MagicMock()), \
             patch("orchestrator.services.agents_sdk._client", return_value=AsyncMock()), \
             patch("httpx.AsyncClient", return_value=mock_http_instance):

            mock_runner.run = fake_runner_run
            result = await executor._run_map_analyst("task1", step)

        assert result.success is True
        assert "direct" in result.message  # first candidate
        assert "visualization unavailable" in result.message


# ── Phase 3: route comparison ─────────────────────────────────────────────────

class TestRouteComparison:
    @pytest.mark.asyncio
    async def test_winning_route_in_final_message(self, monkeypatch):
        executor = _make_executor()
        step = _make_step()
        ctx = _make_map_context()

        async def fake_post(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.content = _PNG_MAGIC
            return resp

        mock_http_instance = AsyncMock()
        mock_http_instance.post = fake_post
        mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http_instance.__aexit__ = AsyncMock(return_value=False)

        async def fake_runner_run(agent, agent_input, run_config=None):
            return _mock_agent_result(json.dumps(_CANDIDATES_JSON))

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create = AsyncMock(
            return_value=_mock_comparison_response("optimal", "best balance of safety and efficiency")
        )

        with patch("orchestrator.services.agents_sdk.get_map_context", AsyncMock(return_value=ctx)), \
             patch("orchestrator.services.agents_sdk.Runner") as mock_runner, \
             patch("orchestrator.services.agents_sdk._build_agent", return_value=MagicMock(mcp_servers=[], handoffs=[])), \
             patch("orchestrator.services.agents_sdk._mcp_configs_for", return_value=[]), \
             patch("orchestrator.services.agents_sdk._run_config", return_value=MagicMock()), \
             patch("orchestrator.services.agents_sdk._client", return_value=mock_openai), \
             patch("httpx.AsyncClient", return_value=mock_http_instance):

            mock_runner.run = fake_runner_run
            result = await executor._run_map_analyst("task1", step)

        assert result.success is True
        assert "optimal" in result.message
        assert "TARGET" in result.message
        assert "WAYPOINTS" in result.message
        assert "BEST ROUTE" in result.message

    @pytest.mark.asyncio
    async def test_all_candidates_listed_in_message(self, monkeypatch):
        executor = _make_executor()
        step = _make_step()
        ctx = _make_map_context()

        async def fake_post(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.content = _PNG_MAGIC
            return resp

        mock_http_instance = AsyncMock()
        mock_http_instance.post = fake_post
        mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http_instance.__aexit__ = AsyncMock(return_value=False)

        async def fake_runner_run(agent, agent_input, run_config=None):
            return _mock_agent_result(json.dumps(_CANDIDATES_JSON))

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create = AsyncMock(
            return_value=_mock_comparison_response("optimal", "best")
        )

        with patch("orchestrator.services.agents_sdk.get_map_context", AsyncMock(return_value=ctx)), \
             patch("orchestrator.services.agents_sdk.Runner") as mock_runner, \
             patch("orchestrator.services.agents_sdk._build_agent", return_value=MagicMock(mcp_servers=[], handoffs=[])), \
             patch("orchestrator.services.agents_sdk._mcp_configs_for", return_value=[]), \
             patch("orchestrator.services.agents_sdk._run_config", return_value=MagicMock()), \
             patch("orchestrator.services.agents_sdk._client", return_value=mock_openai), \
             patch("httpx.AsyncClient", return_value=mock_http_instance):

            mock_runner.run = fake_runner_run
            result = await executor._run_map_analyst("task1", step)

        # All 3 candidate names appear in the output
        assert "direct" in result.message
        assert "safe" in result.message
        assert "optimal" in result.message

    @pytest.mark.asyncio
    async def test_warnings_included_in_message(self, monkeypatch):
        executor = _make_executor()
        step = _make_step()
        ctx = _make_map_context()

        async def fake_post(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.content = _PNG_MAGIC
            return resp

        mock_http_instance = AsyncMock()
        mock_http_instance.post = fake_post
        mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http_instance.__aexit__ = AsyncMock(return_value=False)

        async def fake_runner_run(agent, agent_input, run_config=None):
            return _mock_agent_result(json.dumps(_CANDIDATES_JSON))

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create = AsyncMock(
            return_value=_mock_comparison_response("optimal", "best")
        )

        with patch("orchestrator.services.agents_sdk.get_map_context", AsyncMock(return_value=ctx)), \
             patch("orchestrator.services.agents_sdk.Runner") as mock_runner, \
             patch("orchestrator.services.agents_sdk._build_agent", return_value=MagicMock(mcp_servers=[], handoffs=[])), \
             patch("orchestrator.services.agents_sdk._mcp_configs_for", return_value=[]), \
             patch("orchestrator.services.agents_sdk._run_config", return_value=MagicMock()), \
             patch("orchestrator.services.agents_sdk._client", return_value=mock_openai), \
             patch("httpx.AsyncClient", return_value=mock_http_instance):

            mock_runner.run = fake_runner_run
            result = await executor._run_map_analyst("task1", step)

        assert "narrow passage" in result.message


# ── non-fatal fallbacks ───────────────────────────────────────────────────────

class TestNonFatalFallbacks:
    @pytest.mark.asyncio
    async def test_returns_success_when_map_fetch_fails(self, monkeypatch):
        executor = _make_executor()
        step = _make_step()

        with patch("orchestrator.services.agents_sdk.get_map_context", AsyncMock(return_value=None)):
            result = await executor._run_map_analyst("task1", step)

        assert result.success is True
        assert result.message == ""

    @pytest.mark.asyncio
    async def test_returns_success_when_agent_fails(self, monkeypatch):
        executor = _make_executor()
        step = _make_step()
        ctx = _make_map_context()

        async def fake_runner_run(agent, agent_input, run_config=None):
            raise RuntimeError("LLM error")

        with patch("orchestrator.services.agents_sdk.get_map_context", AsyncMock(return_value=ctx)), \
             patch("orchestrator.services.agents_sdk.Runner") as mock_runner, \
             patch("orchestrator.services.agents_sdk._build_agent", return_value=MagicMock(mcp_servers=[], handoffs=[])), \
             patch("orchestrator.services.agents_sdk._mcp_configs_for", return_value=[]), \
             patch("orchestrator.services.agents_sdk._run_config", return_value=MagicMock()), \
             patch("orchestrator.services.agents_sdk._client", return_value=AsyncMock()):

            mock_runner.run = fake_runner_run
            result = await executor._run_map_analyst("task1", step)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_returns_success_when_comparison_fails(self, monkeypatch):
        executor = _make_executor()
        step = _make_step()
        ctx = _make_map_context()

        async def fake_post(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.content = _PNG_MAGIC
            return resp

        mock_http_instance = AsyncMock()
        mock_http_instance.post = fake_post
        mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http_instance.__aexit__ = AsyncMock(return_value=False)

        async def fake_runner_run(agent, agent_input, run_config=None):
            return _mock_agent_result(json.dumps(_CANDIDATES_JSON))

        # Comparison LLM raises
        mock_openai = AsyncMock()
        mock_openai.chat.completions.create = AsyncMock(side_effect=Exception("Vision API down"))

        with patch("orchestrator.services.agents_sdk.get_map_context", AsyncMock(return_value=ctx)), \
             patch("orchestrator.services.agents_sdk.Runner") as mock_runner, \
             patch("orchestrator.services.agents_sdk._build_agent", return_value=MagicMock(mcp_servers=[], handoffs=[])), \
             patch("orchestrator.services.agents_sdk._mcp_configs_for", return_value=[]), \
             patch("orchestrator.services.agents_sdk._run_config", return_value=MagicMock()), \
             patch("orchestrator.services.agents_sdk._client", return_value=mock_openai), \
             patch("httpx.AsyncClient", return_value=mock_http_instance):

            mock_runner.run = fake_runner_run
            result = await executor._run_map_analyst("task1", step)

        # Falls back to first candidate
        assert result.success is True
        assert "direct" in result.message


# ── _format_map_result ────────────────────────────────────────────────────────

class TestFormatMapResult:
    def test_contains_all_required_sections(self):
        from orchestrator.services.agents_sdk import AgentsSDKExecutor
        best = _CANDIDATES_JSON["candidates"][2]  # optimal
        msg = AgentsSDKExecutor._format_map_result(_CANDIDATES_JSON, best, "best balance")

        assert "TARGET" in msg
        assert "BEST ROUTE" in msg
        assert "WAYPOINTS" in msg
        assert "WARNINGS" in msg
        assert "OTHER CANDIDATES" in msg

    def test_winner_waypoints_formatted(self):
        from orchestrator.services.agents_sdk import AgentsSDKExecutor
        best = _CANDIDATES_JSON["candidates"][2]
        msg = AgentsSDKExecutor._format_map_result(_CANDIDATES_JSON, best, "reason")

        assert "0.50" in msg
        assert "0.30" in msg
        assert "2.40" in msg
        assert "1.80" in msg

    def test_non_winner_candidates_listed_as_other(self):
        from orchestrator.services.agents_sdk import AgentsSDKExecutor
        best = _CANDIDATES_JSON["candidates"][2]  # optimal
        msg = AgentsSDKExecutor._format_map_result(_CANDIDATES_JSON, best, "reason")

        assert "direct" in msg
        assert "safe" in msg

    def test_no_warnings_section_when_empty(self):
        from orchestrator.services.agents_sdk import AgentsSDKExecutor
        data = {**_CANDIDATES_JSON, "warnings": []}
        best = data["candidates"][0]
        msg = AgentsSDKExecutor._format_map_result(data, best, "reason")

        assert "WARNINGS" not in msg
