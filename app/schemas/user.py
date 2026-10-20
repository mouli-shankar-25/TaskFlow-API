import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserBrief(BaseModel):
    """Minimal user info for embedding in other responses."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    email: str


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip()
        return v
