import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.membership import MemberRole
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate
from app.services import project_service
from app.utils.pagination import paginate_response

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project. The creator becomes the owner."""
    project = await project_service.create_project(
        db, body.name, body.description, current_user.id
    )
    return project


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1, le=10000),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List projects the current user is a member of."""
    projects, total = await project_service.list_user_projects(db, current_user.id, page, limit)
    return paginate_response(projects, total, page, limit)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get project details. User must be a member."""
    membership = await project_service.get_user_membership(db, project_id, current_user.id)
    project_service.require_membership(membership)
    project = await project_service.get_project(db, project_id)
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update project. Requires admin or owner role."""
    membership = await project_service.get_user_membership(db, project_id, current_user.id)
    project_service.require_membership(membership, min_role=MemberRole.ADMIN)
    project = await project_service.get_project(db, project_id)
    updated = await project_service.update_project(db, project, body.name, body.description)
    return updated


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete project. Requires owner role. Cascades to memberships and tasks."""
    membership = await project_service.get_user_membership(db, project_id, current_user.id)
    project_service.require_membership(membership, min_role=MemberRole.OWNER)
    project = await project_service.get_project(db, project_id)
    await project_service.delete_project(db, project)
