import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_not_found_error_envelope(async_client: AsyncClient):
    """Verifies that 404 responses conform to the dual-format error envelope."""
    response = await async_client.get("/api/v1/videos/nonexistent-uuid-1234")
    assert response.status_code == 404
    data = response.json()

    # FastAPI standard properties
    assert "error_code" in data
    assert data["error_code"] == "RESOURCE_NOT_FOUND"
    assert "detail" in data

    # Documented nested error object (docs/05-API.md)
    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "message" in data["error"]


@pytest.mark.asyncio
async def test_validation_error_envelope(async_client: AsyncClient):
    """Verifies that Pydantic 422 validation errors conform to standard envelope."""
    # Send invalid type for page query param (string instead of int)
    response = await async_client.get("/api/v1/videos?page=not-a-number")
    assert response.status_code == 422
    data = response.json()

    assert data["error_code"] == "VALIDATION_ERROR"
    assert "detail" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["details"] is not None


@pytest.mark.asyncio
async def test_not_implemented_error_envelope(async_client: AsyncClient):
    """Verifies that 501 responses return informative messages specifying activation phase."""
    response = await async_client.post("/api/v1/transcripts/transcribe")
    assert response.status_code == 501
    data = response.json()

    assert data["error_code"] == "NOT_IMPLEMENTED"
    assert "Phase 13" in data["detail"]
    assert data["error"]["code"] == "NOT_IMPLEMENTED"
