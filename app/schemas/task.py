import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.task import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = Field(None, max_length=5000)
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: uuid.UUID | None = None
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        return v.strip()


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = Field(None, max_length=5000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: uuid.UUID | None = None
    due_date: datetime | None = None
    expected_version: int | None = Field(None, description="For optimistic concurrency control")

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip()
        return v


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    expected_version: int = Field(..., description="Current version for concurrency check")


class TaskAssigneeUpdate(BaseModel):
    assignee_id: uuid.UUID | None = None
    expected_version: int = Field(..., description="Current version for concurrency check")


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    status: str
    priority: str
    created_by: uuid.UUID
    assignee_id: uuid.UUID | None
    due_date: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    limit: int
    total_pages: int
