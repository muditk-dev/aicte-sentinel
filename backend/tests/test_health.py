import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["service"] == "AICTE Sentinel"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_probe(client: AsyncClient):
    response = await client.get("/api/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["dependencies"]["database"]["healthy"] is True
