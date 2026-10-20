import uuid
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.membership import ProjectMembership
from app.models.task import Task, TaskPriority, TaskStatus


async def create_task(
    db: AsyncSession,
    project_id: uuid.UUID,
    title: str,
    created_by: uuid.UUID,
    description: str | None = None,
    status: str | TaskStatus = TaskStatus.TODO.value,
    priority: str | TaskPriority = TaskPriority.MEDIUM.value,
    assignee_id: uuid.UUID | None = None,
    due_date: datetime | None = None,
) -> Task:
    """Create a task. Assignee must be a project member."""
    if assignee_id:
        await _verify_project_member(db, project_id, assignee_id)

    status_val = status.value if hasattr(status, "value") else status
    priority_val = priority.value if hasattr(priority, "value") else priority

    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        status=status_val,
        priority=priority_val,
        created_by=created_by,
        assignee_id=assignee_id,
        due_date=due_date,
    )
    db.add(task)
    await db.flush()
    return task


async def get_task(db: AsyncSession, task_id: uuid.UUID) -> Task:
    """Fetch a task by ID or raise NotFoundError."""
    stmt = select(Task).where(Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task")
    return task


async def list_tasks(
    db: AsyncSession,
    project_id: uuid.UUID,
    page: int = 1,
    limit: int = 20,
    status: str | TaskStatus | None = None,
    priority: str | TaskPriority | None = None,
    assignee_id: uuid.UUID | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    due_before: datetime | None = None,
    due_after: datetime | None = None,
) -> tuple[list[Task], int]:
    """List tasks with filtering, searching, sorting, and pagination."""
    base = select(Task).where(Task.project_id == project_id)
    count_base = select(func.count()).select_from(Task).where(Task.project_id == project_id)

    filters = []
    if status is not None:
        status_val = status.value if hasattr(status, "value") else status
        filters.append(Task.status == status_val)
    if priority is not None:
        priority_val = priority.value if hasattr(priority, "value") else priority
        filters.append(Task.priority == priority_val)
    if assignee_id is not None:
        filters.append(Task.assignee_id == assignee_id)
    if search:
        filters.append(Task.title.ilike(f"%{search}%"))
    if due_before:
        filters.append(Task.due_date <= due_before)
    if due_after:
        filters.append(Task.due_date >= due_after)

    if filters:
        combined = and_(*filters)
        base = base.where(combined)
        count_base = count_base.where(combined)

    # Count
    total = (await db.execute(count_base)).scalar_one()

    # Sorting
    allowed_sort = {
        "created_at": Task.created_at,
        "updated_at": Task.updated_at,
        "priority": Task.priority,
        "due_date": Task.due_date,
        "title": Task.title,
    }
    sort_col = allowed_sort.get(sort_by, Task.created_at)
    base = base.order_by(sort_col.asc()) if sort_order == "asc" else base.order_by(sort_col.desc())

    offset = (page - 1) * limit
    base = base.offset(offset).limit(limit)

    result = await db.execute(base)
    tasks = list(result.scalars().all())
    return tasks, total


async def update_task(
    db: AsyncSession,
    task: Task,
    project_id: uuid.UUID,
    title: str | None = None,
    description: str | None = None,
    status: str | TaskStatus | None = None,
    priority: str | TaskPriority | None = None,
    assignee_id: uuid.UUID | None = ...,  # sentinel: ... means 'not provided'
    due_date: datetime | None = ...,
    expected_version: int | None = None,
) -> Task:
    """Update task with optimistic concurrency control."""
    # Concurrency check
    if expected_version is not None and task.version != expected_version:
        raise ConflictError(
            f"Task has been modified. Current version: {task.version}, "
            f"expected: {expected_version}"
        )

    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if status is not None:
        task.status = status.value if hasattr(status, "value") else status
    if priority is not None:
        task.priority = priority.value if hasattr(priority, "value") else priority
    if assignee_id is not ...:
        if assignee_id is not None:
            await _verify_project_member(db, project_id, assignee_id)
        task.assignee_id = assignee_id
    if due_date is not ...:
        task.due_date = due_date

    task.version += 1
    db.add(task)
    await db.flush()
    return task


async def update_task_status(
    db: AsyncSession,
    task: Task,
    new_status: str | TaskStatus,
    expected_version: int,
) -> Task:
    """Update task status with optimistic concurrency."""
    if task.version != expected_version:
        raise ConflictError(
            f"Task has been modified. Current version: {task.version}, "
            f"expected: {expected_version}"
        )
    task.status = new_status.value if hasattr(new_status, "value") else new_status
    task.version += 1
    db.add(task)
    await db.flush()
    return task


async def update_task_assignee(
    db: AsyncSession,
    task: Task,
    assignee_id: uuid.UUID | None,
    expected_version: int,
) -> Task:
    """Update task assignee with concurrency control."""
    if task.version != expected_version:
        raise ConflictError(
            f"Task has been modified. Current version: {task.version}, "
            f"expected: {expected_version}"
        )
    if assignee_id is not None:
        await _verify_project_member(db, task.project_id, assignee_id)
    task.assignee_id = assignee_id
    task.version += 1
    db.add(task)
    await db.flush()
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    """Delete a task."""
    await db.delete(task)
    await db.flush()


async def _verify_project_member(
    db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Verify a user is a member of the project."""
    stmt = select(ProjectMembership).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == user_id,
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise BadRequestError("Assignee must be a member of the project")
