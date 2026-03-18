"""API endpoints for Communication Results.

These endpoints allow browsing, searching, and analysing the per-communication
classification results produced by Playground task runs.

Endpoints:
  GET  /api/v1/communications/{task_id}/results        — paginated list with filters
  GET  /api/v1/communications/{task_id}/stats          — aggregated statistics
  GET  /api/v1/communications/items/{communication_id} — single communication detail
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from service.presentation.dependencies.auth import require_user
from service.presentation.dependencies.services import get_communication_result_service
from service.presentation.schemas.communication_results import (
    CommunicationResponse,
    CommunicationResultPage,
    TaskCommunicationStats,
)

logger = logging.getLogger(__name__)

communication_results_router = APIRouter(
    prefix="/api/v1/communications",
    tags=["Communication Results"],
)


@communication_results_router.get(
    "/{task_id}/results",
    response_model=CommunicationResultPage,
    summary="Список результатов коммуникаций",
    description=(
        "Возвращает постраничный список коммуникаций и их классификаций для задачи. "
        "Поддерживается полнотекстовый поиск и фильтры по параметрам."
    ),
)
async def list_communication_results(
    task_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=200, description="Records per page"),
    search: str | None = Query(None, description="Search in communication text"),
    risk_id: str | None = Query(
        None, alias="risk_id", description="Filter by predicted risk ID"
    ),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by result status (completed/failed)"
    ),
    type_filter: str | None = Query(
        None, alias="type", description="Filter by communication type (push/sms/email)"
    ),
    product_type: str | None = Query(
        None, description="Filter by product type"
    ),
    has_risks: bool | None = Query(
        None, description="true — only with risks, false — only without risks"
    ),
    current_user=Depends(require_user),
    comm_result_service=Depends(get_communication_result_service),
) -> CommunicationResultPage:
    """Return paginated, searchable list of communication results for a task."""
    return await comm_result_service.list_results(
        task_id=task_id,
        page=page,
        page_size=page_size,
        search=search,
        risk_id_filter=risk_id,
        status_filter=status_filter,
        type_filter=type_filter,
        product_type_filter=product_type,
        has_risks=has_risks,
    )


@communication_results_router.get(
    "/{task_id}/stats",
    response_model=TaskCommunicationStats,
    summary="Статистика коммуникаций",
    description=(
        "Возвращает агрегированную статистику по коммуникациям задачи: кол-во, "
        "распределение рисков, времена обработки, версии моделей и т.д."
    ),
)
async def get_communication_stats(
    task_id: UUID,
    current_user=Depends(require_user),
    comm_result_service=Depends(get_communication_result_service),
) -> TaskCommunicationStats:
    """Return aggregated statistics for a task's communications."""
    return await comm_result_service.get_task_stats(task_id)


@communication_results_router.get(
    "/items/{communication_id}",
    response_model=CommunicationResponse,
    summary="Детали коммуникации",
    description=(
        "Возвращает одну коммуникацию с полной информацией по классификациям (может "
        "быть несколько результатов, если применялись разные правила)."
    ),
)
async def get_communication_detail(
    communication_id: UUID,
    current_user=Depends(require_user),
    comm_result_service=Depends(get_communication_result_service),
) -> CommunicationResponse:
    """Return a single communication with all its nested results."""
    comm = await comm_result_service.get_communication_detail(communication_id)
    if comm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Communication {communication_id} not found",
        )
    return CommunicationResponse.model_validate(comm)
