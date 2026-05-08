from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GetProfileOverviewQuery(BaseModel):
    user_id: UUID


class UpdateProfileCommand(BaseModel):
    user_id: UUID
    first_name: str | None = None
    company: str | None = None
    timezone: str | None = None
    phone: str | None = None
    avatar_url: str | None = None


class DeleteChatHistoryCommand(BaseModel):
    user_id: UUID


class ProfileOverviewResult(BaseModel):
    id: UUID
    email: str
    first_name: str | None
    company: str | None
    timezone: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime
