"""
Интеграционные тесты для всех HTTP-роутов (без реальной БД/Redis).

Стратегия:
- httpx.AsyncClient + ASGITransport — реальный FastAPI app, без сетевого стека.
- Все зависимости, требующие БД/Redis/Celery, переопределяются через
  app.dependency_overrides на лёгкие заглушки.
- Проверяется HTTP-статус ответа и (где возможно) структура JSON.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
import httpx
from fastapi import FastAPI

# Импортируем app уже построенным
from service.main import create_app
from service.presentation.dependencies.auth import (
    get_current_active_user,
    get_current_user,
    get_current_user_or_guest,
    require_user,
    require_admin,
)
from service.presentation.dependencies.services import (
    get_auth_service,
    get_profile_service,
    get_rule_service,
    get_playground_logic,
    get_pipeline_logic,
    get_file_logic,
    get_communication_result_service,
)
from service.models.pydantic.auth import AuthProfile, LoginResponse, TokenRefreshResponse
from service.models.pydantic.profile import UserResponse
from service.models.pydantic.risk import (
    RuleResponse,
    RuleListResponse,
    RuleVersionResponse,
    UserRulesSnapshot,
    UserRulePreferenceResponse,
    PipelineConfigResponse,
)
from service.models.pydantic.communication import (
    CommunicationResultPage,
    TaskCommunicationStats,
)
from service.models.enums import UserType, TaskStatus, TaskType

# ---------------------------------------------------------------------------
# Фиксированные идентификаторы для тестов
# ---------------------------------------------------------------------------
TEST_USER_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_TASK_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
TEST_RULE_UUID = uuid.UUID("cccccccc-0000-0000-0000-000000000003")
TEST_RULE_ID = "1.1-ОР"
TEST_COMM_ID = uuid.UUID("dddddddd-0000-0000-0000-000000000004")
TEST_PIPELINE_CONFIG_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")

NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Вспомогательные фабрики Pydantic-объектов
# ---------------------------------------------------------------------------

def _auth_profile(is_guest: bool = False) -> AuthProfile:
    return AuthProfile(
        user_id=TEST_USER_ID,
        fingerprint=None,
        type=UserType.GUEST if is_guest else UserType.REGISTERED_USER,
    )


def _make_user_response() -> UserResponse:
    return UserResponse(
        id=TEST_USER_ID,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        is_active=True,
        timezone="UTC",
        role="lawyer",
        created_at=NOW,
        updated_at=None,
    )


def _make_rule_version() -> RuleVersionResponse:
    return RuleVersionResponse(
        id=TEST_RULE_UUID,
        rule_id=TEST_RULE_UUID,
        version_number=1,
        additional_instructions=None,
        change_description=None,
        created_by_user_id=TEST_USER_ID,
        created_at=NOW,
    )


def _make_rule_response() -> RuleResponse:
    return RuleResponse(
        id=TEST_RULE_UUID,
        rule_id=TEST_RULE_ID,
        risk_id="1.1",
        risk_category="Финансовые риски",
        name="Test Rule",
        description="Test description",
        consequences=None,
        levels=None,
        measures=None,
        additional_information=None,
        rule_type="simple",
        risk_present_if=1,
        product_types=["кредит"],
        channel_types=["push"],
        is_active=True,
        current_version=1,
        created_by_user_id=TEST_USER_ID,
        created_at=NOW,
        updated_at=None,
        versions=[_make_rule_version()],
    )


def _make_rule_list_response() -> RuleListResponse:
    return RuleListResponse(
        id=TEST_RULE_UUID,
        rule_id=TEST_RULE_ID,
        risk_id="1.1",
        risk_category="Финансовые риски",
        name="Test Rule",
        rule_type="simple",
        product_types=["кредит"],
        channel_types=["push"],
        is_active=True,
        current_version=1,
        created_at=NOW,
    )


def _make_preference_response() -> UserRulePreferenceResponse:
    return UserRulePreferenceResponse(
        rule_id=TEST_RULE_ID,
        rule_uuid=TEST_RULE_UUID,
        pinned_version_number=None,
        effective_version_number=1,
    )


def _make_pipeline_config() -> PipelineConfigResponse:
    return PipelineConfigResponse(
        id=TEST_PIPELINE_CONFIG_ID,
        version_number=1,
        config_data={"model": "test"},
        change_description=None,
        is_active=True,
        created_by_user_id=TEST_USER_ID,
        created_at=NOW,
    )


def _make_login_response() -> LoginResponse:
    return LoginResponse(
        access_token="tok",
        refresh_token="rtok",
        user=_make_user_response(),
    )


def _make_token_refresh_response() -> TokenRefreshResponse:
    return TokenRefreshResponse(
        access_token="newtok",
        refresh_token="newrtok",
    )


def _make_comm_result_page() -> CommunicationResultPage:
    return CommunicationResultPage(
        task_id=TEST_TASK_ID,
        items=[],
        total=0,
        page=1,
        page_size=50,
        total_pages=0,
        has_next=False,
        has_prev=False,
    )


def _make_task_stats() -> TaskCommunicationStats:
    return TaskCommunicationStats(
        task_id=TEST_TASK_ID,
        total_communications=0,
        processed=0,
        with_risks=0,
        without_risks=0,
        failed=0,
        unique_risk_ids=[],
        risk_counts={},
        avg_processing_time_ms=None,
        models_used=[],
    )


# ---------------------------------------------------------------------------
# Фабрики сервис-заглушек
# ---------------------------------------------------------------------------

def _make_auth_service() -> MagicMock:
    svc = AsyncMock()
    svc.login = AsyncMock(return_value=_make_login_response())
    svc.refresh_token = AsyncMock(return_value=_make_token_refresh_response())
    svc.validate_password_strength = MagicMock()
    svc.repository = AsyncMock()
    svc.repository.fetch_user_session = AsyncMock(return_value=None)
    svc.repository.revoke_session = AsyncMock()
    svc.repository.create_guest_session = AsyncMock(
        return_value=MagicMock(id=TEST_USER_ID)
    )
    return svc


def _make_profile_service() -> MagicMock:
    svc = AsyncMock()
    user = _make_user_response()
    svc.fetch_user_profile = AsyncMock(return_value=user)
    svc.fetch_user_profile_by_email = AsyncMock(return_value=None)
    svc.create_new_user = AsyncMock(return_value=user)
    svc.update_profile = AsyncMock(return_value=user)
    svc.normalize_email = MagicMock(return_value="test@example.com")
    return svc


def _make_rule_service() -> MagicMock:
    svc = AsyncMock()
    rule = _make_rule_response()
    rule_list = _make_rule_list_response()
    version = _make_rule_version()
    preference = _make_preference_response()
    pipeline_cfg = _make_pipeline_config()

    svc.list_rules = AsyncMock(return_value=[rule_list])
    svc.get_rule = AsyncMock(return_value=rule)
    svc.list_rule_versions = AsyncMock(return_value=[version])
    svc.create_rule = AsyncMock(return_value=rule)
    svc.update_rule = AsyncMock(return_value=rule)
    svc.deactivate_rule = AsyncMock()
    svc.create_rule_version = AsyncMock(return_value=version)
    svc.get_user_preference = AsyncMock(return_value=preference)
    svc.set_user_preference = AsyncMock(return_value=preference)
    svc.get_user_rules_snapshot = AsyncMock(return_value=UserRulesSnapshot(rules=[], total=0))
    svc.import_rules_from_toml = AsyncMock(return_value={"imported": 0, "skipped": 0})
    svc.list_pipeline_configs = AsyncMock(return_value=[pipeline_cfg])
    svc.create_pipeline_config = AsyncMock(return_value=pipeline_cfg)
    svc.activate_pipeline_config = AsyncMock(return_value=pipeline_cfg)
    return svc


def _make_playground_logic() -> MagicMock:
    logic = AsyncMock()
    logic.analyze_communications = AsyncMock(return_value={
        "task_id": TEST_TASK_ID,
        "task_type": "playground_single",
    })
    logic.get_task_status = AsyncMock(return_value={
        "id": str(TEST_TASK_ID),
        "status": "pending",
        "task_type": "playground_single",
        "created_at": NOW.isoformat(),
        "started_at": None,
        "completed_at": None,
        "error_message": None,
    })
    logic.get_results = AsyncMock(return_value=[{"result": "ok"}])
    logic.list_user_tasks = AsyncMock(return_value=[])
    logic.cancel_task = AsyncMock(return_value=True)
    return logic


def _make_pipeline_logic() -> MagicMock:
    logic = AsyncMock()
    logic.run_pipeline = AsyncMock(return_value={
        "task_id": TEST_TASK_ID,
        "task_type": "pipeline",
    })
    logic.get_task_status = AsyncMock(return_value={
        "id": str(TEST_TASK_ID),
        "status": "pending",
        "task_type": "pipeline",
        "created_at": NOW.isoformat(),
        "started_at": None,
        "completed_at": None,
        "error_message": None,
    })
    logic.get_pipeline_reports = AsyncMock(return_value=[])
    logic.get_report_details = AsyncMock(return_value=None)
    logic.cancel_task = AsyncMock(return_value=True)
    logic.download_artifact = AsyncMock(return_value=b"artifact bytes")
    return logic


def _make_file_logic() -> MagicMock:
    logic = AsyncMock()
    # file_uploads router also calls logic.container.task_orchestrator_service().get_task()
    task_mock = MagicMock()
    task_mock.created_at = NOW
    task_mock.started_at = None
    task_mock.completed_at = None
    task_mock.error_message = None

    orchestrator = AsyncMock()
    orchestrator.get_task = AsyncMock(return_value=task_mock)

    container_mock = MagicMock()
    container_mock.task_orchestrator_service = MagicMock(return_value=orchestrator)

    logic.upload_config = AsyncMock(return_value={
        "task_id": TEST_TASK_ID,
        "status": "pending",
    })
    logic.upload_dataset = AsyncMock(return_value={
        "task_id": TEST_TASK_ID,
        "status": "pending",
    })
    logic.container = container_mock
    return logic


def _make_comm_result_service() -> MagicMock:
    svc = AsyncMock()
    svc.list_results = AsyncMock(return_value=_make_comm_result_page())
    svc.get_task_stats = AsyncMock(return_value=_make_task_stats())
    svc.get_communication_detail = AsyncMock(return_value=None)
    return svc


# ---------------------------------------------------------------------------
# Fixture: app с подменёнными зависимостями
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app() -> FastAPI:
    application = create_app()

    registered_profile = _auth_profile(is_guest=False)

    application.dependency_overrides[get_current_user] = lambda: registered_profile
    application.dependency_overrides[get_current_active_user] = lambda: registered_profile
    application.dependency_overrides[require_user] = lambda: registered_profile
    application.dependency_overrides[require_admin] = lambda: registered_profile
    application.dependency_overrides[get_current_user_or_guest] = lambda: {
        "user_id": TEST_USER_ID,
        "guest_session_id": None,
        "is_guest": False,
    }

    application.dependency_overrides[get_auth_service] = lambda: _make_auth_service()
    application.dependency_overrides[get_profile_service] = lambda: _make_profile_service()
    application.dependency_overrides[get_rule_service] = lambda: _make_rule_service()
    application.dependency_overrides[get_playground_logic] = lambda: _make_playground_logic()
    application.dependency_overrides[get_pipeline_logic] = lambda: _make_pipeline_logic()
    application.dependency_overrides[get_file_logic] = lambda: _make_file_logic()
    application.dependency_overrides[get_communication_result_service] = (
        lambda: _make_comm_result_service()
    )

    return application


@pytest_asyncio.fixture(scope="module")
async def client(app: FastAPI) -> httpx.AsyncClient:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ===========================================================================
# Health
# ===========================================================================


@pytest.mark.asyncio
async def test_root(client: httpx.AsyncClient):
    r = await client.get("/")
    assert r.status_code == 200
    assert "title" in r.json()


@pytest.mark.asyncio
async def test_health(client: httpx.AsyncClient):
    r = await client.get("/api/health")
    # может быть unhealthy без БД, но ответ всегда 200
    assert r.status_code == 200
    assert "status" in r.json()


# ===========================================================================
# Auth
# ===========================================================================

@pytest.mark.asyncio
async def test_register(client: httpx.AsyncClient):
    r = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "Secure123!",
        "first_name": "Иван",
        "last_name": "Петров",
    })
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_login(client: httpx.AsyncClient):
    r = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "Secure123!",
    })
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token(client: httpx.AsyncClient):
    r = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "some-refresh-token",
    })
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_logout(client: httpx.AsyncClient):
    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_guest_session(client: httpx.AsyncClient):
    r = await client.post("/api/v1/auth/guest")
    assert r.status_code in (200, 201)
    data = r.json()
    assert "guest_token" in data
    assert "guest_session_id" in data


# ===========================================================================
# Profile
# ===========================================================================


@pytest.mark.asyncio
async def test_get_profile(client: httpx.AsyncClient):
    r = await client.get("/api/v1/profile/me")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_update_profile(client: httpx.AsyncClient):
    r = await client.patch("/api/v1/profile/me", json={"first_name": "Новое"})
    assert r.status_code == 200


# ===========================================================================
# Rules
# ===========================================================================


@pytest.mark.asyncio
async def test_list_rules(client: httpx.AsyncClient):
    r = await client.get("/api/v1/rules")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_get_rule_snapshot(client: httpx.AsyncClient):
    r = await client.get("/api/v1/rules/snapshot")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_get_rule(client: httpx.AsyncClient):
    r = await client.get(f"/api/v1/rules/{TEST_RULE_ID}")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_list_rule_versions(client: httpx.AsyncClient):
    r = await client.get(f"/api/v1/rules/{TEST_RULE_ID}/versions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_create_rule(client: httpx.AsyncClient):
    r = await client.post("/api/v1/rules", json={
        "rule_id": "1.1-ОР",
        "name": "Test Rule",
        "description": "Testing",
        "rule_type": "simple",
        "product_types": ["кредит"],
        "channel_types": ["push"],
    })
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_update_rule(client: httpx.AsyncClient):
    r = await client.patch(f"/api/v1/rules/{TEST_RULE_ID}", json={
        "name": "Updated Rule",
        "description": "Updated",
    })
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_delete_rule(client: httpx.AsyncClient):
    r = await client.delete(f"/api/v1/rules/{TEST_RULE_ID}")
    assert r.status_code in (200, 204)


@pytest.mark.asyncio
async def test_create_rule_version(client: httpx.AsyncClient):
    r = await client.post(f"/api/v1/rules/{TEST_RULE_ID}/versions", json={
        "content": "rule content",
        "description": "v2",
    })
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_get_rule_preference(client: httpx.AsyncClient):
    r = await client.get(f"/api/v1/rules/{TEST_RULE_ID}/preference")
    assert r.status_code in (200, 404)


@pytest.mark.asyncio
async def test_set_rule_preference(client: httpx.AsyncClient):
    r = await client.put(f"/api/v1/rules/{TEST_RULE_ID}/preference", json={
        "pinned_version_number": 1,
    })
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_import_rules(client: httpx.AsyncClient):
    file_content = b"# test toml config"
    r = await client.post(
        "/api/v1/rules/import",
        files={"file": ("rules.toml", file_content, "application/octet-stream")},
    )
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_list_pipeline_configs(client: httpx.AsyncClient):
    r = await client.get("/api/v1/rules/pipeline-configs")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_create_pipeline_config(client: httpx.AsyncClient):
    r = await client.post("/api/v1/rules/pipeline-configs", json={
        "config_data": {"model": "gpt-4"},
        "change_description": "Initial config",
        "is_active": False,
    })
    assert r.status_code in (200, 201)


# ===========================================================================
# Playground
# ===========================================================================


@pytest.mark.asyncio
async def test_playground_analyze(client: httpx.AsyncClient):
    r = await client.post("/api/v1/playground/analyze", json={
        "communications": [{"text": "Купи кредит!", "type": "sms"}],
    })
    assert r.status_code in (200, 202)


@pytest.mark.asyncio
async def test_playground_results(client: httpx.AsyncClient):
    r = await client.get(f"/api/v1/playground/results/{TEST_TASK_ID}")
    assert r.status_code in (200, 404)


@pytest.mark.asyncio
async def test_playground_list_tasks(client: httpx.AsyncClient):
    r = await client.get("/api/v1/playground/tasks")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_playground_task_status(client: httpx.AsyncClient):
    r = await client.get(f"/api/v1/playground/tasks/{TEST_TASK_ID}")
    assert r.status_code in (200, 404)


@pytest.mark.asyncio
async def test_playground_cancel_task(client: httpx.AsyncClient):
    r = await client.delete(f"/api/v1/playground/tasks/{TEST_TASK_ID}")
    assert r.status_code == 200


# ===========================================================================
# Pipeline
# ===========================================================================


@pytest.mark.asyncio
async def test_pipeline_run(client: httpx.AsyncClient):
    r = await client.post(
        "/api/v1/pipeline/run",
        params={"dataset_id": str(TEST_TASK_ID)},
    )
    assert r.status_code in (200, 202)


@pytest.mark.asyncio
async def test_pipeline_reports(client: httpx.AsyncClient):
    r = await client.get("/api/v1/pipeline/reports")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_pipeline_report_detail(client: httpx.AsyncClient):
    r = await client.get(f"/api/v1/pipeline/reports/{TEST_TASK_ID}")
    assert r.status_code in (200, 404)


@pytest.mark.asyncio
async def test_pipeline_task_status(client: httpx.AsyncClient):
    r = await client.get(f"/api/v1/pipeline/tasks/{TEST_TASK_ID}")
    assert r.status_code in (200, 404)


@pytest.mark.asyncio
async def test_pipeline_cancel_task(client: httpx.AsyncClient):
    r = await client.delete(f"/api/v1/pipeline/tasks/{TEST_TASK_ID}")
    assert r.status_code == 200


# ===========================================================================
# Files
# ===========================================================================


@pytest.mark.asyncio
async def test_upload_config(client: httpx.AsyncClient):
    r = await client.post(
        "/api/v1/files/config",
        files={"file": ("config.yaml", b"rules: []", "application/x-yaml")},
    )
    assert r.status_code in (200, 202)


@pytest.mark.asyncio
async def test_upload_dataset(client: httpx.AsyncClient):
    r = await client.post(
        "/api/v1/files/dataset",
        files={"file": ("data.xlsx", b"PK", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code in (200, 202)


# ===========================================================================
# Communication Results
# ===========================================================================


@pytest.mark.asyncio
async def test_comm_results_list(client: httpx.AsyncClient):
    r = await client.get(f"/api/v1/communications/{TEST_TASK_ID}/results")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_comm_results_stats(client: httpx.AsyncClient):
    r = await client.get(f"/api/v1/communications/{TEST_TASK_ID}/stats")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_comm_detail_not_found(client: httpx.AsyncClient):
    r = await client.get(f"/api/v1/communications/items/{TEST_COMM_ID}")
    assert r.status_code == 404
