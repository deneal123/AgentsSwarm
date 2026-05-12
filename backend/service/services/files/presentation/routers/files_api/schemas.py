from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from service.models.key_value import ServiceType
from service.services.files.application.dto import (
    FetchUserFilesResponse,
    FileMetadata,
    UploadResponse,
)


class FetchModesResponse(BaseModel):
    modes: Annotated[
        list[ServiceType], Field(..., description="Available service processing modes")
    ]


class PresignRequest(BaseModel):
    filename: Annotated[str, Field(..., description="Original filename")]
    expiry_sec: Annotated[int | None, Field(None, description="Expiry seconds for presigned URL")] = None


class PresignResponse(BaseModel):
    file_id: Annotated[UUID, Field(..., description="Temporary file id")]
    file_key: Annotated[str, Field(..., description="Storage file key")]
    upload_url: Annotated[str, Field(..., description="Presigned upload URL")]
    expires_in: Annotated[int | None, Field(None, description="Expiry seconds")]


class CallbackRequest(BaseModel):
    file_key: Annotated[str, Field(..., description="Storage file key created by presign flow")]
    mode: Annotated[ServiceType, Field(..., description="Service mode used for file")]


class FileDetailResponse(BaseModel):
    file_id: Annotated[UUID, Field(..., description="File id")]
    file_url: Annotated[str, Field(..., description="Stored file URL")]
    download_url: Annotated[str | None, Field(None, description="Presigned download URL if available")]


__all__ = [
    "FileMetadata",
    "UploadResponse",
    "FetchUserFilesResponse",
    "FetchModesResponse",
    "PresignRequest",
    "PresignResponse",
    "CallbackRequest",
    "FileDetailResponse",
]
