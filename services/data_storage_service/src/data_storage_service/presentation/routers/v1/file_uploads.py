"""File upload endpoints for configs and datasets."""

import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status

from service.models.enums import FileType
from service.presentation.schemas.file import (
    FileMetaResponse,
    FileListResponse,
    FileUploadTaskResponse,
    FileUploadTaskStatusResponse,
)
from service.presentation.schemas.task import TaskResponse
from service.presentation.dependencies.auth import get_current_active_user, require_admin
from service.presentation.dependencies.services import get_file_logic

logger = logging.getLogger(__name__)

file_uploads_router = APIRouter(prefix="/api/v1/files", tags=["Files"])


@file_uploads_router.post(
    "/config",
    response_model=FileUploadTaskStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Загрузить конфиг правил (admin)",
    description="Загружает и валидирует файл конфигурации правил в формате YAML или TOML. Доступно только администратору.",
)
async def upload_config(
    file: UploadFile = File(..., description="Configuration file (YAML/TOML)"),
    file_logic=Depends(get_file_logic),
    current_user=Depends(require_admin),
):
    """Upload configuration file for risk rules.

    Supported formats:
    - YAML (.yaml, .yml)
    - TOML (.toml)

    Returns task for monitoring validation process.
    """
    # Validate file extension
    allowed_extensions = [".yaml", ".yml", ".toml"]
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {', '.join(allowed_extensions)} files are supported",
        )

    content = await file.read()

    upload_info = await file_logic.upload_config(
        file_content=content,
        file_name=file.filename,
        user_id=current_user.user_id,
    )

    # Re-fetch task after dispatch so celery_task_id is populated
    task_id = upload_info["task_id"]
    orchestrator = file_logic.container.task_orchestrator_service()
    task = await orchestrator.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return FileUploadTaskStatusResponse(
        task_id=task.id,
        file_id=task.file_id,
        status=task.status,
        task_type=task.task_type,
        file_name=file.filename,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error_message=task.error_message,
        result=task.result,
    )


@file_uploads_router.post(
    "/dataset",
    response_model=FileUploadTaskStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Загрузить датасет",
    description="Загружает и валидирует файл датасета в формате Excel (.xlsx) для пакетной обработки.",
)
async def upload_dataset(
    file: UploadFile = File(..., description="Dataset file (Excel)"),
    file_logic=Depends(get_file_logic),
    current_user=Depends(get_current_active_user),
):
    """Upload dataset file for batch processing.

    Supported formats:
    - Excel (.xlsx)

    Returns task for monitoring validation process.
    """
    # Validate file extension
    allowed_extensions = [".xlsx"]
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {', '.join(allowed_extensions)} files are supported",
        )

    content = await file.read()

    upload_info = await file_logic.upload_dataset(
        file_content=content,
        file_name=file.filename,
        user_id=current_user.user_id,
    )

    # Re-fetch task after dispatch so celery_task_id is populated
    task_id = upload_info["task_id"]
    orchestrator = file_logic.container.task_orchestrator_service()
    task = await orchestrator.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return FileUploadTaskStatusResponse(
        task_id=task.id,
        file_id=task.file_id,
        status=task.status,
        task_type=task.task_type,
        file_name=file.filename,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error_message=task.error_message,
        result=task.result,
    )


@file_uploads_router.get(
    "",
    response_model=FileListResponse,
    summary="Список файлов пользователя",
    description=(
        "Возвращает все файлы, загруженные текущим пользователем. "
        "Можно фильтровать по типу файла: `config_yaml`, `dataset`, `etalon_dataset`, и т.д."
    ),
)
async def list_my_files(
    file_type: Optional[str] = Query(
        None,
        description="Тип файла для фильтрации (config_yaml | dataset | etalon_dataset | rule_prompt | …)",
        examples={"config": {"value": "config_yaml"}, "dataset": {"value": "dataset"}},
    ),
    limit: int = Query(50, ge=1, le=200, description="Максимум результатов"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    file_logic=Depends(get_file_logic),
    current_user=Depends(get_current_active_user),
):
    """Список файлов текущего пользователя с опциональным фильтром по типу."""
    ft: FileType | None = None
    if file_type:
        try:
            ft = FileType(file_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown file_type '{file_type}'. Valid values: {[e.value for e in FileType]}",
            )

    files = await file_logic.list_user_files(
        user_id=current_user.user_id,
        file_type=ft,
        limit=limit,
        offset=offset,
    )

    items = [
        FileMetaResponse(
            id=f["file_id"],
            file_name=f["file_name"],
            file_path=f["file_path"],
            file_size=f["file_size"],
            mime_type=f["mime_type"],
            file_type=f["file_type"],
            storage_type=f["storage_type"],
            is_public=f["is_public"],
            uploaded_by_user_id=f["uploaded_by_user_id"],
            uploaded_by_guest_id=f["uploaded_by_guest_id"],
            created_at=f["created_at"],
        )
        for f in files
    ]

    return FileListResponse(items=items, total=len(items), offset=offset, limit=limit)


@file_uploads_router.get(
    "/tasks/{task_id}",
    response_model=FileUploadTaskStatusResponse,
    summary="Статус задачи загрузки файла",
    description=(
        "Возвращает текущий статус задачи обработки загруженного файла. "
        "В поле `file_id` содержится ID файла, сохранённого при загрузке. "
        "В поле `result` — результат валидации (ошибки, сводка конфига или инфо о датасете). "
        "Используйте `task_id` из ответа на POST /files/config или POST /files/dataset."
    ),
)
async def get_file_upload_task_status(
    task_id: UUID,
    file_logic=Depends(get_file_logic),
    current_user=Depends(get_current_active_user),
):
    """Получить статус задачи обработки загруженного файла."""
    task_info = await file_logic.get_upload_task_status(
        task_id=task_id,
        user_id=current_user.user_id,
    )

    if not task_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return FileUploadTaskStatusResponse(
        task_id=task_info["task_id"],
        file_id=task_info["file_id"],
        status=task_info["status"],
        task_type=task_info["task_type"],
        file_name=task_info["file_name"],
        created_at=task_info["created_at"],
        started_at=task_info["started_at"],
        completed_at=task_info["completed_at"],
        error_message=task_info["error_message"],
        result=task_info["result"],
    )


@file_uploads_router.get(
    "/{file_id}",
    response_model=FileMetaResponse,
    summary="Информация о файле",
    description="Возвращает метаданные конкретного файла по его ID.",
)
async def get_file(
    file_id: UUID,
    file_logic=Depends(get_file_logic),
    current_user=Depends(get_current_active_user),
):
    """Получить метаданные файла по ID."""
    info = await file_logic.get_file_info(file_id)
    if not info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Проверяем, что файл принадлежит текущему пользователю
    if info["uploaded_by_user_id"] and info["uploaded_by_user_id"] != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return FileMetaResponse(
        id=info["file_id"],
        file_name=info["file_name"],
        file_path=info["file_path"],
        file_size=info["file_size"],
        mime_type=info["mime_type"],
        file_type=info["file_type"],
        storage_type=info["storage_type"],
        is_public=info["is_public"],
        uploaded_by_user_id=info["uploaded_by_user_id"],
        uploaded_by_guest_id=info["uploaded_by_guest_id"],
        created_at=info["created_at"],
    )


@file_uploads_router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить файл",
    description=(
        "Удаляет файл из хранилища и базы данных. "
        "Нельзя удалить файл, который используется активной задачей (статус pending/processing/new)."
    ),
)
async def delete_file(
    file_id: UUID,
    file_logic=Depends(get_file_logic),
    current_user=Depends(get_current_active_user),
):
    """Удалить файл по ID. Возвращает 204 No Content при успехе."""
    await file_logic.delete_file(
        file_id=file_id,
        user_id=current_user.user_id,
    )