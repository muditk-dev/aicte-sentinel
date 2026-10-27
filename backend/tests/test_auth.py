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


@pytest.mark.asyncio
async def test_bootstrap_initial_admin_flow(client: AsyncClient):
    """
    Verifies that when zero users exist:
    1. bootstrap/status reports bootstrap_available = True.
    2. POST /auth/bootstrap succeeds and creates the Super Admin.
    3. Subsequent POST /auth/bootstrap is locked and returns 409 Conflict.
    4. bootstrap/status reports bootstrap_available = False.
    """
    # 1. Status check on empty db
    status_res = await client.get("/api/v1/auth/bootstrap/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["bootstrap_available"] is True
    assert status_data["total_users"] == 0

    # 2. Bootstrap initial admin
    payload = {
        "email": "lead.admin@aicte-sentinel.gov.in",
        "password": "StrongPassword2026!",
        "full_name": "Chief Evaluator",
        "designation": "Central Council Member Secretary",
    }
    bootstrap_res = await client.post("/api/v1/auth/bootstrap", json=payload)
    assert bootstrap_res.status_code == 201
    b_data = bootstrap_res.json()
    assert "access_token" in b_data
    assert b_data["user"]["email"] == "lead.admin@aicte-sentinel.gov.in"
    assert b_data["user"]["roles"][0]["code"] == "SUPER_ADMIN"
    admin_token = b_data["access_token"]

    # 3. Subsequent bootstrap attempt must fail with 409 Conflict
    dup_res = await client.post("/api/v1/auth/bootstrap", json=payload)
    assert dup_res.status_code == 409
    assert dup_res.json()["code"] == "STATE_CONFLICT"

    # 4. Status check now reports locked
    status_after = await client.get("/api/v1/auth/bootstrap/status")
    assert status_after.status_code == 200
    assert status_after.json()["bootstrap_available"] is False
    assert status_after.json()["total_users"] == 1

    # 5. Super Admin can provision a new officer
    prov_payload = {
        "email": "ro.west@aicte.gov.in",
        "password": "RegionalSecure123!",
        "full_name": "Dr. Western Officer",
        "role_code": "REGIONAL_OFFICER",
        "designation": "Regional Director",
        "assigned_region": "Western",
    }
    prov_res = await client.post(
        "/api/v1/auth/provision-user",
        json=prov_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert prov_res.status_code == 201
    prov_data = prov_res.json()
    assert prov_data["email"] == "ro.west@aicte.gov.in"
    assert prov_data["roles"][0]["code"] == "REGIONAL_OFFICER"

    # 6. Unauthenticated attempt to provision user is rejected with 401
    unauth_prov = await client.post("/api/v1/auth/provision-user", json=prov_payload)
    assert unauth_prov.status_code == 401

