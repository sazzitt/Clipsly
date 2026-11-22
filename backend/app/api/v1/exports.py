from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.exceptions import NotFoundError, NotImplementedFeatureError
from backend.app.models.export_job import ExportJob
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/exports", tags=["Exports"])


def _serialize_export(e: ExportJob) -> Dict[str, Any]:
    return {
        "id": e.id,
        "clip_id": e.clip_id,
        "video_id": e.video_id,
        "output_filename": e.output_filename,
        "output_path": e.output_path,
        "resolution": e.resolution,
        "fps": e.fps,
        "encoder": e.encoder,
        "render_time_seconds": e.render_time_seconds,
        "file_size_bytes": e.file_size_bytes,
        "status": e.status,
        "progress_percent": e.progress_percent,
        "error_message": e.error_message,
        "process_pid": e.process_pid,
        "started_at": e.started_at.isoformat() if e.started_at else None,
        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get(
    "",
    response_model=PaginatedResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Export Jobs",
    description="Retrieves a paginated list of render and export jobs."
)
async def list_exports(
    clip_id: Optional[str] = Query(None, description="Filter by Clip UUID"),
    video_id: Optional[str] = Query(None, description="Filter by Video UUID"),
    export_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_database)
):
    """Lists export jobs from the database."""
    offset = (page - 1) * limit
    filters = []
    if clip_id:
        filters.append(ExportJob.clip_id == clip_id)
    if video_id:
        filters.append(ExportJob.video_id == video_id)
    if export_status:
        filters.append(ExportJob.status == export_status)

    count_stmt = select(func.count(ExportJob.id)).where(*filters)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = select(ExportJob).where(*filters).order_by(ExportJob.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    exports = result.scalars().all()

    items = [_serialize_export(e) for e in exports]
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{export_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Export Job Details",
    description="Retrieves render progress and output metadata for an export job."
)
async def get_export(
    export_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Retrieves single export job by ID."""
    stmt = select(ExportJob).where(ExportJob.id == export_id)
    result = await db.execute(stmt)
    e = result.scalar_one_or_none()

    if not e:
        raise NotFoundError(f"Export job with id '{export_id}' was not found.")

    return _serialize_export(e)


@router.post(
    "",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Trigger Export Rendering",
    description="Queues NVIDIA NVENC hardware-accelerated 9:16 video render (activates in Phase 16)."
)
async def trigger_export():
    """Placeholder endpoint for video export rendering. Activates in Phase 16."""
    raise NotImplementedFeatureError("NVIDIA NVENC hardware-accelerated export rendering pipeline activates in Phase 16.")
