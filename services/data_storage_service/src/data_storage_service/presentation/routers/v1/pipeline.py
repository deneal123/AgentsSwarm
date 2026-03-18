"""Pipeline endpoints for batch risk processing."""

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from service.models.enums import TaskStatus
from service.presentation.dependencies.auth import get_current_active_user
from service.presentation.dependencies.services import get_pipeline_logic
from service.presentation.schemas.pipeline import (
    PipelineTaskCancelResponse,
    TaskResponse,
)

logger = logging.getLogger(__name__)

pipeline_router = APIRouter(prefix="/api/v1/pipeline", tags=["Pipeline"])


@pipeline_router.post(
    "/run",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Запустить pipeline-анализ",
    description="Запускает пакетный risk-анализ датасета через pipeline.",
)
async def run_pipeline(
    dataset_id: UUID,
    max_parallel_batches: int = Query(
        5,
        description="Max parallel batches (1-10)",
        ge=1,
        le=10,
    ),
    config_file_id: UUID | None = Query(
        None,
        description="Optional uploaded config file UUID",
    ),
    format_file: str = Query(
        "xlsx",
        description="Dataset file format (xlsx, xls, csv)",
        max_length=10,
    ),
    pipeline_logic=Depends(get_pipeline_logic),
    current_user=Depends(get_current_active_user),
):
    """Run pipeline analysis on dataset.

    - **dataset_id**: ID of the dataset to analyze
    - **max_parallel_batches**: Maximum parallel batches (capped at project limit)
    - **config_file_id**: Optional config file UUID (uploaded via /api/v1/files/config)
    - **format_file**: Dataset format, default xlsx
    """
    config = {
        "max_parallel_batches": max_parallel_batches,
    }
    
    task_info = await pipeline_logic.run_pipeline(
        dataset_file_id=dataset_id,
        config=config,
        config_file_id=config_file_id,
        format_file=format_file,
        user_id=current_user.user_id,
    )

    # Get full task info
    task_id = task_info["task_id"]
    task_status = await pipeline_logic.get_task_status(task_id)
    
    if not task_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    return TaskResponse(
        id=task_id,
        task_type=task_info["task_type"],
        status=task_status["status"],
        created_at=task_status.get("created_at"),
        started_at=task_status.get("started_at"),
        completed_at=task_status.get("completed_at"),
        error_message=task_status.get("error_message"),
        payload={"dataset_file_id": str(dataset_id)},
        result=None,
    )


@pipeline_router.get(
    "/reports",
    summary="Список отчётов pipeline",
    description="Возвращает отчёты pipeline текущего пользователя с поддержкой фильтрации.",
)
async def get_pipeline_reports(
    status: TaskStatus | None = Query(
        None,
        description="Filter by task status",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=100,
    ),
    offset: int = Query(0, ge=0),
    pipeline_logic=Depends(get_pipeline_logic),
    current_user=Depends(get_current_active_user),
):
    """Get pipeline reports for current user."""
    reports = await pipeline_logic.get_pipeline_reports(
        user_id=current_user.user_id,
        limit=limit,
        offset=offset,
    )

    # Filter by status at router level if requested
    if status:
        reports = [r for r in reports if r.get("status") == status.value]

    return reports


@pipeline_router.get(
    "/reports/{task_id}",
    summary="Детали отчёта",
    description="Возвращает подробности отчёта по завершённой задаче pipeline.",
)
async def get_report_details(
    task_id: UUID,
    pipeline_logic=Depends(get_pipeline_logic),
    current_user=Depends(get_current_active_user),
):
    """Get detailed report for pipeline task."""
    report = await pipeline_logic.get_report_details(
        task_id=task_id,
        user_id=current_user.user_id,
    )

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found for task {task_id}",
        )

    return report


# ---------------------------------------------------------------------------
# Task status & cancellation
# ---------------------------------------------------------------------------

_MIME_MAP = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".zip": "application/zip",
}


@pipeline_router.get(
    "/tasks/{task_id}",
    summary="Статус задачи pipeline",
    description=(
        "Возвращает текущий статус задачи pipeline и позицию в очереди для PENDING."
    ),
)
async def get_task_status(
    task_id: UUID,
    pipeline_logic=Depends(get_pipeline_logic),
    current_user=Depends(get_current_active_user),
):
    """Return current status and queue info for a pipeline task."""
    task = await pipeline_logic.get_task_status(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return task


@pipeline_router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=PipelineTaskCancelResponse,
    summary="Отменить задачу pipeline",
    description="Отменяет задачу pipeline в статусах NEW, PENDING или PROCESSING.",
)
async def cancel_task(
    task_id: UUID,
    pipeline_logic=Depends(get_pipeline_logic),
    current_user=Depends(get_current_active_user),
):
    """Cancel a pipeline task. Raises 403 if the task belongs to another user."""
    cancelled = await pipeline_logic.cancel_task(
        task_id=task_id,
        user_id=current_user.user_id,
    )

    return PipelineTaskCancelResponse(
        message="Задача успешно отменена",
        task_id=task_id,
        cancelled=cancelled,
    )


# ---------------------------------------------------------------------------
# Artifact download
# ---------------------------------------------------------------------------

@pipeline_router.get(
    "/reports/{task_id}/download",
    summary="Скачать артефакт pipeline",
    description=(
        "Скачивает артефакт (xlsx, pdf и т.д.) завершённого pipeline-запуска. "
        "Передавайте путь `path` из деталей отчёта."
    ),
)
async def download_artifact(
    task_id: UUID,
    artifact_path: str = Query(
        ...,
        description="Full artifact path as returned by GET /reports/{task_id}",
    ),
    pipeline_logic=Depends(get_pipeline_logic),
    current_user=Depends(get_current_active_user),
):
    """Stream an artifact file to the client."""
    file_bytes = await pipeline_logic.download_artifact(
        task_id=task_id,
        artifact_path=artifact_path,
        user_id=current_user.user_id,
    )

    suffix = Path(artifact_path).suffix.lower()
    media_type = _MIME_MAP.get(suffix, "application/octet-stream")
    filename = Path(artifact_path).name

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )