"""
Роутер для рабочих зон (zones).

Эндпоинты:
  GET    /zones            — список зон
  GET    /zones/{zone_id}  — детали зоны
  POST   /zones            — создать зону (требует OPERATOR+)
  PUT    /zones/{zone_id}  — обновить зону (требует OPERATOR+)
  DELETE /zones/{zone_id}  — удалить зону (требует ADMIN)

До реализации gRPC-клиента (Этап 6) используется хранилище в памяти.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from gateway_service.auth.permissions import require_admin, require_authenticated, require_operator
from gateway_service.auth.schemas import UserContext
from gateway_service.schemas.common import PaginatedResponse, PaginationParams, pagination_params
from gateway_service.schemas.zone import ZoneCreate, ZoneDetail, ZoneSummary, ZoneUpdate

logger = structlog.get_logger(__name__)

router = APIRouter()


# ─── In-memory store (заглушка до подключения БД в Этапе 6) ─────────────────


class _ZoneStore:
    """Простое хранилище зон в памяти для разработки и тестирования."""

    _data: ClassVar[dict[str, ZoneDetail]] = {}

    @classmethod
    def all(cls) -> list[ZoneDetail]:
        return list(cls._data.values())

    @classmethod
    def get(cls, zone_id: str) -> ZoneDetail | None:
        return cls._data.get(zone_id)

    @classmethod
    def create(cls, zone: ZoneDetail) -> ZoneDetail:
        cls._data[zone.zone_id] = zone
        return zone

    @classmethod
    def update(cls, zone_id: str, update: ZoneUpdate) -> ZoneDetail | None:
        existing = cls._data.get(zone_id)
        if existing is None:
            return None
        data = existing.model_dump()
        for field, value in update.model_dump(exclude_none=True).items():
            data[field] = value
        data["updated_at"] = datetime.utcnow()
        updated = ZoneDetail(**data)
        cls._data[zone_id] = updated
        return updated

    @classmethod
    def delete(cls, zone_id: str) -> bool:
        return cls._data.pop(zone_id, None) is not None


# ─── GET /zones ───────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=PaginatedResponse[ZoneSummary],
    summary="Список рабочих зон",
)
async def list_zones(
    pagination: PaginationParams = Depends(pagination_params),
    current_user: UserContext = Depends(require_authenticated),
) -> PaginatedResponse[ZoneSummary]:
    all_zones = _ZoneStore.all()
    summaries = [
        ZoneSummary(
            zone_id=z.zone_id,
            name=z.name,
            is_active=z.is_active,
            is_restricted=z.is_restricted,
            robot_count=z.robot_count,
            max_robots=z.max_robots,
        )
        for z in all_zones
    ]

    # Пагинация вручную (пока нет БД)
    total = len(summaries)
    page_items = summaries[pagination.offset : pagination.offset + pagination.limit]

    return PaginatedResponse.create(
        items=page_items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ─── GET /zones/{zone_id} ─────────────────────────────────────────────────────


@router.get(
    "/{zone_id}",
    response_model=ZoneDetail,
    summary="Детали зоны",
    responses={404: {"description": "Зона не найдена"}},
)
async def get_zone(
    zone_id: str,
    current_user: UserContext = Depends(require_authenticated),
) -> ZoneDetail:
    zone = _ZoneStore.get(zone_id)
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ZONE_NOT_FOUND", "message": f"Zone '{zone_id}' not found"},
        )
    return zone


# ─── POST /zones ──────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ZoneDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Создать зону",
)
async def create_zone(
    body: ZoneCreate,
    current_user: UserContext = Depends(require_operator),
) -> ZoneDetail:
    now = datetime.utcnow()
    zone = ZoneDetail(
        zone_id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        bounds=body.bounds,
        map_id=body.map_id,
        max_robots=body.max_robots,
        is_restricted=body.is_restricted,
        metadata=body.metadata,
        created_at=now,
        updated_at=now,
    )
    _ZoneStore.create(zone)
    logger.info("zones.created", user_id=current_user.user_id, zone_id=zone.zone_id, name=zone.name)
    return zone


# ─── PUT /zones/{zone_id} ─────────────────────────────────────────────────────


@router.put(
    "/{zone_id}",
    response_model=ZoneDetail,
    summary="Обновить зону",
    responses={404: {"description": "Зона не найдена"}},
)
async def update_zone(
    zone_id: str,
    body: ZoneUpdate,
    current_user: UserContext = Depends(require_operator),
) -> ZoneDetail:
    zone = _ZoneStore.update(zone_id, body)
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ZONE_NOT_FOUND", "message": f"Zone '{zone_id}' not found"},
        )
    logger.info("zones.updated", user_id=current_user.user_id, zone_id=zone_id)
    return zone


# ─── DELETE /zones/{zone_id} ──────────────────────────────────────────────────


@router.delete(
    "/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить зону",
    responses={404: {"description": "Зона не найдена"}},
)
async def delete_zone(
    zone_id: str,
    current_user: UserContext = Depends(require_admin),
) -> Response:
    deleted = _ZoneStore.delete(zone_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ZONE_NOT_FOUND", "message": f"Zone '{zone_id}' not found"},
        )
    logger.info("zones.deleted", user_id=current_user.user_id, zone_id=zone_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
