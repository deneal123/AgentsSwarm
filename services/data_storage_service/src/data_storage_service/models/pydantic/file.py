"""
Pydantic models for file handling (Pushi)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from service.models.enums import FileType, StorageType


class FileUploadRequest(BaseModel):
    """File upload request schema"""

    file_name: str = Field(max_length=255, description="Original filename")
    file_size: int = Field(gt=0, description="File size in bytes")
    mime_type: str = Field(max_length=100, description="MIME type")
    file_type: FileType = Field(
        default=FileType.RESULT_JSON, description="File category type"
    )


class FileResponse(BaseModel):
    """File metadata response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    file_size: int
    mime_type: str
    file_type: FileType
    storage_type: StorageType
    storage_path: str
    is_public: bool = False
    uploaded_at: datetime | None


class FileMetadataLogic(BaseModel):
    """File metadata for internal logic"""

    model_config = ConfigDict(from_attributes=True)

    file_id: UUID
    file_url: str
