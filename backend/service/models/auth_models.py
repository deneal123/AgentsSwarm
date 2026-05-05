from uuid import UUID

from pydantic import BaseModel

from service.models.key_value import UserTypes


class AuthProfile(BaseModel):
    user_id: UUID
    fingerprint: str | None
    type: UserTypes
