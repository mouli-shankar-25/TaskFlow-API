from datetime import timedelta

import pytest
from app.core.security import create_access_token
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_test_user, make_auth_header


@pytest.mark.asyncio
class TestRegistration:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "NewPass123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert "password_hash" not in data
        assert "password" not in data
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient, test_session: AsyncSession):
        await create_test_user(test_session, email="dupe@example.com")
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Another User",
                "email": "dupe@example.com",
                "password": "NewPass123",
            },
        )
        assert response.status_code == 409

    async def test_register_weak_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Weak",
                "email": "weak@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Bad Email",
                "email": "not-an-email",
                "password": "ValidPass123",
            },
        )
        assert response.status_code == 422

    async def test_register_missing_fields(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={})
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(self, client: AsyncClient, test_session: AsyncSession):
        await create_test_user(test_session, email="login@example.com", password="LoginPass1")
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "LoginPass1",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_session: AsyncSession):
        await create_test_user(test_session, email="wrongpw@example.com", password="RightPass1")
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrongpw@example.com",
                "password": "WrongPass1",
            },
        )
        assert response.status_code == 401

    async def test_login_nonexistent_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "ghost@example.com",
                "password": "SomePass123",
            },
        )
        assert response.status_code == 401
        # Should not reveal whether email exists
        assert "not found" not in response.json()["detail"].lower()

    async def test_login_inactive_user(self, client: AsyncClient, test_session: AsyncSession):
        await create_test_user(
            test_session,
            email="inactive@example.com",
            password="InactiveP1",
            is_active=False,
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "InactiveP1",
            },
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestAuthMe:
    async def test_get_me_success(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="me@example.com")
        headers = make_auth_header(user.id)
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == "me@example.com"

    async def test_get_me_no_token(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code in (401, 403)

    async def test_get_me_invalid_token(self, client: AsyncClient):
        headers = {"Authorization": "Bearer invalid-token"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

    async def test_get_me_expired_token(self, client: AsyncClient, test_session: AsyncSession):
        user = await create_test_user(test_session, email="expired@example.com")
        token = create_access_token(subject=str(user.id), expires_delta=timedelta(seconds=-1))
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

    async def test_password_hash_never_in_response(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        user = await create_test_user(test_session, email="nohash@example.com")
        headers = make_auth_header(user.id)
        response = await client.get("/api/v1/auth/me", headers=headers)
        body = response.text
        assert "password_hash" not in body
        assert "password" not in body.lower() or '"password"' not in body
