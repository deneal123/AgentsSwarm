from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserProfileLogic(BaseModel):
    id: UUID
    email: str
    password_hash: str
    available_launches: int = 0
    first_name: str | None = None
    timezone: str | None = None
    avatar_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)



