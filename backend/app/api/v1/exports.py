import os
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.exceptions import NotFoundError, NotImplementedFeatureError
from backend.app.models.clip import Clip
from backend.app.models.export_job import ExportJob
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/exports", tags=["Exports"])


def _serialize_export(e: ExportJob, clip_title: Optional[str] = None) -> Dict[str, Any]:
    file_exists = os.path.exists(e.output_path) if e.output_path else False
    return {
        "id": e.id,
        "clip_id": e.clip_id,
        "clip_title": clip_title,
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
        "file_exists": file_exists,
        "started_at": e.started_at.isoformat() if e.started_at else None,
        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get(
    "",
    response_model=PaginatedResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Export Jobs",
    description="Retrieves a paginated list of render and export jobs with search, filtering, and sorting."
)
async def list_exports(
    clip_id: Optional[str] = Query(None, description="Filter by Clip UUID"),
    video_id: Optional[str] = Query(None, description="Filter by Video UUID"),
    export_status: Optional[str] = Query(None, alias="status", description="Filter by status (e.g. PENDING, RENDERING, COMPLETED, FAILED)"),
    search: Optional[str] = Query(None, description="Search exports by output filename"),
    sort_by: str = Query("created_at", description="Field to sort by: created_at, output_filename, file_size_bytes, render_time_seconds, status"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_database)
):
    """Lists export jobs from the database with filtering and sorting."""
    offset = (page - 1) * limit
    filters = []

    if clip_id:
        filters.append(ExportJob.clip_id == clip_id)
    if video_id:
        filters.append(ExportJob.video_id == video_id)
    if export_status and export_status.strip() and export_status.upper() != "ALL":
        filters.append(ExportJob.status == export_status.strip().upper())
    if search:
        filters.append(ExportJob.output_filename.ilike(f"%{search.strip()}%"))

    count_stmt = select(func.count(ExportJob.id)).where(*filters)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    sort_mapping = {
        "created_at": ExportJob.created_at,
        "output_filename": ExportJob.output_filename,
        "file_size_bytes": ExportJob.file_size_bytes,
        "render_time_seconds": ExportJob.render_time_seconds,
        "status": ExportJob.status,
    }
    sort_column = sort_mapping.get(sort_by, ExportJob.created_at)
    order_clause = sort_column.asc() if order.lower() == "asc" else sort_column.desc()

    stmt = (
        select(ExportJob, Clip.title)
        .outerjoin(Clip, ExportJob.clip_id == Clip.id)
        .where(*filters)
        .order_by(order_clause)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = [_serialize_export(e, clip_title=c_title) for e, c_title in rows]
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
    stmt = (
        select(ExportJob, Clip.title)
        .outerjoin(Clip, ExportJob.clip_id == Clip.id)
        .where(ExportJob.id == export_id)
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise NotFoundError(f"Export job with id '{export_id}' was not found.")

    e, c_title = row
    return _serialize_export(e, clip_title=c_title)


@router.delete(
    "/{export_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Export Record",
    description="Deletes an export record from the database with optional disk file cleanup."
)
async def delete_export(
    export_id: str,
    delete_file: bool = Query(False, description="Also delete rendered video file from disk if present"),
    db: AsyncSession = Depends(get_database)
):
    """Deletes an export record, respecting the export retention lifecycle."""
    stmt = select(ExportJob).where(ExportJob.id == export_id)
    result = await db.execute(stmt)
    export_job = result.scalar_one_or_none()

    if not export_job:
        raise NotFoundError(f"Export record with id '{export_id}' was not found.")

    file_unlinked = False
    if delete_file and export_job.output_path:
        try:
            if os.path.exists(export_job.output_path):
                os.remove(export_job.output_path)
                file_unlinked = True
        except OSError:
            pass

    await db.delete(export_job)
    await db.commit()
    return {"success": True, "id": export_id, "file_unlinked": file_unlinked}


@router.post(
    "",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Trigger Export Rendering",
    description="Queues NVIDIA NVENC hardware-accelerated 9:16 video render (activates in Phase 16)."
)
async def trigger_export():
    """Placeholder endpoint for video export rendering. Activates in Phase 16."""
    raise NotImplementedFeatureError("NVIDIA NVENC hardware-accelerated export rendering pipeline activates in Phase 16.")
