import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    owned_projects = relationship("Project", back_populates="owner", lazy="selectin")
    memberships = relationship("ProjectMembership", back_populates="user", lazy="selectin")
    created_tasks = relationship(
        "Task", back_populates="creator", foreign_keys="Task.created_by", lazy="selectin"
    )
    assigned_tasks = relationship(
        "Task", back_populates="assignee", foreign_keys="Task.assignee_id", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
