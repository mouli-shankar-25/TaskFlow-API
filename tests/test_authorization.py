import pytest
from app.models.membership import MemberRole
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    add_test_member,
    create_test_project,
    create_test_task,
    create_test_user,
    make_auth_header,
)


@pytest.mark.asyncio
class TestCrossProjectAccess:
    async def test_cannot_access_other_project_tasks(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        user1 = await create_test_user(test_session, email="cross1@example.com")
        user2 = await create_test_user(test_session, email="cross2@example.com")
        project1 = await create_test_project(test_session, user1, name="P1")
        await create_test_project(test_session, user2, name="P2")
        task = await create_test_task(test_session, project1, user1)
        # user2 tries to access task in project1
        headers = make_auth_header(user2.id)
        response = await client.get(f"/api/v1/tasks/{task.id}", headers=headers)
        assert response.status_code == 404

    async def test_cannot_create_task_in_other_project(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        user1 = await create_test_user(test_session, email="cross3@example.com")
        user2 = await create_test_user(test_session, email="cross4@example.com")
        project = await create_test_project(test_session, user1)
        headers = make_auth_header(user2.id)
        response = await client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "Unauthorized"},
            headers=headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestRoleEnforcement:
    async def test_member_cannot_delete_project(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        owner = await create_test_user(test_session, email="roleowner@example.com")
        member = await create_test_user(test_session, email="rolemember@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, member)
        headers = make_auth_header(member.id)
        response = await client.delete(f"/api/v1/projects/{project.id}", headers=headers)
        assert response.status_code == 403

    async def test_admin_can_add_members(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="roleowner2@example.com")
        admin = await create_test_user(test_session, email="roleadmin@example.com")
        new_user = await create_test_user(test_session, email="rolenew@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, admin, MemberRole.ADMIN)
        headers = make_auth_header(admin.id)
        response = await client.post(
            f"/api/v1/projects/{project.id}/members",
            json={"user_id": str(new_user.id), "role": "member"},
            headers=headers,
        )
        assert response.status_code == 201
