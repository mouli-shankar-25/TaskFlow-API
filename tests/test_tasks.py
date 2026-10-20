import uuid

import pytest
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
class TestTaskCreate:
    async def test_create_task(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="taskcreator@example.com")
        project = await create_test_project(test_session, user)
        headers = make_auth_header(user.id)
        response = await client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "New Task", "priority": "high"},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Task"
        assert data["priority"] == "high"
        assert data["status"] == "todo"
        assert data["version"] == 1

    async def test_create_task_with_assignee(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        owner = await create_test_user(test_session, email="taskowner@example.com")
        member = await create_test_user(test_session, email="taskassignee@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, member)
        headers = make_auth_header(owner.id)
        response = await client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "Assigned Task", "assignee_id": str(member.id)},
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["assignee_id"] == str(member.id)

    async def test_create_task_non_member_assignee(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        owner = await create_test_user(test_session, email="taskowner2@example.com")
        outsider = await create_test_user(test_session, email="taskoutsider@example.com")
        project = await create_test_project(test_session, owner)
        headers = make_auth_header(owner.id)
        response = await client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "Bad Assign", "assignee_id": str(outsider.id)},
            headers=headers,
        )
        assert response.status_code == 400

    async def test_create_task_as_non_member(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        owner = await create_test_user(test_session, email="taskowner3@example.com")
        outsider = await create_test_user(test_session, email="taskoutsider2@example.com")
        project = await create_test_project(test_session, owner)
        headers = make_auth_header(outsider.id)
        response = await client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "Unauthorized Task"},
            headers=headers,
        )
        assert response.status_code == 404

    async def test_create_task_invalid_priority(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        user = await create_test_user(test_session, email="taskprio@example.com")
        project = await create_test_project(test_session, user)
        headers = make_auth_header(user.id)
        response = await client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "Bad Priority", "priority": "critical"},
            headers=headers,
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestTaskList:
    async def test_list_tasks(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="tasklister@example.com")
        project = await create_test_project(test_session, user)
        await create_test_task(test_session, project, user, title="Task 1")
        await create_test_task(test_session, project, user, title="Task 2")
        headers = make_auth_header(user.id)
        response = await client.get(
            f"/api/v1/projects/{project.id}/tasks",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_filter_by_status(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="filterstatus@example.com")
        project = await create_test_project(test_session, user)
        await create_test_task(test_session, project, user, title="Todo", status="todo")
        await create_test_task(test_session, project, user, title="Done", status="done")
        headers = make_auth_header(user.id)
        response = await client.get(
            f"/api/v1/projects/{project.id}/tasks?status=done",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "done"

    async def test_search_by_title(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="searchtitle@example.com")
        project = await create_test_project(test_session, user)
        await create_test_task(test_session, project, user, title="Fix login bug")
        await create_test_task(test_session, project, user, title="Add feature")
        headers = make_auth_header(user.id)
        response = await client.get(
            f"/api/v1/projects/{project.id}/tasks?search=login",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_pagination(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="paginate@example.com")
        project = await create_test_project(test_session, user)
        for i in range(5):
            await create_test_task(test_session, project, user, title=f"Task {i}")
        headers = make_auth_header(user.id)
        response = await client.get(
            f"/api/v1/projects/{project.id}/tasks?page=1&limit=2",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["total_pages"] == 3


@pytest.mark.asyncio
class TestTaskUpdate:
    async def test_update_task(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="taskupdater@example.com")
        project = await create_test_project(test_session, user)
        task = await create_test_task(test_session, project, user)
        headers = make_auth_header(user.id)
        response = await client.patch(
            f"/api/v1/tasks/{task.id}",
            json={"title": "Updated Title", "expected_version": 1},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
        assert response.json()["version"] == 2

    async def test_update_task_stale_version(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        user = await create_test_user(test_session, email="staleupdater@example.com")
        project = await create_test_project(test_session, user)
        task = await create_test_task(test_session, project, user)
        headers = make_auth_header(user.id)
        # First update succeeds
        await client.patch(
            f"/api/v1/tasks/{task.id}",
            json={"title": "First Update", "expected_version": 1},
            headers=headers,
        )
        # Second update with old version fails
        response = await client.patch(
            f"/api/v1/tasks/{task.id}",
            json={"title": "Stale Update", "expected_version": 1},
            headers=headers,
        )
        assert response.status_code == 409


@pytest.mark.asyncio
class TestTaskStatusUpdate:
    async def test_update_status(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="statusupd@example.com")
        project = await create_test_project(test_session, user)
        task = await create_test_task(test_session, project, user)
        headers = make_auth_header(user.id)
        response = await client.patch(
            f"/api/v1/tasks/{task.id}/status",
            json={"status": "in_progress", "expected_version": 1},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"


@pytest.mark.asyncio
class TestTaskAssignee:
    async def test_update_assignee(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="assignowner@example.com")
        member = await create_test_user(test_session, email="assignmember@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, member)
        task = await create_test_task(test_session, project, owner)
        headers = make_auth_header(owner.id)
        response = await client.patch(
            f"/api/v1/tasks/{task.id}/assignee",
            json={"assignee_id": str(member.id), "expected_version": 1},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["assignee_id"] == str(member.id)

    async def test_assign_non_member_rejected(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        owner = await create_test_user(test_session, email="assignowner2@example.com")
        outsider = await create_test_user(test_session, email="assignoutsider@example.com")
        project = await create_test_project(test_session, owner)
        task = await create_test_task(test_session, project, owner)
        headers = make_auth_header(owner.id)
        response = await client.patch(
            f"/api/v1/tasks/{task.id}/assignee",
            json={"assignee_id": str(outsider.id), "expected_version": 1},
            headers=headers,
        )
        assert response.status_code == 400


@pytest.mark.asyncio
class TestTaskDelete:
    async def test_delete_task_as_admin(self, client: AsyncClient, test_session: AsyncSession):
        owner = await create_test_user(test_session, email="delowner@example.com")
        project = await create_test_project(test_session, owner)
        task = await create_test_task(test_session, project, owner)
        headers = make_auth_header(owner.id)
        response = await client.delete(f"/api/v1/tasks/{task.id}", headers=headers)
        assert response.status_code == 204

    async def test_delete_task_as_member_forbidden(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        owner = await create_test_user(test_session, email="delowner2@example.com")
        member = await create_test_user(test_session, email="delmember@example.com")
        project = await create_test_project(test_session, owner)
        await add_test_member(test_session, project, member)
        task = await create_test_task(test_session, project, owner)
        headers = make_auth_header(member.id)
        response = await client.delete(f"/api/v1/tasks/{task.id}", headers=headers)
        assert response.status_code == 403

    async def test_get_nonexistent_task(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="nonexisttask@example.com")
        headers = make_auth_header(user.id)
        response = await client.get(f"/api/v1/tasks/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404
