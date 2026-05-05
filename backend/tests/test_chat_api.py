import pytest

from httpx import AsyncClient, ASGITransport

from service.main import app
from service import container
from service.agents.chat_agent import ChatAgent
from service.presentation.routers.chat_api import chat_api
from service.services.chat_contracts import ChatProcessingMetadata, ChatReplyResult


@pytest.mark.asyncio
async def test_chat_agent_handle_message():
    agent = ChatAgent()
    res = await agent.handle_message("T1", "hello", user_id=1)
    # Strict mode no longer falls back to an echo; ensure we get a string reply
    assert isinstance(res.reply, str)
    assert len(res.reply) > 0
    assert res.thread_id == "T1"
    # metadata may be empty or contain structured action info; ensure it's a dict
    assert isinstance(res.metadata.data, dict)


@pytest.mark.asyncio
async def test_chat_endpoint_returns_echo():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {"text": "Hi agent", "user_id": 42}
        r = await ac.post("/api/chats/THREAD123/message", json=payload)

    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("reply"), str)
    assert len(data.get("reply") or "") > 0
    assert data["thread_id"] == "THREAD123"
    assert isinstance(data.get("metadata"), dict)


@pytest.mark.asyncio
async def test_chat_endpoint_empty_text_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/chats/T1/message", json={"text": "", "user_id": 1})

    assert r.status_code == 422


@pytest.mark.asyncio
async def test_chat_models_endpoint(monkeypatch):
    async def _fake_models():
        return ["mws-gpt-alpha", "kodify-2.0"]

    monkeypatch.setattr(chat_api, "list_available_models", _fake_models)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/chats/models")

    assert r.status_code == 200
    assert r.json() == {"models": ["mws-gpt-alpha", "kodify-2.0"]}


@pytest.mark.asyncio
async def test_chat_endpoint_passes_selected_model_to_service():
    class _FakeService:
        def __init__(self):
            self.captured = None

        async def post_message(
            self, context
        ):
            self.captured = {
                "thread_id": context.thread_id,
                "text": context.text,
                "user_id": context.user_id,
                "selected_model": context.selected_model,
                "input_type": context.input_type,
                "web_search": context.web_search,
                "deep_research": context.deep_research,
                "file_context": context.file_context,
            }
            return ChatReplyResult(reply="ok", thread_id=context.thread_id, metadata=ChatProcessingMetadata(data={"selected_model": context.selected_model}))

    fake_service = _FakeService()

    from service.presentation.routers.chat_api.chat_api import get_chat_service

    app.dependency_overrides[get_chat_service] = lambda: fake_service
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/chats/T1/message",
                json={"text": "hello", "user_id": 1, "model": "mws-gpt-alpha"},
            )

        assert r.status_code == 200
        assert fake_service.captured == {
            "thread_id": "T1",
            "text": "hello",
            "user_id": 1,
            "selected_model": "mws-gpt-alpha",
            "input_type": None,
            "web_search": False,
            "deep_research": False,
            "file_context": "",
        }
        assert r.json().get("metadata", {}).get("selected_model") == "mws-gpt-alpha"
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


@pytest.mark.asyncio
async def test_chat_endpoint_passes_input_type_to_service():
    class _FakeService:
        def __init__(self):
            self.captured = None

        async def post_message(
            self, context
        ):
            self.captured = {
                "thread_id": context.thread_id,
                "text": context.text,
                "user_id": context.user_id,
                "selected_model": context.selected_model,
                "input_type": context.input_type,
                "web_search": context.web_search,
                "deep_research": context.deep_research,
                "file_context": context.file_context,
            }
            return ChatReplyResult(reply="ok", thread_id=context.thread_id, metadata=ChatProcessingMetadata(data={"input_type": context.input_type}))

    fake_service = _FakeService()

    from service.presentation.routers.chat_api.chat_api import get_chat_service

    app.dependency_overrides[get_chat_service] = lambda: fake_service
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/chats/T1/message",
                json={"text": "describe this image", "user_id": 1, "input_type": "image"},
            )

        assert r.status_code == 200
        assert fake_service.captured == {
            "thread_id": "T1",
            "text": "describe this image",
            "user_id": 1,
            "selected_model": None,
            "input_type": "image",
            "web_search": False,
            "deep_research": False,
            "file_context": "",
        }
        assert r.json().get("metadata", {}).get("input_type") == "image"
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


@pytest.mark.asyncio
async def test_chat_endpoint_passes_tool_flags_to_service():
    class _FakeService:
        def __init__(self):
            self.captured = None

        async def post_message(
            self, context
        ):
            self.captured = {
                "thread_id": context.thread_id,
                "text": context.text,
                "web_search": context.web_search,
                "deep_research": context.deep_research,
                "file_context": context.file_context,
            }
            return ChatReplyResult(
                reply="ok",
                thread_id=context.thread_id,
                metadata=ChatProcessingMetadata(
                    data={
                        "web_search": context.web_search,
                        "deep_research": context.deep_research,
                    }
                ),
            )

    fake_service = _FakeService()

    from service.presentation.routers.chat_api.chat_api import get_chat_service

    app.dependency_overrides[get_chat_service] = lambda: fake_service
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/chats/T1/message",
                json={
                    "text": "research this",
                    "user_id": 1,
                    "web_search": True,
                    "deep_research": True,
                    "file_context": "doc context",
                },
            )

        assert r.status_code == 200
        assert fake_service.captured == {
            "thread_id": "T1",
            "text": "research this",
            "web_search": True,
            "deep_research": True,
            "file_context": "doc context",
        }
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


@pytest.mark.asyncio
async def test_chat_download_generated_file_returns_binary(monkeypatch):
    captured = {}

    class _FakeFileService:
        async def get_presigned_url_by_key(self, *, file_key: str, expiry_sec: int = 3600):
            captured["presigned_key"] = file_key
            return None

        async def get_file_by_key(self, *, file_key: str):
            captured["download_key"] = file_key
            return b"pptx-bytes"

    fake = _FakeFileService()
    monkeypatch.setattr(container, "get", lambda name: fake if name == container.FileSaverServiceName else None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/chats/files/download", params={"file_key": "uploads/CHAT/demo.pptx", "filename": "demo.pptx"})

    assert r.status_code == 200
    assert r.content == b"pptx-bytes"
    assert captured["download_key"] == "uploads/CHAT/demo.pptx"
    assert "attachment; filename=\"demo.pptx\"" in (r.headers.get("content-disposition") or "")


@pytest.mark.asyncio
async def test_chat_download_generated_file_normalizes_legacy_local_path(monkeypatch):
    captured = {}

    class _FakeFileService:
        async def get_presigned_url_by_key(self, *, file_key: str, expiry_sec: int = 3600):
            return None

        async def get_file_by_key(self, *, file_key: str):
            captured["download_key"] = file_key
            return b"ok"

    fake = _FakeFileService()
    monkeypatch.setattr(container, "get", lambda name: fake if name == container.FileSaverServiceName else None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/api/chats/files/download",
            params={"file_key": "/var/lib/app/storage/uploads/CHAT/legacy.pptx"},
        )

    assert r.status_code == 200
    assert captured["download_key"] == "uploads/CHAT/legacy.pptx"
