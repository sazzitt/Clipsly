from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_database
from backend.app.core.exceptions import ConflictError, NotFoundError, NotImplementedFeatureError
from backend.app.models.processing_job import ProcessingJob
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/jobs", tags=["Processing Jobs"])


@router.get(
    "",
    response_model=PaginatedResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Processing Jobs",
    description="Returns a paginated list of background processing jobs with optional filtering and search."
)
async def list_jobs(
    video_id: Optional[str] = Query(None, description="Filter jobs by video UUID"),
    job_status: Optional[str] = Query(None, alias="status", description="Filter jobs by status"),
    job_type: Optional[str] = Query(None, description="Filter jobs by job type"),
    search: Optional[str] = Query(None, description="Search jobs by current step, error message, or job type"),
    sort_by: str = Query("created_at", description="Field to sort by: created_at, updated_at, progress_percent, status"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_database)
):
    """Lists processing jobs from the database with filtering and search."""
    offset = (page - 1) * limit
    filters = []

    if video_id:
        filters.append(ProcessingJob.video_id == video_id)
    if job_status and job_status.strip() and job_status.upper() != "ALL":
        filters.append(ProcessingJob.status == job_status.strip().upper())
    if job_type and job_type.strip() and job_type.upper() != "ALL":
        filters.append(ProcessingJob.job_type == job_type.strip().upper())
    if search:
        search_term = f"%{search.strip()}%"
        filters.append(
            or_(
                ProcessingJob.current_step.ilike(search_term),
                ProcessingJob.error_message.ilike(search_term),
                ProcessingJob.job_type.ilike(search_term),
                ProcessingJob.id.ilike(search_term),
            )
        )

    count_stmt = select(func.count(ProcessingJob.id)).where(*filters)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    sort_mapping = {
        "created_at": ProcessingJob.created_at,
        "updated_at": ProcessingJob.updated_at,
        "progress_percent": ProcessingJob.progress_percent,
        "status": ProcessingJob.status,
        "job_type": ProcessingJob.job_type,
    }
    sort_column = sort_mapping.get(sort_by, ProcessingJob.created_at)
    order_clause = sort_column.asc() if order.lower() == "asc" else sort_column.desc()

    stmt = (
        select(ProcessingJob)
        .where(*filters)
        .order_by(order_clause)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    items = [
        {
            "id": j.id,
            "video_id": j.video_id,
            "job_type": j.job_type,
            "status": j.status,
            "progress_percent": j.progress_percent,
            "current_step": j.current_step,
            "error_message": j.error_message,
            "process_pid": j.process_pid,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "updated_at": j.updated_at.isoformat() if j.updated_at else None,
        }
        for j in jobs
    ]

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Job Details",
    description="Retrieves status, progress, and telemetry for an individual processing job."
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Retrieves single processing job details by UUID."""
    stmt = select(ProcessingJob).where(ProcessingJob.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise NotFoundError(f"Processing job with id '{job_id}' was not found.")

    return {
        "id": job.id,
        "video_id": job.video_id,
        "job_type": job.job_type,
        "status": job.status,
        "progress_percent": job.progress_percent,
        "current_step": job.current_step,
        "error_message": job.error_message,
        "process_pid": job.process_pid,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.post(
    "/{job_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel Processing Job",
    description="Cancels an active or queued background job."
)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_database)
):
    """Cancels a queued or running job."""
    stmt = select(ProcessingJob).where(ProcessingJob.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise NotFoundError(f"Processing job with id '{job_id}' was not found.")

    if job.status in ("COMPLETED", "FAILED", "CANCELLED"):
        raise ConflictError(f"Job '{job_id}' is already in terminal state '{job.status}' and cannot be cancelled.")

    from backend.app.services.queue import job_queue
    await job_queue.cancel_job(job_id, db)
    await db.refresh(job)

    return {
        "id": job.id,
        "status": job.status,
        "current_step": job.current_step,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.post(
    "/{job_id}/retry",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Retry Processing Job",
    description="Retries a failed background job (activates in Phase 13)."
)
async def retry_job(job_id: str):
    """Placeholder endpoint for retrying jobs. Activates in Phase 13."""
    raise NotImplementedFeatureError("Job execution and retry orchestration pipeline activates in Phase 13.")
