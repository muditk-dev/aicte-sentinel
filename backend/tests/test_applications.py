import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_applications_tenant_scoped(client: AsyncClient, seed_test_data):
    # Log in as institution admin
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "inst@apex.edu.in", "password": "College@2026!"},
    )
    token = login_res.json()["access_token"]

    response = await client.get(
        "/api/v1/applications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    apps = response.json()
    assert len(apps) >= 1
    assert apps[0]["institution_id"] == "inst-test-uuid-1"


@pytest.mark.asyncio
async def test_valid_statutory_transition(client: AsyncClient, seed_test_data):
    # Scrutiny officer logs in
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "scrutiny@aicte-india.org", "password": "Scrutiny@2026!"},
    )
    token = login_res.json()["access_token"]

    # Transition from SUBMITTED -> UNDER_SCRUTINY
    app_id = seed_test_data["application"].id
    response = await client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "target_status": "UNDER_SCRUTINY",
            "remarks": "Assigned to desk, document scrutiny initiated.",
        },
    )
    assert response.status_code == 200
    updated_app = response.json()
    assert updated_app["current_status"] == "UNDER_SCRUTINY"
    # Event logged
    assert any(e["to_status"] == "UNDER_SCRUTINY" for e in updated_app["events"])


@pytest.mark.asyncio
async def test_invalid_statutory_transition_blocked(client: AsyncClient, seed_test_data):
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "scrutiny@aicte-india.org", "password": "Scrutiny@2026!"},
    )
    token = login_res.json()["access_token"]

    # Cannot transition SUBMITTED directly to APPROVED (skips scrutiny and committee)
    app_id = seed_test_data["application"].id
    response = await client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "target_status": "APPROVED",
            "remarks": "Bypass attempt.",
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "INVALID_WORKFLOW_TRANSITION"
