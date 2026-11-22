import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app


@pytest.mark.asyncio
async def test_correlation_id_generated(async_client: AsyncClient):
    """Verifies that an X-Request-ID is automatically generated when omitted."""
    response = await async_client.get("/api/v1/system/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


@pytest.mark.asyncio
async def test_correlation_id_propagated(async_client: AsyncClient):
    """Verifies that an incoming X-Request-ID is preserved and reflected in the response."""
    custom_id = "test-custom-request-id-12345"
    response = await async_client.get("/api/v1/system/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == custom_id


@pytest.mark.asyncio
async def test_request_timing_header(async_client: AsyncClient):
    """Verifies that X-Process-Time-Ms is measured and returned in response headers."""
    response = await async_client.get("/api/v1/system/health")
    assert response.status_code == 200
    assert "x-process-time-ms" in response.headers
    time_ms = float(response.headers["x-process-time-ms"])
    assert time_ms >= 0.0


@pytest.mark.asyncio
async def test_localhost_security_blocks_external_host():
    """Verifies that requests with an unauthorized Host header are rejected with 403."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        response = await client.get("/api/v1/system/health", headers={"Host": "external-attacker.com"})
        assert response.status_code == 403
        data = response.json()
        assert data["error_code"] == "FORBIDDEN_HOST"
