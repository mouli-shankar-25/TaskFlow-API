import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.membership import MemberRole
from app.models.user import User
from app.schemas.membership import AddMemberRequest, MembershipResponse, UpdateMemberRoleRequest
from app.services import membership_service, project_service

router = APIRouter(prefix="/projects/{project_id}/members", tags=["Project Members"])


def _membership_to_response(m) -> MembershipResponse:
    """Convert a ProjectMembership ORM object to response schema."""
    return MembershipResponse(
        id=m.id,
        project_id=m.project_id,
        user_id=m.user_id,
        role=m.role,
        joined_at=m.joined_at,
        user_name=m.user.name if m.user else None,
        user_email=m.user.email if m.user else None,
    )


@router.get("", response_model=list[MembershipResponse])
async def list_members(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all members of a project. User must be a member."""
    membership = await project_service.get_user_membership(db, project_id, current_user.id)
    project_service.require_membership(membership)
    members = await membership_service.list_members(db, project_id)
    return [_membership_to_response(m) for m in members]


@router.post("", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    project_id: uuid.UUID,
    body: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a member to a project. Requires admin or owner role."""
    membership = await project_service.get_user_membership(db, project_id, current_user.id)
    project_service.require_membership(membership, min_role=MemberRole.ADMIN)
    new_member = await membership_service.add_member(db, project_id, body.user_id, body.role)
    # Refresh to get user relationship
    await db.refresh(new_member, ["user"])
    return _membership_to_response(new_member)


@router.patch("/{user_id}", response_model=MembershipResponse)
async def update_member_role(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    body: UpdateMemberRoleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a member's role. Requires owner role."""
    membership = await project_service.get_user_membership(db, project_id, current_user.id)
    project_service.require_membership(membership, min_role=MemberRole.OWNER)
    updated = await membership_service.update_member_role(db, project_id, user_id, body.role)
    await db.refresh(updated, ["user"])
    return _membership_to_response(updated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from a project. Requires admin or owner role."""
    membership = await project_service.get_user_membership(db, project_id, current_user.id)
    project_service.require_membership(membership, min_role=MemberRole.ADMIN)
    await membership_service.remove_member(db, project_id, user_id)
