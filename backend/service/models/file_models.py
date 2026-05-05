from uuid import UUID

from pydantic import BaseModel


class FileMetadataLogic(BaseModel):
    file_id: UUID
    file_url: str
