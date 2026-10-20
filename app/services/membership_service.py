import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.membership import MemberRole, ProjectMembership
from app.models.user import User


async def list_members(db: AsyncSession, project_id: uuid.UUID) -> list[ProjectMembership]:
    """List all members of a project ordered by joined_at."""
    stmt = (
        select(ProjectMembership)
        .where(ProjectMembership.project_id == project_id)
        .order_by(ProjectMembership.joined_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_member(
    db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID
) -> ProjectMembership | None:
    """Get a specific project membership."""
    stmt = select(ProjectMembership).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def add_member(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    role: MemberRole | str = MemberRole.MEMBER,
) -> ProjectMembership:
    """Add a member to a project. Raises ConflictError if duplicate."""
    # Verify user exists
    user = await db.get(User, user_id)
    if not user:
        raise NotFoundError("User")

    # Check duplicate
    stmt = select(ProjectMembership).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == user_id,
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError("User is already a member of this project")

    role_val = role.value if isinstance(role, MemberRole) else role

    # Don't allow adding someone as owner (owner is set at creation)
    if role_val == MemberRole.OWNER.value:
        raise BadRequestError("Cannot add a member with owner role")

    membership = ProjectMembership(
        project_id=project_id,
        user_id=user_id,
        role=role_val,
    )
    membership.user = user
    db.add(membership)
    await db.flush()
    return membership


async def update_member_role(
    db: AsyncSession,
    project_id: uuid.UUID,
    target_user_id: uuid.UUID,
    new_role: MemberRole | str,
) -> ProjectMembership:
    """Update a member's role. Cannot change to/from owner."""
    stmt = select(ProjectMembership).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == target_user_id,
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()
    if not membership:
        raise NotFoundError("Membership")

    new_role_val = new_role.value if isinstance(new_role, MemberRole) else new_role

    # Prevent changing owner role
    if membership.role == MemberRole.OWNER.value:
        raise ForbiddenError("Cannot change the role of the project owner")

    if new_role_val == MemberRole.OWNER.value:
        raise BadRequestError("Cannot promote a member to owner")

    membership.role = new_role_val
    db.add(membership)
    await db.flush()
    return membership


async def remove_member(
    db: AsyncSession,
    project_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> None:
    """Remove a member from a project. Cannot remove the last owner."""
    stmt = select(ProjectMembership).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == target_user_id,
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()
    if not membership:
        raise NotFoundError("Membership")

    # Prevent removing the last owner
    if membership.role == MemberRole.OWNER.value:
        owner_count_stmt = (
            select(func.count())
            .select_from(ProjectMembership)
            .where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.role == MemberRole.OWNER.value,
            )
        )
        owner_count = (await db.execute(owner_count_stmt)).scalar_one()
        if owner_count <= 1:
            raise BadRequestError("Cannot remove the last owner of the project")

    await db.delete(membership)
    await db.flush()
