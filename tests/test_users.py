import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_test_user, make_auth_header


@pytest.mark.asyncio
class TestUserProfile:
    async def test_get_profile(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(
            test_session, email="profile@example.com", name="Profile User"
        )
        headers = make_auth_header(user.id)
        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Profile User"

    async def test_update_name(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="update@example.com", name="Old Name")
        headers = make_auth_header(user.id)
        response = await client.patch(
            "/api/v1/users/me", json={"name": "New Name"}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    async def test_update_profile_unauthenticated(self, client: AsyncClient):
        response = await client.patch("/api/v1/users/me", json={"name": "Hacker"})
        assert response.status_code in (401, 403)
