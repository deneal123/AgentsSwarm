from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserProfileLogic(BaseModel):
    id: UUID
    email: str
    password_hash: str
    first_name: str | None
    company: str | None = None  # Make company optional with default None
    timezone: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)



