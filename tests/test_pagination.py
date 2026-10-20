import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_test_project,
    create_test_task,
    create_test_user,
    make_auth_header,
)


@pytest.mark.asyncio
class TestPagination:
    async def test_default_pagination(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="defpage@example.com")
        project = await create_test_project(test_session, user)
        for i in range(25):
            await create_test_task(test_session, project, user, title=f"Task {i}")
        headers = make_auth_header(user.id)
        response = await client.get(f"/api/v1/projects/{project.id}/tasks", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 20  # default limit
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["total_pages"] == 2

    async def test_custom_pagination(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="custpage@example.com")
        project = await create_test_project(test_session, user)
        for i in range(10):
            await create_test_task(test_session, project, user, title=f"Task {i}")
        headers = make_auth_header(user.id)
        response = await client.get(
            f"/api/v1/projects/{project.id}/tasks?page=2&limit=3", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["page"] == 2

    async def test_invalid_page_rejected(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="badpage@example.com")
        project = await create_test_project(test_session, user)
        headers = make_auth_header(user.id)
        response = await client.get(f"/api/v1/projects/{project.id}/tasks?page=0", headers=headers)
        assert response.status_code == 422

    async def test_invalid_limit_rejected(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="badlimit@example.com")
        project = await create_test_project(test_session, user)
        headers = make_auth_header(user.id)
        response = await client.get(
            f"/api/v1/projects/{project.id}/tasks?limit=200", headers=headers
        )
        assert response.status_code == 422

    async def test_project_list_pagination(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="projpage@example.com")
        for i in range(5):
            await create_test_project(test_session, user, name=f"Project {i}")
        headers = make_auth_header(user.id)
        response = await client.get("/api/v1/projects?page=1&limit=2", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
