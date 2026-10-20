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
class TestListMembers:
    async def test_list_members(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="memowner@example.com")
        member = await create_test_user(test_session, email="memmember@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, member)
        headers = make_auth_header(owner.id)
        response = await client.get(f"/api/v1/projects/{project.id}/members", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_list_members_non_member(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="memowner2@example.com")
        outsider = await create_test_user(test_session, email="memoutsider@example.com")
        project = await create_test_project(test_session, owner)
        headers = make_auth_header(outsider.id)
        response = await client.get(f"/api/v1/projects/{project.id}/members", headers=headers)
        assert response.status_code == 404


@pytest.mark.asyncio
class TestAddMember:
    async def test_add_member_as_admin(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="addowner@example.com")
        admin = await create_test_user(test_session, email="addadmin@example.com")
        new_user = await create_test_user(test_session, email="addnew@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, admin, MemberRole.ADMIN)
        headers = make_auth_header(admin.id)
        response = await client.post(
            f"/api/v1/projects/{project.id}/members",
            json={"user_id": str(new_user.id), "role": "member"},
            headers=headers,
        )
        assert response.status_code == 201

    async def test_add_duplicate_member(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="dupeowner@example.com")
        member = await create_test_user(test_session, email="dupemember@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, member)
        headers = make_auth_header(owner.id)
        response = await client.post(
            f"/api/v1/projects/{project.id}/members",
            json={"user_id": str(member.id), "role": "member"},
            headers=headers,
        )
        assert response.status_code == 409

    async def test_add_member_as_regular_member_forbidden(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        owner = await create_test_user(test_session, email="addowner2@example.com")
        member = await create_test_user(test_session, email="regmember@example.com")
        new_user = await create_test_user(test_session, email="addnew2@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, member)
        headers = make_auth_header(member.id)
        response = await client.post(
            f"/api/v1/projects/{project.id}/members",
            json={"user_id": str(new_user.id), "role": "member"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_add_nonexistent_user(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="addowner3@example.com")
        project = await create_test_project(test_session, owner)
        headers = make_auth_header(owner.id)
        response = await client.post(
            f"/api/v1/projects/{project.id}/members",
            json={"user_id": str(uuid.uuid4()), "role": "member"},
            headers=headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestUpdateMemberRole:
    async def test_update_role_as_owner(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="roleowner@example.com")
        member = await create_test_user(test_session, email="rolemember@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, member)
        headers = make_auth_header(owner.id)
        response = await client.patch(
            f"/api/v1/projects/{project.id}/members/{member.id}",
            json={"role": "admin"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    async def test_cannot_change_owner_role(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="ownerrole@example.com")
        project = await create_test_project(test_session, owner)
        headers = make_auth_header(owner.id)
        response = await client.patch(
            f"/api/v1/projects/{project.id}/members/{owner.id}",
            json={"role": "admin"},
            headers=headers,
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestRemoveMember:
    async def test_remove_member_as_owner(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="rmowner@example.com")
        member = await create_test_user(test_session, email="rmmember@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, member)
        headers = make_auth_header(owner.id)
        response = await client.delete(
            f"/api/v1/projects/{project.id}/members/{member.id}",
            headers=headers,
        )
        assert response.status_code == 204

    async def test_cannot_remove_last_owner(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="lastowner@example.com")
        project = await create_test_project(test_session, owner)
        headers = make_auth_header(owner.id)
        response = await client.delete(
            f"/api/v1/projects/{project.id}/members/{owner.id}",
            headers=headers,
        )
        assert response.status_code == 400
