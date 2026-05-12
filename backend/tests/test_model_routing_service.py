import sys
import types

import pytest

from service.services.chat.domain.chat_exceptions import ModelRoutingError
from service.services.agents.application.model_routing_service import ModelRoutingService


@pytest.mark.asyncio
async def test_resolve_route_enables_web_search(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_route_model(**kwargs):
        return "m1", {"tool": "web_search"}

    fake_router_module = types.ModuleType("service.services.agents.domain.tools.router")
    fake_router_module.route_model = _fake_route_model
    monkeypatch.setitem(sys.modules, "service.services.agents.domain.tools.router", fake_router_module)

    service = ModelRoutingService()
    decision = await service.resolve_route(
        text="q",
        selected_model=None,
        input_type=None,
        web_search=False,
        deep_research=False,
        route_override=None,
    )

    assert decision.selected_model == "m1"
    assert decision.web_search is True
    assert decision.deep_research is False
    assert decision.route_override is None


@pytest.mark.asyncio
async def test_resolve_route_raises_domain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_route_model(**kwargs):
        raise RuntimeError("boom")

    fake_router_module = types.ModuleType("service.services.agents.domain.tools.router")
    fake_router_module.route_model = _fake_route_model
    monkeypatch.setitem(sys.modules, "service.services.agents.domain.tools.router", fake_router_module)

    service = ModelRoutingService()
    with pytest.raises(ModelRoutingError):
        await service.resolve_route("q", None, None, False, False, None)
