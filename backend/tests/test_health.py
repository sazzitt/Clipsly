import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Verifies that the root path returns basic application metadata."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["application"] == "Clipsly"
    assert data["version"] == "1.0.0"
    assert "health" in data


@pytest.mark.asyncio
async def test_system_health_endpoint(async_client: AsyncClient):
    """Verifies that GET /api/v1/system/health returns 200 OK and valid health telemetry."""
    response = await async_client.get("/api/v1/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["version"] == "1.0.0"
    assert data["database_connected"] is True
    assert isinstance(data["cuda_available"], bool)
    assert isinstance(data["nvenc_available"], bool)
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["active_jobs_count"] == 0
