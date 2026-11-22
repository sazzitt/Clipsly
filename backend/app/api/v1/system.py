from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.config import settings
from backend.app.core.database import check_db_connection
from backend.app.schemas.system import (
    SettingUpdateRequest,
    SettingsListResponse,
    SystemHardwareTelemetry,
    SystemHealthResponse,
    SystemInfoResponse,
)
from backend.app.services.system import (
    check_cuda_available,
    check_nvenc_available,
    get_all_settings,
    get_hardware_telemetry,
    get_system_info,
    get_uptime_seconds,
    set_setting,
)

router = APIRouter(prefix="/system", tags=["System"])


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    description="Verifies backend availability, SQLite WAL database connectivity, and hardware acceleration status."
)
async def get_system_health() -> SystemHealthResponse:
    """Returns the operational status of the backend, database, and hardware encoders."""
    db_ok = await check_db_connection()
    cuda_ok = check_cuda_available()
    nvenc_ok = check_nvenc_available()

    health_status = "healthy" if db_ok else "degraded"

    return SystemHealthResponse(
        status=health_status,
        version=settings.VERSION,
        database_connected=db_ok,
        cuda_available=cuda_ok,
        nvenc_available=nvenc_ok,
        active_jobs_count=0,
        uptime_seconds=get_uptime_seconds(),
    )


@router.get(
    "/info",
    response_model=SystemInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Host System Information",
    description="Returns platform operating system, processor, GPU hardware, and FFmpeg version specifications."
)
async def get_system_information() -> SystemInfoResponse:
    """Returns host specifications and detected software runtime versions."""
    return get_system_info()


@router.get(
    "/hardware",
    response_model=SystemHardwareTelemetry,
    status_code=status.HTTP_200_OK,
    summary="Hardware Telemetry Diagnostics",
    description="Real-time GPU VRAM, compute utilization, physical RAM, and SSD storage measurements."
)
async def get_system_hardware() -> SystemHardwareTelemetry:
    """Returns real-time telemetry from nvidia-smi and system memory status."""
    return get_hardware_telemetry()


@router.get(
    "/settings",
    response_model=SettingsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Settings",
    description="Retrieves all user and pipeline preferences from application_settings."
)
async def get_application_settings(
    db: AsyncSession = Depends(get_database)
) -> SettingsListResponse:
    """Returns current key-value preferences stored in the database."""
    settings_dict = await get_all_settings(db)
    return SettingsListResponse(settings=settings_dict)


@router.patch(
    "/settings",
    status_code=status.HTTP_200_OK,
    summary="Update Application Setting",
    description="Updates or sets an individual key-value preference."
)
async def update_application_setting(
    payload: SettingUpdateRequest,
    db: AsyncSession = Depends(get_database)
):
    """Updates a single setting key and persists the change to SQLite."""
    res = await set_setting(
        session=db,
        key=payload.key,
        value=payload.value,
        category=payload.category or "GENERAL",
        description=payload.description
    )
    return {"success": True, "setting": res}
