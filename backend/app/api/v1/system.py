from fastapi import APIRouter, status
from backend.app.core.config import settings
from backend.app.core.database import check_db_connection
from backend.app.schemas.system import SystemHealthResponse
from backend.app.services.system import (
    check_cuda_available,
    check_nvenc_available,
    get_uptime_seconds,
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
