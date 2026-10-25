import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, seed_test_data):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@aicte-india.org", "password": "Sentinel@Admin2026!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert data["user"]["email"] == "superadmin@aicte-india.org"
    assert data["user"]["roles"][0]["code"] == "SUPER_ADMIN"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, seed_test_data):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@aicte-india.org", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_get_my_profile_authenticated(client: AsyncClient, seed_test_data):
    # Login first
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "inst@apex.edu.in", "password": "College@2026!"},
    )
    token = login_res.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "inst@apex.edu.in"
    assert data["institution_id"] == "inst-test-uuid-1"
    assert data["roles"][0]["code"] == "INSTITUTION_ADMIN"
