import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.membership import MemberRole, ProjectMembership
from app.models.project import Project


async def create_project(
    db: AsyncSession, name: str, description: str | None, owner_id: uuid.UUID
) -> Project:
    """Create project and add owner membership in one transaction."""
    project = Project(name=name, description=description, owner_id=owner_id)
    db.add(project)
    await db.flush()

    membership = ProjectMembership(
        project_id=project.id,
        user_id=owner_id,
        role=MemberRole.OWNER.value,
    )
    db.add(membership)
    await db.flush()
    return project


async def list_user_projects(
    db: AsyncSession, user_id: uuid.UUID, page: int = 1, limit: int = 20
) -> tuple[list[Project], int]:
    """List projects the user is a member of."""
    # Count
    count_stmt = (
        select(func.count())
        .select_from(Project)
        .join(ProjectMembership, ProjectMembership.project_id == Project.id)
        .where(ProjectMembership.user_id == user_id)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    # Fetch
    offset = (page - 1) * limit
    stmt = (
        select(Project)
        .join(ProjectMembership, ProjectMembership.project_id == Project.id)
        .where(ProjectMembership.user_id == user_id)
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    projects = list(result.scalars().all())
    return projects, total


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Project:
    """Fetch a project by ID or raise NotFoundError."""
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project")
    return project


async def get_user_membership(
    db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID
) -> ProjectMembership | None:
    """Fetch project membership for a specific user and project."""
    stmt = select(ProjectMembership).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def require_membership(
    membership: ProjectMembership | None, min_role: MemberRole | str | None = None
) -> ProjectMembership:
    """Verify user has a membership. Optionally check minimum role."""
    if not membership:
        raise NotFoundError("Project")  # 404 to not reveal project existence

    if min_role:
        role_hierarchy = {MemberRole.MEMBER: 0, MemberRole.ADMIN: 1, MemberRole.OWNER: 2}
        user_role = (
            MemberRole(membership.role) if isinstance(membership.role, str) else membership.role
        )
        req_role = MemberRole(min_role) if isinstance(min_role, str) else min_role
        user_level = role_hierarchy.get(user_role, -1)
        required_level = role_hierarchy.get(req_role, 99)
        if user_level < required_level:
            raise ForbiddenError("Insufficient permissions for this operation")

    return membership


async def update_project(
    db: AsyncSession, project: Project, name: str | None = None, description: str | None = None
) -> Project:
    """Update project details."""
    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    db.add(project)
    await db.flush()
    return project


async def delete_project(db: AsyncSession, project: Project) -> None:
    """Delete a project."""
    await db.delete(project)
    await db.flush()
