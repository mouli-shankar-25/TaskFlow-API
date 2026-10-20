"""Seed demo data for development and demonstration purposes.

Run with: python -m scripts.seed_demo
Requires: DATABASE_URL environment variable or .env file.
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.security import hash_password
from app.db.session import async_session_factory
from app.models.membership import MemberRole, ProjectMembership
from app.models.project import Project
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User


async def seed() -> None:
    """Create demo users, projects, memberships, and tasks."""
    async with async_session_factory() as db:
        try:
            # Create demo users
            alice = User(
                id=uuid4(),
                name="Alice Johnson",
                email="alice@example.com",
                password_hash=hash_password("Alice123!"),
                is_active=True,
            )
            bob = User(
                id=uuid4(),
                name="Bob Smith",
                email="bob@example.com",
                password_hash=hash_password("Bob12345!"),
                is_active=True,
            )
            charlie = User(
                id=uuid4(),
                name="Charlie Brown",
                email="charlie@example.com",
                password_hash=hash_password("Charlie1!"),
                is_active=True,
            )
            db.add_all([alice, bob, charlie])
            await db.flush()
            print(f"Created users: alice ({alice.id}), bob ({bob.id}), charlie ({charlie.id})")

            # Create projects
            project1 = Project(
                id=uuid4(),
                name="Website Redesign",
                description="Complete redesign of the company website with modern UI/UX.",
                owner_id=alice.id,
            )
            project2 = Project(
                id=uuid4(),
                name="Mobile App",
                description="Build a cross-platform mobile application.",
                owner_id=bob.id,
            )
            db.add_all([project1, project2])
            await db.flush()
            print(
                f"Created projects: {project1.name} ({project1.id}),\n"
                f"                  {project2.name} ({project2.id})"
            )

            # Create memberships
            memberships = [
                ProjectMembership(
                    project_id=project1.id, user_id=alice.id, role=MemberRole.OWNER.value
                ),
                ProjectMembership(
                    project_id=project1.id, user_id=bob.id, role=MemberRole.ADMIN.value
                ),
                ProjectMembership(
                    project_id=project1.id, user_id=charlie.id, role=MemberRole.MEMBER.value
                ),
                ProjectMembership(
                    project_id=project2.id, user_id=bob.id, role=MemberRole.OWNER.value
                ),
                ProjectMembership(
                    project_id=project2.id, user_id=alice.id, role=MemberRole.MEMBER.value
                ),
            ]
            db.add_all(memberships)
            await db.flush()
            print(f"Created {len(memberships)} memberships")

            # Create tasks for project 1
            now = datetime.now(UTC)
            tasks = [
                Task(
                    project_id=project1.id,
                    title="Design homepage mockup",
                    description="Create high-fidelity mockups for the new homepage.",
                    status=TaskStatus.IN_PROGRESS.value,
                    priority=TaskPriority.HIGH.value,
                    created_by=alice.id,
                    assignee_id=bob.id,
                    due_date=now + timedelta(days=7),
                ),
                Task(
                    project_id=project1.id,
                    title="Set up CI/CD pipeline",
                    description="Configure GitHub Actions for automated testing and deployment.",
                    status=TaskStatus.TODO.value,
                    priority=TaskPriority.MEDIUM.value,
                    created_by=alice.id,
                    assignee_id=charlie.id,
                    due_date=now + timedelta(days=14),
                ),
                Task(
                    project_id=project1.id,
                    title="Write API documentation",
                    description="Document all REST API endpoints with examples.",
                    status=TaskStatus.TODO.value,
                    priority=TaskPriority.LOW.value,
                    created_by=bob.id,
                    assignee_id=None,
                    due_date=now + timedelta(days=21),
                ),
                Task(
                    project_id=project1.id,
                    title="Fix navigation bug",
                    description="Navigation menu not working on mobile devices.",
                    status=TaskStatus.BLOCKED.value,
                    priority=TaskPriority.URGENT.value,
                    created_by=charlie.id,
                    assignee_id=alice.id,
                    due_date=now + timedelta(days=2),
                ),
                Task(
                    project_id=project1.id,
                    title="Database optimization",
                    description="Optimize slow queries and add missing indexes.",
                    status=TaskStatus.DONE.value,
                    priority=TaskPriority.HIGH.value,
                    created_by=alice.id,
                    assignee_id=bob.id,
                ),
                # Tasks for project 2
                Task(
                    project_id=project2.id,
                    title="Set up React Native project",
                    description="Initialize the React Native project with TypeScript.",
                    status=TaskStatus.DONE.value,
                    priority=TaskPriority.HIGH.value,
                    created_by=bob.id,
                    assignee_id=bob.id,
                ),
                Task(
                    project_id=project2.id,
                    title="Implement authentication screens",
                    description="Login, register, and forgot password screens.",
                    status=TaskStatus.IN_PROGRESS.value,
                    priority=TaskPriority.HIGH.value,
                    created_by=bob.id,
                    assignee_id=alice.id,
                    due_date=now + timedelta(days=10),
                ),
            ]
            db.add_all(tasks)
            await db.flush()
            print(f"Created {len(tasks)} tasks")

            await db.commit()
            print("\nDemo data seeded successfully!")
            print("\nDemo credentials:")
            print("  alice@example.com / Alice123!")
            print("  bob@example.com   / Bob12345!")
            print("  charlie@example.com / Charlie1!")

        except Exception as e:
            await db.rollback()
            print(f"Error seeding data: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(seed())
