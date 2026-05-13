import asyncio
from unittest.mock import AsyncMock, patch

from service.services.agents.domain.tools.router import (
    _parse_llm_response,
    _pick_router_model,
    route_model,
)

# ── Unit: helpers ─────────────────────────────────────────────────────────────


def test_pick_router_model_prefers_small():
    models = ["qwen3-235b-alpha", "qwen3-8b-instruct", "mws-gpt-alpha"]
    assert _pick_router_model(models) == "qwen3-8b-instruct"


def test_pick_router_model_falls_back_to_text_family():
    models = ["mws-gpt-alpha", "some-unknown-model"]
    assert _pick_router_model(models) == "mws-gpt-alpha"


def test_parse_llm_response_valid():
    raw = '{"model": "qwen3-32b", "tool": "web_search", "reason": "needs live data"}'
    result = _parse_llm_response(raw, ["qwen3-32b", "other"])
    assert result["model"] == "qwen3-32b"
    assert result["tool"] == "web_search"
    assert result["reason"] == "needs live data"


def test_parse_llm_response_strips_markdown():
    raw = '```json\n{"model": "qwen3-32b", "tool": "none", "reason": "ok"}\n```'
    result = _parse_llm_response(raw, ["qwen3-32b"])
    assert result["model"] == "qwen3-32b"


def test_parse_llm_response_drops_hallucinated_model():
    raw = '{"model": "gpt-9000-turbo", "tool": "none", "reason": "nope"}'
    result = _parse_llm_response(raw, ["qwen3-32b", "llama-3"])
    assert result["model"] is None


def test_parse_llm_response_sanitizes_invalid_tool():
    raw = '{"model": "qwen3-32b", "tool": "INVALID", "reason": "x"}'
    result = _parse_llm_response(raw, ["qwen3-32b"])
    assert result["tool"] == "none"


def test_parse_llm_response_accepts_pptx_gen():
    raw = '{"model": "qwen3-32b", "tool": "pptx_gen", "reason": "slides requested"}'
    result = _parse_llm_response(raw, ["qwen3-32b"])
    assert result["tool"] == "pptx_gen"


def test_parse_llm_response_accepts_audio_transcribe():
    raw = '{"model": "qwen3-32b", "tool": "audio_transcribe", "reason": "audio to text"}'
    result = _parse_llm_response(raw, ["qwen3-32b"])
    assert result["tool"] == "audio_transcribe"


# ── Integration: manual override (no API needed) ─────────────────────────────


def test_route_model_keeps_manual_if_available():
    model, meta = asyncio.run(
        route_model(
            text="hello",
            selected_model="qwen3-32b",
            input_type="text",
            available_models=["qwen3-32b", "mws-gpt-alpha"],
        )
    )
    assert model == "qwen3-32b"
    assert meta.get("source") == "manual"


# ── Integration: LLM router (mocked via _llm_route) ──────────────────────────


def test_route_model_uses_llm_router_result():
    llm_result = {"model": "qwen3-coder-480b-a35b", "tool": "none", "reason": "code task"}

    with patch(
        "service.services.agents.domain.tools.router._llm_route",
        new=AsyncMock(return_value=llm_result),
    ):
        model, meta = asyncio.run(
            route_model(
                text="fix this python bug",
                selected_model=None,
                input_type=None,
                available_models=["qwen3-8b-instruct", "qwen3-coder-480b-a35b"],
            )
        )

    assert model == "qwen3-coder-480b-a35b"
    assert meta["source"] == "llm"
    assert meta["tool"] == "none"
    assert "reason" in meta


def test_route_model_llm_receives_input_type():
    """input_type is passed through as-is (it's a fact, not a prediction)."""
    llm_result = {"model": "qwen-vl-72b", "tool": "none", "reason": "image analysis with VLM"}

    with patch(
        "service.services.agents.domain.tools.router._llm_route",
        new=AsyncMock(return_value=llm_result),
    ) as mock:
        model, meta = asyncio.run(
            route_model(
                text="что на этой картинке?",
                selected_model=None,
                input_type="image",
                available_models=["qwen3-8b-instruct", "qwen-vl-72b"],
            )
        )

    # input_type is passed through to metadata from the request, not from LLM
    assert meta["input_type"] == "image"
    assert meta["source"] == "llm"
    assert model == "qwen-vl-72b"

    # Verify _llm_route received input_type as an argument
    mock.assert_called_once()
    call_kwargs = mock.call_args
    assert call_kwargs[0][3] == "image"  # 4th positional arg = input_type


def test_route_model_llm_auto_web_search():
    llm_result = {"model": "mws-gpt-alpha", "tool": "web_search", "reason": "needs live data"}

    with patch(
        "service.services.agents.domain.tools.router._llm_route",
        new=AsyncMock(return_value=llm_result),
    ):
        model, meta = asyncio.run(
            route_model(
                text="какой курс доллара сейчас?",
                selected_model=None,
                input_type=None,
                available_models=["qwen3-8b-instruct", "mws-gpt-alpha"],
            )
        )

    assert meta["tool"] == "web_search"
    assert meta["source"] == "llm"
    assert model == "mws-gpt-alpha"


def test_route_model_llm_pptx_gen():
    llm_result = {"model": "mws-gpt-alpha", "tool": "pptx_gen", "reason": "presentation requested"}

    with patch(
        "service.services.agents.domain.tools.router._llm_route",
        new=AsyncMock(return_value=llm_result),
    ):
        model, meta = asyncio.run(
            route_model(
                text="сделай презентацию про ИИ",
                selected_model=None,
                input_type=None,
                available_models=["qwen3-8b-instruct", "mws-gpt-alpha"],
            )
        )

    assert meta["tool"] == "pptx_gen"
    assert meta["source"] == "llm"


# ── Integration: regex fallback when LLM returns None ────────────────────────


def test_route_model_regex_fallback_on_llm_failure():
    with patch(
        "service.services.agents.domain.tools.router._llm_route", new=AsyncMock(return_value=None)
    ):
        model, meta = asyncio.run(
            route_model(
                text="```python\nimport os\nprint('hi')\n```\nfix bug",
                selected_model=None,
                input_type="text",
                available_models=["mws-gpt-alpha", "qwen3-coder-480b-a35b"],
            )
        )

    assert model == "qwen3-coder-480b-a35b"
    assert meta["source"] == "regex_fallback"
    assert meta.get("text_kind") == "code"


def test_route_model_regex_fallback_image_input_type():
    with patch(
        "service.services.agents.domain.tools.router._llm_route", new=AsyncMock(return_value=None)
    ):
        model, meta = asyncio.run(
            route_model(
                text="analyze attached image",
                selected_model=None,
                input_type="image",
                available_models=["mws-gpt-alpha", "qwen-image"],
            )
        )

    assert model == "qwen-image"
    assert meta.get("input_type") == "image"
    assert meta["source"] == "regex_fallback"


def test_route_model_regex_fallback_audio_input_type_sets_audio_tool():
    with patch(
        "service.services.agents.domain.tools.router._llm_route", new=AsyncMock(return_value=None)
    ):
        model, meta = asyncio.run(
            route_model(
                text="распознай речь из аудио",
                selected_model=None,
                input_type="audio",
                available_models=["mws-gpt-alpha", "qwen3-8b-instruct"],
            )
        )

    assert model in {"mws-gpt-alpha", "qwen3-8b-instruct"}
    assert meta.get("tool") == "audio_transcribe"
    assert meta["source"] == "regex_fallback"


def test_route_model_regex_fallback_high_complexity():
    with patch(
        "service.services.agents.domain.tools.router._llm_route", new=AsyncMock(return_value=None)
    ):
        text = "\n".join(
            [
                "Design an architecture with constraints and edge cases.",
                "Must optimize performance and reliability.",
                "Need pipeline design and fallback strategy.",
                "Include migration plan and rollback policy.",
                "Consider observability and testing strategy.",
                "Add security constraints and compliance controls.",
            ]
        )
        model, meta = asyncio.run(
            route_model(
                text=text,
                selected_model=None,
                input_type="text",
                available_models=["llama-3.1-8b-instruct", "Qwen3-235B-A22B-Instruct-2507-FP8"],
            )
        )

    assert model == "Qwen3-235B-A22B-Instruct-2507-FP8"
    assert meta.get("complexity") in {"medium", "high"}
    assert meta["source"] == "regex_fallback"
