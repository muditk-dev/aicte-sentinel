import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_audit_verification_empty(client: AsyncClient, seed_test_data):
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@aicte-india.org", "password": "Sentinel@Admin2026!"},
    )
    token = login_res.json()["access_token"]

    response = await client.get(
        "/api/v1/audit/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True


@pytest.mark.asyncio
async def test_audit_events_logged_and_verified(client: AsyncClient, seed_test_data):
    # Log in as admin
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@aicte-india.org", "password": "Sentinel@Admin2026!"},
    )
    token = login_res.json()["access_token"]

    # Verify cryptographic integrity
    verify_res = await client.get(
        "/api/v1/audit/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["is_valid"] is True
    # At least the login event should be recorded in audit log
    assert verify_data["total_events_checked"] >= 1
    assert verify_data["chain_head_hash"] is not None
