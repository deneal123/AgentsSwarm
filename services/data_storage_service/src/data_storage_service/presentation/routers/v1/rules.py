"""Rules Marketplace endpoints.

Access model:
  - GET  /rules, /rules/{rule_id}, /rules/{rule_id}/versions  — any authenticated user
  - POST /rules, PATCH /rules/{rule_id}, DELETE /rules/{rule_id}  — admin only
  - POST /rules/{rule_id}/versions  — any authenticated user
  - GET/PUT /rules/{rule_id}/preference  — own user preference (any authenticated)
  - GET /rules/snapshot  — resolved rule set for pipeline/playground
  - POST /rules/import   — bulk TOML import by file_id (admin only)
  - Pipeline config endpoints — admin only
"""

import logging
import tomllib
from uuid import UUID

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from service.presentation.schemas.rules import (
    PipelineConfigCreate,
    PipelineConfigResponse,
    RuleCreate,
    RuleListResponse,
    RuleResponse,
    RuleUpdate,
    RuleVersionCreate,
    RuleVersionResponse,
    RulesImportStats,
    UserRulePreferenceResponse,
    UserRulePreferenceSet,
    UserRulesSnapshot,
)
from service.presentation.dependencies.auth import get_current_active_user, require_admin
from service.presentation.dependencies.services import get_rule_service, get_file_logic
from service.services.rule_service import RuleService

logger = logging.getLogger(__name__)

rules_router = APIRouter(prefix="/api/v1/rules", tags=["Rules"])


# ==================== MARKETPLACE — read (any authenticated user) ====================


@rules_router.get(
    "",
    response_model=list[RuleListResponse],
    summary="Список правил маркетплейса",
    description="Возвращает каталог всех правил маркетплейса с возможностью фильтрации.",
)
async def list_rules(
    active_only: bool = True,
    product_type: str | None = None,
    channel_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(get_current_active_user),
):
    return await rule_service.list_rules(
        active_only=active_only,
        product_type=product_type,
        channel_type=channel_type,
        limit=limit,
        offset=offset,
    )


@rules_router.get(
    "/snapshot",
    response_model=UserRulesSnapshot,
    summary="Снепшот активных правил пользователя",
    description=(
        "Возвращает полный набор правил с разрешёнными активными версиями для текущего пользователя. "
        "Именно этот набор используется при запуске pipeline или playground."
    ),
)
async def get_my_rules_snapshot(
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(get_current_active_user),
):
    return await rule_service.get_user_rules_snapshot(current_user.user_id)


@rules_router.get(
    "/{rule_id}",
    response_model=RuleResponse,
    summary="Детали правила",
    description="Возвращает полную информацию о правиле, включая все его версии.",
)
async def get_rule(
    rule_id: str,
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(get_current_active_user),
):
    return await rule_service.get_rule(rule_id)


@rules_router.get(
    "/{rule_id}/versions",
    response_model=list[RuleVersionResponse],
    summary="Список версий правила",
    description="Возвращает все версии указанного правила (созданные любым пользователем).",
)
async def list_rule_versions(
    rule_id: str,
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(get_current_active_user),
):
    return await rule_service.list_rule_versions(rule_id)


# ==================== VERSIONING — any authenticated user ====================


@rules_router.post(
    "/{rule_id}/versions",
    response_model=RuleVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать версию правила",
    description=(
        "Создаёт новую версию существующего правила. "
        "Новая версия получает следующий порядковый номер. "
        "Используйте PUT /{rule_id}/preference, чтобы сделать эту версию активной для ваших запусков."
    ),
)
async def create_rule_version(
    rule_id: str,
    version_data: RuleVersionCreate,
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(get_current_active_user),
):
    return await rule_service.create_rule_version(
        rule_id=rule_id,
        version_data=version_data,
        created_by_user_id=current_user.user_id,
    )


# ==================== PREFERENCE — per-user active version ====================


@rules_router.get(
    "/{rule_id}/preference",
    response_model=UserRulePreferenceResponse,
    summary="Моя активная версия правила",
    description="Возвращает версию, которая будет использована для данного правила в ваших запусках pipeline/playground.",
)
async def get_my_preference(
    rule_id: str,
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(get_current_active_user),
):
    return await rule_service.get_user_preference(rule_id, current_user.user_id)


@rules_router.put(
    "/{rule_id}/preference",
    response_model=UserRulePreferenceResponse,
    summary="Установить активную версию правила",
    description=(
        "Закрепляет конкретную версию как активную для ваших запусков, или передайте `null`, "
        "чтобы сбросить к поведению «последняя» (последняя созданная вами или глобально последняя)."
    ),
)
async def set_my_preference(
    rule_id: str,
    pref_data: UserRulePreferenceSet,
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(get_current_active_user),
):
    return await rule_service.set_user_preference(
        rule_id=rule_id,
        user_id=current_user.user_id,
        pref_data=pref_data,
    )


# ==================== ADMIN — rule catalogue management ====================


@rules_router.post(
    "",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать правило (admin)",
    description=(
        "Добавляет новое правило в каталог маркетплейса. "
        "Автоматически создаёт версию 1 с переданными initial_instructions. "
        "rule_id должен быть уникальным (например, '1.1-ОР')."
    ),
)
async def create_rule(
    rule_data: RuleCreate,
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(require_admin),
):
    return await rule_service.create_rule(rule_data, current_user.user_id)


@rules_router.patch(
    "/{rule_id}",
    response_model=RuleResponse,
    summary="Обновить правило (admin)",
    description="Обновляет описательные поля правила (название, описание и т.д.).",
)
async def update_rule(
    rule_id: str,
    rule_data: RuleUpdate,
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(require_admin),
):
    return await rule_service.update_rule(rule_id, rule_data)


@rules_router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Деактивировать правило (admin)",
    description="Мягкое удаление правила. Исчезает из маркетплейса, но исторические данные сохраняются.",
)
async def deactivate_rule(
    rule_id: str,
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(require_admin),
):
    await rule_service.deactivate_rule(rule_id)


# ==================== IMPORT FROM FILE (admin) ====================


class FileIdRequest(BaseModel):
    """Request body containing a reference to an already-uploaded file."""
    file_id: UUID


@rules_router.post(
    "/import",
    status_code=status.HTTP_201_CREATED,
    response_model=RulesImportStats,
    summary="Массовый импорт правил из загруженного TOML (admin)",
    description=(
        "Импортирует правила из уже загруженного файла rules.toml по его `file_id`. "
        "Правила с уже существующим rule_id пропускаются. "
        "Для каждого нового правила автоматически создаётся версия 1."
    ),
)
async def import_rules(
    body: FileIdRequest,
    rule_service: RuleService = Depends(get_rule_service),
    file_logic=Depends(get_file_logic),
    current_user=Depends(require_admin),
):
    content = await file_logic.read_file_content(body.file_id)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {body.file_id} not found",
        )
    file_bytes, file_name = content
    if not file_name.endswith(".toml"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .toml files are supported for rules import",
        )
    stats = await rule_service.import_rules_from_toml(
        file_bytes.decode("utf-8"), current_user.user_id
    )
    return RulesImportStats(status="completed", stats=stats)


# ==================== PIPELINE CONFIG (admin) ====================


@rules_router.get(
    "/pipeline-configs",
    response_model=list[PipelineConfigResponse],
    summary="Список конфигов pipeline (admin)",
)
async def list_pipeline_configs(
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(require_admin),
):
    return await rule_service.list_pipeline_configs()


@rules_router.post(
    "/pipeline-configs",
    response_model=PipelineConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать конфиг pipeline (admin)",
)
async def create_pipeline_config(
    config_data: PipelineConfigCreate,
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(require_admin),
):
    return await rule_service.create_pipeline_config(config_data, current_user.user_id)


@rules_router.post(
    "/pipeline-configs/from-file",
    response_model=PipelineConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Импортировать конфиг pipeline из загруженного файла (admin)",
    description=(
        "Создаёт новую версию конфига pipeline из уже загруженного файла по его `file_id`. "
        "Файл должен быть в формате YAML (.yaml/.yml) или TOML (.toml). "
        "Для активации новой версии укажите `is_active: true` в теле запроса."
    ),
)
async def import_pipeline_config_from_file(
    body: FileIdRequest,
    is_active: bool = False,
    change_description: str | None = None,
    rule_service: RuleService = Depends(get_rule_service),
    file_logic=Depends(get_file_logic),
    current_user=Depends(require_admin),
):
    content = await file_logic.read_file_content(body.file_id)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {body.file_id} not found",
        )
    file_bytes, file_name = content
    lower = file_name.lower()
    if lower.endswith((".yaml", ".yml")):
        try:
            parsed = yaml.safe_load(file_bytes.decode("utf-8"))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse YAML: {exc}",
            )
    elif lower.endswith(".toml"):
        try:
            parsed = tomllib.loads(file_bytes.decode("utf-8"))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse TOML: {exc}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .yaml, .yml or .toml files are supported for pipeline config import",
        )

    config_create = PipelineConfigCreate(
        config_data=parsed,
        change_description=change_description or f"Imported from file {file_name}",
        is_active=is_active,
    )
    return await rule_service.create_pipeline_config(config_create, current_user.user_id)


@rules_router.post(
    "/pipeline-configs/{config_id}/activate",
    response_model=PipelineConfigResponse,
    summary="Активировать конфиг pipeline (admin)",
)
async def activate_pipeline_config(
    config_id: UUID,
    rule_service: RuleService = Depends(get_rule_service),
    current_user=Depends(require_admin),
):
    return await rule_service.activate_pipeline_config(config_id)

