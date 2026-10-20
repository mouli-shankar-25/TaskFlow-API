import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.membership import MemberRole


class AddMemberRequest(BaseModel):
    user_id: uuid.UUID
    role: MemberRole = MemberRole.MEMBER


class UpdateMemberRoleRequest(BaseModel):
    role: MemberRole


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime
    user_name: str | None = None
    user_email: str | None = None
