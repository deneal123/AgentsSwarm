import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.models.auth_models import AuthProfile
from service.models.key_value import UserTypes
from service.presentation.routers.memory_api import memory_api as memory_module
from service.presentation.routers.memory_api.memory_api import get_memory_service, memory_router


class _FakeMemoryService:
    def __init__(self) -> None:
        self.deleted_fact_ids: list[tuple[str, str]] = []

    async def list_facts(self, user_id: str, query: str | None = None, top_k: int = 50) -> list[dict]:
        return [
            {
                "id": "fact-1",
                "fact_type": "preference",
                "fact_key": "Язык",
                "fact_value": "Русский",
                "confidence": 0.91,
                "updated_at": "2026-01-01T10:00:00+00:00",
            }
        ]

    async def get_memory_context(self, user_id: str, top_k: int = 5) -> str:
        return "## Контекст из памяти пользователя:\n- Язык: Русский"

    async def add_fact(self, user_id: str, fact_type: str, fact_key: str, fact_value: str) -> dict:
        return {
            "id": "fact-new",
            "fact_type": fact_type,
            "fact_key": fact_key,
            "fact_value": fact_value,
            "confidence": None,
            "updated_at": None,
        }

    async def delete_fact(self, user_id: str, fact_id: str) -> bool:
        self.deleted_fact_ids.append((user_id, fact_id))
        return fact_id == "fact-1"


def _make_auth(user_id: str):
    def _fake_auth() -> AuthProfile:
        return AuthProfile(user_id=uuid.UUID(user_id), fingerprint=None, type=UserTypes.REGISTERED)

    return _fake_auth


def _make_client(fake_service: _FakeMemoryService, auth_user_id: str) -> TestClient:
    app = FastAPI()
    app.include_router(memory_router)
    app.dependency_overrides[get_memory_service] = lambda: fake_service
    app.dependency_overrides[memory_module.check_auth] = _make_auth(auth_user_id)
    return TestClient(app)


def test_get_user_memory_returns_facts_and_context():
    user_id = "11111111-1111-1111-1111-111111111111"
    client = _make_client(_FakeMemoryService(), user_id)

    resp = client.get(f"/api/memory/{user_id}")

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert isinstance(payload.get("facts"), list)
    assert payload["facts"][0]["fact_key"] == "Язык"
    assert "Контекст из памяти пользователя" in (payload.get("context_text") or "")


def test_search_user_memory_uses_query_param():
    user_id = "11111111-1111-1111-1111-111111111111"
    client = _make_client(_FakeMemoryService(), user_id)

    resp = client.get(f"/api/memory/{user_id}/search", params={"q": "язык"})

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert len(payload["facts"]) == 1


def test_add_memory_fact_creates_fact():
    user_id = "11111111-1111-1111-1111-111111111111"
    client = _make_client(_FakeMemoryService(), user_id)

    resp = client.post(
        f"/api/memory/{user_id}/facts",
        json={
            "user_id": user_id,
            "fact_type": "preference",
            "fact_key": "Стиль ответа",
            "fact_value": "Кратко",
        },
    )

    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["fact"]["id"] == "fact-new"
    assert payload["fact"]["fact_key"] == "Стиль ответа"


def test_delete_memory_fact_returns_204():
    user_id = "11111111-1111-1111-1111-111111111111"
    fake_service = _FakeMemoryService()
    client = _make_client(fake_service, user_id)

    resp = client.delete(f"/api/memory/{user_id}/facts/fact-1")

    assert resp.status_code == 204, resp.text
    assert fake_service.deleted_fact_ids == [(user_id, "fact-1")]


def test_memory_api_forbids_access_to_other_user():
    auth_user_id = "11111111-1111-1111-1111-111111111111"
    another_user_id = "22222222-2222-2222-2222-222222222222"
    client = _make_client(_FakeMemoryService(), auth_user_id)

    resp = client.get(f"/api/memory/{another_user_id}")

    assert resp.status_code == 403, resp.text
