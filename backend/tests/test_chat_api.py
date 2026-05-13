import pytest
from httpx import ASGITransport, AsyncClient

from service.composition.state import get_chat_application_service
from service.main import app
from service.services.agents.chat_agent import ChatAgent


@pytest.mark.asyncio
async def test_chat_agent_handle_message():
    agent = ChatAgent()
    res = await agent.handle_message("T1", "hello", user_id=1)
    assert isinstance(res.reply, str)
    assert len(res.reply) > 0
    assert res.thread_id == "T1"
    assert isinstance(res.metadata.data, dict)


@pytest.mark.asyncio
async def test_chat_endpoint_returns_echo():
    class _FakeSvc:
        async def post_message(self, thread_id, payload):
            return {"reply": "hello back", "thread_id": thread_id, "metadata": {}}

    app.dependency_overrides[get_chat_application_service] = lambda: _FakeSvc()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/chats/THREAD123/message", json={"text": "Hi agent", "user_id": 42}
            )

        assert r.status_code == 200
        data = r.json()
        assert isinstance(data.get("reply"), str)
        assert len(data.get("reply") or "") > 0
        assert data["thread_id"] == "THREAD123"
        assert isinstance(data.get("metadata"), dict)
    finally:
        app.dependency_overrides.pop(get_chat_application_service, None)


@pytest.mark.asyncio
async def test_chat_endpoint_empty_text_returns_422():
    class _FakeSvc:
        async def post_message(self, thread_id, payload):
            return {"reply": "ok", "thread_id": thread_id, "metadata": {}}

    app.dependency_overrides[get_chat_application_service] = lambda: _FakeSvc()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post("/api/chats/T1/message", json={"text": "", "user_id": 1})

        assert r.status_code == 422
    finally:
        app.dependency_overrides.pop(get_chat_application_service, None)


@pytest.mark.asyncio
async def test_chat_models_endpoint():
    class _FakeSvc:
        async def get_models(self):
            return ["mws-gpt-alpha", "kodify-2.0"]

    app.dependency_overrides[get_chat_application_service] = lambda: _FakeSvc()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/chats/models")

        assert r.status_code == 200
        assert r.json() == {"models": ["mws-gpt-alpha", "kodify-2.0"]}
    finally:
        app.dependency_overrides.pop(get_chat_application_service, None)


@pytest.mark.asyncio
async def test_chat_endpoint_passes_selected_model_to_service():
    captured = {}

    class _FakeService:
        async def post_message(self, thread_id, payload):
            captured["thread_id"] = thread_id
            captured["text"] = payload.text
            captured["user_id"] = payload.user_id
            captured["selected_model"] = payload.model
            captured["input_type"] = payload.input_type
            captured["web_search"] = payload.web_search
            captured["deep_research"] = payload.deep_research
            captured["file_context"] = payload.file_context
            return {
                "reply": "ok",
                "thread_id": thread_id,
                "metadata": {"selected_model": payload.model},
            }

    app.dependency_overrides[get_chat_application_service] = lambda: _FakeService()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/chats/T1/message",
                json={"text": "hello", "user_id": 1, "model": "mws-gpt-alpha"},
            )

        assert r.status_code == 200
        assert captured == {
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
        app.dependency_overrides.pop(get_chat_application_service, None)


@pytest.mark.asyncio
async def test_chat_endpoint_passes_input_type_to_service():
    captured = {}

    class _FakeService:
        async def post_message(self, thread_id, payload):
            captured["thread_id"] = thread_id
            captured["text"] = payload.text
            captured["user_id"] = payload.user_id
            captured["selected_model"] = payload.model
            captured["input_type"] = payload.input_type
            captured["web_search"] = payload.web_search
            captured["deep_research"] = payload.deep_research
            captured["file_context"] = payload.file_context
            return {
                "reply": "ok",
                "thread_id": thread_id,
                "metadata": {"input_type": payload.input_type},
            }

    app.dependency_overrides[get_chat_application_service] = lambda: _FakeService()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/chats/T1/message",
                json={"text": "describe this image", "user_id": 1, "input_type": "image"},
            )

        assert r.status_code == 200
        assert captured == {
            "thread_id": "T1",
            "text": "describe this image",
            "user_id": 1,
            "selected_model": None,  # payload.model
            "input_type": "image",
            "web_search": False,
            "deep_research": False,
            "file_context": "",
        }
        assert r.json().get("metadata", {}).get("input_type") == "image"
    finally:
        app.dependency_overrides.pop(get_chat_application_service, None)


@pytest.mark.asyncio
async def test_chat_endpoint_passes_tool_flags_to_service():
    captured = {}

    class _FakeService:
        async def post_message(self, thread_id, payload):
            captured["thread_id"] = thread_id
            captured["text"] = payload.text
            captured["web_search"] = payload.web_search
            captured["deep_research"] = payload.deep_research
            captured["file_context"] = payload.file_context
            return {"reply": "ok", "thread_id": thread_id, "metadata": {}}

    app.dependency_overrides[get_chat_application_service] = lambda: _FakeService()
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
        assert captured == {
            "thread_id": "T1",
            "text": "research this",
            "web_search": True,
            "deep_research": True,
            "file_context": "doc context",
        }
    finally:
        app.dependency_overrides.pop(get_chat_application_service, None)


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

    from service.services.chat.application.chat_application_service import ChatApplicationService

    fake_app_svc = ChatApplicationService.__new__(ChatApplicationService)
    fake_app_svc.file_service = _FakeFileService()

    app.dependency_overrides[get_chat_application_service] = lambda: fake_app_svc
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get(
                "/api/chats/files/download",
                params={"file_key": "uploads/CHAT/demo.pptx", "filename": "demo.pptx"},
            )

        assert r.status_code == 200
        assert r.content == b"pptx-bytes"
        assert captured["download_key"] == "uploads/CHAT/demo.pptx"
        assert 'attachment; filename="demo.pptx"' in (r.headers.get("content-disposition") or "")
    finally:
        app.dependency_overrides.pop(get_chat_application_service, None)


@pytest.mark.asyncio
async def test_chat_download_generated_file_normalizes_legacy_local_path(monkeypatch):
    captured = {}

    class _FakeFileService:
        async def get_presigned_url_by_key(self, *, file_key: str, expiry_sec: int = 3600):
            return None

        async def get_file_by_key(self, *, file_key: str):
            captured["download_key"] = file_key
            return b"ok"

    from service.services.chat.application.chat_application_service import ChatApplicationService

    fake_app_svc = ChatApplicationService.__new__(ChatApplicationService)
    fake_app_svc.file_service = _FakeFileService()

    app.dependency_overrides[get_chat_application_service] = lambda: fake_app_svc
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get(
                "/api/chats/files/download",
                params={"file_key": "/var/lib/app/storage/uploads/CHAT/legacy.pptx"},
            )

        assert r.status_code == 200
        assert captured["download_key"] == "uploads/CHAT/legacy.pptx"
    finally:
        app.dependency_overrides.pop(get_chat_application_service, None)
