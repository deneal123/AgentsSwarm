"""Схемы для эндпоинтов загрузки и управления файлами."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# Re-export task response для ответа после загрузки (запуск задачи)
from service.models.pydantic.task import TaskResponse as FileUploadTaskResponse  # noqa: F401


class FileMetaResponse(BaseModel):
    """Метаданные загруженного файла."""

    id: UUID
    file_name: str = Field(..., description="Оригинальное имя файла")
    file_path: str = Field(..., description="Путь в хранилище")
    file_size: int = Field(..., description="Размер в байтах")
    mime_type: str
    file_type: str = Field(..., description="Тип файла: config | dataset | other")
    storage_type: str = Field(..., description="Тип хранилища: local | minio | s3")
    is_public: bool
    uploaded_by_user_id: UUID | None = None
    uploaded_by_guest_id: UUID | None = None
    created_at: datetime


class FileListResponse(BaseModel):
    """Список файлов с пагинацией."""

    items: list[FileMetaResponse]
    total: int
    offset: int
    limit: int


class FileUploadTaskStatusResponse(BaseModel):
    """Статус задачи обработки загруженного файла."""

    task_id: UUID = Field(..., description="ID задачи обработки файла")
    file_id: UUID | None = Field(None, description="ID загруженного файла (доступен сразу после загрузки)")
    status: str = Field(..., description="Статус задачи: pending | processing | completed | failed | cancelled")
    task_type: str = Field(..., description="Тип задачи: file_config_upload | file_dataset_upload")
    file_name: str | None = Field(None, description="Оригинальное имя файла")
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    result: dict[str, Any] | None = Field(
        None,
        description="Результат обработки: validation_errors, config_summary или dataset_info",
    )
