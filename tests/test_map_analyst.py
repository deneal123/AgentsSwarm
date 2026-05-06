"""Tests for orchestrator.services.map_analyst — map fetch service."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── helpers ──────────────────────────────────────────────────────────────────

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
_METADATA = {
    "map_id": "map",
    "resolution": 0.05,
    "x_offset": -10.275,
    "y_offset": -17.375,
    "safety_distance": 0.45,
    "rotation": 0,
}


def _make_http_response(status_code: int, json_data=None, content: bytes = b""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.content = content
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


# ── MapContext ────────────────────────────────────────────────────────────────

class TestMapContext:
    def test_stores_image_bytes_and_metadata(self):
        from orchestrator.services.map_analyst import MapContext
        ctx = MapContext(image_bytes=_PNG_MAGIC, metadata=_METADATA)
        assert ctx.image_bytes == _PNG_MAGIC
        assert ctx.metadata["map_id"] == "map"
        assert ctx.metadata["resolution"] == 0.05

    def test_default_metadata_is_empty_dict(self):
        from orchestrator.services.map_analyst import MapContext
        ctx = MapContext(image_bytes=b"x")
        assert ctx.metadata == {}


# ── get_map_context ───────────────────────────────────────────────────────────

class TestGetMapContext:
    @pytest.mark.asyncio
    async def test_returns_map_context_on_success(self, monkeypatch):
        from orchestrator.services import map_analyst

        monkeypatch.setenv("MISSION_CONTROL_URL", "http://mc-test:8050")

        mock_meta_resp = MagicMock()
        mock_meta_resp.raise_for_status = MagicMock()
        mock_meta_resp.json.return_value = _METADATA

        mock_img_resp = MagicMock()
        mock_img_resp.raise_for_status = MagicMock()
        mock_img_resp.content = _PNG_MAGIC

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_meta_resp, mock_img_resp])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.services.map_analyst.httpx.AsyncClient", return_value=mock_client):
            ctx = await map_analyst.get_map_context()

        assert ctx is not None
        assert ctx.image_bytes == _PNG_MAGIC
        assert ctx.metadata["map_id"] == "map"
        assert ctx.metadata["resolution"] == 0.05

    @pytest.mark.asyncio
    async def test_returns_none_on_connection_error(self, monkeypatch):
        from orchestrator.services import map_analyst

        monkeypatch.setenv("MISSION_CONTROL_URL", "http://unreachable:8050")

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.services.map_analyst.httpx.AsyncClient", return_value=mock_client):
            ctx = await map_analyst.get_map_context()

        assert ctx is None

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_image(self, monkeypatch):
        from orchestrator.services import map_analyst

        monkeypatch.setenv("MISSION_CONTROL_URL", "http://mc-test:8050")

        mock_meta_resp = MagicMock()
        mock_meta_resp.raise_for_status = MagicMock()
        mock_meta_resp.json.return_value = _METADATA

        mock_img_resp = MagicMock()
        mock_img_resp.raise_for_status = MagicMock()
        mock_img_resp.content = b""  # empty image

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_meta_resp, mock_img_resp])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.services.map_analyst.httpx.AsyncClient", return_value=mock_client):
            ctx = await map_analyst.get_map_context()

        assert ctx is None

    @pytest.mark.asyncio
    async def test_returns_none_on_metadata_error(self, monkeypatch):
        from orchestrator.services import map_analyst

        monkeypatch.setenv("MISSION_CONTROL_URL", "http://mc-test:8050")

        mock_meta_resp = MagicMock()
        mock_meta_resp.raise_for_status.side_effect = Exception("404 Not Found")

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_meta_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.services.map_analyst.httpx.AsyncClient", return_value=mock_client):
            ctx = await map_analyst.get_map_context()

        assert ctx is None

    @pytest.mark.asyncio
    async def test_uses_default_url_when_env_not_set(self, monkeypatch):
        from orchestrator.services import map_analyst

        monkeypatch.delenv("MISSION_CONTROL_URL", raising=False)
        captured_urls: list[str] = []

        mock_meta_resp = MagicMock()
        mock_meta_resp.raise_for_status = MagicMock()
        mock_meta_resp.json.return_value = _METADATA

        mock_img_resp = MagicMock()
        mock_img_resp.raise_for_status = MagicMock()
        mock_img_resp.content = _PNG_MAGIC

        async def fake_get(url, **kwargs):
            captured_urls.append(url)
            return mock_meta_resp if "metadata" in url else mock_img_resp

        mock_client = AsyncMock()
        mock_client.get = fake_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.services.map_analyst.httpx.AsyncClient", return_value=mock_client):
            await map_analyst.get_map_context()

        assert any("localhost:8050" in url for url in captured_urls)
