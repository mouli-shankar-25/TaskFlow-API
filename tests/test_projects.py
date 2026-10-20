import uuid

import pytest
from app.models.membership import MemberRole
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    add_test_member,
    create_test_project,
    create_test_user,
    make_auth_header,
)


@pytest.mark.asyncio
class TestProjectCreate:
    async def test_create_project(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="projcreator@example.com")
        headers = make_auth_header(user.id)
        response = await client.post(
            "/api/v1/projects",
            json={
                "name": "My Project",
                "description": "A great project",
            },
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Project"
        assert data["owner_id"] == str(user.id)

    async def test_create_project_unauthenticated(self, client: AsyncClient):
        response = await client.post("/api/v1/projects", json={"name": "Fail"})
        assert response.status_code in (401, 403)

    async def test_create_project_missing_name(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        user = await create_test_user(test_session, email="missingname@example.com")
        headers = make_auth_header(user.id)
        response = await client.post("/api/v1/projects", json={}, headers=headers)
        assert response.status_code == 422


@pytest.mark.asyncio
class TestProjectList:
    async def test_list_own_projects(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="lister@example.com")
        await create_test_project(test_session, user, name="P1")
        await create_test_project(test_session, user, name="P2")
        headers = make_auth_header(user.id)
        response = await client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_excludes_other_users_projects(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        user1 = await create_test_user(test_session, email="user1@example.com")
        user2 = await create_test_user(test_session, email="user2@example.com")
        await create_test_project(test_session, user1, name="User1 Project")
        headers = make_auth_header(user2.id)
        response = await client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0


@pytest.mark.asyncio
class TestProjectDetail:
    async def test_get_project_as_member(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="detailowner@example.com")
        project = await create_test_project(test_session, owner)
        headers = make_auth_header(owner.id)
        response = await client.get(f"/api/v1/projects/{project.id}", headers=headers)
        assert response.status_code == 200

    async def test_get_project_as_non_member(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        owner = await create_test_user(test_session, email="detailowner2@example.com")
        outsider = await create_test_user(test_session, email="outsider@example.com")
        project = await create_test_project(test_session, owner)
        headers = make_auth_header(outsider.id)
        response = await client.get(f"/api/v1/projects/{project.id}", headers=headers)
        assert response.status_code == 404

    async def test_get_nonexistent_project(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="nonexist@example.com")
        headers = make_auth_header(user.id)
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/v1/projects/{fake_id}", headers=headers)
        assert response.status_code == 404


@pytest.mark.asyncio
class TestProjectUpdate:
    async def test_update_as_owner(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="updowner@example.com")
        project = await create_test_project(test_session, owner)
        headers = make_auth_header(owner.id)
        response = await client.patch(
            f"/api/v1/projects/{project.id}",
            json={"name": "Updated Name"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    async def test_update_as_member_forbidden(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        owner = await create_test_user(test_session, email="updowner2@example.com")
        member = await create_test_user(test_session, email="updmember@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, member, MemberRole.MEMBER)
        headers = make_auth_header(member.id)
        response = await client.patch(
            f"/api/v1/projects/{project.id}",
            json={"name": "Hacked"},
            headers=headers,
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestProjectDelete:
    async def test_delete_as_owner(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="delowner@example.com")
        project = await create_test_project(test_session, owner)
        headers = make_auth_header(owner.id)
        response = await client.delete(f"/api/v1/projects/{project.id}", headers=headers)
        assert response.status_code == 204

    async def test_delete_as_admin_forbidden(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        owner = await create_test_user(test_session, email="delowner2@example.com")
        admin = await create_test_user(test_session, email="deladmin@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, admin, MemberRole.ADMIN)
        headers = make_auth_header(admin.id)
        response = await client.delete(f"/api/v1/projects/{project.id}", headers=headers)
        assert response.status_code == 403
