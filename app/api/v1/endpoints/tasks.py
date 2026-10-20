import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.membership import MemberRole
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.task import (
    TaskAssigneeUpdate,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services import project_service, task_service
from app.utils.pagination import paginate_response

router = APIRouter(tags=["Tasks"])


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    project_id: uuid.UUID,
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a task in a project. User must be a member."""
    membership = await project_service.get_user_membership(db, project_id, current_user.id)
    project_service.require_membership(membership)
    task = await task_service.create_task(
        db,
        project_id=project_id,
        title=body.title,
        created_by=current_user.id,
        description=body.description,
        status=body.status.value,
        priority=body.priority.value,
        assignee_id=body.assignee_id,
        due_date=body.due_date,
    )
    return task


@router.get("/projects/{project_id}/tasks", response_model=TaskListResponse)
async def list_tasks(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1, le=10000),
    limit: int = Query(20, ge=1, le=100),
    status: TaskStatus | None = Query(None),
    priority: TaskPriority | None = Query(None),
    assignee_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None, max_length=200),
    sort_by: str = Query(
        "created_at", pattern="^(created_at|updated_at|priority|due_date|title)$"
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    due_before: datetime | None = Query(None),
    due_after: datetime | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List tasks in a project with filtering, sorting, and pagination."""
    membership = await project_service.get_user_membership(db, project_id, current_user.id)
    project_service.require_membership(membership)
    tasks, total = await task_service.list_tasks(
        db,
        project_id=project_id,
        page=page,
        limit=limit,
        status=status.value if status else None,
        priority=priority.value if priority else None,
        assignee_id=assignee_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        due_before=due_before,
        due_after=due_after,
    )
    return paginate_response(tasks, total, page, limit)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get task details. User must be a member of the task's project."""
    task = await task_service.get_task(db, task_id)
    membership = await project_service.get_user_membership(db, task.project_id, current_user.id)
    project_service.require_membership(membership)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a task. Requires member role.
    Uses optimistic concurrency if expected_version provided.
    """
    task = await task_service.get_task(db, task_id)
    membership = await project_service.get_user_membership(db, task.project_id, current_user.id)
    project_service.require_membership(membership)

    updated = await task_service.update_task(
        db,
        task=task,
        project_id=task.project_id,
        title=body.title,
        description=body.description,
        status=body.status.value if body.status else None,
        priority=body.priority.value if body.priority else None,
        assignee_id=body.assignee_id if body.assignee_id is not None else ...,
        due_date=body.due_date if body.due_date is not None else ...,
        expected_version=body.expected_version,
    )
    return updated


@router.patch("/tasks/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: uuid.UUID,
    body: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update task status with concurrency control."""
    task = await task_service.get_task(db, task_id)
    membership = await project_service.get_user_membership(db, task.project_id, current_user.id)
    project_service.require_membership(membership)
    updated = await task_service.update_task_status(
        db, task, body.status.value, body.expected_version
    )
    return updated


@router.patch("/tasks/{task_id}/assignee", response_model=TaskResponse)
async def update_task_assignee(
    task_id: uuid.UUID,
    body: TaskAssigneeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update task assignee with concurrency control. Assignee must be a project member."""
    task = await task_service.get_task(db, task_id)
    membership = await project_service.get_user_membership(db, task.project_id, current_user.id)
    project_service.require_membership(membership)
    updated = await task_service.update_task_assignee(
        db, task, body.assignee_id, body.expected_version
    )
    return updated


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task. Requires admin or owner role in the project."""
    task = await task_service.get_task(db, task_id)
    membership = await project_service.get_user_membership(db, task.project_id, current_user.id)
    project_service.require_membership(membership, min_role=MemberRole.ADMIN)
    await task_service.delete_task(db, task)
