from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
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
    description="Returns a paginated list of background processing jobs with optional filtering."
)
async def list_jobs(
    video_id: Optional[str] = Query(None, description="Filter jobs by video UUID"),
    job_status: Optional[str] = Query(None, alias="status", description="Filter jobs by status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_database)
):
    """Lists processing jobs from the database."""
    offset = (page - 1) * limit
    base_filter = []
    if video_id:
        base_filter.append(ProcessingJob.video_id == video_id)
    if job_status:
        base_filter.append(ProcessingJob.status == job_status)

    count_stmt = select(func.count(ProcessingJob.id)).where(*base_filter)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = (
        select(ProcessingJob)
        .where(*base_filter)
        .order_by(ProcessingJob.created_at.desc())
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

    job.status = "CANCELLED"
    job.current_step = "Cancelled by user"
    job.completed_at = datetime.utcnow()
    await db.commit()
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
