import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.enums import UserRole
from app.services.bootstrap import ensure_default_admin


@pytest.fixture
async def client():
    await ensure_default_admin()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_register_rejects_admin_role(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newadmin@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_admin_login_with_default_credentials(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/admin/login",
        json={"email": "admin@hiremenow.com", "password": "password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_regular_login_rejects_admin(client: AsyncClient):
    await client.post(
        "/api/v1/auth/admin/login",
        json={"email": "admin@hiremenow.com", "password": "password"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@hiremenow.com", "password": "password"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_login_rejects_non_admin(client: AsyncClient):
    email = "clientonly@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "role": UserRole.client.value,
            "company_name": "Acme",
        },
    )
    response = await client.post(
        "/api/v1/auth/admin/login",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 403
