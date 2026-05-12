from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    file_id: Annotated[UUID, Field(..., description="Unique file identifier")]
    file_url: Annotated[str, Field(..., description="URL to access the file")]


class UploadResponse(FileMetadata):
    file_key: str | None = None


class FetchUserFilesResponse(BaseModel):
    files: Annotated[list[FileMetadata], Field(..., description="List of user's uploaded files")]
