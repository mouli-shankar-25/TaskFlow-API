import sqlite3
import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.membership import MemberRole, ProjectMembership
from app.models.project import Project
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# Ensure sqlite can adapt Python UUID objects
sqlite3.register_adapter(uuid.UUID, lambda u: str(u))

# Test database URL - SQLite for fast isolated tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///"


@pytest_asyncio.fixture()
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def client(test_engine, test_session) -> AsyncGenerator[AsyncClient, None]:
    """Create an HTTPX test client."""
    app = create_app()

    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# Helper functions
def make_auth_header(user_id: uuid.UUID) -> dict:
    """Create an Authorization header with a valid JWT."""
    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


async def create_test_user(
    session: AsyncSession,
    name: str = "Test User",
    email: str = "test@example.com",
    password: str = "TestPass123",
    is_active: bool = True,
) -> User:
    """Create and persist a test user."""
    user = User(
        id=uuid.uuid4(),
        name=name,
        email=email.lower(),
        password_hash=hash_password(password),
        is_active=is_active,
    )
    session.add(user)
    await session.flush()
    return user


async def create_test_project(
    session: AsyncSession,
    owner: User,
    name: str = "Test Project",
    description: str = "A test project",
) -> Project:
    """Create a project with owner membership."""
    project = Project(
        id=uuid.uuid4(),
        name=name,
        description=description,
        owner_id=owner.id,
    )
    session.add(project)
    await session.flush()

    membership = ProjectMembership(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=owner.id,
        role=MemberRole.OWNER.value,
    )
    session.add(membership)
    await session.flush()
    return project


async def add_test_member(
    session: AsyncSession,
    project: Project,
    user: User,
    role: MemberRole = MemberRole.MEMBER,
) -> ProjectMembership:
    """Add a member to a project."""
    membership = ProjectMembership(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=user.id,
        role=role.value,
    )
    session.add(membership)
    await session.flush()
    return membership


async def create_test_task(
    session: AsyncSession,
    project: Project,
    creator: User,
    title: str = "Test Task",
    status: str = TaskStatus.TODO.value,
    priority: str = TaskPriority.MEDIUM.value,
    assignee_id: uuid.UUID | None = None,
) -> Task:
    """Create a test task."""
    task = Task(
        id=uuid.uuid4(),
        project_id=project.id,
        title=title,
        status=status,
        priority=priority,
        created_by=creator.id,
        assignee_id=assignee_id,
    )
    session.add(task)
    await session.flush()
    return task
