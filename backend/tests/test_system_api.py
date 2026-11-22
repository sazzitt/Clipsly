import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_system_info_endpoint(async_client: AsyncClient):
    """Verifies that GET /api/v1/system/info returns accurate platform and software metadata."""
    response = await async_client.get("/api/v1/system/info")
    assert response.status_code == 200
    data = response.json()
    assert "os" in data
    assert "cpu" in data
    assert "gpu" in data
    assert "python_version" in data
    assert "ffmpeg_version" in data


@pytest.mark.asyncio
async def test_system_hardware_endpoint(async_client: AsyncClient):
    """Verifies that GET /api/v1/system/hardware returns real-time hardware telemetry."""
    response = await async_client.get("/api/v1/system/hardware")
    assert response.status_code == 200
    data = response.json()
    assert "ssd_free_space_gb" in data
    assert "system_ram_total_gb" in data
    assert data["ssd_free_space_gb"] > 0
    # On this laptop, RTX 3050 should report VRAM or None if not queried
    assert "gpu_vram_total_mb" in data


@pytest.mark.asyncio
async def test_system_settings_get_and_patch(async_client: AsyncClient):
    """Verifies retrieval and dynamic updating of system settings."""
    # 1. GET settings
    get_res = await async_client.get("/api/v1/system/settings")
    assert get_res.status_code == 200
    data = get_res.json()
    assert "settings" in data
    assert isinstance(data["settings"], dict)
    assert len(data["settings"]) > 0

    # 2. PATCH an existing setting (e.g. transcription.default_model)
    patch_res = await async_client.patch(
        "/api/v1/system/settings",
        json={"key": "transcription.default_model", "value": "small"}
    )
    assert patch_res.status_code == 200
    res_data = patch_res.json()
    assert res_data["success"] is True
    assert res_data["setting"]["key"] == "transcription.default_model"
    assert res_data["setting"]["value"] == "small"
